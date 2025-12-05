# MarketEye Setup Guide

Complete guide to set up and run MarketEye locally or in production.

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional, recommended)

## Quick Start with Docker (Recommended)

The easiest way to get started is using Docker Compose:

```bash
# 1. Clone the repository
git clone https://github.com/TapiwaChikwenya/MarketEye.git
cd MarketEye

# 2. Create environment file for backend
cp backend/.env.example backend/.env

# 3. Create environment file for frontend
cp frontend/.env.example frontend/.env

# 4. Start all services
docker-compose up -d

# 5. Run database migrations
docker-compose exec backend alembic upgrade head

# 6. Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

That's it! The application should now be running.

## Manual Setup (Without Docker)

### Backend Setup

```bash
cd backend

# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env and configure your settings

# 4. Ensure PostgreSQL is running and create database
createdb marketeye

# 5. Run database migrations
alembic upgrade head

# 6. Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Celery Workers (in separate terminals)

```bash
cd backend
source venv/bin/activate

# Terminal 1: Start Celery worker
celery -A app.celery_app worker --loglevel=info

# Terminal 2: Start Celery beat (scheduler)
celery -A app.celery_app beat --loglevel=info

# Optional - Monitor with Flower
celery -A app.celery_app flower --port=5555
```

### Frontend Setup

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Set up environment variables
cp .env.example .env
# Edit .env if needed

# 3. Start development server
npm run dev
```

## Configuration

### Backend Environment Variables

Edit `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://marketeye:marketeye123@localhost:5432/marketeye
DATABASE_URL_SYNC=postgresql://marketeye:marketeye123@localhost:5432/marketeye

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Twilio (for SMS/Call notifications)
# Sign up at https://www.twilio.com/try-twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Email (Gmail SMTP example)
# For Gmail, create an App Password: https://support.google.com/accounts/answer/185833
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=noreply@marketeye.com
SMTP_FROM_NAME=MarketEye

# Optional: Market Data API Keys
ALPHA_VANTAGE_API_KEY=  # Get free key at https://www.alphavantage.co/support/#api-key
```

### Frontend Environment Variables

Edit `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Third-Party Services Setup

### 1. Twilio (SMS/Voice)

1. Sign up at https://www.twilio.com/try-twilio
2. Get your Account SID and Auth Token from the dashboard
3. Get a Twilio phone number
4. Add credentials to `backend/.env`

### 2. Gmail SMTP (Email)

1. Enable 2-factor authentication on your Google account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Add credentials to `backend/.env`

### 3. Market Data (All Free!)

- **yfinance**: No API key needed! Works out of the box
- **CoinGecko**: Free tier available, no key needed for basic usage
- **Alpha Vantage** (optional): Get free API key at https://www.alphavantage.co/support/#api-key

## Database Migrations

### Create a new migration

```bash
cd backend
alembic revision --autogenerate -m "description of changes"
```

### Apply migrations

```bash
alembic upgrade head
```

### Rollback migration

```bash
alembic downgrade -1
```

## Testing

### Backend Tests

```bash
cd backend
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

## Production Deployment

### Environment Variables

- Set `ENVIRONMENT=production`
- Set `DEBUG=False`
- Use strong `SECRET_KEY` (min 32 characters)
- Use production database credentials
- Configure proper CORS origins

### Security Checklist

- [ ] Change default database credentials
- [ ] Set strong SECRET_KEY
- [ ] Enable HTTPS
- [ ] Configure proper CORS origins
- [ ] Set up firewall rules
- [ ] Enable database backups
- [ ] Set up monitoring and logging
- [ ] Configure rate limiting
- [ ] Use environment variables for secrets (never commit .env)

### Docker Production Build

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

### Monitoring

Access Celery Flower dashboard for worker monitoring:
```bash
# If running manually
celery -A app.celery_app flower --port=5555

# Access at http://localhost:5555
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
pg_isready

# Check if database exists
psql -l | grep marketeye

# Create database if missing
createdb marketeye
```

### Redis Connection Issues

```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG
```

### Celery Workers Not Running

```bash
# Check Redis connection
redis-cli ping

# Check for Python errors in worker logs
celery -A app.celery_app worker --loglevel=debug
```

### Frontend Can't Connect to Backend

1. Check backend is running: http://localhost:8000/health
2. Check CORS origins in `backend/.env`
3. Verify `VITE_API_URL` in `frontend/.env`

### Market Data Not Updating

1. Check Celery worker is running
2. Check Celery beat scheduler is running
3. View logs: `docker-compose logs celery_worker`

## Development Tips

### Hot Reload

- **Backend**: FastAPI auto-reloads on code changes (--reload flag)
- **Frontend**: Vite auto-reloads on code changes

### API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Database GUI

Use a PostgreSQL client like:
- pgAdmin
- DBeaver
- TablePlus

Connection details from `.env` file.

### Redis GUI

Use Redis GUI tools like:
- RedisInsight
- Redis Commander

```bash
# Quick Redis Commander
npm install -g redis-commander
redis-commander
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login (returns JWT token)

### Users
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update current user

### Assets
- `GET /api/v1/assets/search?q={query}` - Search assets
- `GET /api/v1/assets/{id}` - Get asset details
- `GET /api/v1/assets/{id}/price` - Get current price
- `GET /api/v1/assets/{id}/history` - Get price history

### Watchlists
- `GET /api/v1/watchlists` - Get all watchlists
- `POST /api/v1/watchlists` - Create watchlist
- `GET /api/v1/watchlists/{id}` - Get watchlist
- `POST /api/v1/watchlists/{id}/assets` - Add asset
- `DELETE /api/v1/watchlists/{id}/assets/{asset_id}` - Remove asset

### Alerts
- `GET /api/v1/alerts` - Get all alerts
- `POST /api/v1/alerts` - Create alert
- `PUT /api/v1/alerts/{id}` - Update alert
- `DELETE /api/v1/alerts/{id}` - Delete alert

### Portfolio
- `GET /api/v1/portfolio` - Get portfolio
- `POST /api/v1/portfolio/holdings` - Add holding
- `DELETE /api/v1/portfolio/holdings/{id}` - Remove holding

## Support

For issues and questions:
- GitHub Issues: https://github.com/TapiwaChikwenya/MarketEye/issues
- Documentation: See README.md

## License

MIT License - see LICENSE file for details
