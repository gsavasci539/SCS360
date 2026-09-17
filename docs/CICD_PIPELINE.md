# CI/CD Pipeline Plan

## Overview

This document outlines the CI/CD pipeline strategy for the School Management System using GitHub Actions.

## Branch Strategy

```
main (production)
  ↑
develop (staging)
  ↑
feature/* (feature branches)
  ↑
bugfix/* (bug fix branches)
  ↑
hotfix/* (emergency production fixes)
```

**Branch Rules:**
- `main`: Production-ready code, protected branch
- `develop`: Integration branch for staging
- `feature/*`: Feature development branches
- `bugfix/*`: Bug fix branches
- `hotfix/*`: Emergency fixes for production

---

## GitHub Actions Workflows

### 1. Backend CI Pipeline

**File:** `.github/workflows/backend-ci.yml`

**Triggers:**
- Push to `main`, `develop`, `feature/*`, `bugfix/*`
- Pull request to `main` or `develop`

**Steps:**

```yaml
name: Backend CI

on:
  push:
    branches: [ main, develop, 'feature/*', 'bugfix/*' ]
  pull_request:
    branches: [ main, develop ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install ruff black mypy
      - name: Run Ruff linter
        run: |
          cd backend
          ruff check .
      - name: Run Black format check
        run: |
          cd backend
          black --check .

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install mypy
      - name: Run MyPy type check
        run: |
          cd backend
          mypy app/

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
        run: |
          cd backend
          pytest --cov=app --cov-report=xml --cov-report=term
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

### 2. Frontend CI Pipeline

**File:** `.github/workflows/frontend-ci.yml`

**Triggers:**
- Push to `main`, `develop`, `feature/*`, `bugfix/*`
- Pull request to `main` or `develop`

**Steps:**

```yaml
name: Frontend CI

on:
  push:
    branches: [ main, develop, 'feature/*', 'bugfix/*' ]
  pull_request:
    branches: [ main, develop ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run ESLint
        run: |
          cd frontend
          npm run lint

  format-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run Prettier check
        run: |
          cd frontend
          npm run format:check

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run TypeScript check
        run: |
          cd frontend
          npx tsc --noEmit

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run Vitest tests
        run: |
          cd frontend
          npm run test:ci

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Build frontend
        run: |
          cd frontend
          npm run build
      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: frontend-build
          path: frontend/dist
```

### 3. Docker Build Pipeline

**File:** `.github/workflows/docker-build.yml`

**Triggers:**
- Push to `main`, `develop`
- Manual trigger

**Steps:**

```yaml
name: Docker Build

on:
  push:
    branches: [ main, develop ]
  workflow_dispatch:

jobs:
  build-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Build and push backend image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          file: ./backend/Dockerfile
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/school-management-backend:${{ github.ref_name }}
            ${{ secrets.DOCKER_USERNAME }}/school-management-backend:${{ github.sha }}
          cache-from: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/school-management-backend:buildcache
          cache-to: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/school-management-backend:buildcache,mode=max

  build-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Build and push frontend image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          file: ./frontend/Dockerfile
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/school-management-frontend:${{ github.ref_name }}
            ${{ secrets.DOCKER_USERNAME }}/school-management-frontend:${{ github.sha }}
          cache-from: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/school-management-frontend:buildcache
          cache-to: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/school-management-frontend:buildcache,mode=max
```

### 4. Staging Deployment Pipeline

**File:** `.github/workflows/deploy-staging.yml`

**Triggers:**
- Push to `develop` branch

**Steps:**

```yaml
name: Deploy to Staging

on:
  push:
    branches: [ develop ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.schoolmanagement.com
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to staging server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /opt/school-management
            docker-compose -f docker-compose.staging.yml pull
            docker-compose -f docker-compose.staging.yml up -d
            docker-compose -f docker-compose.staging.yml exec -T backend alembic upgrade head
            docker-compose -f docker-compose.staging.yml exec -T backend python -m app.seed.seed_data
      
      - name: Health check
        run: |
          sleep 30
          curl -f https://staging.schoolmanagement.com/health || exit 1
      
      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Staging Deployment Failed',
              body: 'Deployment to staging failed. Please check the logs.',
              labels: ['deployment', 'staging']
            })
```

### 5. Production Deployment Pipeline

**File:** `.github/workflows/deploy-production.yml`

**Triggers:**
- Push to `main` branch (requires manual approval)
- Manual workflow dispatch

**Steps:**

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://app.schoolmanagement.com
    steps:
      - uses: actions/checkout@v4
      
      - name: Create backup
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/school-management
            ./scripts/backup.sh
      
      - name: Deploy to production server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/school-management
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d
            docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
      
      - name: Health check
        run: |
          sleep 30
          curl -f https://app.schoolmanagement.com/health || exit 1
          curl -f https://app.schoolmanagement.com/ready || exit 1
      
      - name: Rollback on failure
        if: failure()
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/school-management
            ./scripts/rollback.sh
      
      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Production Deployment Failed',
              body: 'Deployment to production failed. Rollback initiated.',
              labels: ['deployment', 'production', 'critical']
            })
```

---

## Environment Configuration

### Staging Environment (.env.staging)

```bash
# Database
DATABASE_URL=postgresql://staging_user:staging_pass@db-staging:5432/school_management_staging

# JWT
JWT_SECRET_KEY=staging_secret_key_change_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# SMTP
SMTP_HOST=smtp.staging.example.com
SMTP_PORT=587
SMTP_USER=staging@example.com
SMTP_PASSWORD=staging_password
SMTP_FROM_EMAIL=noreply-staging@example.com

# SMS
SMS_PROVIDER=netgsm
SMS_API_URL=https://api.netgsm.com
SMS_USERNAME=staging_user
SMS_PASSWORD=staging_pass

# WhatsApp
WHATSAPP_PROVIDER=meta
WHATSAPP_API_URL=https://graph.facebook.com
WHATSAPP_ACCESS_TOKEN=staging_token
WHATSAPP_PHONE_NUMBER_ID=staging_phone_id

# CORS
CORS_ORIGINS=https://staging.schoolmanagement.com

# App
APP_ENV=staging
DEBUG=true
LOG_LEVEL=DEBUG
```

### Production Environment (.env.production)

```bash
# Database
DATABASE_URL=postgresql://prod_user:prod_pass@db-prod:5432/school_management

# JWT
JWT_SECRET_KEY=production_secret_key_very_secure
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# SMTP
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=notifications@example.com
SMTP_PASSWORD=production_password
SMTP_FROM_EMAIL=noreply@example.com

# SMS
SMS_PROVIDER=netgsm
SMS_API_URL=https://api.netgsm.com
SMS_USERNAME=production_user
SMS_PASSWORD=production_pass

# WhatsApp
WHATSAPP_PROVIDER=meta
WHATSAPP_API_URL=https://graph.facebook.com
WHATSAPP_ACCESS_TOKEN=production_token
WHATSAPP_PHONE_NUMBER_ID=production_phone_id

# CORS
CORS_ORIGINS=https://app.schoolmanagement.com

# App
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
```

---

## Pull Request Rules

### Required Checks

Before merging a PR to `main` or `develop`, the following checks must pass:

**Backend:**
- Ruff lint check
- Black format check
- MyPy type check
- Pytest tests (minimum 80% coverage)
- Docker build

**Frontend:**
- ESLint check
- Prettier format check
- TypeScript check
- Vitest tests (minimum 80% coverage)
- Build check

### PR Requirements

1. **Branch Naming:**
   - Features: `feature/description`
   - Bug fixes: `bugfix/description`
   - Hotfixes: `hotfix/description`

2. **Commit Messages:**
   - Follow conventional commits format
   - Examples: `feat: add student management`, `fix: payment calculation error`

3. **Description:**
   - Describe what the PR does
   - List related issues
   - Include screenshots for UI changes
   - Document breaking changes

4. **Reviewers:**
   - At least one code review required
   - Technical lead approval for `main` merges

---

## Deployment Strategy

### Blue-Green Deployment (Production)

**Process:**
1. Deploy new version to green environment
2. Run health checks on green environment
3. Switch traffic from blue to green
4. Keep blue environment for rollback
5. Monitor for issues
6. Decommission blue after successful deployment

### Rolling Update (Staging)

**Process:**
1. Update containers one by one
2. Health check after each container update
3. Continue until all containers updated
4. If failure occurs, stop and rollback

---

## Rollback Plan

### Automatic Rollback Triggers

- Health check failure
- Critical error rate increase
- Database migration failure
- Significant performance degradation

### Manual Rollback Procedure

1. **Database Rollback:**
   ```bash
   docker-compose exec backend alembic downgrade -1
   ```

2. **Application Rollback:**
   ```bash
   docker-compose pull school-management-backend:previous_tag
   docker-compose up -d
   ```

3. **Full System Rollback:**
   ```bash
   ./scripts/rollback.sh
   ```

### Rollback Script

```bash
#!/bin/bash
# scripts/rollback.sh

BACKUP_DIR="/opt/backups/school-management"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Restore database backup
docker-compose exec -T postgres psql -U postgres -d school_management < $BACKUP_DIR/db_$TIMESTAMP.sql

# Rollback application
docker-compose pull school-management-backend:previous
docker-compose pull school-management-frontend:previous
docker-compose up -d

echo "Rollback completed"
```

---

## Monitoring and Alerts

### Health Check Endpoints

- `/health` - Basic health check
- `/ready` - Readiness check (database connection)
- `/metrics` - Application metrics (Prometheus)

### Monitoring Tools

- **Application:** Prometheus + Grafana
- **Logs:** ELK Stack (Elasticsearch, Logstash, Kibana)
- **Uptime:** UptimeRobot or similar
- **Error Tracking:** Sentry

### Alert Conditions

- Health check failure for > 5 minutes
- Error rate > 5% for > 10 minutes
- Response time > 2 seconds for > 5 minutes
- Database connection failure
- Disk space < 20%
- Memory usage > 90%

---

## Secrets Management

### GitHub Secrets

Required secrets for CI/CD:

```
DOCKER_USERNAME
DOCKER_PASSWORD
STAGING_HOST
STAGING_USER
STAGING_SSH_KEY
PRODUCTION_HOST
PRODUCTION_USER
PRODUCTION_SSH_KEY
CODECOV_TOKEN
SENTRY_DSN
```

### Environment Variables

Sensitive data stored in environment variables:
- Database credentials
- JWT secret keys
- API keys (SMS, WhatsApp, Email)
- Third-party service credentials

---

## Backup Strategy

### Database Backups

**Schedule:**
- Daily full backups at 2:00 AM
- Hourly incremental backups
- Retention: 30 days

**Backup Script:**

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

### Application Backups

- Docker images pushed to Docker Hub
- Source code in Git repository
- Configuration files backed up separately

---

## Performance Testing

### Load Testing

**Tools:** k6, Locust

**Test Scenarios:**
- Normal load: 100 concurrent users
- Peak load: 500 concurrent users
- Stress test: 1000 concurrent users

**Metrics to Monitor:**
- Response time
- Error rate
- Throughput
- CPU/Memory usage
- Database query time

---

## Security Scanning

### Dependency Scanning

**Tools:** Dependabot, Snyk

**Schedule:** Weekly

### Container Scanning

**Tools:** Trivy, Clair

**Schedule:** On every build

### Code Scanning

**Tools:** SonarQube, CodeQL

**Schedule:** On every PR

---

## Documentation

### Deployment Documentation

- Runbook for common operations
- Emergency contact information
- Troubleshooting guide
- Architecture diagrams

### Change Log

Maintain CHANGELOG.md with:
- Version numbers
- Release dates
- New features
- Bug fixes
- Breaking changes
- Migration instructions
