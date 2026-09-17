# Security Plan

## Overview

This document outlines the comprehensive security strategy for the School Management System, covering authentication, authorization, data protection, and operational security.

---

## Authentication Security

### JWT Token Management

**Access Token:**
- Algorithm: HS256
- Expiration: 30 minutes
- Storage: HttpOnly cookie or localStorage (with XSS protection)
- Payload: User ID, organization ID, permissions, expiration

**Refresh Token:**
- Algorithm: HS256
- Expiration: 7 days
- Storage: HttpOnly cookie
- Rotation: On every refresh
- Revocation: Database-backed with expiration tracking

**Token Security:**
```python
# Token generation
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    token_data = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid4())  # Unique token ID
    }
    token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    # Store in database for revocation
    store_refresh_token(user_id, token, expire)
    return token
```

### Password Security

**Password Requirements:**
- Minimum length: 8 characters
- Must include: uppercase, lowercase, number, special character
- No common passwords (check against breached passwords list)
- No personal information (name, email, etc.)

**Password Hashing:**
```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
```

**Password Reset Flow:**
1. User requests reset with email
2. Generate secure token (UUID + timestamp)
3. Send email with reset link (valid 1 hour)
4. User sets new password
5. Invalidate all existing refresh tokens
6. Log password reset event

### Login Attempt Tracking

**Implementation:**
```python
# Track failed login attempts
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 30  # minutes

def track_login_attempt(email: str, success: bool):
    if success:
        # Reset counter on successful login
        reset_login_counter(email)
    else:
        # Increment counter
        attempts = increment_login_counter(email)
        if attempts >= MAX_LOGIN_ATTEMPTS:
            lock_user_account(email, LOCKOUT_DURATION)
            send_lockout_notification(email)
```

---

## Authorization Security

### Role-Based Access Control (RBAC)

**Role Hierarchy:**
1. Super Admin - Full system access
2. Kurum Admini - Organization-level access
3. Şube Yetkilisi - Branch-level access
4. Öğretmen - Class-level access
5. Muhasebe - Finance module access
6. Personel - Limited access

**Permission Matrix:**
- Granular permissions for each action
- Permission inheritance from roles
- Permission checking at every protected endpoint

**Implementation:**
```python
from functools import wraps
from fastapi import HTTPException, Depends

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if not has_permission(current_user, permission):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def has_permission(user: User, permission: str) -> bool:
    user_permissions = get_user_permissions(user.id)
    return permission in user_permissions
```

### Organization and Branch Isolation

**Multi-tenancy Strategy:**
- Every request includes organization context
- Database queries filtered by organization_id
- Branch-level data filtered by branch_id
- Cross-organization access prevention

**Implementation:**
```python
# Tenant resolver middleware
async def get_current_organization(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Organization:
    organization_id = request.headers.get("X-Organization-ID")
    if not organization_id:
        organization_id = current_user.organization_id
    
    organization = get_organization(organization_id)
    if not organization or organization.id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Invalid organization")
    
    return organization

# Branch scope filter
def apply_branch_filter(query: Query, user: User) -> Query:
    if user.role not in ["Super Admin", "Kurum Admini"]:
        user_branches = get_user_branches(user.id)
        query = query.filter(Branch.id.in_(user_branches))
    return query
```

---

## Data Protection

### Sensitive Data Handling

**Data Classification:**
- **Public:** Organization name, general info
- **Internal:** User names, roles, class info
- **Confidential:** Student personal data, financial data
- **Restricted:** Passwords, API keys, secrets

**Encryption at Rest:**
- Database: PostgreSQL with TLS
- File storage: Encrypted volumes
- Backups: Encrypted with GPG

**Encryption in Transit:**
- TLS 1.2/1.3 for all connections
- Certificate pinning for API calls
- HTTPS only in production

### Financial Data Security

**Transaction Safety:**
```python
from decimal import Decimal
from sqlalchemy import text

@transaction.atomic
def process_payment(payment_data: PaymentCreate):
    # Validate amount
    if payment_data.amount <= 0:
        raise ValueError("Amount must be positive")
    
    # Check debt exists and belongs to user's organization
    debt = get_debt(payment_data.debt_id)
    validate_debt_ownership(debt, current_user)
    
    # Check payment doesn't exceed remaining debt
    if payment_data.amount > debt.remaining_amount:
        raise ValueError("Payment exceeds remaining debt")
    
    # Create payment
    payment = create_payment(payment_data)
    
    # Create receipt (immutable)
    receipt = create_receipt(payment)
    
    # Update debt
    update_debt_paid_amount(debt.id, payment.amount)
    
    # Audit log
    log_financial_transaction(payment, receipt)
    
    return payment
```

