# MarketEye 📈

**24/7 Investment Watcher** - Monitor markets and assets with intelligent alerts via SMS, calls, push notifications, and email.

## 🚀 Features

- 📊 Real-time market monitoring (Stocks, ETFs, Crypto, Mutual Funds)
- 🔔 Smart alerts with customizable conditions (price, %, volume, portfolio-level)
- 📱 Multi-channel notifications (SMS, Call, Push, Email)
- 💼 Virtual portfolio tracking with P&L analytics
- 🎨 Futuristic dark-themed UI with smooth animations
- 🔒 Secure authentication with JWT
- 🌙 Quiet hours and notification preferences
- 📈 Live charts with technical indicators

## 🛠️ Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **PostgreSQL** - Relational database
- **Redis** - Caching and message broker
- **SQLAlchemy** - ORM with async support
- **Celery** - Background task processing
- **WebSockets** - Real-time updates

### Frontend
- **React + TypeScript** - Type-safe UI development
- **Vite** - Lightning-fast build tool
- **TailwindCSS** - Utility-first CSS framework
- **Framer Motion** - Beautiful animations
- **shadcn/ui** - High-quality component library
- **Lightweight Charts** - Professional financial charts

### Market Data (Free APIs)
- **yfinance** - Yahoo Finance (stocks, ETFs, indices)
- **CoinGecko** - Cryptocurrency data
- **Alpha Vantage** - Backup market data

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/TapiwaChikwenya/MarketEye.git
cd MarketEye

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Production-Style Docker Deployment (LAN/Another Device)

```bash
# 1) Clone
git clone https://github.com/TapiwaChikwenya/MarketEye.git
cd MarketEye

# 2) Create/Update .env at repo root
# Required:
#   SECRET_KEY=<strong-random-secret>
# Optional:
#   POSTGRES_USER=marketeye
#   POSTGRES_PASSWORD=change-me
#   POSTGRES_DB=marketeye
#   FINNHUB_API_KEY=<recommended>
#   ALPHA_VANTAGE_API_KEY=<optional>
#   CORS_ORIGINS=http://<server-ip>,http://localhost
#   VITE_API_URL=   # leave empty to auto-use current host

# 3) Build and start production stack (API + workers; no UI on :5173)
docker compose -f docker-compose.prod.yml up -d --build

# Optional: nginx static UI on port 80 only (does not use :5173)
# docker compose -f docker-compose.prod.yml --profile prod-ui up -d --build frontend

# Local UI development (live reload): npm run dev → http://localhost:5173

# 4) Access
# App (prod-ui profile): http://<server-ip>/
# App (local dev):       http://localhost:5173
# API docs: http://<server-ip>/docs
# Health:   http://<server-ip>/health
```

#### If another device cannot reach the site

- Use the server LAN IP (for example `http://192.168.x.x`), not `localhost`.
- Ensure host firewall allows inbound TCP `80` (and `8000` if directly testing backend).
- Confirm both devices are on the same subnet and AP client isolation is disabled.
- Verify published ports are listening:
  - `docker compose -f docker-compose.prod.yml ps`
  - `curl http://localhost/health`
- If app loads but API calls fail in browser, hard refresh after rebuild (`Ctrl/Cmd+Shift+R`) to clear old frontend bundle.

### Manual Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start Celery worker
celery -A app.celery_app worker --loglevel=info

# Start Celery beat scheduler
celery -A app.celery_app beat --loglevel=info
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start development server
npm run dev
```

## 📚 Documentation

- [API Documentation](http://localhost:8000/docs) - Interactive OpenAPI docs
- [Architecture Guide](./docs/architecture.md) - system topology, flows, and operations
- [Public Market Data Feature](./docs/feature-public-market-data.md) - landing/demo data paths and safeguards

## 🔐 Environment Variables

Copy `backend/.env.example` to `backend/.env` and adjust values. The snippets below highlight the most important groups.

### Backend (.env)

```env
# Database (async + sync URLs for tooling)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/marketeye
DATABASE_URL_SYNC=postgresql://user:password@localhost:5432/marketeye

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Password reset emails (links point to your SPA)
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=60
FRONTEND_BASE_URL=http://localhost:5173

# Twilio (SMS/Calls)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=your-twilio-number

# Email (SMTP) — see [SMTP setup](#smtp-setup-email-alerts--password-reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=MarketEye

