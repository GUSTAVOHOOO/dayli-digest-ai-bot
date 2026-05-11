#!/bin/bash
set -e

echo "🤖 AI Daily Digest Bot - Setup"

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Create directories
mkdir -p data logs scripts

# Setup .env
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Configure .env with your real tokens!"
fi

# Build
echo "🔨 Building Docker images..."
docker-compose build

# Start
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "✅ Setup complete!"
echo "   Status: docker-compose ps"
echo "   Logs: docker-compose logs -f"
