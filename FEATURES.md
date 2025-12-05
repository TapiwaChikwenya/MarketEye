# MarketEye Features

## 🎨 Beautiful User Interface

### Futuristic Cyberpunk Theme
- **Dark Mode**: Eye-friendly dark background with cyber-inspired aesthetics
- **Neon Accents**: Cyan, magenta, and lime neon colors for visual appeal
- **Glassmorphism**: Frosted glass effect on cards and panels
- **Smooth Animations**: Framer Motion animations for all interactions
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile

### Dashboard
- **Live Asset Tiles**: Real-time price updates with sparkline charts
- **Portfolio Summary**: Total value, daily P&L, top gainers/losers
- **Alert Status**: Active alerts and recent triggers
- **Quick Actions**: Search, add assets, create alerts
- **Cyber Grid Background**: Animated background with subtle grid pattern

## 📊 Market Data

### Supported Asset Types
- **Stocks**: US and international equities
- **Crypto**: Bitcoin, Ethereum, and 1000+ cryptocurrencies
- **ETFs**: Exchange-traded funds
- **Mutual Funds**: Mutual fund tracking
- **Indexes**: S&P 500, NASDAQ, Dow Jones, etc.

### Data Sources (All FREE!)
- **yfinance**: Yahoo Finance API (no API key needed)
- **CoinGecko**: Cryptocurrency data (free tier)
- **Alpha Vantage**: Backup stock data (optional, free tier)

### Real-time Updates
- Price updates every 60 seconds
- 24/7 monitoring for crypto
- Market hours detection for stocks
- Automatic stale data handling

## 🔔 Smart Alert System

### Alert Condition Types

#### Price-Based Alerts
- **Price Above**: Alert when asset price goes above threshold
- **Price Below**: Alert when asset price drops below threshold

#### Performance Alerts
- **Percent Change Up**: Alert on X% increase in 24h
- **Percent Change Down**: Alert on X% decrease in 24h
- **Volume Above**: Alert on unusual volume spikes
- **Market Cap Above**: Alert when market cap threshold reached

#### Portfolio Alerts
- **Portfolio Value Up**: Alert when total portfolio increases by X%
- **Portfolio Value Down**: Alert when total portfolio decreases by X%
- **Position P&L**: Alert on individual position performance

### Notification Channels

#### SMS Notifications
- Powered by Twilio
- Instant text messages
- Custom message support
- Delivery confirmation

#### Voice Calls
- Powered by Twilio
- Text-to-speech alerts
- Custom voice messages
- Call status tracking

#### Email Notifications
- SMTP support (Gmail, etc.)
- HTML email templates
- Rich formatting
- Works out of the box

#### Push Notifications (Coming Soon)
- Browser push notifications
- Mobile app notifications

### Advanced Alert Features

#### Quiet Hours
- Set do-not-disturb hours
- Automatic notification suppression
- Per-alert override option
- Timezone-aware

#### Repeat Behaviors
- **One-time**: Alert once, then disable
- **Once per hour**: Maximum once per hour
- **Once per day**: Maximum once per day
- **Unlimited**: Alert every time condition is met

#### Smart Debouncing
- Prevents notification spam
- Configurable cooldown periods
- Per-user rate limits
- Alert history tracking

## 💼 Portfolio Management

### Virtual Portfolio Tracking
- Track holdings without connecting brokerage
- Manual entry of positions
- Multiple purchase tracking
- Average cost basis calculation

### Portfolio Analytics
- **Total Value**: Real-time portfolio valuation
- **Cost Basis**: Total amount invested
- **Unrealized P&L**: Profit/loss calculation
- **P&L Percentage**: Return on investment
- **Asset Allocation**: Breakdown by asset type
- **Top Gainers/Losers**: Best and worst performers

### Holdings Management
- Add holdings with purchase details
- Update quantity and cost basis
- Remove sold positions
- Historical purchase tracking

## 📋 Watchlist Features

### Multiple Watchlists
- Create unlimited watchlists (free tier: 3)
- Custom names and descriptions
- Drag-and-drop ordering
- Quick toggle show/hide