**Audit Trail:**
- All financial transactions logged
- Before/after values recorded
- User and timestamp tracked
- Immutable audit logs

### Personal Data Protection (GDPR Compliance)

**Data Minimization:**
- Collect only necessary data
- Regular data review and cleanup
- Data retention policies

**Right to be Forgotten:**
- Soft delete with anonymization
- Complete deletion after retention period
- Export data on request

**Data Portability:**
- Export functionality for user data
- Standard formats (JSON, CSV)
- Secure transfer mechanisms

---

## API Security

### Input Validation

**Pydantic Schemas:**
```python
from pydantic import BaseModel, Field, validator

class StudentCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: Optional[EmailStr]
    phone: Optional[str] = Field(None, regex=r'^\+?[0-9]{10,15}$')
    
    @validator('first_name', 'last_name')
    def name_must_not_contain_numbers(cls, v):
        if any(char.isdigit() for char in v):
            raise ValueError('Name must not contain numbers')
        return v
```

### SQL Injection Prevention

**ORM Usage:**
- Always use SQLAlchemy ORM
- Never use raw SQL with user input
- Parameterized queries for raw SQL when necessary

**Example:**
```python
# Safe
students = session.query(Student).filter(
    Student.organization_id == org_id,
    Student.branch_id == branch_id
).all()

# Unsafe - NEVER DO THIS
query = f"SELECT * FROM students WHERE organization_id = '{org_id}'"
session.execute(query)
```

### XSS Prevention

**Frontend:**
- React auto-escapes JSX
- DOMPurify for HTML content
- Content Security Policy (CSP) headers

**Backend:**
- Sanitize user input
- Escape output in templates
- Use safe rendering methods

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.schoolmanagement.com",
        "https://staging.schoolmanagement.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Rate Limiting

**Implementation:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, credentials: LoginSchema):
    # Login logic
    pass

@app.get("/api/students")
@limiter.limit("100/minute")
async def get_students(request: Request):
    # Get students logic
    pass
```

---

## File Upload Security

### File Validation

**Validation Rules:**
```python
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'docx'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(file: UploadFile):
    # Check extension
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Invalid file type")
    
    # Check MIME type
    file_content = file.file.read(1024)
    file.file.seek(0)
    mime_type = magic.from_buffer(file_content, mime=True)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError("Invalid MIME type")
    
    # Check file size
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE:
        raise ValueError("File too large")
```

### Secure File Storage

**Storage Strategy:**
- Random filenames (UUID)
- Separate storage directory
- No direct file access (serve through application)
- Virus scanning on upload

**Implementation:**
```python
import uuid
import os

def save_uploaded_file(file: UploadFile, upload_dir: str) -> str:
    # Generate random filename
    file_ext = file.filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{file_ext}"
    
    # Create secure path
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Scan for viruses
    if not scan_file_for_viruses(file_path):
        os.remove(file_path)
        raise ValueError("File contains virus")
    
    return filename
```

---

## Logging and Monitoring

### Structured Logging

**Implementation:**
```python
import structlog

logger = structlog.get_logger()

def log_security_event(event_type: str, user_id: str, details: dict):
    logger.info(
        "security_event",
        event_type=event_type,
        user_id=user_id,
        timestamp=datetime.utcnow().isoformat(),
        details=details
    )
```

**Log Levels:**
- DEBUG: Development information
- INFO: Normal operations
- WARNING: Security concerns
- ERROR: Errors and failures
- CRITICAL: Security incidents

### Security Event Logging

**Events to Log:**
- Login attempts (success/failure)
- Permission denials
- Data access (sensitive data)
- Configuration changes
- Financial transactions
- File uploads/downloads
- Password changes
- Token refresh/revocation

### Monitoring and Alerting

**Metrics to Monitor:**
- Failed login attempts
- Permission denials
- Unusual data access patterns
- API error rates
- Response time anomalies
- Failed transactions

**Alert Triggers:**
- > 10 failed logins from same IP in 5 minutes
- > 50 permission denials in 1 hour
- Unusual data export activity
- Financial transaction failures
- Database connection failures

---

## Secrets Management

### Environment Variables

**Sensitive Data in .env:**
```bash
# Never commit .env to version control
JWT_SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@host:port/db
SMTP_PASSWORD=smtp-password
SMS_API_KEY=sms-api-key
WHATSAPP_ACCESS_TOKEN=whatsapp-token
```

### Secrets Storage

**Production Options:**
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Docker Secrets (for containers)

**Implementation:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    def __init__(self):
        if not self.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY not set")
```

