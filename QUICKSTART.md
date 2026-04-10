# MarketEye - Quick Start Guide 🚀

## What You Just Built

**MarketEye** is a complete 24/7 investment monitoring platform with:

✨ **Beautiful Futuristic UI** - Cyberpunk-inspired dark theme with neon accents
📊 **Real-time Market Data** - Stocks, crypto, ETFs using free APIs
🔔 **Smart Alerts** - SMS, voice calls, and email notifications
💼 **Portfolio Tracking** - Virtual portfolio with P&L calculations
⚡ **Background Workers** - Celery tasks for automated monitoring

## Get Started in 3 Steps

### Step 1: Start the Application

```bash
# Make sure you're in the MarketEye directory
cd MarketEye

# Start all services with Docker
docker-compose up -d

# Wait about 30 seconds for services to initialize
```

### Step 2: Run Database Migrations

```bash
# Run migrations to create database tables
docker-compose exec backend alembic upgrade head
```

### Step 3: Access the Application

Open your browser:
- **Frontend (dev stack, `docker-compose.yml`)**: http://localhost:5173  
  Or from the repo root after `cd frontend && npm install`: `npm run dev` (or `npm run dev` from root — see root `package.json`).
- **Frontend (prod stack, `docker-compose.prod.yml`)**: http://localhost (port 80) **or** http://localhost:5173 (mapped to the same UI)
- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health

## First Time Setup

### 1. Register an Account

1. Go to http://localhost:5173
2. Click "Sign up"
3. Enter your email and password
4. Click "Create Account"

### 2. Sign In

1. Use your email and password to sign in
2. You'll be redirected to the dashboard

### 3. Add Your First Asset

1. Click "Add Asset" button
2. Search for a stock (e.g., "AAPL", "TSLA") or crypto (e.g., "BTC", "ETH")
3. Select from search results
4. Asset will be added to your watchlist

### 4. Create an Alert

1. Click on an asset to view details
2. Click "Add Alert"
3. Choose condition type:
   - **Price Above/Below**: Alert when price crosses threshold
   - **Percent Change**: Alert on % increase/decrease
4. Set threshold value
5. Choose notification method (Email is ready to use)
6. Click "Create Alert"

## What's Running

When you run `docker-compose up`, these services start:

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 5173 | React app with beautiful UI |
| Backend API | 8000 | FastAPI REST API |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache & message broker |
| Celery Worker | - | Background tasks |
| Celery Beat | - | Task scheduler |

## Configuration (Optional)

### Enable SMS/Call Notifications

1. Sign up for Twilio: https://www.twilio.com/try-twilio (free trial)
2. Get your credentials
3. Edit `backend/.env`:
   ```env
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+1234567890
   ```
4. Restart backend: `docker-compose restart backend celery_worker`

### Enable Email Notifications

Email works out of the box with SMTP. For Gmail:

1. Create App Password: https://myaccount.google.com/apppasswords
2. Edit `backend/.env`:
   ```env
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```
3. Restart backend: `docker-compose restart backend celery_worker`

## Testing the Alert System

### Quick Test

1. Create a watchlist with a stock
2. Set up an alert with a condition that's currently met
3. Wait 1-2 minutes for the Celery worker to evaluate alerts
4. Check your email/phone for the notification

### Monitor Background Workers

```bash
# View Celery worker logs
docker-compose logs -f celery_worker

# View all service logs
docker-compose logs -f
```

## Useful Commands

```bash
# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart backend

# View logs
docker-compose logs -f backend

# Access database
docker-compose exec postgres psql -U marketeye -d marketeye

# Access Redis CLI
docker-compose exec redis redis-cli

# Run backend shell
docker-compose exec backend python
```

## Features to Explore

### 1. Dashboard
- Real-time price updates
- Portfolio value tracking
- Active alerts overview
- Beautiful asset tiles with animations

### 2. Watchlists
- Create multiple watchlists
- Organize assets by category
- Quick add/remove assets

### 3. Alerts
- Multiple condition types
- Custom notification channels
- Repeat behaviors
- Quiet hours support

### 4. Portfolio
- Add holdings manually
- Track cost basis
- View unrealized P&L
- Performance metrics

## Troubleshooting

### Frontend won't load
```bash
# Check if frontend is running
docker-compose ps

# Restart frontend
docker-compose restart frontend

# View logs
docker-compose logs frontend
```

### Backend errors
```bash
# Check backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend

# Run migrations again
docker-compose exec backend alembic upgrade head
```

### No price updates
```bash
# Check Celery worker is running
docker-compose ps celery_worker

# View worker logs
docker-compose logs celery_worker

# Restart worker
docker-compose restart celery_worker celery_beat
```

### Database connection issues
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Restart database
docker-compose restart postgres

# Wait 10 seconds then restart backend
docker-compose restart backend
```

## Development

### Backend Development

```bash
# Access backend container
docker-compose exec backend bash

# Run tests
pytest

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

### Frontend Development

```bash
# Access frontend container
docker-compose exec frontend sh

# Run linter
npm run lint

# Build for production
npm run build
```

## Tech Stack

**Backend:**
- FastAPI (Python web framework)
- PostgreSQL (Database)
- Redis (Cache & queue)
- Celery (Background workers)
- SQLAlchemy (ORM)

**Frontend:**
- React + TypeScript
- Vite (Build tool)
- TailwindCSS (Styling)
- Framer Motion (Animations)
- React Query (Data fetching)

**Market Data:**
- yfinance (Yahoo Finance - FREE!)
- CoinGecko API (Crypto - FREE!)

**Notifications:**
- Twilio (SMS/Voice - free trial)
- SMTP (Email - free with Gmail)

## Next Steps

1. ✅ Explore the dashboard
2. ✅ Add some assets to watchlist
3. ✅ Create your first alert
4. ✅ Set up notifications (SMS/Email)
5. ✅ Add portfolio holdings
6. ✅ Customize your profile settings

## Production Deployment

For production deployment, see **SETUP_GUIDE.md** for:
- Security best practices
- Environment configuration
- SSL/HTTPS setup
- Database backups
- Monitoring

## Get Help

- **API Documentation**: http://localhost:8000/docs
- **Setup Guide**: See SETUP_GUIDE.md
- **README**: See README.md
- **Issues**: GitHub Issues

## Architecture Overview

```
┌─────────────────┐
│   Frontend      │ ← React UI (Port 5173)
│   (Vite)        │
└────────┬────────┘
         │
         ↓ HTTP/WebSocket
┌─────────────────┐
│   Backend API   │ ← FastAPI (Port 8000)
│   (FastAPI)     │
└────────┬────────┘
         │
    ┌────┴────┬─────────┬──────────┐
    ↓         ↓         ↓          ↓
┌────────┐ ┌─────┐ ┌────────┐ ┌─────────┐
│Postgres│ │Redis│ │Celery  │ │Celery   │
│        │ │     │ │Worker  │ │Beat     │
└────────┘ └─────┘ └────────┘ └─────────┘
                        │
                        ↓
              ┌──────────────────┐
              │ External Services│
              │ - yfinance       │
              │ - CoinGecko      │
              │ - Twilio         │
              │ - SMTP           │
              └──────────────────┘
```

---

**Happy Monitoring! 📈**

Built with ❤️ using Python, React, and free APIs