# Market Data APIs (optional)
ALPHA_VANTAGE_API_KEY=your-api-key
COINGECKO_API_KEY=

# Application
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### SMTP setup (email alerts & password reset)

SMTP is used for **transactional email**: alert notifications, and **forgot-password** messages that contain a reset link.

1. **Choose a provider** (Gmail, SendGrid, Amazon SES, your own MTA, etc.). For **Gmail**, use an [App Password](https://support.google.com/accounts/answer/185833) on a Google account with 2-Step Verification enabled—do not use your normal login password.
2. **Set the variables** in `backend/.env`:
   - `SMTP_HOST`, `SMTP_PORT` — typically `smtp.gmail.com` and `587` with STARTTLS (the app uses STARTTLS).
   - `SMTP_USER` / `SMTP_PASSWORD` — provider credentials (for Gmail, the app password).
   - `SMTP_FROM_EMAIL` / `SMTP_FROM_NAME` — what recipients see as the sender (use a domain or address you are allowed to send from).
3. **Set `FRONTEND_BASE_URL`** to the exact origin users use in the browser, with **no trailing slash** (for example `https://app.example.com` in production). Password reset links are built as `{FRONTEND_BASE_URL}/reset-password?token=...`. If this is wrong, links in emails will point at the wrong host.
4. **Without SMTP**, the API still accepts forgot-password requests, but email is not delivered; the server logs a demo placeholder instead. Configure SMTP before relying on password reset or email alerts in production.

### Admin console and API

Access is limited to users with **`is_superuser = true`** in the database (the `users` table).

**Grant admin access (PostgreSQL example):**

```sql
UPDATE users SET is_superuser = true WHERE email = 'you@example.com';
```

**Web UI:** sign in, then open **`/admin`** (for example `http://localhost:5173/admin` in local dev). The navbar shows an **Admin** link when your account is a superuser. Non-admin users are redirected away from `/admin`.

**HTTP API:** all routes are under **`/api/v1/admin`** and require a **Bearer JWT** from `POST /api/v1/auth/login` (same token as the rest of the app). Examples:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/admin/overview` | Aggregated usage (users, alerts, tracked assets, cache hit/miss, etc.) |
| `GET` | `/api/v1/admin/users` | Paginated user list (`skip`, `limit` query params) |
| `PATCH` | `/api/v1/admin/users/{user_id}` | Update `is_active` / `is_superuser` |
| `GET` | `/api/v1/admin/system/health` | Uptime, DB/Redis latency, configured TTLs |
| `GET` | `/api/v1/admin/stocks/usage` | Top tracked symbols |

Interactive documentation: **[`/docs`](http://localhost:8000/docs)** (Swagger UI) — expand the **Admin** tag. In production, replace the host with your deployed API origin.

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## 🏗️ Project Structure

```
MarketEye/
├── backend/
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── core/             # Core configuration
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   ├── workers/          # Celery tasks
│   │   └── main.py           # FastAPI app
│   ├── alembic/              # Database migrations
│   ├── tests/                # Backend tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── hooks/            # Custom hooks
│   │   ├── lib/              # Utilities
│   │   ├── services/         # API services
│   │   └── App.tsx
│   ├── public/
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 🎨 UI Preview

The app features a cyberpunk-inspired dark theme with:
- Neon accent colors (cyan, magenta, lime)
- Smooth animations and transitions
- Real-time sparkline charts
- Glassmorphism effects
- Responsive grid layouts

## 📱 Key Features

### Alert Conditions
- Price above/below threshold
- Percentage change (daily, hourly)
- Volume spikes
- Portfolio-level alerts
- Custom indicator-based alerts

### Notification Channels
- SMS via Twilio
- Voice calls via Twilio
- Email via SMTP
- Push notifications (coming soon)

### Portfolio Analytics
- Real-time P&L tracking
- Asset allocation breakdown
- Performance metrics
- Top gainers/losers

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](./CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## ⚠️ Disclaimer

**MarketEye is for informational purposes only. It is not a broker and does not execute trades. Data may be delayed. This is not financial advice. Always verify with your broker before making investment decisions.**

## 🙏 Acknowledgments

- Market data powered by Yahoo Finance, CoinGecko, and Alpha Vantage
- Charts by TradingView Lightweight Charts
- Icons by Lucide

---

Built with ❤️ by the MarketEye team
