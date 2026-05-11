# AI Daily Digest Bot - Setup for Windows (PowerShell)

echo "🤖 AI Daily Digest Bot - Setup"

# Check for Docker
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    echo "❌ Docker not found. Please install Docker Desktop first."
    exit
}

# Create directories
if (!(Test-Path data)) { New-Item -ItemType Directory data }
if (!(Test-Path logs)) { New-Item -ItemType Directory logs }

# Setup .env
if (!(Test-Path .env)) {
    echo "📝 Creating .env from template..."
    Copy-Item .env.example .env
    echo "⚠️  Configure .env with your real tokens!"
}

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