### Watchlist Limits (Free Tier)
- Max 3 watchlists
- Max 25 assets per watchlist
- Max 20 active alerts

### Watchlist Limits (Pro Tier)
- Unlimited watchlists
- Unlimited assets per watchlist
- Unlimited active alerts
- Priority support

## 🔐 Security & Privacy

### Authentication
- JWT token-based authentication
- Secure password hashing (bcrypt)
- Email verification
- Phone number verification (for SMS/calls)
- Session management

### Data Protection
- All passwords hashed
- Sensitive data encrypted at rest
- HTTPS support (production)
- CORS protection
- Rate limiting

### Privacy
- No trading execution (view only)
- No brokerage account linking required
- Optional phone number
- Data deletion on request

## ⚡ Background Workers

### Celery Tasks

#### Market Data Worker
- Updates all asset prices every 60 seconds
- Handles API rate limits
- Caches results in Redis
- Error handling and retry logic

#### Alert Evaluation Worker
- Evaluates all active alerts every 60 seconds
- Checks alert conditions
- Triggers notifications
- Updates alert status

#### Portfolio Calculation Worker
- Recalculates portfolio values every 5 minutes
- Updates P&L for all holdings
- Calculates asset allocation
- Performance metrics

#### Cleanup Worker
- Removes old notification logs (30+ days)
- Database maintenance
- Runs daily at midnight

## 🌐 API Features

### RESTful API
- OpenAPI/Swagger documentation
- JSON request/response
- Versioned endpoints (/api/v1)
- Pagination support
- Error handling with proper HTTP codes

### Authentication
- OAuth2 password flow
- Bearer token authentication
- Token refresh
- Secure endpoints

### Rate Limiting
- Per-user rate limits
- API key support (future)
- Abuse prevention

## 🐳 DevOps & Deployment

### Docker Support
- Multi-container setup
- Production-ready configuration
- Environment-based config
- Health checks
- Auto-restart on failure

### Database Migrations
- Alembic migration system
- Version control for schema
- Rollback support
- Safe schema updates

### Monitoring
- Celery Flower dashboard
- API health endpoints
- Detailed logging
- Error tracking

## 📱 Responsive Design

### Desktop
- Full-featured dashboard
- Multi-column layouts
- Hover effects and tooltips
- Keyboard shortcuts ready

### Tablet
- Responsive grid layouts
- Touch-friendly buttons
- Optimized spacing

### Mobile
- Mobile-first design
- Swipe gestures ready
- Bottom navigation
- Compact views

## 🎯 Use Cases

### Day Traders
- Monitor multiple positions
- Quick price alerts
- Real-time portfolio tracking
- SMS notifications for speed

### Long-term Investors
- Track portfolio performance
- Monthly/quarterly alerts
- Email notifications
- Cost basis tracking

### Crypto Enthusiasts
- 24/7 crypto monitoring
- Volatility alerts
- Multi-exchange support
- Real-time price updates

### Risk Managers
- Downside protection alerts
- Portfolio value alerts
- Diversification tracking
- Stop-loss notifications

## 🚀 Coming Soon

- [ ] Mobile apps (iOS/Android)
- [ ] Browser push notifications
- [ ] WebSocket real-time updates
- [ ] Advanced charting with indicators
- [ ] Backtesting for alert strategies
- [ ] Social features (share watchlists)
- [ ] AI-powered insights
- [ ] Custom alert formulas
- [ ] Trading view integration
- [ ] News and sentiment analysis

## 💎 Free vs Pro Tiers

### Free Tier ✨
- 3 watchlists
- 25 assets per watchlist
- 20 active alerts
- Email notifications
- Basic portfolio tracking
- Community support

### Pro Tier 💎
- Unlimited watchlists
- Unlimited assets
- Unlimited alerts
- All notification channels (SMS, Call, Email, Push)
- Advanced analytics
- Backtesting
- Priority support
- Custom alert formulas
- API access
- $9.99/month

---

**MarketEye** - Never miss a market move again! 📈
