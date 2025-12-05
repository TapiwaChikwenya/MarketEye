#!/bin/bash

echo "🔧 Pulling latest fixes..."
git pull

echo ""
echo "🔄 Restarting frontend container..."
docker compose restart frontend

echo ""
echo "⏳ Waiting for frontend to rebuild (30 seconds)..."
sleep 30

echo ""
echo "✅ Frontend should now be accessible at http://localhost:5173"
echo ""
echo "📊 Checking container status..."
docker compose ps

echo ""
echo "💡 If you still see issues, run: docker compose logs frontend"
