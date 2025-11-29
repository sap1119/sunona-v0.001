# Deployment Guide

This guide covers how to deploy Sunona to a production environment.

## 🏗️ Architecture Overview

The platform consists of several dockerized services:
- **API Server (FastAPI)**: Handles business logic and API requests.
- **Worker/Orchestrator**: Manages real-time voice sessions (WebSocket).
- **Frontend (React)**: Admin dashboard.
- **PostgreSQL**: Persistent storage for agents, users, and logs.
- **Redis**: Message broker and ephemeral state for active calls.

## 🚀 Production Setup (Docker)

### 1. Server Requirements
- **CPU**: 2+ vCPUs recommended (for handling concurrent WebSocket connections).
- **RAM**: 4GB+ RAM.
- **OS**: Ubuntu 20.04/22.04 LTS (recommended).

### 2. Clone & Configure
```bash
git clone https://github.com/sap1119/sunona-v0.001.git
cd sunona-v0.001
cp local_setup/.env.sample .env
```

Edit `.env` with your production keys. **Important**:
- Set `ENVIRONMENT=production`
- Change `JWT_SECRET_KEY` to a strong random string.
- Set `POSTGRES_PASSWORD` to a strong password.

### 3. Docker Compose
Use the production compose file (if available) or modify the default one to restart on failure.

```bash
docker-compose -f docker-compose.yml up -d --build
```

## 🔒 SSL/TLS & Domain

For WebRTC and Telephony webhooks to work, **SSL is required**.

### Using Nginx & Certbot (Recommended)
Set up Nginx as a reverse proxy in front of the docker containers.

**Nginx Config Example:**
```nginx
server {
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

Run Certbot to get a free certificate:
```bash
sudo certbot --nginx -d api.yourdomain.com
```

## 📈 Scaling

### Horizontal Scaling
The system is designed to be stateless (state is stored in Redis/Postgres).
- **API Server**: Can be scaled horizontally behind a load balancer.
- **Orchestrator**: Can be scaled, but ensure sticky sessions or proper Redis Pub/Sub routing for WebSocket connections.

### Database
- Use a managed PostgreSQL instance (AWS RDS, Google Cloud SQL, Supabase) for better reliability than a local docker container.
- Use a managed Redis (AWS ElastiCache, Upstash) for production.

## 🛠️ Monitoring & Logs

- **Logs**: View logs via Docker:
  ```bash
  docker-compose logs -f --tail=100
  ```
- **Metrics**: The platform exposes Prometheus-compatible metrics at `/metrics` (if enabled).

## 🔄 Updates

To update to the latest version:
```bash
git pull origin main
docker-compose down
docker-compose up -d --build
```
