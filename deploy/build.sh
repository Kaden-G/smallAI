#!/bin/bash
# SmallAI Docker Build Script

set -e

echo "🚀 Building SmallAI Docker Image..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Build image
docker build -f deploy/Dockerfile -t smallai:latest -t smallai:2.0 .

echo "✅ Build complete!"
echo ""
echo "To run the container:"
echo "  docker run -d -p 8000:8000 --name smallai smallai:latest"
echo ""
echo "Or use docker-compose:"
echo "  docker-compose up -d"
echo ""
echo "To test the API:"
echo "  curl http://localhost:8000/health"
