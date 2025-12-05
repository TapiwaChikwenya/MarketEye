"""
Market data service using free APIs (yfinance, CoinGecko).
"""
import yfinance as yf
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from app.models.asset import AssetType

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching market data from various free sources."""

    def __init__(self):
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"

    async def get_stock_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current stock price using yfinance.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'TSLA')

        Returns:
            Dict with price data or None if error
        """
        try:
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

            return {
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
        except Exception as e:
            logger.error(f"Error fetching stock price for {symbol}: {e}")
            return None

    async def get_crypto_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current crypto price using CoinGecko API.

        Args:
            symbol: Crypto symbol (e.g., 'BTC', 'ETH')

        Returns:
            Dict with price data or None if error
        """
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

            return {
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


# Global instance
market_data_service = MarketDataService()
