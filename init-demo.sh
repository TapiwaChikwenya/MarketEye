#!/bin/bash

echo "🚀 MarketEye - Complete Demo Initialization"
echo "==========================================="
echo ""

# Create backend .env if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "📝 Creating backend/.env file..."
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env"
else
    echo "✅ backend/.env already exists"
fi

# Create frontend .env if it doesn't exist
if [ ! -f frontend/.env ]; then
    echo "📝 Creating frontend/.env file..."
    cp frontend/.env.example frontend/.env
    echo "✅ Created frontend/.env"
else
    echo "✅ frontend/.env already exists"
fi

echo ""
echo "🐳 Starting Docker containers..."
docker compose down -v
docker compose up -d

echo ""
echo "⏳ Waiting for services to be ready (30 seconds)..."
sleep 30

echo ""
echo "🗄️  Running database migrations..."
docker compose exec -T backend alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully"
else
    echo "⚠️  Migration failed, retrying in 5 seconds..."
    sleep 5
    docker compose exec -T backend alembic upgrade head
fi

echo ""
echo "🔄 Restarting frontend to ensure clean build..."
docker compose restart frontend

echo ""
echo "⏳ Waiting for frontend to rebuild (20 seconds)..."
sleep 20

echo ""
echo "==========================================="
echo "✅ Initialization Complete!"
echo "==========================================="
echo ""
echo "📊 Testing system..."
echo ""

./test-system.sh

echo ""
echo "🎉 MarketEye is ready!"
echo ""
echo "Open in your browser: http://localhost:5173"
echo ""
