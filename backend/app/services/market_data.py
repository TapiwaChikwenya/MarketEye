"""
Market data service using free APIs (yfinance, CoinGecko).
"""
import yfinance as yf
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import time
from functools import lru_cache
from app.models.asset import AssetType

logger = logging.getLogger(__name__)

# Simple in-memory cache
_cache: Dict[str, tuple] = {}  # key -> (data, timestamp)
CACHE_TTL_SECONDS = 300  # 5 minutes cache


def get_cached(key: str) -> Optional[Any]:
    """Get cached data if still valid."""
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            return data
        del _cache[key]
    return None


def set_cached(key: str, data: Any) -> None:
    """Set cache data."""
    _cache[key] = (data, time.time())


class MarketDataService:
    """Service for fetching market data from various free sources."""

    def __init__(self):
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        self._last_yfinance_call = 0
        self._min_yfinance_interval = 1.0  # Minimum 1 second between yfinance calls

    def _rate_limit_yfinance(self):
        """Apply rate limiting for yfinance calls."""
        elapsed = time.time() - self._last_yfinance_call
        if elapsed < self._min_yfinance_interval:
            time.sleep(self._min_yfinance_interval - elapsed)
        self._last_yfinance_call = time.time()

    async def get_stock_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current stock price using yfinance with caching.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'TSLA')

        Returns:
            Dict with price data or None if error
        """
        cache_key = f"stock_{symbol}"
        cached = get_cached(cache_key)
        if cached:
            logger.debug(f"Cache hit for {symbol}")
            return cached

        try:
            # Apply rate limiting
            self._rate_limit_yfinance()
            
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Get current price
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            if not current_price:
                # Fallback: get latest close from history
                hist = ticker.history(period='1d')
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]

            # Get 24h change
            previous_close = info.get('previousClose')
            change_24h = None
            change_percent_24h = None

            if current_price and previous_close:
                change_24h = current_price - previous_close
                change_percent_24h = (change_24h / previous_close) * 100

            result = {
                'symbol': symbol,
                'current_price': str(current_price) if current_price else None,
                'market_cap': str(info.get('marketCap', '')),
                'volume_24h': str(info.get('volume', '')),
                'change_24h': str(change_24h) if change_24h else None,
                'change_percent_24h': str(change_percent_24h) if change_percent_24h else None,
                'last_updated': datetime.utcnow().isoformat(),
                'name': info.get('longName') or info.get('shortName'),
                'exchange': info.get('exchange'),
                'currency': info.get('currency', 'USD'),
            }
            
            # Cache the result if we got valid price
            if result.get('current_price'):
                set_cached(cache_key, result)
                return result

            logger.warning(f"No price data for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Error fetching stock price for {symbol}: {e}")
            return None

    async def get_crypto_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current crypto price using CoinGecko API with caching.

        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')

        Returns:
            Dict with price data or None if error
        """
        cache_key = f"crypto_{symbol.upper()}"
        cached = get_cached(cache_key)
        if cached:
            logger.debug(f"Cache hit for crypto {symbol}")
            return cached

        try:
            # Map common symbols to CoinGecko IDs
            symbol_to_id = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'USDT': 'tether',
                'BNB': 'binancecoin',
                'SOL': 'solana',
                'XRP': 'ripple',
                'ADA': 'cardano',
                'AVAX': 'avalanche-2',
                'DOGE': 'dogecoin',
                'DOT': 'polkadot',
                'MATIC': 'matic-network',
                'LTC': 'litecoin',
                'LINK': 'chainlink',
                'UNI': 'uniswap',
            }

            coin_id = symbol_to_id.get(symbol.upper())
            if not coin_id:
                # Try to search for the coin
                search_url = f"{self.coingecko_base_url}/search"
                search_response = requests.get(search_url, params={'query': symbol}, timeout=10)
                search_data = search_response.json()

                if search_data.get('coins'):
                    coin_id = search_data['coins'][0]['id']
                else:
                    logger.warning(f"Crypto {symbol} not found in CoinGecko")
                    return None

            # Get coin data
            url = f"{self.coingecko_base_url}/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'community_data': 'false',
                'developer_data': 'false',
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if 'market_data' not in data:
                return None

            market_data = data['market_data']
            current_price = market_data['current_price'].get('usd')

            result = {
                'symbol': symbol.upper(),
                'current_price': str(current_price) if current_price else None,
                'market_cap': str(market_data.get('market_cap', {}).get('usd', '')),
                'volume_24h': str(market_data.get('total_volume', {}).get('usd', '')),
                'change_24h': str(market_data.get('price_change_24h', '')),
                'change_percent_24h': str(market_data.get('price_change_percentage_24h', '')),
                'last_updated': datetime.utcnow().isoformat(),
                'name': data.get('name'),
                'exchange': 'CoinGecko',
                'currency': 'USD',
            }
            
            # Cache the result
            if result.get('current_price'):
                set_cached(cache_key, result)
            
            return result
        except Exception as e:
            logger.error(f"Error fetching crypto price for {symbol}: {e}")
            return None

    async def get_asset_price(self, symbol: str, asset_type: AssetType) -> Optional[Dict[str, Any]]:
        """
        Get asset price based on asset type.

        Args:
            symbol: Asset symbol
            asset_type: Type of asset (STOCK, CRYPTO, ETF, etc.)

        Returns:
            Dict with price data or None if error
        """
        if asset_type == AssetType.CRYPTO:
            return await self.get_crypto_price(symbol)
        else:
            # Use yfinance for stocks, ETFs, mutual funds, indexes
            return await self.get_stock_price(symbol)

    async def get_historical_data(
        self,
        symbol: str,
        asset_type: AssetType,
        period: str = "1mo",
        interval: str = "1d"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical price data.

        Args:
            symbol: Asset symbol
            asset_type: Type of asset
            period: Period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            List of historical data points
        """
        try:
            if asset_type == AssetType.CRYPTO:
                # Use yfinance for crypto too (supports BTC-USD, ETH-USD, etc.)
                crypto_symbol = f"{symbol}-USD"
                ticker = yf.Ticker(crypto_symbol)
            else:
                ticker = yf.Ticker(symbol)

            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                return None

            data_points = []
            for index, row in hist.iterrows():
                data_points.append({
                    'timestamp': index.isoformat(),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': float(row['Volume']),
                })

            return data_points
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None

    async def search_assets(self, query: str, asset_type: Optional[AssetType] = None) -> List[Dict[str, Any]]:
        """
        Search for assets by query.

        Args:
            query: Search query
            asset_type: Filter by asset type

        Returns:
            List of matching assets
        """
        results = []

        try:
            if asset_type == AssetType.CRYPTO or asset_type is None:
                # Search CoinGecko
                url = f"{self.coingecko_base_url}/search"
                response = requests.get(url, params={'query': query}, timeout=10)
                data = response.json()

                for coin in data.get('coins', [])[:10]:
                    results.append({
                        'symbol': coin.get('symbol', '').upper(),
                        'name': coin.get('name'),
                        'asset_type': 'CRYPTO',
                        'exchange': 'CoinGecko',
                    })

            if asset_type != AssetType.CRYPTO or asset_type is None:
                # For stocks, we can't search directly with yfinance
                # We'd need to maintain a symbol database or use another API
                # For now, just try to fetch the symbol directly
                try:
                    ticker = yf.Ticker(query.upper())
                    info = ticker.info
                    if info and info.get('symbol'):
                        results.append({
                            'symbol': info['symbol'],
                            'name': info.get('longName') or info.get('shortName'),
                            'asset_type': self._detect_asset_type(info),
                            'exchange': info.get('exchange'),
                        })
                except:
                    pass

            return results
        except Exception as e:
            logger.error(f"Error searching assets for query {query}: {e}")
            return []

    def _detect_asset_type(self, info: Dict) -> str:
        """Detect asset type from yfinance info."""
        quote_type = info.get('quoteType', '').upper()

        if quote_type == 'ETF':
            return 'ETF'
        elif quote_type == 'MUTUALFUND':
            return 'MUTUAL_FUND'
        elif quote_type == 'INDEX':
            return 'INDEX'
        elif quote_type == 'CRYPTOCURRENCY':
            return 'CRYPTO'
        else:
            return 'STOCK'

    async def get_mutual_fund_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get mutual fund data using yfinance.
        Works for Fidelity funds (FXAIX, FSKAX, etc.) and other mutual funds.
        """
        cache_key = f"fund_{symbol}"
        cached = get_cached(cache_key)
        if cached:
            logger.debug(f"Cache hit for fund {symbol}")
            return cached

        try:
            self._rate_limit_yfinance()
            
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Get NAV (Net Asset Value) for mutual funds
            current_price = (
                info.get('navPrice') or 
                info.get('regularMarketPrice') or 
                info.get('previousClose')
            )
            
            if not current_price:
                hist = ticker.history(period='5d')
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]

            previous_close = info.get('previousClose')
            change_24h = None
            change_percent_24h = None

            if current_price and previous_close:
                change_24h = current_price - previous_close
                change_percent_24h = (change_24h / previous_close) * 100

            result = {
                'symbol': symbol.upper(),
                'current_price': str(current_price) if current_price else None,
                'market_cap': str(info.get('totalAssets', '')),
                'volume_24h': str(info.get('volume', '')),
                'change_24h': str(change_24h) if change_24h else None,
                'change_percent_24h': str(change_percent_24h) if change_percent_24h else None,
                'last_updated': datetime.utcnow().isoformat(),
                'name': info.get('longName') or info.get('shortName') or symbol,
                'exchange': info.get('exchange', 'Mutual Fund'),
                'currency': info.get('currency', 'USD'),
                'asset_type': 'MUTUAL_FUND',
                'expense_ratio': str(info.get('annualReportExpenseRatio', '')),
                'category': info.get('category', ''),
                'fund_family': info.get('fundFamily', ''),
            }
            
            if result.get('current_price'):
                set_cached(cache_key, result)
            
            return result
        except Exception as e:
            logger.error(f"Error fetching mutual fund price for {symbol}: {e}")
            return None

    async def get_etf_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ETF data using yfinance."""
        # ETFs work like stocks in yfinance
        result = await self.get_stock_price(symbol)
        if result:
            result['asset_type'] = 'ETF'
        return result

    async def search_funds(self, query: str) -> List[Dict[str, Any]]:
        """Search for mutual funds and ETFs."""
        results = []
        
        # Popular Fidelity funds for search
        fidelity_funds = [
            {'symbol': 'FXAIX', 'name': 'Fidelity 500 Index Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FSKAX', 'name': 'Fidelity Total Market Index Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FZROX', 'name': 'Fidelity ZERO Total Market Index Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FZILX', 'name': 'Fidelity ZERO International Index Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FXNAX', 'name': 'Fidelity U.S. Bond Index Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FTBFX', 'name': 'Fidelity Total Bond Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FBALX', 'name': 'Fidelity Balanced Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FCNTX', 'name': 'Fidelity Contrafund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FDGRX', 'name': 'Fidelity Growth Company Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FBGRX', 'name': 'Fidelity Blue Chip Growth Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FMAGX', 'name': 'Fidelity Magellan Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FOCPX', 'name': 'Fidelity OTC Portfolio', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FSPTX', 'name': 'Fidelity Select Technology', 'type': 'MUTUAL_FUND'},
            {'symbol': 'FSHOX', 'name': 'Fidelity Select Construction & Housing', 'type': 'MUTUAL_FUND'},
        ]
        
        # Vanguard funds
        vanguard_funds = [
            {'symbol': 'VFIAX', 'name': 'Vanguard 500 Index Fund Admiral', 'type': 'MUTUAL_FUND'},
            {'symbol': 'VTSAX', 'name': 'Vanguard Total Stock Market Index Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'VBTLX', 'name': 'Vanguard Total Bond Market Index Fund', 'type': 'MUTUAL_FUND'},
            {'symbol': 'VTIAX', 'name': 'Vanguard Total International Stock Index', 'type': 'MUTUAL_FUND'},
            {'symbol': 'VWELX', 'name': 'Vanguard Wellington Fund', 'type': 'MUTUAL_FUND'},
        ]
        
        # Popular ETFs
        etfs = [
            {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'type': 'ETF'},
            {'symbol': 'VOO', 'name': 'Vanguard S&P 500 ETF', 'type': 'ETF'},
            {'symbol': 'VTI', 'name': 'Vanguard Total Stock Market ETF', 'type': 'ETF'},
            {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust', 'type': 'ETF'},
            {'symbol': 'IWM', 'name': 'iShares Russell 2000 ETF', 'type': 'ETF'},
            {'symbol': 'VEA', 'name': 'Vanguard FTSE Developed Markets ETF', 'type': 'ETF'},
            {'symbol': 'VWO', 'name': 'Vanguard FTSE Emerging Markets ETF', 'type': 'ETF'},
            {'symbol': 'BND', 'name': 'Vanguard Total Bond Market ETF', 'type': 'ETF'},
            {'symbol': 'AGG', 'name': 'iShares Core U.S. Aggregate Bond ETF', 'type': 'ETF'},
            {'symbol': 'GLD', 'name': 'SPDR Gold Shares', 'type': 'ETF'},
            {'symbol': 'ARKK', 'name': 'ARK Innovation ETF', 'type': 'ETF'},
            {'symbol': 'XLF', 'name': 'Financial Select Sector SPDR Fund', 'type': 'ETF'},
            {'symbol': 'XLK', 'name': 'Technology Select Sector SPDR Fund', 'type': 'ETF'},
        ]
        
        all_funds = fidelity_funds + vanguard_funds + etfs
        query_lower = query.lower()
        
        for fund in all_funds:
            if (query_lower in fund['symbol'].lower() or 
                query_lower in fund['name'].lower()):
                results.append({
                    'symbol': fund['symbol'],
                    'name': fund['name'],
                    'asset_type': fund['type'],
                    'exchange': 'Fund' if fund['type'] == 'MUTUAL_FUND' else 'ETF',
                })
        
        # If direct symbol match, try yfinance
        if len(results) == 0 and len(query) >= 2:
            try:
                self._rate_limit_yfinance()
                ticker = yf.Ticker(query.upper())
                info = ticker.info
                if info and info.get('symbol'):
                    asset_type = self._detect_asset_type(info)
                    results.append({
                        'symbol': info['symbol'],
                        'name': info.get('longName') or info.get('shortName') or query.upper(),
                        'asset_type': asset_type,
                        'exchange': info.get('exchange', 'Unknown'),
                    })
            except:
                pass
        
        return results[:20]  # Limit results


# Global instance
market_data_service = MarketDataService()
