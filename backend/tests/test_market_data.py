import math
import time
from datetime import date, timedelta
from typing import Any, Dict, List
from unittest.mock import patch

import pandas as pd
import pytest
import requests
import yfinance as yf

from app.api.v1.public import get_trending_assets
from app.models.asset import AssetType
from app.services.price_history_utils import points_to_rows, safe_decimal
from app.services.market_data import (
    CircuitBreaker,
    MarketDataService,
    ProviderRegistry,
    MarketDataProvider,
    YFinanceProvider,
    CoinGeckoProvider,
    CoinCapProvider,
    FinnhubProvider,
    AlphaVantageProvider,
    _fallback_cache,
    _search_static_stocks,
    _period_to_date_range,
    _expected_trading_days,
    get_cached,
    get_stale,
    set_cached,
    _cache_key,
    market_data_service,
)


# -----------------------------------------------------------------------
# CircuitBreaker tests
# -----------------------------------------------------------------------


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker("test", max_failures=3, reset_timeout=10)
        assert not cb.is_open

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", max_failures=3, reset_timeout=10)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open
        cb.record_failure()
        assert cb.is_open

    def test_success_resets_count(self):
        cb = CircuitBreaker("test", max_failures=3, reset_timeout=10)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        assert not cb.is_open

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker("test", max_failures=1, reset_timeout=5)
        cb.record_failure()
        assert cb.is_open
        cb._last_failure_time = time.time() - 10  # simulate timeout passed
        assert not cb.is_open  # transitions to half-open
        assert cb._state == "half-open"

    def test_half_open_closes_on_success(self):
        cb = CircuitBreaker("test", max_failures=1, reset_timeout=0)
        cb.record_failure()
        cb._last_failure_time = time.time() - 1
        _ = cb.is_open  # trigger half-open
        cb.record_success()
        assert cb._state == "closed"
        assert not cb.is_open


# -----------------------------------------------------------------------
# Cache tests (stale-while-revalidate with in-memory fallback)
# -----------------------------------------------------------------------


class TestCache:
    def test_fresh_cache_hit(self):
        key = _cache_key("stock", "AAPL")
        set_cached(key, {"symbol": "AAPL", "current_price": "150"})
        result = get_cached(key)
        assert result is not None
        assert result["symbol"] == "AAPL"

    def test_stale_cache_returned_by_get_stale(self):
        key = _cache_key("stock", "AAPL")
        data = {"symbol": "AAPL", "current_price": "150"}
        _fallback_cache[key] = (data, time.time() - 400)  # 400s old, past 300s fresh
        assert get_cached(key) is None
        assert get_stale(key) is not None
        assert get_stale(key)["symbol"] == "AAPL"

    def test_expired_stale_returns_none(self):
        key = _cache_key("stock", "AAPL")
        data = {"symbol": "AAPL", "current_price": "150"}
        _fallback_cache[key] = (data, time.time() - 2000)  # past 1800s stale TTL
        assert get_stale(key) is None


# -----------------------------------------------------------------------
# ProviderRegistry fallback tests
# -----------------------------------------------------------------------


class StubProvider(MarketDataProvider):
    """Provider that returns a fixed result or raises."""

    def __init__(self, name: str, result: Any = None, raises: bool = False):
        self.name = name
        self._result = result
        self._raises = raises
        self.call_count = 0

    def fetch_quote_sync(self, symbol: str) -> Any:
        self.call_count += 1
        if self._raises:
            raise ConnectionError(f"{self.name} is down")
        return self._result


@pytest.mark.asyncio
async def test_registry_uses_first_healthy_provider():
    primary = StubProvider("primary", result={"symbol": "X", "current_price": "10"})
    secondary = StubProvider("secondary", result={"symbol": "X", "current_price": "20"})
    reg = ProviderRegistry(
        stock_chain=[primary, secondary], crypto_chain=[], cb_threshold=5, cb_timeout=60
    )
    result = await reg.get_quote("X", "STOCK")
    assert result["current_price"] == "10"
    assert primary.call_count == 1
    assert secondary.call_count == 0


@pytest.mark.asyncio
async def test_registry_falls_back_on_failure():
    failing = StubProvider("failing", raises=True)
    fallback = StubProvider("fallback", result={"symbol": "X", "current_price": "20"})
    reg = ProviderRegistry(
        stock_chain=[failing, fallback], crypto_chain=[], cb_threshold=5, cb_timeout=60
    )
    result = await reg.get_quote("X", "STOCK")
    assert result["current_price"] == "20"
    assert failing.call_count == 1
    assert fallback.call_count == 1


