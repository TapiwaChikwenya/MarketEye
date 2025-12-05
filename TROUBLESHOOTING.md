# MarketEye - Troubleshooting Guide

## Quick Fix - Complete Reset

If you're having any issues, run this to completely reset and reinitialize:

```bash
cd MarketEye
./init-demo.sh
```

This will:
1. Create .env files
2. Stop and remove all containers
3. Start fresh containers
4. Run database migrations
5. Test all endpoints
6. Confirm everything works

---

## Common Issues & Solutions

### 1. Registration Not Working

**Symptoms:**
- Registration form doesn't submit
- Gets error message
- Page refreshes but nothing happens

**Solutions:**

```bash
# Check if database migrations ran
docker compose exec backend alembic current

# If no output, run migrations
docker compose exec backend alembic upgrade head

# Check backend logs for errors
docker compose logs backend --tail=50

# Test registration endpoint directly
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","name":"Test"}'
```

**Expected Response:**
```json
{
  "id": "...",
  "email": "test@example.com",
  "name": "Test",
  ...
}
```

---

### 2. Frontend Not Loading / White Screen

**Symptoms:**
- Blank white screen
- "Cannot find module" errors
- Build errors in console

**Solutions:**

```bash
# Option 1: Restart frontend
docker compose restart frontend

# Option 2: Rebuild frontend
docker compose down frontend
docker compose up -d --build frontend

# Option 3: Clear node_modules and rebuild
docker compose down
docker volume rm marketeye_frontend_node_modules 2>/dev/null
docker compose up -d --build

# Check frontend logs
docker compose logs frontend --tail=100
```

---

### 3. Port Conflicts

**Symptoms:**
- "port is already allocated"
- "bind: address already in use"

**Solutions:**

The docker-compose.yml already uses non-standard ports:
- PostgreSQL: 5433 (not 5432)
- Redis: 6380 (not 6379)
- Frontend: 5173
- Backend: 8000

If you still have conflicts:

```bash
# Check what's using the ports
lsof -i :5173
lsof -i :8000

# Stop conflicting services or change ports in docker-compose.yml
```

---

### 4. Database Connection Failed

**Symptoms:**
- Backend crashes on startup
- "database does not exist" error
- Connection timeout errors

**Solutions:**

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check PostgreSQL logs
docker compose logs postgres

# Wait for PostgreSQL to be ready
docker compose exec postgres pg_isready -U marketeye

# Recreate database
docker compose down -v
docker compose up -d postgres
sleep 10
docker compose up -d

# Run migrations
docker compose exec backend alembic upgrade head
```

---

### 5. CORS Errors in Browser

**Symptoms:**
- "CORS policy: No 'Access-Control-Allow-Origin' header"
- API calls fail from frontend
- Network errors in browser console

**Solutions:**

Check `backend/.env` has correct CORS settings:

```env
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

Then restart backend:

```bash
docker compose restart backend
```

---

### 6. Login Not Working

**Symptoms:**
- "Incorrect email or password" even with correct credentials
- Login form submits but nothing happens

**Solutions:**

```bash
# Test login endpoint directly
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123"

# Should return:
# {"access_token":"...","token_type":"bearer"}

# Check if user exists in database
docker compose exec postgres psql -U marketeye -d marketeye \
  -c "SELECT email, is_active FROM users;"

# Check backend logs for auth errors
docker compose logs backend --tail=50 | grep -i auth
```

---

### 7. No Market Data / Prices Not Updating

**Symptoms:**
- Asset tiles show no prices
- Landing page has no data
- "Unable to fetch price data" errors

**Solutions:**

```bash
# Check Celery worker is running
docker compose ps celery_worker

# Check worker logs
docker compose logs celery_worker --tail=50

# Should see:
# "Updated prices for X/Y assets"
# "Evaluated X alerts"

# Manually trigger price update
docker compose exec backend python -c "
from app.workers.market_data import _update_all_asset_prices
import asyncio
asyncio.run(_update_all_asset_prices())
"

# Test market data API directly
curl http://localhost:8000/api/v1/public/trending
```

---

### 8. Celery Workers Not Starting

**Symptoms:**
- No price updates
- Alerts not triggering
- Worker logs show errors

