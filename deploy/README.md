# SmallAI Deployment Guide

## Quick Start with Docker

### Option 1: Docker Compose (Recommended)

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 2: Docker CLI

```bash
# Build the image
./deploy/build.sh

# Run the container
docker run -d \
  -p 8000:8000 \
  --name smallai \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/reports:/app/reports \
  smallai:latest

# View logs
docker logs -f smallai

# Stop and remove
docker stop smallai && docker rm smallai
```

### Option 3: Manual Build

```bash
# Build image
docker build -f deploy/Dockerfile -t smallai:latest .

# Run container
docker run -d -p 8000:8000 smallai:latest
```

## API Endpoints

Once running, the API is available at `http://localhost:8000`

### Health Check
```bash
curl http://localhost:8000/health
```

### Parse Query
```bash
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"query": "show failed logins from yesterday"}'
```

## Environment Variables

- `PYTHONUNBUFFERED=1` - Unbuffered Python output
- `LOG_LEVEL` - Logging level (default: info)

## Volumes

- `/app/logs` - Application logs
- `/app/reports` - Training/validation reports
- `/app/models` - ML model files (optional mount)

## Image Details

- **Base**: Python 3.12-slim
- **Port**: 8000
- **Workers**: 2 (uvicorn)
- **Health Check**: Every 30s

## Troubleshooting

### Check container status
```bash
docker ps -a | grep smallai
```

### View container logs
```bash
docker logs smallai
```

### Exec into container
```bash
docker exec -it smallai /bin/bash
```

### Test parsing manually
```bash
docker exec smallai python hybrid_parser.py "show 404 errors"
```

## Production Deployment

For production, consider:

1. **Use a reverse proxy** (nginx, traefik)
2. **Enable HTTPS** with SSL certificates
3. **Set resource limits** in docker-compose
4. **Use Docker secrets** for sensitive data
5. **Monitor with** Prometheus + Grafana
6. **Scale with** Kubernetes or Docker Swarm

Example with nginx reverse proxy:

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - smallai
```