@pytest.mark.asyncio
async def test_registry_skips_open_circuit():
    failing = StubProvider("failing", raises=True)
    fallback = StubProvider("fallback", result={"symbol": "X", "current_price": "30"})
    reg = ProviderRegistry(
        stock_chain=[failing, fallback], crypto_chain=[], cb_threshold=1, cb_timeout=300
    )
    await reg.get_quote("X1", "STOCK")
    assert reg._breakers["failing"].is_open

    result = await reg.get_quote("X2", "STOCK")
    assert result["current_price"] == "30"
    assert failing.call_count == 1  # not called again


@pytest.mark.asyncio
async def test_registry_returns_stale_when_all_fail():
    key = _cache_key("stock", "STALE")
    _fallback_cache[key] = ({"symbol": "STALE", "current_price": "99"}, time.time() - 400)

    failing = StubProvider("only", raises=True)
    reg = ProviderRegistry(
        stock_chain=[failing], crypto_chain=[], cb_threshold=5, cb_timeout=60
    )
    result = await reg.get_quote("STALE", "STOCK")
    assert result is not None
    assert result["current_price"] == "99"


# -----------------------------------------------------------------------
# MarketDataService integration tests (mocked providers)
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stock_price_caches_and_returns_change(monkeypatch):
    """Stock price fetch should cache results and compute change percent."""
    ticker_calls = {"count": 0}

    class DummyTicker:
        def __init__(self, symbol: str):
            ticker_calls["count"] += 1
            self.info = {
                "symbol": symbol,
                "currentPrice": 150.0,
                "previousClose": 148.0,
                "longName": "Test Asset",
                "exchange": "NASDAQ",
                "currency": "USD",
                "marketCap": 123456789,
                "volume": 42,
            }

        def history(self, period: str = "1d"):
            return pd.DataFrame({"Close": [147.0]})

    monkeypatch.setattr(yf, "Ticker", DummyTicker)

    first = await market_data_service.get_stock_price("TEST")
    second = await market_data_service.get_stock_price("TEST")

    assert first == second
    assert first["symbol"] == "TEST"
    assert first["current_price"] == "150.0"
    assert first["change_percent_24h"] == str(((150.0 - 148.0) / 148.0) * 100)


@pytest.mark.asyncio
async def test_get_crypto_price_maps_symbol_and_caches(monkeypatch):
    """Crypto price fetch should use static map (no search), cache, and include key fields."""
    call_counts: Dict[str, int] = {"coin": 0}

    class FakeResponse:
        status_code = 200
        def __init__(self, payload: Dict[str, Any]):
            self._payload = payload
        def json(self):
            return self._payload
        def raise_for_status(self):
            pass

    original_request = requests.request
    def fake_request(method, url, **kwargs):
        call_counts["coin"] += 1
        return FakeResponse(
            {
                "market_data": {
                    "current_price": {"usd": 42000.0},
                    "market_cap": {"usd": 850000000000},
                    "total_volume": {"usd": 123456789},
                    "price_change_24h": 500.0,
                    "price_change_percentage_24h": 1.25,
                },
                "name": "Bitcoin",
            }
        )

    monkeypatch.setattr(requests, "request", fake_request)

    first = await market_data_service.get_crypto_price("BTC")
    second = await market_data_service.get_crypto_price("BTC")

    assert first == second
    assert call_counts["coin"] == 1, "BTC uses static map and result is cached"
    assert first["symbol"] == "BTC"
    assert first["current_price"] == "42000.0"
    assert first["change_percent_24h"] == "1.25"


@pytest.mark.asyncio
async def test_get_stock_price_returns_none_on_missing_price(monkeypatch):
    """Should return None when yfinance provides no price."""

    class EmptyTicker:
        def __init__(self, symbol: str):
            self.info = {"symbol": symbol}
        def history(self, period: str = "1d"):
            return pd.DataFrame()

    monkeypatch.setattr(yf, "Ticker", EmptyTicker)
    result = await market_data_service.get_stock_price("NOPRICE")
    assert result is None


@pytest.mark.asyncio
async def test_public_trending_summary_counts(monkeypatch):
    """Public trending endpoint should aggregate gainers/losers and averages correctly."""

    async def fake_stock_price(symbol: str):
        return {
            "symbol": symbol,
            "name": f"Stock {symbol}",
            "current_price": "100",
            "change_percent_24h": "1",
        }

    async def fake_crypto_price(symbol: str):
        return {
            "symbol": symbol,
            "name": f"Crypto {symbol}",
            "current_price": "200",
            "change_percent_24h": "-2",
        }

    async def fake_mutual_fund_price(symbol: str):
        return {
            "symbol": symbol,
            "name": f"Fund {symbol}",
            "current_price": "50",
            "change_percent_24h": "0.5",
        }

    monkeypatch.setattr(market_data_service, "get_stock_price", fake_stock_price)
    monkeypatch.setattr(market_data_service, "get_crypto_price", fake_crypto_price)
    monkeypatch.setattr(market_data_service, "get_mutual_fund_price", fake_mutual_fund_price)

    result = await get_trending_assets()

    assert len(result["stocks"]) == 10
    assert len(result["crypto"]) == 9
    assert len(result["funds"]) == 19

    assert result["market_summary"]["gainers"] == 29
    assert result["market_summary"]["losers"] == 9

    # total_change = 10*1 + 9*(-2) + 14*0.5 + 5*1 = 4; avg = round(4/38, 2) = 0.11
    assert math.isclose(result["market_summary"]["avg_change_24h"], 0.11, abs_tol=0.01)


