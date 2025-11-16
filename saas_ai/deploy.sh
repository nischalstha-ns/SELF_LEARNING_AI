#!/bin/bash

# AI Learning SaaS Deployment Script

echo "🚀 Deploying AI Learning SaaS Platform..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p database
mkdir -p logs

# Set environment variables
echo "🔧 Setting up environment..."
export SECRET_KEY=$(openssl rand -hex 32)
echo "Generated SECRET_KEY: $SECRET_KEY"

# Build and start services
echo "🏗️ Building and starting services..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running successfully!"
    echo ""
    echo "🌐 Access your SaaS platform:"
    echo "   Frontend: http://localhost"
    echo "   Backend API: http://localhost/api"
    echo "   API Documentation: http://localhost/api/docs"
    echo ""
    echo "👤 Test Account:"
    echo "   Email: admin@example.com"
    echo "   Password: admin123"
    echo ""
    echo "📊 Next Steps:"
    echo "   1. Register a new account"
    echo "   2. Create your first AI model"
    echo "   3. Start making predictions"
    echo "   4. Monitor usage in dashboard"
else
    echo "❌ Failed to start services. Check logs:"
    docker-compose logs
fi