**Solutions:**

```bash
# Check Redis is running
docker compose ps redis
docker compose exec redis redis-cli ping
# Should return: PONG

# Restart workers
docker compose restart celery_worker celery_beat

# Check worker status
docker compose logs celery_worker --tail=100
docker compose logs celery_beat --tail=100

# Should see:
# celery@... ready
# celerybeat@... beat: Starting...
```

---

### 9. Dashboard Not Loading After Login

**Symptoms:**
- Login succeeds but dashboard is blank
- Redirected to login again
- Token issues

**Solutions:**

```bash
# Check browser console for errors
# Open DevTools > Console

# Check if token is stored
# Open DevTools > Application > Local Storage
# Should see 'token' key

# Test if backend accepts the token
# Get token from localStorage, then:
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Should return user info

# Clear localStorage and try again
# In browser console:
localStorage.clear()
# Then refresh and login again
```

---

### 10. Build Errors

**Symptoms:**
- "Cannot find module" errors
- TypeScript errors
- Import errors

**Solutions:**

For Frontend:
```bash
# Rebuild with no cache
docker compose build --no-cache frontend
docker compose up -d frontend

# Or shell into container and debug
docker compose exec frontend sh
npm install
npm run build
```

For Backend:
```bash
# Rebuild backend
docker compose build --no-cache backend
docker compose up -d backend

# Check Python errors
docker compose logs backend
```

---

## Testing Checklist

Run these tests to verify everything works:

```bash
# Run comprehensive test
./test-system.sh

# Manual tests:

# 1. Backend health
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# 2. Public API
curl http://localhost:8000/api/v1/public/trending
# Expected: JSON with stocks and crypto

# 3. Frontend
curl -I http://localhost:5173
# Expected: HTTP/1.1 200 OK

# 4. Registration
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"new@test.com","password":"pass123","name":"New User"}'
# Expected: User JSON

# 5. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=new@test.com&password=pass123"
# Expected: {"access_token":"...","token_type":"bearer"}
```

---

## Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f celery_worker
docker compose logs -f postgres

# Last 100 lines
docker compose logs backend --tail=100

# Follow logs (live)
docker compose logs -f backend

# Search logs
docker compose logs backend | grep ERROR
docker compose logs backend | grep -i auth
```

---

## Database Commands

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U marketeye -d marketeye

# Once connected, run SQL:
\dt                    # List tables
\d users              # Describe users table
SELECT * FROM users;  # View all users
SELECT COUNT(*) FROM alert_rules;  # Count alerts
\q                    # Quit

# Direct SQL from command line
docker compose exec postgres psql -U marketeye -d marketeye \
  -c "SELECT email FROM users;"
```

---

## Redis Commands

```bash
# Connect to Redis
docker compose exec redis redis-cli

# Once connected:
PING              # Test connection
KEYS *            # List all keys
GET key_name      # Get value
FLUSHALL          # Clear all data (careful!)
```

---

## Complete Reset

If nothing else works, nuclear option:

```bash
# Stop and remove everything
docker compose down -v

# Remove all MarketEye volumes
docker volume ls | grep marketeye | awk '{print $2}' | xargs docker volume rm

# Remove images
docker images | grep marketeye | awk '{print $3}' | xargs docker rmi

# Start fresh
./init-demo.sh
```

---

## Getting Help

1. **Check logs first:**
   ```bash
   docker compose logs backend --tail=100
   docker compose logs frontend --tail=100
   ```

2. **Run system test:**
   ```bash
   ./test-system.sh
   ```

3. **Check browser console:**
   - Open DevTools (F12)
   - Check Console tab for errors
   - Check Network tab for failed requests

4. **Verify services are running:**
   ```bash
   docker compose ps
   ```
   All should show "Up" or "running"

5. **Check the DEMO.md guide** for expected behavior

---

## Still Having Issues?

1. Make sure Docker is running
2. Make sure you have enough disk space
3. Check Docker logs: `docker compose logs`
4. Try the complete reset above
5. Check if ports 5173, 8000, 5433, 6380 are available

---

**Remember**: The app is designed to work WITHOUT any external services. No Twilio, no SMTP, no API keys needed. Everything should work in demo mode!