---

## Network Security

### Firewall Rules

**Allowed Ports:**
- 80/443: HTTP/HTTPS (Nginx)
- 22: SSH (restricted IPs only)
- 5432: PostgreSQL (internal only)

**Blocked Ports:**
- All other ports

### SSL/TLS Configuration

**Nginx SSL Config:**
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

### DDoS Protection

**Mitigation Strategies:**
- Rate limiting
- IP blocking
- Cloudflare or similar service
- Request size limits

---

## Dependency Security

### Vulnerability Scanning

**Tools:**
- Safety (Python)
- Snyk
- Dependabot
- Trivy (Docker images)

**Process:**
- Weekly automated scans
- Immediate scan on new dependencies
- Manual review before production deployment

### Dependency Updates

**Strategy:**
- Regular dependency updates
- Security patches immediately
- Major version updates with testing
- Changelog review

---

## Backup and Recovery Security

### Secure Backups

**Backup Encryption:**
```bash
# Encrypt backup with GPG
gpg --symmetric --cipher-algo AES256 backup.sql

# Decrypt backup
gpg --decrypt backup.sql.gpg > backup.sql
```

**Backup Storage:**
- Encrypted at rest
- Offsite storage
- Access logging
- Regular restoration testing

### Disaster Recovery

**Recovery Plan:**
1. Assess damage and scope
2. Restore from latest clean backup
3. Verify data integrity
4. Bring systems online
5. Monitor for anomalies
6. Document incident

---

## Security Testing

### Penetration Testing

**Testing Areas:**
- Authentication bypass
- Authorization flaws
- SQL injection
- XSS vulnerabilities
- CSRF protection
- File upload vulnerabilities
- API security
- Network security

**Schedule:**
- Quarterly penetration tests
- After major changes
- Before production deployment

### Code Review

**Security Review Checklist:**
- Input validation
- Output encoding
- Authentication/authorization
- Error handling
- Logging (no sensitive data)
- Dependency vulnerabilities
- Configuration security

---

## Incident Response

### Incident Response Plan

**1. Detection:**
- Monitor security alerts
- Analyze logs
- Identify scope

**2. Containment:**
- Isolate affected systems
- Block malicious IPs
- Disable compromised accounts

**3. Eradication:**
- Remove malware
- Patch vulnerabilities
- Update configurations

**4. Recovery:**
- Restore from clean backups
- Verify system integrity
- Monitor for recurrence

**5. Lessons Learned:**
- Document incident
- Update procedures
- Train team

### Security Team Contacts

- **Security Lead:** security@schoolmanagement.com
- **CTO:** cto@schoolmanagement.com
- **Incident Response:** incidents@schoolmanagement.com

---

## Compliance

### GDPR Compliance

**Requirements:**
- Data protection by design
- Data subject rights
- Breach notification (72 hours)
- Data protection officer
- Privacy policy
- Cookie consent

### SOC 2 Compliance

**Trust Service Criteria:**
- Security
- Availability
- Processing integrity
- Confidentiality
- Privacy

---

## Security Checklist

### Pre-Deployment Checklist
- [ ] All secrets are in environment variables
- [ ] SSL/TLS certificates valid
- [ ] Database backups tested
- [ ] Security scans passed
- [ ] Dependencies updated
- [ ] Firewall rules configured
- [ ] Monitoring enabled
- [ ] Logging configured
- [ ] Rate limiting enabled
- [ ] CORS configured correctly

### Ongoing Security Tasks
- [ ] Weekly dependency scans
- [ ] Monthly security reviews
- [ ] Quarterly penetration tests
- [ ] Regular backup testing
- [ ] Security training for team
- [ ] Update incident response plan
- [ ] Review access logs
- [ ] Update security documentation
