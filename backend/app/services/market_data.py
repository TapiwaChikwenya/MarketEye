"""
Multi-provider market data service with resilience patterns.

Architecture:
- Multiple data providers (Finnhub, yfinance, Alpha Vantage, CoinGecko, CoinCap)
  arranged in fallback chains per asset class.
- CircuitBreaker per provider prevents wasting time on failing providers.
- Redis-backed cache with stale-while-revalidate semantics ensures callers
  almost always get data, even during provider outages.
- All blocking I/O is offloaded via asyncio.to_thread; the event loop is
  never blocked.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional

import requests
import yfinance as yf

from app.models.asset import AssetType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy settings accessor (avoids import-time pydantic validation in tests)
# ---------------------------------------------------------------------------
_settings = None


def _get_settings():
    global _settings
    if _settings is None:
        from app.core.config import settings
        _settings = settings
    return _settings


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Per-provider circuit breaker (closed -> open -> half-open -> closed)."""

    def __init__(self, name: str, max_failures: int = 5, reset_timeout: int = 60):
        self.name = name
        self._max_failures = max_failures
        self._reset_timeout = reset_timeout
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._state = "closed"  # closed | open | half-open

    @property
    def is_open(self) -> bool:
        if self._state == "closed":
            return False
        if self._state == "open":
            if time.time() - self._last_failure_time >= self._reset_timeout:
                self._state = "half-open"
                return False
            return True
        return False  # half-open allows one probe

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._max_failures:
            self._state = "open"
            logger.warning(
                "CircuitBreaker OPEN for %s after %d failures",
                self.name,
                self._failure_count,
            )


# ---------------------------------------------------------------------------
# Redis-backed cache with stale-while-revalidate
# ---------------------------------------------------------------------------

_redis_client = None
_fallback_cache: Dict[str, tuple] = {}  # in-memory fallback if Redis unavailable


def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis as redis_lib
            settings = _get_settings()
            _redis_client = redis_lib.Redis.from_url(
                settings.REDIS_URL, decode_responses=True, socket_timeout=2
            )
            _redis_client.ping()
        except Exception:
            logger.warning("Redis unavailable for market data cache, using in-memory fallback")
            _redis_client = False  # sentinel: tried and failed
    return _redis_client if _redis_client is not False else None


def _cache_key(prefix: str, symbol: str) -> str:
    return f"marketeye:price:{prefix}:{symbol.upper()}"


def get_cached(key: str) -> Optional[Dict[str, Any]]:
    """Return cached data if within fresh TTL."""
    settings = _get_settings()
    fresh_ttl = settings.CACHE_FRESH_TTL_SECONDS

    r = _get_redis()
    if r:
        try:
            raw = r.get(key)
            if raw:
                entry = json.loads(raw)
                age = time.time() - entry["ts"]
                if age < fresh_ttl:
                    return entry["data"]
        except Exception:
            pass

    if key in _fallback_cache:
        data, ts = _fallback_cache[key]
        if time.time() - ts < fresh_ttl:
            return data
    return None


def get_stale(key: str) -> Optional[Dict[str, Any]]:
    """Return cached data even if past fresh TTL but within stale TTL."""
    settings = _get_settings()
    stale_ttl = settings.CACHE_STALE_TTL_SECONDS

    r = _get_redis()
    if r:
        try:
            raw = r.get(key)
            if raw:
                entry = json.loads(raw)
                age = time.time() - entry["ts"]
                if age < stale_ttl:
                    return entry["data"]
        except Exception:
            pass

    if key in _fallback_cache:
        data, ts = _fallback_cache[key]
        if time.time() - ts < stale_ttl:
            return data
    return None


def set_cached(key: str, data: Dict[str, Any]) -> None:
    """Store data in Redis (with stale TTL expiry) and in-memory fallback."""
    settings = _get_settings()
    stale_ttl = settings.CACHE_STALE_TTL_SECONDS

    entry = {"data": data, "ts": time.time()}
    _fallback_cache[key] = (data, entry["ts"])

    r = _get_redis()
    if r:
        try:
            r.setex(key, stale_ttl, json.dumps(entry))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Retry helper with exponential backoff + jitter
# ---------------------------------------------------------------------------

def _request_with_retry(
    method: str,
    url: str,
    *,
    params: Optional[dict] = None,
    timeout: int = 10,
    max_retries: int = 2,
) -> requests.Response:
    """HTTP request with retry on 429/5xx. Runs in a worker thread."""
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.request(method, url, params=params, timeout=timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < max_retries:
                    delay = (2 ** attempt) * 0.5 + random.uniform(0, 0.5)
                    time.sleep(delay)
                    continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError as exc:
            last_exc = exc
            if attempt < max_retries and (
                exc.response is not None
                and (exc.response.status_code == 429 or exc.response.status_code >= 500)
            ):
                delay = (2 ** attempt) * 0.5 + random.uniform(0, 0.5)
                time.sleep(delay)
                continue
            raise
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = (2 ** attempt) * 0.5 + random.uniform(0, 0.5)
                time.sleep(delay)
                continue
            raise
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Historical data helpers (interval/period to provider-specific formats)
# ---------------------------------------------------------------------------

def _interval_to_finnhub_resolution(interval: str) -> str:
    """Map yfinance-style interval strings to Finnhub resolution codes."""
    mapping = {
        "1m": "1", "5m": "5", "15m": "15", "30m": "30", "60m": "60",
        "1h": "60", "1d": "D", "1wk": "W", "1mo": "M",
    }
    return mapping.get(interval, "D")


def _period_to_timestamps(period: str) -> tuple:
    """Convert a yfinance-style period string to (from_unix, to_unix)."""
    now = int(time.time())
    seconds_map = {
        "1d": 86400,
        "5d": 5 * 86400,
        "1mo": 30 * 86400,
        "3mo": 90 * 86400,
        "6mo": 180 * 86400,
        "1y": 365 * 86400,
        "2y": 730 * 86400,
        "5y": 5 * 365 * 86400,
        "max": 20 * 365 * 86400,
    }
    delta = seconds_map.get(period, 30 * 86400)
    return (now - delta, now)


def _period_to_coingecko_days(period: str) -> str:
    """Convert a yfinance-style period string to CoinGecko `days` parameter."""
    mapping = {
        "1d": "1", "5d": "5", "1mo": "30", "3mo": "90",
        "6mo": "180", "1y": "365", "2y": "730", "max": "max",
    }
    return mapping.get(period, "30")


CRYPTO_SYMBOL_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LTC": "litecoin",
    "LINK": "chainlink",
    "UNI": "uniswap",
}


