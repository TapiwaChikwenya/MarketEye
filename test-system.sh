#!/bin/bash

echo "🔍 MarketEye - Complete System Test & Fix"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Function to print info
print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

echo "1️⃣ Checking Docker containers..."
docker compose ps

echo ""
echo "2️⃣ Checking if database is ready..."
sleep 5
docker compose exec -T postgres pg_isready -U marketeye
print_status $? "PostgreSQL is ready"

echo ""
echo "3️⃣ Running database migrations..."
docker compose exec -T backend alembic upgrade head
print_status $? "Database migrations completed"

echo ""
echo "4️⃣ Testing backend health..."
health_response=$(curl -s http://localhost:8000/health)
if [[ $health_response == *"healthy"* ]]; then
    print_status 0 "Backend is healthy"
else
    print_status 1 "Backend health check failed"
    echo "Response: $health_response"
fi

echo ""
echo "5️⃣ Testing public API endpoint..."
trending_response=$(curl -s http://localhost:8000/api/v1/public/trending)
if [[ $trending_response == *"stocks"* ]]; then
    print_status 0 "Public API is working"
else
    print_status 1 "Public API failed"
    echo "Response: $trending_response"
fi

echo ""
echo "6️⃣ Testing registration endpoint..."
register_payload='{"email":"test@example.com","password":"testpass123","name":"Test User"}'
register_response=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "$register_payload" \
  http://localhost:8000/api/v1/auth/register)

if [[ $register_response == *"email"* ]] || [[ $register_response == *"already registered"* ]]; then
    print_status 0 "Registration endpoint is working"
    echo "Response preview: ${register_response:0:100}..."
else
    print_status 1 "Registration endpoint failed"
    echo "Response: $register_response"
fi

echo ""
echo "7️⃣ Testing login endpoint..."
login_response=$(curl -s -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpass123" \
  http://localhost:8000/api/v1/auth/login)

if [[ $login_response == *"access_token"* ]]; then
    print_status 0 "Login endpoint is working"
    # Extract token
    token=$(echo $login_response | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    echo "Token preview: ${token:0:20}..."
else
    print_status 1 "Login endpoint failed"
    echo "Response: $login_response"
fi

echo ""
echo "8️⃣ Checking frontend..."
frontend_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173)
if [ "$frontend_status" == "200" ]; then
    print_status 0 "Frontend is accessible"
else
    print_status 1 "Frontend returned HTTP $frontend_status"
fi

echo ""
echo "9️⃣ Checking Celery worker..."
worker_logs=$(docker compose logs celery_worker --tail=10 2>&1)
if [[ $worker_logs == *"ready"* ]] || [[ $worker_logs == *"mingle"* ]]; then
    print_status 0 "Celery worker is running"
else
    print_status 1 "Celery worker may not be ready"
fi

echo ""
echo "🔟 Checking Celery beat..."
beat_logs=$(docker compose logs celery_beat --tail=10 2>&1)
if [[ $beat_logs == *"beat"* ]] || [[ $beat_logs == *"Scheduler"* ]]; then
    print_status 0 "Celery beat is running"
else
    print_status 1 "Celery beat may not be ready"
fi

echo ""
echo "=========================================="
echo "📊 Summary"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  • Frontend:  http://localhost:5173"
echo "  • Backend:   http://localhost:8000"
echo "  • API Docs:  http://localhost:8000/docs"
echo ""
echo "Test Credentials (if created):"
echo "  • Email:     test@example.com"
echo "  • Password:  testpass123"
echo ""
echo "Next Steps:"
echo "  1. Open http://localhost:5173 in your browser"
echo "  2. Click 'Get Started Free'"
echo "  3. Register with a new email"
echo "  4. Check your browser console for any errors"
echo ""
echo "Troubleshooting:"
echo "  • Frontend logs: docker compose logs frontend"
echo "  • Backend logs:  docker compose logs backend"
echo "  • Database logs: docker compose logs postgres"
echo ""