@pytest.mark.asyncio
async def test_public_trending_handles_provider_failure(monkeypatch):
    """Trending endpoint should return partial data when some providers fail."""

    async def failing_stock_price(symbol: str):
        raise ConnectionError("provider down")

    async def ok_crypto_price(symbol: str):
        return {
            "symbol": symbol,
            "name": f"Crypto {symbol}",
            "current_price": "100",
            "change_percent_24h": "3",
        }

    async def ok_fund_price(symbol: str):
        return {
            "symbol": symbol,
            "name": f"Fund {symbol}",
            "current_price": "50",
            "change_percent_24h": "1",
        }

    monkeypatch.setattr(market_data_service, "get_stock_price", failing_stock_price)
    monkeypatch.setattr(market_data_service, "get_crypto_price", ok_crypto_price)
    monkeypatch.setattr(market_data_service, "get_mutual_fund_price", ok_fund_price)

    result = await get_trending_assets()

    assert len(result["stocks"]) == 0
    assert len(result["crypto"]) == 9
    assert result["market_summary"]["losers"] == 0


# -----------------------------------------------------------------------
# Static stock search tests
# -----------------------------------------------------------------------


class TestStaticStockSearch:
    def test_exact_symbol_match(self):
        results = _search_static_stocks("AAPL")
        assert len(results) == 1
        assert results[0]["symbol"] == "AAPL"
        assert results[0]["name"] == "Apple Inc."

    def test_partial_symbol_match(self):
        results = _search_static_stocks("AA")
        symbols = [r["symbol"] for r in results]
        assert "AAPL" in symbols
        assert "AAL" in symbols

    def test_name_match(self):
        results = _search_static_stocks("apple")
        assert any(r["symbol"] == "AAPL" for r in results)

    def test_case_insensitive(self):
        r1 = _search_static_stocks("aapl")
        r2 = _search_static_stocks("AAPL")
        assert r1[0]["symbol"] == r2[0]["symbol"]

    def test_no_match(self):
        results = _search_static_stocks("XYZNONEXISTENT999")
        assert len(results) == 0


# -----------------------------------------------------------------------
# search_assets integration tests (mocked external APIs)
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_assets_returns_static_stocks_without_api(monkeypatch):
    """Searching AAPL should return Apple Inc. from static DB, no API calls needed."""
    api_calls = {"count": 0}

    original_request = requests.request
    def counting_request(method, url, **kwargs):
        api_calls["count"] += 1
        raise ConnectionError("should not reach external APIs for static matches")

    monkeypatch.setattr(requests, "request", counting_request)

    service = MarketDataService()
    results = await service.search_assets("AAPL")

    assert len(results) >= 1
    assert results[0]["symbol"] == "AAPL"
    assert results[0]["name"] == "Apple Inc."
    assert results[0]["asset_type"] == "STOCK"


@pytest.mark.asyncio
async def test_search_assets_ranks_stock_above_crypto(monkeypatch):
    """When static stock matches exist, they should rank above CoinGecko crypto results."""

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"coins": [
                {"symbol": "AAPLX", "name": "Apple xStock"},
                {"symbol": "AAPL.D", "name": "Dinari AAPL"},
            ]}
        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "request", lambda *a, **kw: FakeResponse())

    service = MarketDataService()
    results = await service.search_assets("AAPL")

    assert results[0]["symbol"] == "AAPL"
    assert results[0]["asset_type"] == "STOCK"


@pytest.mark.asyncio
async def test_search_assets_filters_tokenized_crypto(monkeypatch):
    """Tokenized crypto wrappers should be ranked below real stocks."""

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"coins": [
                {"symbol": "AAPLX", "name": "Apple xStock"},
                {"symbol": "BTC", "name": "Bitcoin"},
            ]}
        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "request", lambda *a, **kw: FakeResponse())

    service = MarketDataService()
    results = await service.search_assets("AAPL")

    stock_idx = next(i for i, r in enumerate(results) if r["symbol"] == "AAPL" and r["asset_type"] == "STOCK")
    tokenized_indices = [i for i, r in enumerate(results) if "xstock" in (r.get("name") or "").lower()]

    for ti in tokenized_indices:
        assert stock_idx < ti, "Real AAPL should rank above tokenized crypto"