def _fetch_yahoo_chart_sync(
    symbol: str, period: str, interval: str
) -> Optional[List[Dict[str, Any]]]:
    """Fetch OHLCV data directly from Yahoo Finance v8 chart API (no auth needed)."""
    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"range": period, "interval": interval},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        result_data = data.get("chart", {}).get("result", [])
        if not result_data:
            return None

        entry = result_data[0]
        timestamps = entry.get("timestamp", [])
        quotes = entry.get("indicators", {}).get("quote", [{}])[0]
        if not timestamps or not quotes:
            return None

        opens = quotes.get("open", [])
        highs = quotes.get("high", [])
        lows = quotes.get("low", [])
        closes = quotes.get("close", [])
        volumes = quotes.get("volume", [])

        points = []
        for i, ts in enumerate(timestamps):
            c = closes[i] if i < len(closes) else None
            if c is None:
                continue
            points.append({
                "timestamp": datetime.fromtimestamp(ts, tz=UTC).isoformat(),
                "open": float(opens[i]) if i < len(opens) and opens[i] is not None else float(c),
                "high": float(highs[i]) if i < len(highs) and highs[i] is not None else float(c),
                "low": float(lows[i]) if i < len(lows) and lows[i] is not None else float(c),
                "close": float(c),
                "volume": float(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0.0,
            })
        return points if points else None
    except Exception as e:
        logger.debug("Yahoo chart API failed for %s: %s", symbol, e)
        return None


def _fetch_coingecko_history_sync(
    symbol: str, period: str, interval: str
) -> Optional[List[Dict[str, Any]]]:
    """Fetch historical price data from CoinGecko /coins/{id}/market_chart."""
    coin_id = CRYPTO_SYMBOL_MAP.get(symbol.upper())
    if not coin_id:
        try:
            resp = _request_with_retry(
                "GET",
                "https://api.coingecko.com/api/v3/search",
                params={"query": symbol},
                max_retries=1, timeout=5,
            )
            coins = resp.json().get("coins", [])
            if coins:
                coin_id = coins[0]["id"]
        except Exception:
            pass
    if not coin_id:
        return None

    days = _period_to_coingecko_days(period)
    try:
        resp = _request_with_retry(
            "GET",
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": days},
            timeout=10,
        )
        data = resp.json()
    except Exception:
        return None

    prices = data.get("prices", [])
    volumes = data.get("total_volumes", [])
    if not prices:
        return None

    vol_map = {int(v[0]): v[1] for v in volumes} if volumes else {}

    points = []
    for ts_ms, price in prices:
        ts_sec = int(ts_ms)
        points.append({
            "timestamp": datetime.fromtimestamp(ts_ms / 1000, tz=UTC).isoformat(),
            "open": float(price),
            "high": float(price),
            "low": float(price),
            "close": float(price),
            "volume": float(vol_map.get(ts_sec, 0)),
        })
    return points if points else None


# ---------------------------------------------------------------------------
# Provider base class
# ---------------------------------------------------------------------------

class MarketDataProvider(ABC):
    """Abstract base for a market data provider."""

    name: str = "base"

    @abstractmethod
    def fetch_quote_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Synchronous quote fetch (runs inside asyncio.to_thread)."""


# ---------------------------------------------------------------------------
# Finnhub provider (primary for stocks/ETFs)
# ---------------------------------------------------------------------------

class FinnhubProvider(MarketDataProvider):
    name = "finnhub"

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._base_url = "https://finnhub.io/api/v1"

    def fetch_quote_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        resp = _request_with_retry(
            "GET",
            f"{self._base_url}/quote",
            params={"symbol": symbol.upper(), "token": self._api_key},
        )
        data = resp.json()
        price = data.get("c")
        if not price or price == 0:
            return None
        prev_close = data.get("pc", 0)
        change = data.get("d")
        change_pct = data.get("dp")
        return {
            "symbol": symbol.upper(),
            "current_price": str(price),
            "market_cap": "",
            "volume_24h": "",
            "change_24h": str(change) if change is not None else None,
            "change_percent_24h": str(change_pct) if change_pct is not None else None,
            "last_updated": datetime.now(UTC).isoformat(),
            "name": symbol.upper(),
            "exchange": "Finnhub",
            "currency": "USD",
        }

    def fetch_profile_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch company profile for name/exchange enrichment."""
        try:
            resp = _request_with_retry(
                "GET",
                f"{self._base_url}/stock/profile2",
                params={"symbol": symbol.upper(), "token": self._api_key},
            )
            data = resp.json()
            if data.get("name"):
                return {"name": data["name"], "exchange": data.get("exchange", "")}
        except Exception:
            pass
        return None

    def fetch_candles_sync(
        self, symbol: str, period: str, interval: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch OHLCV candle data from Finnhub /stock/candle."""
        resolution = _interval_to_finnhub_resolution(interval)
        from_ts, to_ts = _period_to_timestamps(period)

        resp = _request_with_retry(
            "GET",
            f"{self._base_url}/stock/candle",
            params={
                "symbol": symbol.upper(),
                "resolution": resolution,
                "from": from_ts,
                "to": to_ts,
                "token": self._api_key,
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("s") != "ok" or not data.get("t"):
            return None

        points = []
        for i in range(len(data["t"])):
            points.append({
                "timestamp": datetime.fromtimestamp(data["t"][i], tz=UTC).isoformat(),
                "open": float(data["o"][i]),
                "high": float(data["h"][i]),
                "low": float(data["l"][i]),
                "close": float(data["c"][i]),
                "volume": float(data["v"][i]),
            })
        return points if points else None


# ---------------------------------------------------------------------------
# Alpha Vantage provider (tertiary for stocks)
# ---------------------------------------------------------------------------

class AlphaVantageProvider(MarketDataProvider):
    name = "alpha_vantage"

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._base_url = "https://www.alphavantage.co/query"

    def fetch_quote_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        resp = _request_with_retry(
            "GET",
            self._base_url,
            params={
                "function": "GLOBAL_QUOTE",
                "symbol": symbol.upper(),
                "apikey": self._api_key,
            },
        )
        data = resp.json()
        gq = data.get("Global Quote", {})
        price = gq.get("05. price")
        if not price:
            return None
        change = gq.get("09. change")
        change_pct_raw = gq.get("10. change percent", "")
        change_pct = change_pct_raw.replace("%", "") if change_pct_raw else None
        return {
            "symbol": symbol.upper(),
            "current_price": str(price),
            "market_cap": "",
            "volume_24h": str(gq.get("06. volume", "")),
            "change_24h": str(change) if change else None,
            "change_percent_24h": str(change_pct) if change_pct else None,
            "last_updated": datetime.now(UTC).isoformat(),
            "name": symbol.upper(),
            "exchange": "AlphaVantage",
            "currency": "USD",
        }

    def search_sync(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Use SYMBOL_SEARCH to find matching tickers (fast, reliable)."""
        try:
            resp = _request_with_retry(
                "GET",
                self._base_url,
                params={
                    "function": "SYMBOL_SEARCH",
                    "keywords": query,
                    "apikey": self._api_key,
                },
            )
            data = resp.json()
            results = []
            for match in data.get("bestMatches", [])[:limit]:
                sym = match.get("1. symbol", "")
                if not sym:
                    continue
                asset_type = match.get("3. type", "Equity")
                mapped_type = "ETF" if asset_type == "ETF" else "STOCK"
                results.append({
                    "symbol": sym,
                    "name": match.get("2. name", sym),
                    "asset_type": mapped_type,
                    "exchange": match.get("4. region", "US"),
                })
            return results
        except Exception:
            logger.debug("Alpha Vantage SYMBOL_SEARCH failed for %s", query)
            return []


# ---------------------------------------------------------------------------
# yfinance provider (secondary for stocks, primary for mutual funds & history)
# ---------------------------------------------------------------------------

_yfinance_semaphore = asyncio.Semaphore(1)
_yfinance_last_call: float = 0.0
_YF_MIN_INTERVAL = 1.0  # seconds between calls


class YFinanceProvider(MarketDataProvider):
    name = "yfinance"

    def fetch_quote_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        global _yfinance_last_call
        elapsed = time.time() - _yfinance_last_call
        if elapsed < _YF_MIN_INTERVAL:
            time.sleep(_YF_MIN_INTERVAL - elapsed)
        _yfinance_last_call = time.time()

        ticker = yf.Ticker(symbol)
        info = ticker.info

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not current_price:
            hist = ticker.history(period="1d")
            if not hist.empty:
                current_price = hist["Close"].iloc[-1]

        previous_close = info.get("previousClose")
        change_24h = None
        change_percent_24h = None
        if current_price and previous_close:
            change_24h = current_price - previous_close
            change_percent_24h = (change_24h / previous_close) * 100

        result = {
            "symbol": symbol.upper(),
            "current_price": str(current_price) if current_price else None,
            "market_cap": str(info.get("marketCap", "")),
            "volume_24h": str(info.get("volume", "")),
            "change_24h": str(change_24h) if change_24h else None,
            "change_percent_24h": str(change_percent_24h) if change_percent_24h else None,
            "last_updated": datetime.now(UTC).isoformat(),
            "name": info.get("longName") or info.get("shortName") or symbol.upper(),
            "exchange": info.get("exchange", ""),
            "currency": info.get("currency", "USD"),
        }
        return result if result.get("current_price") else None

    @staticmethod
    def fetch_mutual_fund_sync(symbol: str) -> Optional[Dict[str, Any]]:
        global _yfinance_last_call
        elapsed = time.time() - _yfinance_last_call
        if elapsed < _YF_MIN_INTERVAL:
            time.sleep(_YF_MIN_INTERVAL - elapsed)
        _yfinance_last_call = time.time()

        ticker = yf.Ticker(symbol)
        info = ticker.info

        current_price = (
            info.get("navPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
        )
        if not current_price:
            hist = ticker.history(period="5d")
            if not hist.empty:
                current_price = hist["Close"].iloc[-1]

        previous_close = info.get("previousClose")
        change_24h = None
        change_percent_24h = None
        if current_price and previous_close:
            change_24h = current_price - previous_close
            change_percent_24h = (change_24h / previous_close) * 100

        result = {
            "symbol": symbol.upper(),
            "current_price": str(current_price) if current_price else None,
            "market_cap": str(info.get("totalAssets", "")),
            "volume_24h": str(info.get("volume", "")),
            "change_24h": str(change_24h) if change_24h else None,
            "change_percent_24h": str(change_percent_24h) if change_percent_24h else None,
            "last_updated": datetime.now(UTC).isoformat(),
            "name": info.get("longName") or info.get("shortName") or symbol,
            "exchange": info.get("exchange", "Mutual Fund"),
            "currency": info.get("currency", "USD"),
            "asset_type": "MUTUAL_FUND",
            "expense_ratio": str(info.get("annualReportExpenseRatio", "")),
            "category": info.get("category", ""),
            "fund_family": info.get("fundFamily", ""),
        }
        return result if result.get("current_price") else None

    @staticmethod
    def fetch_history_sync(
        yf_symbol: str, period: str, interval: str
    ) -> Optional[List[Dict[str, Any]]]:
        global _yfinance_last_call
        elapsed = time.time() - _yfinance_last_call
        if elapsed < _YF_MIN_INTERVAL:
            time.sleep(_YF_MIN_INTERVAL - elapsed)
        _yfinance_last_call = time.time()

        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            return None
        data_points = []
        for index, row in hist.iterrows():
            data_points.append(
                {
                    "timestamp": index.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                }
            )
        return data_points

    @staticmethod
    def detect_asset_type(info: Dict) -> str:
        quote_type = info.get("quoteType", "").upper()
        if quote_type == "ETF":
            return "ETF"
        elif quote_type == "MUTUALFUND":
            return "MUTUAL_FUND"
        elif quote_type == "INDEX":
            return "INDEX"
        elif quote_type == "CRYPTOCURRENCY":
            return "CRYPTO"
        return "STOCK"


# ---------------------------------------------------------------------------
# CoinGecko provider (primary for crypto)
# ---------------------------------------------------------------------------

_coingecko_semaphore = asyncio.Semaphore(5)


class CoinGeckoProvider(MarketDataProvider):
    name = "coingecko"

    def __init__(self):
        self._base_url = "https://api.coingecko.com/api/v3"

    def fetch_quote_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        coin_id = CRYPTO_SYMBOL_MAP.get(symbol.upper())
        if not coin_id:
            coin_id = self._search_sync(symbol)
        if not coin_id:
            return None
        return self._fetch_coin_sync(coin_id, symbol)

    def _search_sync(self, symbol: str) -> Optional[str]:
        try:
            resp = _request_with_retry(
                "GET", f"{self._base_url}/search", params={"query": symbol}
            )
            data = resp.json()
            if data.get("coins"):
                return data["coins"][0]["id"]
        except Exception:
            pass
        return None

    def _fetch_coin_sync(self, coin_id: str, original_symbol: str) -> Optional[Dict[str, Any]]:
        resp = _request_with_retry(
            "GET",
            f"{self._base_url}/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
            },
        )
        data = resp.json()
        if "market_data" not in data:
            return None

        md = data["market_data"]
        current_price = md["current_price"].get("usd")
        change_24h = md.get("price_change_24h")
        change_pct = md.get("price_change_percentage_24h")

        return {
            "symbol": original_symbol.upper(),
            "current_price": str(current_price) if current_price else None,
            "market_cap": str(md.get("market_cap", {}).get("usd", "")),
            "volume_24h": str(md.get("total_volume", {}).get("usd", "")),
            "change_24h": str(change_24h) if change_24h is not None else None,
            "change_percent_24h": str(change_pct) if change_pct is not None else None,
            "last_updated": datetime.now(UTC).isoformat(),
            "name": data.get("name"),
            "exchange": "CoinGecko",
            "currency": "USD",
        }


# ---------------------------------------------------------------------------
# CoinCap provider (fallback for crypto)
# ---------------------------------------------------------------------------

COINCAP_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "BNB": "binance-coin",
    "SOL": "solana",
    "XRP": "xrp",
    "ADA": "cardano",
    "AVAX": "avalanche",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LTC": "litecoin",
    "LINK": "chainlink",
    "UNI": "uniswap",
}


# ---------------------------------------------------------------------------
# Static stock database for instant search (no API call needed)
# ---------------------------------------------------------------------------

STOCK_TICKER_DB: List[Dict[str, str]] = [
    {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
    {"symbol": "GOOGL", "name": "Alphabet Inc. (Class A)", "exchange": "NASDAQ"},
    {"symbol": "GOOG", "name": "Alphabet Inc. (Class C)", "exchange": "NASDAQ"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ"},
    {"symbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ"},
    {"symbol": "BRK.B", "name": "Berkshire Hathaway Inc. (Class B)", "exchange": "NYSE"},
    {"symbol": "BRK.A", "name": "Berkshire Hathaway Inc. (Class A)", "exchange": "NYSE"},
    {"symbol": "UNH", "name": "UnitedHealth Group Inc.", "exchange": "NYSE"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "exchange": "NYSE"},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE"},
    {"symbol": "V", "name": "Visa Inc.", "exchange": "NYSE"},
    {"symbol": "XOM", "name": "Exxon Mobil Corporation", "exchange": "NYSE"},
    {"symbol": "PG", "name": "Procter & Gamble Co.", "exchange": "NYSE"},
    {"symbol": "MA", "name": "Mastercard Inc.", "exchange": "NYSE"},
    {"symbol": "HD", "name": "Home Depot Inc.", "exchange": "NYSE"},
    {"symbol": "LLY", "name": "Eli Lilly and Company", "exchange": "NYSE"},
    {"symbol": "CVX", "name": "Chevron Corporation", "exchange": "NYSE"},
    {"symbol": "MRK", "name": "Merck & Co. Inc.", "exchange": "NYSE"},
    {"symbol": "ABBV", "name": "AbbVie Inc.", "exchange": "NYSE"},
    {"symbol": "PEP", "name": "PepsiCo Inc.", "exchange": "NASDAQ"},
    {"symbol": "KO", "name": "Coca-Cola Company", "exchange": "NYSE"},
    {"symbol": "AVGO", "name": "Broadcom Inc.", "exchange": "NASDAQ"},
    {"symbol": "COST", "name": "Costco Wholesale Corporation", "exchange": "NASDAQ"},
    {"symbol": "TMO", "name": "Thermo Fisher Scientific Inc.", "exchange": "NYSE"},
    {"symbol": "WMT", "name": "Walmart Inc.", "exchange": "NYSE"},
    {"symbol": "MCD", "name": "McDonald's Corporation", "exchange": "NYSE"},
    {"symbol": "CSCO", "name": "Cisco Systems Inc.", "exchange": "NASDAQ"},
    {"symbol": "CRM", "name": "Salesforce Inc.", "exchange": "NYSE"},
    {"symbol": "ABT", "name": "Abbott Laboratories", "exchange": "NYSE"},
    {"symbol": "ACN", "name": "Accenture plc", "exchange": "NYSE"},
    {"symbol": "BAC", "name": "Bank of America Corp.", "exchange": "NYSE"},
    {"symbol": "CMCSA", "name": "Comcast Corporation", "exchange": "NASDAQ"},
    {"symbol": "ADBE", "name": "Adobe Inc.", "exchange": "NASDAQ"},
    {"symbol": "TXN", "name": "Texas Instruments Inc.", "exchange": "NASDAQ"},
    {"symbol": "NKE", "name": "Nike Inc.", "exchange": "NYSE"},
    {"symbol": "NFLX", "name": "Netflix Inc.", "exchange": "NASDAQ"},
    {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "exchange": "NASDAQ"},
    {"symbol": "INTC", "name": "Intel Corporation", "exchange": "NASDAQ"},
    {"symbol": "WFC", "name": "Wells Fargo & Company", "exchange": "NYSE"},
    {"symbol": "PM", "name": "Philip Morris International", "exchange": "NYSE"},
    {"symbol": "LIN", "name": "Linde plc", "exchange": "NYSE"},
    {"symbol": "DHR", "name": "Danaher Corporation", "exchange": "NYSE"},
    {"symbol": "UPS", "name": "United Parcel Service Inc.", "exchange": "NYSE"},
    {"symbol": "QCOM", "name": "Qualcomm Inc.", "exchange": "NASDAQ"},
    {"symbol": "RTX", "name": "RTX Corporation", "exchange": "NYSE"},
    {"symbol": "LOW", "name": "Lowe's Companies Inc.", "exchange": "NYSE"},
    {"symbol": "SPGI", "name": "S&P Global Inc.", "exchange": "NYSE"},
    {"symbol": "NEE", "name": "NextEra Energy Inc.", "exchange": "NYSE"},
    {"symbol": "INTU", "name": "Intuit Inc.", "exchange": "NASDAQ"},
    {"symbol": "HON", "name": "Honeywell International Inc.", "exchange": "NASDAQ"},
    {"symbol": "GE", "name": "GE Aerospace", "exchange": "NYSE"},
    {"symbol": "AMAT", "name": "Applied Materials Inc.", "exchange": "NASDAQ"},
    {"symbol": "CAT", "name": "Caterpillar Inc.", "exchange": "NYSE"},
    {"symbol": "BKNG", "name": "Booking Holdings Inc.", "exchange": "NASDAQ"},
    {"symbol": "AXP", "name": "American Express Company", "exchange": "NYSE"},
    {"symbol": "GS", "name": "Goldman Sachs Group Inc.", "exchange": "NYSE"},
    {"symbol": "MDLZ", "name": "Mondelez International Inc.", "exchange": "NASDAQ"},
    {"symbol": "SYK", "name": "Stryker Corporation", "exchange": "NYSE"},
    {"symbol": "BLK", "name": "BlackRock Inc.", "exchange": "NYSE"},
    {"symbol": "PLD", "name": "Prologis Inc.", "exchange": "NYSE"},
    {"symbol": "ISRG", "name": "Intuitive Surgical Inc.", "exchange": "NASDAQ"},
    {"symbol": "ADI", "name": "Analog Devices Inc.", "exchange": "NASDAQ"},
    {"symbol": "GILD", "name": "Gilead Sciences Inc.", "exchange": "NASDAQ"},
    {"symbol": "VRTX", "name": "Vertex Pharmaceuticals Inc.", "exchange": "NASDAQ"},
    {"symbol": "AMGN", "name": "Amgen Inc.", "exchange": "NASDAQ"},
    {"symbol": "REGN", "name": "Regeneron Pharmaceuticals Inc.", "exchange": "NASDAQ"},
    {"symbol": "T", "name": "AT&T Inc.", "exchange": "NYSE"},
    {"symbol": "TMUS", "name": "T-Mobile US Inc.", "exchange": "NASDAQ"},
    {"symbol": "PANW", "name": "Palo Alto Networks Inc.", "exchange": "NASDAQ"},
    {"symbol": "NOW", "name": "ServiceNow Inc.", "exchange": "NYSE"},
    {"symbol": "LRCX", "name": "Lam Research Corporation", "exchange": "NASDAQ"},
    {"symbol": "MU", "name": "Micron Technology Inc.", "exchange": "NASDAQ"},
    {"symbol": "SNPS", "name": "Synopsys Inc.", "exchange": "NASDAQ"},
    {"symbol": "CDNS", "name": "Cadence Design Systems Inc.", "exchange": "NASDAQ"},
    {"symbol": "KLAC", "name": "KLA Corporation", "exchange": "NASDAQ"},
    {"symbol": "MRVL", "name": "Marvell Technology Inc.", "exchange": "NASDAQ"},
    {"symbol": "UBER", "name": "Uber Technologies Inc.", "exchange": "NYSE"},
    {"symbol": "ABNB", "name": "Airbnb Inc.", "exchange": "NASDAQ"},
    {"symbol": "CRWD", "name": "CrowdStrike Holdings Inc.", "exchange": "NASDAQ"},
    {"symbol": "SNOW", "name": "Snowflake Inc.", "exchange": "NYSE"},
    {"symbol": "SQ", "name": "Block Inc.", "exchange": "NYSE"},
    {"symbol": "SHOP", "name": "Shopify Inc.", "exchange": "NYSE"},
    {"symbol": "COIN", "name": "Coinbase Global Inc.", "exchange": "NASDAQ"},
    {"symbol": "PLTR", "name": "Palantir Technologies Inc.", "exchange": "NYSE"},
    {"symbol": "RIVN", "name": "Rivian Automotive Inc.", "exchange": "NASDAQ"},
    {"symbol": "LCID", "name": "Lucid Group Inc.", "exchange": "NASDAQ"},
    {"symbol": "PYPL", "name": "PayPal Holdings Inc.", "exchange": "NASDAQ"},
    {"symbol": "DIS", "name": "Walt Disney Company", "exchange": "NYSE"},
    {"symbol": "PFE", "name": "Pfizer Inc.", "exchange": "NYSE"},
    {"symbol": "BMY", "name": "Bristol-Myers Squibb Company", "exchange": "NYSE"},
    {"symbol": "MRNA", "name": "Moderna Inc.", "exchange": "NASDAQ"},
    {"symbol": "C", "name": "Citigroup Inc.", "exchange": "NYSE"},
    {"symbol": "MS", "name": "Morgan Stanley", "exchange": "NYSE"},
    {"symbol": "SCHW", "name": "Charles Schwab Corporation", "exchange": "NYSE"},
    {"symbol": "USB", "name": "U.S. Bancorp", "exchange": "NYSE"},
    {"symbol": "PNC", "name": "PNC Financial Services Group", "exchange": "NYSE"},
    {"symbol": "TFC", "name": "Truist Financial Corporation", "exchange": "NYSE"},
    {"symbol": "GS", "name": "Goldman Sachs Group Inc.", "exchange": "NYSE"},
    {"symbol": "CB", "name": "Chubb Limited", "exchange": "NYSE"},
    {"symbol": "MMC", "name": "Marsh & McLennan Companies", "exchange": "NYSE"},
    {"symbol": "SO", "name": "Southern Company", "exchange": "NYSE"},
    {"symbol": "DUK", "name": "Duke Energy Corporation", "exchange": "NYSE"},
    {"symbol": "CL", "name": "Colgate-Palmolive Company", "exchange": "NYSE"},
    {"symbol": "ZTS", "name": "Zoetis Inc.", "exchange": "NYSE"},
    {"symbol": "CME", "name": "CME Group Inc.", "exchange": "NASDAQ"},
    {"symbol": "DE", "name": "Deere & Company", "exchange": "NYSE"},
    {"symbol": "MMM", "name": "3M Company", "exchange": "NYSE"},
    {"symbol": "BA", "name": "Boeing Company", "exchange": "NYSE"},
    {"symbol": "LMT", "name": "Lockheed Martin Corporation", "exchange": "NYSE"},
    {"symbol": "NOC", "name": "Northrop Grumman Corporation", "exchange": "NYSE"},
    {"symbol": "GD", "name": "General Dynamics Corporation", "exchange": "NYSE"},
    {"symbol": "F", "name": "Ford Motor Company", "exchange": "NYSE"},
    {"symbol": "GM", "name": "General Motors Company", "exchange": "NYSE"},
    {"symbol": "SBUX", "name": "Starbucks Corporation", "exchange": "NASDAQ"},
    {"symbol": "TGT", "name": "Target Corporation", "exchange": "NYSE"},
    {"symbol": "CVS", "name": "CVS Health Corporation", "exchange": "NYSE"},
    {"symbol": "CI", "name": "Cigna Group", "exchange": "NYSE"},
    {"symbol": "ELV", "name": "Elevance Health Inc.", "exchange": "NYSE"},
    {"symbol": "HUM", "name": "Humana Inc.", "exchange": "NYSE"},
    {"symbol": "COP", "name": "ConocoPhillips", "exchange": "NYSE"},
    {"symbol": "SLB", "name": "Schlumberger Limited", "exchange": "NYSE"},
    {"symbol": "EOG", "name": "EOG Resources Inc.", "exchange": "NYSE"},
    {"symbol": "MPC", "name": "Marathon Petroleum Corporation", "exchange": "NYSE"},
    {"symbol": "VLO", "name": "Valero Energy Corporation", "exchange": "NYSE"},
    {"symbol": "PSX", "name": "Phillips 66", "exchange": "NYSE"},
    {"symbol": "FDX", "name": "FedEx Corporation", "exchange": "NYSE"},
    {"symbol": "DAL", "name": "Delta Air Lines Inc.", "exchange": "NYSE"},
    {"symbol": "UAL", "name": "United Airlines Holdings Inc.", "exchange": "NASDAQ"},
    {"symbol": "AAL", "name": "American Airlines Group Inc.", "exchange": "NASDAQ"},
    {"symbol": "LUV", "name": "Southwest Airlines Co.", "exchange": "NYSE"},
    {"symbol": "ORCL", "name": "Oracle Corporation", "exchange": "NYSE"},
    {"symbol": "IBM", "name": "International Business Machines", "exchange": "NYSE"},
    {"symbol": "DELL", "name": "Dell Technologies Inc.", "exchange": "NYSE"},
    {"symbol": "HPQ", "name": "HP Inc.", "exchange": "NYSE"},
    {"symbol": "ROKU", "name": "Roku Inc.", "exchange": "NASDAQ"},
    {"symbol": "ZM", "name": "Zoom Video Communications", "exchange": "NASDAQ"},
    {"symbol": "SNAP", "name": "Snap Inc.", "exchange": "NYSE"},
    {"symbol": "PINS", "name": "Pinterest Inc.", "exchange": "NYSE"},
    {"symbol": "SPOT", "name": "Spotify Technology S.A.", "exchange": "NYSE"},
    {"symbol": "SQ", "name": "Block Inc.", "exchange": "NYSE"},
    {"symbol": "MELI", "name": "MercadoLibre Inc.", "exchange": "NASDAQ"},
    {"symbol": "SE", "name": "Sea Limited", "exchange": "NYSE"},
    {"symbol": "NET", "name": "Cloudflare Inc.", "exchange": "NYSE"},
    {"symbol": "DDOG", "name": "Datadog Inc.", "exchange": "NASDAQ"},
    {"symbol": "ZS", "name": "Zscaler Inc.", "exchange": "NASDAQ"},
    {"symbol": "FTNT", "name": "Fortinet Inc.", "exchange": "NASDAQ"},
    {"symbol": "WDAY", "name": "Workday Inc.", "exchange": "NASDAQ"},
    {"symbol": "TEAM", "name": "Atlassian Corporation", "exchange": "NASDAQ"},
    {"symbol": "TTD", "name": "Trade Desk Inc.", "exchange": "NASDAQ"},
    {"symbol": "DASH", "name": "DoorDash Inc.", "exchange": "NASDAQ"},
    {"symbol": "RBLX", "name": "Roblox Corporation", "exchange": "NYSE"},
    {"symbol": "U", "name": "Unity Software Inc.", "exchange": "NYSE"},
    {"symbol": "PATH", "name": "UiPath Inc.", "exchange": "NYSE"},
    {"symbol": "SMCI", "name": "Super Micro Computer Inc.", "exchange": "NASDAQ"},
    {"symbol": "ARM", "name": "Arm Holdings plc", "exchange": "NASDAQ"},
    {"symbol": "ON", "name": "ON Semiconductor Corporation", "exchange": "NASDAQ"},
    {"symbol": "ENPH", "name": "Enphase Energy Inc.", "exchange": "NASDAQ"},
    {"symbol": "SEDG", "name": "SolarEdge Technologies Inc.", "exchange": "NASDAQ"},
    {"symbol": "FSLR", "name": "First Solar Inc.", "exchange": "NASDAQ"},
]

_STOCK_SYMBOL_INDEX: Dict[str, Dict[str, str]] = {
    s["symbol"].upper(): s for s in STOCK_TICKER_DB
}

_STOCK_NAME_WORDS: Dict[str, List[Dict[str, str]]] = {}
for _stock in STOCK_TICKER_DB:
    for _word in _stock["name"].lower().split():
        _STOCK_NAME_WORDS.setdefault(_word, []).append(_stock)


def _search_static_stocks(query: str) -> List[Dict[str, str]]:
    """Fast in-memory search of the static stock database."""
    q_upper = query.strip().upper()
    q_lower = query.strip().lower()

    exact = _STOCK_SYMBOL_INDEX.get(q_upper)
    if exact:
        return [exact]

    results: List[Dict[str, str]] = []
    seen: set = set()

    for sym, stock in _STOCK_SYMBOL_INDEX.items():
        if q_upper in sym and sym not in seen:
            results.append(stock)
            seen.add(sym)

    for stock in STOCK_TICKER_DB:
        if q_lower in stock["name"].lower() and stock["symbol"] not in seen:
            results.append(stock)
            seen.add(stock["symbol"])

    return results[:15]


class CoinCapProvider(MarketDataProvider):
    name = "coincap"

    def __init__(self):
        self._base_url = "https://api.coincap.io/v2"

    def fetch_quote_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        asset_id = COINCAP_ID_MAP.get(symbol.upper())
        if not asset_id:
            asset_id = self._search_sync(symbol)
        if not asset_id:
            return None
        return self._fetch_asset_sync(asset_id, symbol)

    def _search_sync(self, symbol: str) -> Optional[str]:
        try:
            resp = _request_with_retry(
                "GET",
                f"{self._base_url}/assets",
                params={"search": symbol, "limit": 1},
            )
            data = resp.json().get("data", [])
            if data:
                return data[0]["id"]
        except Exception:
            pass
        return None

    def _fetch_asset_sync(self, asset_id: str, original_symbol: str) -> Optional[Dict[str, Any]]:
        resp = _request_with_retry("GET", f"{self._base_url}/assets/{asset_id}")
        entry = resp.json().get("data")
        if not entry:
            return None
        price = entry.get("priceUsd")
        if not price:
            return None
        change_pct = entry.get("changePercent24Hr")
        return {
            "symbol": original_symbol.upper(),
            "current_price": str(round(float(price), 2)),
            "market_cap": str(entry.get("marketCapUsd", "")),
            "volume_24h": str(entry.get("volumeUsd24Hr", "")),
            "change_24h": None,
            "change_percent_24h": str(round(float(change_pct), 5)) if change_pct else None,
            "last_updated": datetime.now(UTC).isoformat(),
            "name": entry.get("name", original_symbol.upper()),
            "exchange": "CoinCap",
            "currency": "USD",
        }


# ---------------------------------------------------------------------------
# Provider Registry – fallback chain + circuit breakers + cache
# ---------------------------------------------------------------------------

class ProviderRegistry:
    """Manages ordered provider chains with circuit breakers and caching."""

    def __init__(
        self,
        stock_chain: List[MarketDataProvider],
        crypto_chain: List[MarketDataProvider],
        cb_threshold: int = 5,
        cb_timeout: int = 60,
    ):
        self.stock_chain = stock_chain
        self.crypto_chain = crypto_chain
        self._breakers: Dict[str, CircuitBreaker] = {}
        for p in stock_chain + crypto_chain:
            if p.name not in self._breakers:
                self._breakers[p.name] = CircuitBreaker(
                    p.name, max_failures=cb_threshold, reset_timeout=cb_timeout
                )

    def _get_breaker(self, provider: MarketDataProvider) -> CircuitBreaker:
        return self._breakers[provider.name]

    async def get_quote(
        self, symbol: str, asset_type: str
    ) -> Optional[Dict[str, Any]]:
        """Try providers in order; return first success or stale cache."""
        cache_prefix = "crypto" if asset_type == "CRYPTO" else "stock"
        key = _cache_key(cache_prefix, symbol)

        fresh = get_cached(key)
        if fresh:
            return fresh

        chain = self.crypto_chain if asset_type == "CRYPTO" else self.stock_chain
        semaphore = _coingecko_semaphore if asset_type == "CRYPTO" else _yfinance_semaphore

        for provider in chain:
            cb = self._get_breaker(provider)
            if cb.is_open:
                logger.debug("Skipping %s (circuit open)", provider.name)
                continue
            try:
                if provider.name == "yfinance":
                    async with _yfinance_semaphore:
                        result = await asyncio.to_thread(provider.fetch_quote_sync, symbol)
                elif provider.name in ("coingecko", "coincap"):
                    async with _coingecko_semaphore:
                        result = await asyncio.to_thread(provider.fetch_quote_sync, symbol)
                else:
                    result = await asyncio.to_thread(provider.fetch_quote_sync, symbol)

                if result and result.get("current_price"):
                    cb.record_success()
                    set_cached(key, result)
                    return result
                else:
                    cb.record_failure()
            except Exception as exc:
                cb.record_failure()
                logger.warning(
                    "Provider %s failed for %s: %s", provider.name, symbol, exc
                )

        stale = get_stale(key)
        if stale:
            logger.info("Returning stale cache for %s", symbol)
            return stale

        return None


# ---------------------------------------------------------------------------
# Postgres price_history read/write helpers
# ---------------------------------------------------------------------------

def _period_to_date_range(period: str) -> tuple:
    """Convert a period string to (from_date, to_date) as date objects."""
    from datetime import date as _date
    today = _date.today()
    days_map = {
        "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
        "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "max": 7300,
    }
    delta = days_map.get(period, 30)
    return (today - timedelta(days=delta), today)


def _expected_trading_days(
    from_date, to_date, asset_type: AssetType
) -> int:
    """Estimate how many data points we should have for a date range."""
    total_days = (to_date - from_date).days
    if asset_type == AssetType.CRYPTO:
        return total_days
    return int(total_days * 5 / 7)


async def _query_price_history(
    symbol: str, from_date, to_date
) -> List[Dict[str, Any]]:
    """Read daily OHLCV from price_history table."""
    try:
        from sqlalchemy import select
        from app.db.base import AsyncSessionLocal
        from app.models.price_history import PriceHistory

        async with AsyncSessionLocal() as session:
            stmt = (
                select(PriceHistory)
                .where(
                    PriceHistory.symbol == symbol.upper(),
                    PriceHistory.date >= from_date,
                    PriceHistory.date <= to_date,
                )
                .order_by(PriceHistory.date)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        return [
            {
                "timestamp": r.date.isoformat(),
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": float(r.volume) if r.volume else 0.0,
            }
            for r in rows
        ]
    except Exception as e:
        logger.debug("price_history query failed for %s: %s", symbol, e)
        return []


async def _store_history_points(
    symbol: str, asset_type: AssetType, points: List[Dict[str, Any]]
) -> None:
    """Background task: store API-fetched daily points into price_history."""
    try:
        from decimal import Decimal, InvalidOperation
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from app.db.base import AsyncSessionLocal
        from app.models.price_history import PriceHistory

        rows = []
        seen: set = set()
        for pt in points:
            try:
                ts = pt["timestamp"]
                if "T" in ts:
                    dt = datetime.fromisoformat(ts)
                else:
                    dt = datetime.strptime(ts, "%Y-%m-%d")
                d = dt.date()
            except (KeyError, ValueError):
                continue
            if d in seen:
                continue
            seen.add(d)

            def _dec(v):
                try:
                    return Decimal(str(v))
                except (InvalidOperation, TypeError, ValueError):
                    return Decimal("0")

            rows.append({
                "symbol": symbol.upper(),
                "asset_type": asset_type.value,
                "date": d,
                "open": _dec(pt["open"]),
                "high": _dec(pt["high"]),
                "low": _dec(pt["low"]),
                "close": _dec(pt["close"]),
                "volume": _dec(pt.get("volume", 0)),
            })

        if not rows:
            return

        async with AsyncSessionLocal() as session:
            stmt = pg_insert(PriceHistory).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_symbol_date",
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                },
            )
            await session.execute(stmt)
            await session.commit()
    except Exception as e:
        logger.debug("Failed to store history for %s: %s", symbol, e)


# ---------------------------------------------------------------------------
# MarketDataService – preserves the public API surface
# ---------------------------------------------------------------------------

class MarketDataService:
    """Service for fetching market data from multiple providers with fallback."""

    def __init__(self):
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        self._registry: Optional[ProviderRegistry] = None
        self._yfinance_provider = YFinanceProvider()
        self._coingecko_provider = CoinGeckoProvider()

    def _ensure_registry(self) -> ProviderRegistry:
        if self._registry is not None:
            return self._registry

        settings = _get_settings()

        stock_chain: List[MarketDataProvider] = []
        if settings.FINNHUB_API_KEY:
            stock_chain.append(FinnhubProvider(settings.FINNHUB_API_KEY))
        stock_chain.append(self._yfinance_provider)
        if settings.ALPHA_VANTAGE_API_KEY:
            stock_chain.append(AlphaVantageProvider(settings.ALPHA_VANTAGE_API_KEY))

        crypto_chain: List[MarketDataProvider] = [self._coingecko_provider]
        if settings.COINCAP_ENABLED:
            crypto_chain.append(CoinCapProvider())

        self._registry = ProviderRegistry(
            stock_chain=stock_chain,
            crypto_chain=crypto_chain,
            cb_threshold=settings.PROVIDER_CIRCUIT_BREAKER_THRESHOLD,
            cb_timeout=settings.PROVIDER_CIRCUIT_BREAKER_TIMEOUT,
        )
        return self._registry

    # ------------------------------------------------------------------
    # Public async API (unchanged signatures)
    # ------------------------------------------------------------------

    async def get_stock_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current stock price via provider fallback chain."""
        registry = self._ensure_registry()
        return await registry.get_quote(symbol, "STOCK")

    async def get_crypto_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current crypto price via provider fallback chain."""
        registry = self._ensure_registry()
        return await registry.get_quote(symbol, "CRYPTO")

    async def get_asset_price(
        self, symbol: str, asset_type: AssetType
    ) -> Optional[Dict[str, Any]]:
        """Get asset price based on asset type."""
        if asset_type == AssetType.CRYPTO:
            return await self.get_crypto_price(symbol)
        return await self.get_stock_price(symbol)

    async def get_mutual_fund_price(
        self, symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Get mutual fund data (yfinance only, serialized)."""
        key = _cache_key("fund", symbol)
        cached = get_cached(key)
        if cached:
            return cached

        try:
            async with _yfinance_semaphore:
                result = await asyncio.to_thread(
                    YFinanceProvider.fetch_mutual_fund_sync, symbol
                )
            if result:
                set_cached(key, result)
            return result
        except Exception as e:
            logger.error("Error fetching mutual fund price for %s: %s", symbol, e)
            stale = get_stale(key)
            if stale:
                return stale
            return None

    async def get_etf_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ETF data via stock chain."""
        result = await self.get_stock_price(symbol)
        if result:
            result["asset_type"] = "ETF"
        return result

    async def get_historical_data(
        self,
        symbol: str,
        asset_type: AssetType,
        period: str = "1mo",
        interval: str = "1d",
    ) -> Optional[List[Dict[str, Any]]]:
        """Get historical price data.

        For daily+ intervals: reads from Postgres price_history first, falls
        back to external APIs only when local data is insufficient.
        For intraday intervals (5m, 15m, 30m, 1h): fetches on-demand from
        APIs with Redis caching (not stored in DB).
        """
        is_intraday = interval in ("1m", "5m", "15m", "30m", "60m", "1h")

        if is_intraday:
            return await self._fetch_history_from_apis(symbol, asset_type, period, interval)

        from_date, to_date = _period_to_date_range(period)

        db_points = await _query_price_history(symbol, from_date, to_date)

        trading_days_expected = _expected_trading_days(from_date, to_date, asset_type)
        has_enough = len(db_points) >= max(1, int(trading_days_expected * 0.7))

        if has_enough:
            return db_points

        api_points = await self._fetch_history_from_apis(
            symbol, asset_type, period, interval
        )

        if api_points:
            asyncio.create_task(
                _store_history_points(symbol, asset_type, api_points)
            )

        return api_points or db_points or None

    async def _fetch_history_from_apis(
        self,
        symbol: str,
        asset_type: AssetType,
        period: str,
        interval: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch historical data from external APIs with Redis caching."""
        cache_key = _cache_key("history", f"{symbol}:{period}:{interval}")
        cached = get_cached(cache_key)
        if cached:
            return cached

        result: Optional[List[Dict[str, Any]]] = None

        if asset_type == AssetType.CRYPTO:
            try:
                async with _coingecko_semaphore:
                    result = await asyncio.to_thread(
                        _fetch_coingecko_history_sync, symbol, period, interval
                    )
            except Exception as e:
                logger.debug("CoinGecko history failed for %s: %s", symbol, e)

        if result is None:
            chart_symbol = f"{symbol}-USD" if asset_type == AssetType.CRYPTO else symbol
            try:
                result = await asyncio.to_thread(
                    _fetch_yahoo_chart_sync, chart_symbol, period, interval
                )
            except Exception as e:
                logger.debug("Yahoo chart API failed for %s: %s", symbol, e)

        if result is None:
            try:
                yf_symbol = f"{symbol}-USD" if asset_type == AssetType.CRYPTO else symbol
                async with _yfinance_semaphore:
                    result = await asyncio.to_thread(
                        YFinanceProvider.fetch_history_sync, yf_symbol, period, interval
                    )
            except Exception as e:
                logger.debug("yfinance history failed for %s: %s", symbol, e)

        if result is None:
            stale = get_stale(cache_key)
            if stale:
                return stale
            return None

        set_cached(cache_key, result)
        return result

    async def search_assets(
        self, query: str, asset_type: Optional[AssetType] = None
    ) -> List[Dict[str, Any]]:
        """Search for assets by query. Uses static DBs first, then API searches in parallel."""
        results: List[Dict[str, Any]] = []
        seen_symbols: set = set()

        def _add(item: Dict[str, Any]) -> None:
            sym = item.get("symbol", "").upper()
            if sym and sym not in seen_symbols:
                seen_symbols.add(sym)
                results.append(item)

        search_crypto = asset_type in (AssetType.CRYPTO, None)
        search_stocks = asset_type != AssetType.CRYPTO

        if search_stocks:
            for stock in _search_static_stocks(query):
                _add({
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "asset_type": "STOCK",
                    "exchange": stock["exchange"],
                })

        async_tasks = []

        if search_stocks:
            settings = _get_settings()
            if settings.FINNHUB_API_KEY:
                async_tasks.append(self._search_finnhub(query, settings.FINNHUB_API_KEY))
            if settings.ALPHA_VANTAGE_API_KEY:
                async_tasks.append(self._search_alpha_vantage(query, settings.ALPHA_VANTAGE_API_KEY))

        if search_crypto:
            async_tasks.append(self._search_coingecko(query))

        if async_tasks:
            api_results = await asyncio.gather(*async_tasks, return_exceptions=True)
            for batch in api_results:
                if isinstance(batch, Exception):
                    logger.debug("Search task failed: %s", batch)
                    continue
                for item in batch:
                    _add(item)

        self._rank_results(results, query)
        return results[:20]

    @staticmethod
    async def _search_finnhub(query: str, api_key: str) -> List[Dict[str, Any]]:
        try:
            resp_data = await asyncio.to_thread(
                lambda: _request_with_retry(
                    "GET",
                    "https://finnhub.io/api/v1/search",
                    params={"q": query.upper(), "token": api_key},
                    max_retries=1,
                    timeout=5,
                ).json()
            )
            results = []
            for item in resp_data.get("result", [])[:8]:
                sym = item.get("symbol", "")
                if sym:
                    results.append({
                        "symbol": sym,
                        "name": item.get("description", sym),
                        "asset_type": "STOCK",
                        "exchange": item.get("type", ""),
                    })
            return results
        except Exception:
            return []

    @staticmethod
    async def _search_alpha_vantage(query: str, api_key: str) -> List[Dict[str, Any]]:
        try:
            provider = AlphaVantageProvider(api_key)
            return await asyncio.to_thread(provider.search_sync, query, 8)
        except Exception:
            return []

    @staticmethod
    async def _search_coingecko(query: str) -> List[Dict[str, Any]]:
        try:
            async with _coingecko_semaphore:
                search_data = await asyncio.to_thread(
                    lambda: _request_with_retry(
                        "GET",
                        "https://api.coingecko.com/api/v3/search",
                        params={"query": query},
                        max_retries=1,
                        timeout=5,
                    ).json()
                )
            results = []
            for coin in search_data.get("coins", [])[:10]:
                results.append({
                    "symbol": coin.get("symbol", "").upper(),
                    "name": coin.get("name"),
                    "asset_type": "CRYPTO",
                    "exchange": "CoinGecko",
                })
            return results
        except Exception:
            return []

    @staticmethod
    def _rank_results(results: List[Dict[str, Any]], query: str) -> None:
        """Sort results: exact symbol match first, stocks/ETFs over crypto wrappers."""
        q_upper = query.strip().upper()

        _TOKENIZED_SUFFIXES = {"xstock", "tokenized", "wrapped", "dinari", "ondo"}

        def _sort_key(item: Dict[str, Any]) -> tuple:
            sym = item.get("symbol", "").upper()
            name_lower = (item.get("name") or "").lower()
            asset_type = item.get("asset_type", "")

            is_exact_symbol = 0 if sym == q_upper else 1

            is_tokenized = 1 if any(t in name_lower for t in _TOKENIZED_SUFFIXES) else 0

            type_rank = {"STOCK": 0, "ETF": 1, "MUTUAL_FUND": 2, "CRYPTO": 3}.get(asset_type, 4)

            return (is_exact_symbol, is_tokenized, type_rank)

        results.sort(key=_sort_key)

    async def search_funds(self, query: str) -> List[Dict[str, Any]]:
        """Search for mutual funds and ETFs from static database."""
        results: List[Dict[str, Any]] = []

        fidelity_funds = [
            {"symbol": "FXAIX", "name": "Fidelity 500 Index Fund", "type": "MUTUAL_FUND"},
            {"symbol": "FSKAX", "name": "Fidelity Total Market Index Fund", "type": "MUTUAL_FUND"},
            {"symbol": "FZROX", "name": "Fidelity ZERO Total Market Index Fund", "type": "MUTUAL_FUND"},
            {"symbol": "FZILX", "name": "Fidelity ZERO International Index Fund", "type": "MUTUAL_FUND"},
            {"symbol": "FXNAX", "name": "Fidelity U.S. Bond Index Fund", "type": "MUTUAL_FUND"},
            {"symbol": "FTBFX", "name": "Fidelity Total Bond Fund", "type": "MUTUAL_FUND"},
            {"symbol": "FBALX", "name": "Fidelity Balanced Fund", "type": "MUTUAL_FUND"},
            {"symbol": "FCNTX", "name": "Fidelity Contrafund", "type": "MUTUAL_FUND"},
            {"symbol": "FDGRX", "name": "Fidelity Growth Company Fund", "type": "MUTUAL_FUND"},
            {"symbol": "FBGRX", "name": "Fidelity Blue Chip Growth Fund", "type": "MUTUAL_FUND"},
            {"symbol": "FMAGX", "name": "Fidelity Magellan Fund", "type": "MUTUAL_FUND"},
            {"symbol": "FOCPX", "name": "Fidelity OTC Portfolio", "type": "MUTUAL_FUND"},
            {"symbol": "FSPTX", "name": "Fidelity Select Technology", "type": "MUTUAL_FUND"},
            {"symbol": "FSHOX", "name": "Fidelity Select Construction & Housing", "type": "MUTUAL_FUND"},
        ]
        vanguard_funds = [
            {"symbol": "VFIAX", "name": "Vanguard 500 Index Fund Admiral", "type": "MUTUAL_FUND"},
            {"symbol": "VTSAX", "name": "Vanguard Total Stock Market Index Fund", "type": "MUTUAL_FUND"},
            {"symbol": "VBTLX", "name": "Vanguard Total Bond Market Index Fund", "type": "MUTUAL_FUND"},
            {"symbol": "VTIAX", "name": "Vanguard Total International Stock Index", "type": "MUTUAL_FUND"},
            {"symbol": "VWELX", "name": "Vanguard Wellington Fund", "type": "MUTUAL_FUND"},
        ]
        etfs = [
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "type": "ETF"},
            {"symbol": "VOO", "name": "Vanguard S&P 500 ETF", "type": "ETF"},
            {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF", "type": "ETF"},
            {"symbol": "QQQ", "name": "Invesco QQQ Trust", "type": "ETF"},
            {"symbol": "IWM", "name": "iShares Russell 2000 ETF", "type": "ETF"},
            {"symbol": "VEA", "name": "Vanguard FTSE Developed Markets ETF", "type": "ETF"},
            {"symbol": "VWO", "name": "Vanguard FTSE Emerging Markets ETF", "type": "ETF"},
            {"symbol": "BND", "name": "Vanguard Total Bond Market ETF", "type": "ETF"},
            {"symbol": "AGG", "name": "iShares Core U.S. Aggregate Bond ETF", "type": "ETF"},
            {"symbol": "GLD", "name": "SPDR Gold Shares", "type": "ETF"},
            {"symbol": "ARKK", "name": "ARK Innovation ETF", "type": "ETF"},
            {"symbol": "XLF", "name": "Financial Select Sector SPDR Fund", "type": "ETF"},
            {"symbol": "XLK", "name": "Technology Select Sector SPDR Fund", "type": "ETF"},
        ]

        all_funds = fidelity_funds + vanguard_funds + etfs
        query_lower = query.lower()
        for fund in all_funds:
            if query_lower in fund["symbol"].lower() or query_lower in fund["name"].lower():
                results.append(
                    {
                        "symbol": fund["symbol"],
                        "name": fund["name"],
                        "asset_type": fund["type"],
                        "exchange": "Fund" if fund["type"] == "MUTUAL_FUND" else "ETF",
                    }
                )

        return results[:20]


# ---------------------------------------------------------------------------
# Global instance (backwards-compatible)
# ---------------------------------------------------------------------------
market_data_service = MarketDataService()
