# Production Deployment Guide

## FastAPI Backend

### Requirements
- Python 3.10+
- ClickHouse 24+
- Redis 7+
- Docker & Docker Compose (recommended)

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CLICKHOUSE_HOST` | ClickHouse server host | `clickhouse.example.com` |
| `CLICKHOUSE_PORT` | ClickHouse HTTP port | `8123` |
| `CLICKHOUSE_DATABASE` | ClickHouse database name | `reliability_lab` |
| `CLICKHOUSE_USER` | ClickHouse username | `default` |
| `CLICKHOUSE_PASSWORD` | ClickHouse password | `your-secure-password` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `RELIABILITY_ENABLE_EVALS` | Enable evaluator queue | `true` |

### Docker Deployment

```bash
cd infra/docker
docker-compose up -d
```

Services started:
- ClickHouse (port 8123)
- Redis (port 6379)
- API (port 8000)
- Worker (Celery)
- Evaluator
- Dashboard (port 3000)
- Prometheus (port 9090)
- Grafana (port 3001)

### Manual Deployment

1. **Install Python packages:**
```bash
pip install -e packages/shared
pip install -e packages/sdk
pip install -e packages/evals
pip install -e packages/reliability
pip install -e apps/api
```

2. **Start the API:**
```bash
cd apps/api
uvicorn reliability_api.main:app --host 0.0.0.0 --port 8000
```

### Health Checks

- API: `GET /health`
- ClickHouse: `GET http://localhost:8123/ping`
- Redis: `redis-cli ping`

### Scaling

Run multiple API workers:
```bash
uvicorn reliability_api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Or use Gunicorn with Uvicorn workers:
```bash
gunicorn reliability_api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Dashboard (Vercel)

The Next.js dashboard is deployed to Vercel and fetches data from the FastAPI backend.

### Configuration

Set the `NEXT_PUBLIC_API_URL` environment variable in Vercel to point to your API:
```
NEXT_PUBLIC_API_URL=https://api.your-domain.com
```

### Deploy

```bash
cd apps/dashboard
vercel --prod
```

### CORS

Ensure the API has CORS enabled for your Vercel domain:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-dashboard.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## SSL/TLS

Use a reverse proxy (Nginx, Traefik, or AWS ALB) for SSL termination.

Example Nginx config:
```nginx
server {
    listen 443 ssl;
    server_name api.your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Monitoring

- Prometheus metrics: `http://localhost:9090`
- Grafana dashboards: `http://localhost:3001`
- Jaeger traces: `http://localhost:16686`