@pytest.mark.asyncio
async def test_search_funds_no_yfinance_fallback(monkeypatch):
    """search_funds should NOT call yfinance, only search the static list."""
    yf_calls = {"count": 0}

    class CountingTicker:
        def __init__(self, symbol):
            yf_calls["count"] += 1
            self.info = {}

    monkeypatch.setattr(yf, "Ticker", CountingTicker)

    service = MarketDataService()
    results = await service.search_funds("SPY")

    assert any(r["symbol"] == "SPY" for r in results)
    assert yf_calls["count"] == 0, "search_funds should NOT call yfinance"


@pytest.mark.asyncio
async def test_search_funds_returns_empty_for_unknown():
    """search_funds for an unknown query should return empty (no yfinance fallback)."""
    service = MarketDataService()
    results = await service.search_funds("XYZUNKNOWN999")
    assert results == []


# -----------------------------------------------------------------------
# PriceHistory helpers tests
# -----------------------------------------------------------------------


class TestPeriodToDateRange:
    def test_1mo_returns_30_day_range(self):
        from_date, to_date = _period_to_date_range("1mo")
        assert to_date == date.today()
        assert (to_date - from_date).days == 30

    def test_1y_returns_365_day_range(self):
        from_date, to_date = _period_to_date_range("1y")
        assert (to_date - from_date).days == 365

    def test_unknown_period_defaults_to_30(self):
        from_date, to_date = _period_to_date_range("unknown")
        assert (to_date - from_date).days == 30


class TestExpectedTradingDays:
    def test_crypto_counts_every_day(self):
        today = date.today()
        result = _expected_trading_days(today - timedelta(days=30), today, AssetType.CRYPTO)
        assert result == 30

    def test_stock_excludes_weekends(self):
        today = date.today()
        result = _expected_trading_days(today - timedelta(days=7), today, AssetType.STOCK)
        assert result == 5


class TestPointsToRows:
    def test_converts_api_points_to_db_rows(self):
        points = [
            {
                "timestamp": "2026-03-01T00:00:00+00:00",
                "open": 150.0, "high": 155.0, "low": 149.0,
                "close": 153.0, "volume": 1000000.0,
            },
            {
                "timestamp": "2026-03-02T00:00:00+00:00",
                "open": 153.0, "high": 158.0, "low": 152.0,
                "close": 157.0, "volume": 1200000.0,
            },
        ]
        rows = points_to_rows("AAPL", AssetType.STOCK, points)
        assert len(rows) == 2
        assert rows[0]["symbol"] == "AAPL"
        assert rows[0]["date"] == date(2026, 3, 1)
        assert float(rows[0]["close"]) == 153.0

    def test_deduplicates_same_date(self):
        points = [
            {
                "timestamp": "2026-03-01T10:00:00+00:00",
                "open": 150.0, "high": 155.0, "low": 149.0,
                "close": 153.0, "volume": 1000000.0,
            },
            {
                "timestamp": "2026-03-01T15:00:00+00:00",
                "open": 153.0, "high": 158.0, "low": 152.0,
                "close": 157.0, "volume": 1200000.0,
            },
        ]
        rows = points_to_rows("AAPL", AssetType.STOCK, points)
        assert len(rows) == 1

    def test_handles_bad_timestamps(self):
        points = [{"open": 1, "high": 1, "low": 1, "close": 1}]
        rows = points_to_rows("AAPL", AssetType.STOCK, points)
        assert len(rows) == 0

    def test_safe_decimal_handles_none(self):
        assert safe_decimal(None) == 0
        assert safe_decimal("invalid") == 0
        assert float(safe_decimal(42.5)) == 42.5


@pytest.mark.asyncio
async def test_get_historical_data_intraday_bypasses_db(monkeypatch):
    """Intraday requests should go straight to APIs, not query price_history."""
    import app.services.market_data as md_module

    db_called = {"count": 0}

    original_query = md_module._query_price_history
    async def tracking_query(*args, **kwargs):
        db_called["count"] += 1
        return await original_query(*args, **kwargs)

    monkeypatch.setattr(md_module, "_query_price_history", tracking_query)

    class FakeResponse:
        status_code = 200
        def json(self):
            return {
                "chart": {"result": [{
                    "timestamp": [1000000],
                    "indicators": {"quote": [{
                        "open": [100.0], "high": [101.0], "low": [99.0],
                        "close": [100.5], "volume": [5000],
                    }]},
                }]}
            }

    monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResponse())

    service = MarketDataService()
    result = await service.get_historical_data("AAPL", AssetType.STOCK, "1d", "5m")

    assert db_called["count"] == 0, "Intraday should not query price_history"
    assert result is not None
