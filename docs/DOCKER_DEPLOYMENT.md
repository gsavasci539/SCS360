# Docker and Deployment Plan

## Overview

This document outlines the Docker containerization strategy and deployment procedures for the School Management System.

---

## Docker Architecture

### Container Components

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy                   │
│              (Port 80/443, SSL Termination)              │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌────────▼────────┐
│   Frontend     │          │    Backend      │
│   (React)      │          │   (FastAPI)     │
│   Port 3000    │          │   Port 8000     │
└────────────────┘          └────────┬────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   PostgreSQL       │
                          │   Port 5432        │
                          └───────────────────┘
```

---

## Dockerfiles

### Backend Dockerfile

**File:** `backend/Dockerfile`

```dockerfile
# Multi-stage build for production optimization
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Frontend Dockerfile

**File:** `frontend/Dockerfile`

```dockerfile
# Multi-stage build for production optimization
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

**File:** `nginx/default.conf`

```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name localhost;

    # Frontend static files
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health checks
    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }

    # File uploads (increase size limit)
    location /api/uploads {
        proxy_pass http://backend;
        client_max_body_size 10M;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
}
```

### Frontend Nginx Configuration

**File:** `frontend/nginx.conf`

```nginx
server {
    listen 3000;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Enable gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;

    # Handle client-side routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

---

## Docker Compose Files

### Development Docker Compose

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: school-management-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: school_management
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
      - ./database/seed.sql:/docker-entrypoint-initdb.d/02-seed.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: school-management-backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/school_management
      JWT_SECRET_KEY: dev_secret_key_change_in_production
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30
      REFRESH_TOKEN_EXPIRE_DAYS: 7
      APP_ENV: development
      DEBUG: true
    volumes:
      - ./backend:/app
      - backend_uploads:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: school-management-frontend
    ports:
      - "3000:3000"
    environment:
      VITE_API_BASE_URL: http://localhost:8000/api
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

  nginx:
    image: nginx:alpine
    container_name: school-management-nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  backend_uploads:
```

### Staging Docker Compose

**File:** `docker-compose.staging.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: school-management-db-staging
    environment:
      POSTGRES_USER: ${STAGING_DB_USER}
      POSTGRES_PASSWORD: ${STAGING_DB_PASSWORD}
      POSTGRES_DB: school_management_staging
    volumes:
      - postgres_staging_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${STAGING_DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    image: ${DOCKER_USERNAME}/school-management-backend:develop
    container_name: school-management-backend-staging
    environment:
      DATABASE_URL: postgresql://${STAGING_DB_USER}:${STAGING_DB_PASSWORD}@postgres:5432/school_management_staging
      JWT_SECRET_KEY: ${STAGING_JWT_SECRET}
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30
      REFRESH_TOKEN_EXPIRE_DAYS: 7
      APP_ENV: staging
      DEBUG: false
      CORS_ORIGINS: https://staging.schoolmanagement.com
    volumes:
      - backend_uploads_staging:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    image: ${DOCKER_USERNAME}/school-management-frontend:develop
    container_name: school-management-frontend-staging
    environment:
      VITE_API_BASE_URL: https://staging.schoolmanagement.com/api
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: school-management-nginx-staging
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./nginx/ssl-staging:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

  worker:
    image: ${DOCKER_USERNAME}/school-management-backend:develop
    container_name: school-management-worker-staging
    environment:
      DATABASE_URL: postgresql://${STAGING_DB_USER}:${STAGING_DB_PASSWORD}@postgres:5432/school_management_staging
      APP_ENV: staging
    command: python -m app.infrastructure.notifications.outbox_worker
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_staging_data:
  backend_uploads_staging:
```

### Production Docker Compose

**File:** `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: school-management-db-prod
    environment:
      POSTGRES_USER: ${PROD_DB_USER}
      POSTGRES_PASSWORD: ${PROD_DB_PASSWORD}
      POSTGRES_DB: school_management
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
      - ./backups:/backups
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${PROD_DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  backend:
    image: ${DOCKER_USERNAME}/school-management-backend:main
    container_name: school-management-backend-prod
    environment:
      DATABASE_URL: postgresql://${PROD_DB_USER}:${PROD_DB_PASSWORD}@postgres:5432/school_management
      JWT_SECRET_KEY: ${PROD_JWT_SECRET}
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30
      REFRESH_TOKEN_EXPIRE_DAYS: 7
      APP_ENV: production
      DEBUG: false
      CORS_ORIGINS: https://app.schoolmanagement.com
      LOG_LEVEL: INFO
    volumes:
      - backend_uploads_prod:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  frontend:
    image: ${DOCKER_USERNAME}/school-management-frontend:main
    container_name: school-management-frontend-prod
    environment:
      VITE_API_BASE_URL: https://app.schoolmanagement.com/api
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  nginx:
    image: nginx:alpine
    container_name: school-management-nginx-prod
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./nginx/ssl-prod:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  worker:
    image: ${DOCKER_USERNAME}/school-management-backend:main
    container_name: school-management-worker-prod
    environment:
      DATABASE_URL: postgresql://${PROD_DB_USER}:${PROD_DB_PASSWORD}@postgres:5432/school_management
      APP_ENV: production
      LOG_LEVEL: INFO
    command: python -m app.infrastructure.notifications.outbox_worker
    depends_on:
      - postgres
    restart: unless-stopped
    deploy:
      replicas: 2

  redis:
    image: redis:7-alpine
    container_name: school-management-redis-prod
    volumes:
      - redis_prod_data:/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

volumes:
  postgres_prod_data:
  backend_uploads_prod:
  redis_prod_data:
```

---

## Deployment Procedures

### Local Development Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-org/school-management.git
   cd school-management
   ```

2. **Configure Environment**
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Run Migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **Seed Data**
   ```bash
   docker-compose exec backend python -m app.seed.seed_data
   ```

6. **Access Application**
   - Frontend: http://localhost
   - Backend API: http://localhost/api
   - API Docs: http://localhost/api/docs

### Staging Deployment

1. **Build and Push Images**
   ```bash
   docker build -t your-dockerhub/school-management-backend:develop ./backend
   docker build -t your-dockerhub/school-management-frontend:develop ./frontend
   docker push your-dockerhub/school-management-backend:develop
   docker push your-dockerhub/school-management-frontend:develop
   ```

2. **Deploy to Staging Server**
   ```bash
   ssh user@staging-server
   cd /opt/school-management
   docker-compose -f docker-compose.staging.yml pull
   docker-compose -f docker-compose.staging.yml up -d
   ```

3. **Run Migrations**
   ```bash
   docker-compose -f docker-compose.staging.yml exec -T backend alembic upgrade head
   ```

4. **Health Check**
   ```bash
   curl https://staging.schoolmanagement.com/health
   ```

### Production Deployment

1. **Pre-deployment Checklist**
   - [ ] All tests pass
   - [ ] Code reviewed and approved
   - [ ] Database migrations tested
   - [ ] Backup created
   - [ ] Rollback plan ready

2. **Build and Tag Images**
   ```bash
   docker build -t your-dockerhub/school-management-backend:latest ./backend
   docker build -t your-dockerhub/school-management-frontend:latest ./frontend
   docker tag your-dockerhub/school-management-backend:latest your-dockerhub/school-management-backend:$(date +%Y%m%d)
   docker tag your-dockerhub/school-management-frontend:latest your-dockerhub/school-management-frontend:$(date +%Y%m%d)
   docker push your-dockerhub/school-management-backend:latest
   docker push your-dockerhub/school-management-frontend:latest
   docker push your-dockerhub/school-management-backend:$(date +%Y%m%d)
   docker push your-dockerhub/school-management-frontend:$(date +%Y%m%d)
   ```

3. **Create Backup**
   ```bash
   ssh user@production-server
   cd /opt/school-management
   ./scripts/backup.sh
   ```

4. **Deploy with Zero Downtime**
   ```bash
   docker-compose -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend frontend
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Run Migrations**
   ```bash
   docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
   ```

6. **Health Check**
   ```bash
   curl https://app.schoolmanagement.com/health
   curl https://app.schoolmanagement.com/ready
   ```

7. **Monitor Logs**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f
   ```

---

## SSL/TLS Configuration

### Let's Encrypt Setup

1. **Install Certbot**
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   ```

2. **Generate SSL Certificate**
   ```bash
   sudo certbot --nginx -d app.schoolmanagement.com -d staging.schoolmanagement.com
   ```

3. **Auto-renewal**
   ```bash
   sudo certbot renew --dry-run
   ```

### SSL Configuration in Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name app.schoolmanagement.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... rest of configuration
}

server {
    listen 80;
    server_name app.schoolmanagement.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Monitoring and Logging

### Container Monitoring

```bash
# View container stats
docker stats

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Inspect container
docker inspect school-management-backend-prod
```

### Log Aggregation

**Setup ELK Stack or use cloud service:**
- Elasticsearch for log storage
- Logstash for log processing
- Kibana for log visualization

### Health Monitoring

**Prometheus + Grafana:**
- Expose metrics endpoint
- Configure Prometheus scraping
- Create Grafana dashboards

---

## Backup and Recovery

### Database Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/opt/backups/school-management"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T postgres pg_dump -U postgres school_management > $BACKUP_DIR/db_$TIMESTAMP.sql

# File backup
tar -czf $BACKUP_DIR/files_$TIMESTAMP.tar.gz uploads/

# Cleanup old backups (keep last 30 days)
find $BACKUP_DIR -name "db_*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "files_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
```

### Restore Script

```bash
#!/bin/bash
# scripts/restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh <backup_file>"
    exit 1
fi

# Restore database
docker-compose exec -T postgres psql -U postgres -d school_management < $BACKUP_FILE

echo "Restore completed"
```

---

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs backend

# Check resource usage
docker stats

# Restart container
docker-compose restart backend
```

**Database connection issues:**
```bash
# Check if postgres is running
docker-compose ps postgres

# Test connection
docker-compose exec backend python -c "from app.core.database import engine; print(engine.connect())"
```

**Migration issues:**
```bash
# Check migration status
docker-compose exec backend alembic current

# Rollback migration
docker-compose exec backend alembic downgrade -1

# Force migration
docker-compose exec backend alembic stamp head
```

**Nginx issues:**
```bash
# Test nginx configuration
docker-compose exec nginx nginx -t

# Reload nginx
docker-compose exec nginx nginx -s reload
```

---

## Security Best Practices

1. **Use non-root users in containers**
2. **Scan images for vulnerabilities**
3. **Keep images updated**
4. **Use secrets management for sensitive data**
5. **Enable SSL/TLS**
6. **Implement rate limiting**
7. **Regular security audits**
8. **Network segmentation**
9. **Regular backups**
10. **Monitor container activity**

---

## Performance Optimization

### Backend Optimization

- Use Gunicorn with multiple workers
- Enable database connection pooling
- Implement caching with Redis
- Use async operations where possible
- Optimize database queries

### Frontend Optimization

- Enable gzip compression
- Implement CDN for static assets
- Use lazy loading for images
- Minify JavaScript and CSS
- Implement service worker for caching

### Database Optimization

- Regular vacuum and analyze
- Optimize indexes
- Use connection pooling
- Monitor slow queries
- Implement read replicas for scaling
