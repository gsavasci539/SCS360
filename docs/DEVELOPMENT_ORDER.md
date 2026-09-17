# Development Order

## Overview

This document outlines the recommended development order for building the School Management System. The order is designed to build a solid foundation first, then incrementally add features while maintaining system stability and testability.

---

## Phase 1: Foundation Setup (Week 1-2)

### 1.1 Project Structure Creation
**Duration:** 1 day
**Tasks:**
- Create root directory structure
- Create backend directory structure
- Create frontend directory structure
- Create docs directory
- Initialize Git repository
- Create .gitignore files
- Create README.md

**Deliverables:**
- Complete directory structure
- Git repository initialized
- README with project overview

### 1.2 Backend Core Setup
**Duration:** 2 days
**Tasks:**
- Create Python virtual environment
- Set up requirements.txt with dependencies
- Create core/config.py
- Create core/database.py with SQLAlchemy setup
- Create core/security.py with JWT and password hashing
- Create core/dependencies.py for FastAPI dependencies
- Create core/exceptions.py for custom exceptions
- Create core/middleware.py for custom middleware
- Create main.py with FastAPI app setup
- Configure CORS
- Set up structured logging

**Deliverables:**
- Working FastAPI application
- Database connection configured
- Security utilities implemented
- Logging configured

### 1.3 Database Schema Setup
**Duration:** 2 days
**Tasks:**
- Create database/schema.sql with all tables
- Create database/seed.sql with demo data
- Set up Alembic for migrations
- Create initial migration
- Test database schema locally
- Verify seed data insertion

**Deliverables:**
- Complete database schema
- Alembic configured
- Initial migration created
- Seed data tested

### 1.4 Docker Setup
**Duration:** 1 day
**Tasks:**
- Create backend/Dockerfile
- Create frontend/Dockerfile (placeholder)
- Create docker-compose.yml for development
- Create nginx/default.conf
- Test Docker containers locally
- Verify database connectivity

**Deliverables:**
- Working Docker setup
- All containers running
- Database accessible

---

## Phase 2: Authentication & Authorization (Week 3)

### 2.1 Authentication System
**Duration:** 3 days
**Tasks:**
- Create user model in domain/entities/
- Create user repository in infrastructure/repositories/
- Create authentication use cases in application/use_cases/
- Implement JWT token generation
- Implement refresh token with rotation
- Create auth schemas in application/schemas/
- Create auth router in routers/
- Implement login endpoint
- Implement refresh token endpoint
- Implement logout endpoint
- Implement password reset flow
- Add login attempt tracking
- Write unit tests for auth

**Deliverables:**
- Complete authentication system
- All auth endpoints working
- Unit tests passing

### 2.2 Authorization System
**Duration:** 2 days
**Tasks:**
- Create role and permission models
- Create role and permission repositories
- Implement RBAC middleware
- Create permission checker utility
- Implement role-based route protection
- Implement permission-based route protection
- Create permission dependency for FastAPI
- Add authorization tests

**Deliverables:**
- Complete authorization system
- Role-based access control working
- Permission-based access control working

### 2.3 Multi-tenancy Setup
**Duration:** 2 days
**Tasks:**
- Create organization and branch models
- Implement tenant resolver middleware
- Add organization context to requests
- Implement branch scope filtering
- Create tenant isolation tests
- Verify data isolation between organizations

**Deliverables:**
- Multi-tenancy implemented
- Organization isolation working
- Branch isolation working

---

## Phase 3: Frontend Foundation (Week 4)

### 3.1 Creative Tim Template Integration
**Duration:** 2 days
**Tasks:**
- Clone Creative Tim Material Dashboard React
- Copy essential files to project
- Remove demo content
- Clean up unused dependencies
- Update package.json
- Configure Vite
- Set up TypeScript (if needed)
- Test template build

**Deliverables:**
- Template integrated
- Build working
- Demo content removed

### 3.2 Frontend Core Setup
**Duration:** 2 days
**Tasks:**
- Set up Axios with interceptors
- Create API service base
- Implement error handler
- Create toast notification system
- Set up Zustand stores (auth, ui)
- Create AuthContext
- Create protected route component
- Create role-based route component
- Create 403 and 404 pages
- Create error boundary

**Deliverables:**
- Frontend core infrastructure
- API service configured
- Route guards implemented

### 3.3 Authentication UI
**Duration:** 1 day
**Tasks:**
- Create login page
- Create forgot password page
- Create reset password page
- Implement form validation with Zod
- Connect to backend auth API
- Test authentication flow
- Add loading states
- Add error handling

**Deliverables:**
- Complete authentication UI
- Login flow working
- Password reset working

---

## Phase 4: Organization & User Management (Week 5)

### 4.1 Organization Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create organization entity and repository
- Create organization use cases
- Create organization schemas
- Create organization router
- Implement CRUD operations
- Add organization tests
- Create branch entity and repository
- Create branch use cases
- Create branch schemas
- Create branch router
- Implement CRUD operations
- Add branch tests

**Deliverables:**
- Organization CRUD working
- Branch CRUD working
- Tests passing

### 4.2 User Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create user repository
- Create user use cases
- Create user schemas
- Create user router
- Implement user CRUD
- Implement role assignment
- Implement branch assignment
- Add user tests
- Create role management endpoints
- Create permission matrix endpoint

**Deliverables:**
- User CRUD working
- Role assignment working
- Tests passing

### 4.3 Organization & User UI (Frontend)
**Duration:** 1 day
**Tasks:**
- Create organization list page
- Create organization form page
- Create branch list page
- Create branch form page
- Create user list page
- Create user form page
- Create role permission matrix page
- Connect to backend APIs
- Add form validation

**Deliverables:**
- Organization management UI
- User management UI
- All forms working

---

## Phase 5: Student & Parent Management (Week 6)

### 5.1 Student Module (Backend)
**Duration:** 3 days
**Tasks:**
- Create student entity and repository
- Create parent entity and repository
- Create student-parent relationship
- Create student use cases
- Create student schemas
- Create student router
- Implement student CRUD
- Implement parent management
- Add student tests
- Implement student-photo upload
- Implement file upload abstraction

**Deliverables:**
- Student CRUD working
- Parent management working
- File upload working
- Tests passing

### 5.2 Student Module (Frontend)
**Duration:** 2 days
**Tasks:**
- Create student list page
- Create student form page
- Create student detail page
- Create parent management UI
- Create file upload component
- Implement photo upload
- Connect to backend APIs
- Add form validation

**Deliverables:**
- Student management UI
- Parent management UI
- File upload working

---

## Phase 6: Class Management (Week 7)

### 6.1 Class Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create class entity and repository
- Create class use cases
- Create class schemas
- Create class router
- Implement class CRUD
- Implement student-class assignment
- Implement capacity validation
- Add occupancy calculation
- Add class tests

**Deliverables:**
- Class CRUD working
- Student assignment working
- Capacity validation working
- Tests passing

### 6.2 Class Module (Frontend)
**Duration:** 1 day
**Tasks:**
- Create class list page
- Create class form page
- Create class detail page
- Create student assignment UI
- Create occupancy display
- Connect to backend APIs
- Add form validation

**Deliverables:**
- Class management UI
- Student assignment UI
- Occupancy display working

---

## Phase 7: Attendance Management (Week 8)

### 7.1 Attendance Module (Backend)
**Duration:** 3 days
**Tasks:**
- Create attendance entity and repository
- Create attendance use cases
- Create attendance schemas
- Create attendance router
- Implement single attendance record
- Implement bulk attendance
- Implement duplicate prevention
- Implement class-based attendance view
- Implement student-based attendance view
- Add attendance tests
- Create monthly report endpoint

**Deliverables:**
- Attendance CRUD working
- Bulk attendance working
- Duplicate prevention working
- Tests passing

### 7.2 Attendance Module (Frontend)
**Duration:** 2 days
**Tasks:**
- Create attendance list page
- Create take attendance page (daily)
- Create bulk attendance page
- Create student attendance history page
- Create monthly report page
- Connect to backend APIs
- Add validation

**Deliverables:**
- Attendance management UI
- Bulk attendance UI
- Reports working

---

## Phase 8: Financial Management (Week 9-10)

### 8.1 Debt Module (Backend)
**Duration:** 3 days
**Tasks:**
- Create debt entity and repository
- Create debt use cases
- Implement debt status calculation
- Implement overdue detection
- Create debt schemas
- Create debt router
- Implement debt CRUD
- Implement debt status recalculation
- Add debt tests
- Ensure Decimal type for all financial calculations

**Deliverables:**
- Debt CRUD working
- Status calculation working
- Overdue detection working
- Tests passing

### 8.2 Payment Module (Backend)
**Duration:** 3 days
**Tasks:**
- Create payment entity and repository
- Create payment use cases
- Implement payment transaction safety
- Implement payment cancellation (reverse transaction)
- Create payment schemas
- Create payment router
- Implement payment creation
- Implement payment cancellation
- Add payment tests
- Ensure audit logging for all transactions

**Deliverables:**
- Payment creation working
- Payment cancellation working
- Transaction safety ensured
- Tests passing

### 8.3 Receipt Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create receipt entity and repository
- Create receipt use cases
- Implement receipt number generation
- Implement PDF generation
- Create receipt schemas
- Create receipt router
- Implement receipt creation
- Implement PDF download
- Implement print view
- Add receipt tests

**Deliverables:**
- Receipt creation working
- PDF generation working
- Print view working
- Tests passing

### 8.4 Financial Module (Frontend)
**Duration:** 3 days
**Tasks:**
- Create debt list page
- Create debt form page
- Create payment list page
- Create take payment page
- Create receipt detail page
- Create receipt print view
- Connect to backend APIs
- Add financial validation
- Implement PDF download

**Deliverables:**
- Debt management UI
- Payment management UI
- Receipt UI working
- PDF download working

---

## Phase 9: Notification System (Week 11)

### 9.1 Notification Infrastructure (Backend)
**Duration:** 3 days
**Tasks:**
- Create notification base provider
- Create email provider (SMTP)
- Create SMS provider (Netgsm adapter)
- Create WhatsApp provider (Meta adapter)
- Create notification dispatcher
- Create template renderer
- Create notification_jobs table
- Implement outbox pattern
- Add notification tests

**Deliverables:**
- All providers implemented
- Dispatcher working
- Outbox pattern working
- Tests passing

### 9.2 Notification Worker
**Duration:** 2 days
**Tasks:**
- Create outbox worker
- Implement polling mechanism
- Implement retry logic with exponential backoff
- Implement error handling
- Add worker logging
- Test worker locally
- Add worker to Docker Compose

**Deliverables:**
- Worker running
- Retry logic working
- Error handling working

### 9.3 Notification Integration
**Duration:** 2 days
**Tasks:**
- Integrate notifications with payment flow
- Integrate notifications with announcement flow
- Create notification job creation utilities
- Add notification endpoints
- Create notification log UI
- Test notification flows end-to-end

**Deliverables:**
- Payment notifications working
- Announcement notifications working
- Notification log UI working

---

## Phase 10: Announcement System (Week 12)

### 10.1 Announcement Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create announcement entity and repository
- Create announcement recipient entity
- Create announcement use cases
- Implement audience calculation
- Create announcement schemas
- Create announcement router
- Implement announcement CRUD
- Implement announcement sending
- Add announcement tests

**Deliverables:**
- Announcement CRUD working
- Announcement sending working
- Tests passing

### 10.2 Announcement Module (Frontend)
**Duration:** 2 days
**Tasks:**
- Create announcement list page
- Create announcement form page
- Create announcement detail page
- Implement rich text editor
- Implement audience selection
- Implement channel selection
- Connect to backend APIs
- Add form validation

**Deliverables:**
- Announcement management UI
- Rich text editor working
- Channel selection working

### 10.3 Message Templates
**Duration:** 1 day
**Tasks:**
- Create template CRUD endpoints
- Create template management UI
- Implement variable substitution
- Test template rendering
- Add template examples

**Deliverables:**
- Template management working
- Variable substitution working

---

## Phase 11: Reporting System (Week 13)

### 11.1 Report Endpoints (Backend)
**Duration:** 3 days
**Tasks:**
- Create report use cases
- Implement monthly payment report
- Implement debt report
- Implement overdue debt report
- Implement attendance report
- Implement class occupancy report
- Implement branch performance report
- Implement CSV export
- Implement Excel export
- Add report tests

**Deliverables:**
- All report endpoints working
- CSV export working
- Excel export working
- Tests passing

### 11.2 Report UI (Frontend)
**Duration:** 2 days
**Tasks:**
- Create monthly payment report page
- Create debt report page
- Create overdue debt report page
- Create attendance report page
- Create class occupancy report page
- Create branch performance report page
- Implement chart visualizations
- Implement export functionality
- Connect to backend APIs

**Deliverables:**
- All report pages working
- Charts displaying correctly
- Export working

---

## Phase 12: Dashboard (Week 14)

### 12.1 Dashboard API (Backend)
**Duration:** 2 days
**Tasks:**
- Create dashboard use cases
- Implement summary statistics
- Implement chart data endpoints
- Implement role-based data filtering
- Add dashboard tests
- Optimize queries for performance

**Deliverables:**
- Summary statistics working
- Chart data working
- Role-based filtering working
- Tests passing

### 12.2 Dashboard UI (Frontend)
**Duration:** 2 days
**Tasks:**
- Create dashboard page
- Implement summary cards
- Implement charts (monthly collection, debt vs payment, occupancy)
- Implement recent activities
- Connect to backend APIs
- Add loading states
- Optimize for performance

**Deliverables:**
- Dashboard page working
- Charts displaying correctly
- Real-time updates working

---

## Phase 13: Settings & Configuration (Week 15)

### 13.1 Settings Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create app_settings entity and repository
- Create integration_settings entity and repository
- Create settings use cases
- Create settings schemas
- Create settings router
- Implement general settings CRUD
- Implement integration settings CRUD
- Add settings tests

**Deliverables:**
- Settings CRUD working
- Integration settings working
- Tests passing

### 13.2 Settings Module (Frontend)
**Duration:** 2 days
**Tasks:**
- Create general settings page
- Create integration settings page
- Create SMTP configuration form
- Create SMS configuration form
- Create WhatsApp configuration form
- Implement test connection buttons
- Connect to backend APIs
- Add form validation

**Deliverables:**
- Settings UI working
- Configuration forms working
- Test connection working

---

## Phase 14: Testing & Quality Assurance (Week 16)

### 14.1 Backend Testing
**Duration:** 3 days
**Tasks:**
- Write unit tests for all use cases
- Write integration tests for all endpoints
- Write tests for auth flow
- Write tests for permissions
- Write tests for branch isolation
- Write tests for financial calculations
- Write tests for notification system
- Achieve minimum 80% code coverage
- Run test suite

**Deliverables:**
- Comprehensive test suite
- 80%+ code coverage
- All tests passing

### 14.2 Frontend Testing
**Duration:** 2 days
**Tasks:**
- Write component tests
- Write form validation tests
- Write protected route tests
- Write API service tests
- Achieve minimum 80% code coverage
- Run test suite

**Deliverables:**
- Comprehensive test suite
- 80%+ code coverage
- All tests passing

### 14.3 End-to-End Testing
**Duration:** 2 days
**Tasks:**
- Set up Playwright or Cypress
- Write E2E tests for critical flows
- Test login flow
- Test student creation flow
- Test payment flow
- Test announcement flow
- Run E2E tests

**Deliverables:**
- E2E test suite
- Critical flows tested
- All tests passing

---

## Phase 15: CI/CD Setup (Week 17)

### 15.1 GitHub Actions Configuration
**Duration:** 2 days
**Tasks:**
- Create backend-ci.yml workflow
- Create frontend-ci.yml workflow
- Create docker-build.yml workflow
- Create deploy-staging.yml workflow
- Create deploy-production.yml workflow
- Configure GitHub secrets
- Test CI/CD pipelines
- Fix any pipeline issues

**Deliverables:**
- All CI/CD workflows working
- Tests running on push
- Docker images building
- Deployment workflows configured

### 15.2 Staging Deployment
**Duration:** 2 days
**Tasks:**
- Deploy to staging environment
- Run database migrations
- Load seed data
- Test all features on staging
- Verify integrations (email, SMS, WhatsApp)
- Performance testing
- Fix any staging issues

**Deliverables:**
- Staging environment deployed
- All features tested
- Integrations verified

---

## Phase 16: Production Deployment (Week 18)

### 16.1 Production Preparation
**Duration:** 2 days
**Tasks:**
- Review all configurations
- Update production environment variables
- Generate SSL certificates
- Configure production Nginx
- Set up monitoring
- Set up logging
- Create backup procedures
- Document rollback plan

**Deliverables:**
- Production configured
- SSL certificates installed
- Monitoring configured
- Backup procedures documented

### 16.2 Production Deployment
**Duration:** 1 day
**Tasks:**
- Create database backup
- Deploy to production
- Run database migrations
- Load production seed data
- Verify deployment
- Run health checks
- Monitor for issues

**Deliverables:**
- Production deployed
- Database migrated
- Health checks passing

### 16.3 Post-Deployment Verification
**Duration:** 2 days
**Tasks:**
- Test all critical flows
- Verify all integrations
- Monitor performance
- Check logs for errors
- Fix any production issues
- Document any known issues

**Deliverables:**
- All features verified
- Integrations working
- Performance acceptable
- Issues documented

---

## Phase 17: Documentation & Handover (Week 19)

### 17.1 Technical Documentation
**Duration:** 2 days
**Tasks:**
- Update README.md
- Document API endpoints
- Document database schema
- Document deployment procedures
- Document troubleshooting guide
- Document runbook
- Create architecture diagrams

**Deliverables:**
- Complete technical documentation
- API documentation
- Deployment guide
- Troubleshooting guide

### 17.2 User Documentation
**Duration:** 2 days
**Tasks:**
- Create user manual
- Create admin guide
- Create video tutorials
- Create FAQ
- Document best practices
- Create training materials

**Deliverables:**
- User manual
- Admin guide
- Training materials

### 17.3 Final Review
**Duration:** 1 day
**Tasks:**
- Review all code
- Review all documentation
- Security audit
- Performance review
- Create final report
- Handover to operations team

**Deliverables:**
- Code review complete
- Documentation complete
- Final report
- Handover complete

---

## Summary Timeline

| Phase | Duration | Weeks |
|-------|----------|-------|
| Foundation Setup | 1-2 | 1-2 |
| Authentication & Authorization | 1 | 3 |
| Frontend Foundation | 1 | 4 |
| Organization & User Management | 1 | 5 |
| Student & Parent Management | 1 | 6 |
| Class Management | 1 | 7 |
| Attendance Management | 1 | 8 |
| Financial Management | 2 | 9-10 |
| Notification System | 1 | 11 |
| Announcement System | 1 | 12 |
| Reporting System | 1 | 13 |
| Dashboard | 1 | 14 |
| Settings & Configuration | 1 | 15 |
| Testing & Quality Assurance | 1 | 16 |
| CI/CD Setup | 1 | 17 |
| Production Deployment | 1 | 18 |
| Documentation & Handover | 1 | 19 |

**Total Duration:** 19 weeks (approximately 4.5 months)

---

## Parallel Development Opportunities

To accelerate development, some phases can be worked on in parallel by different team members:

### Parallel Tracks

**Track A (Backend):**
- Phase 2: Authentication & Authorization
- Phase 4.1: Organization Module
- Phase 5.1: Student Module
- Phase 6.1: Class Module
- Phase 7.1: Attendance Module
- Phase 8.1-8.3: Financial Module
- Phase 9.1-9.2: Notification Infrastructure
- Phase 10.1: Announcement Module
- Phase 11.1: Report Endpoints
- Phase 12.1: Dashboard API
- Phase 13.1: Settings Module

**Track B (Frontend):**
- Phase 3: Frontend Foundation
- Phase 4.2: Organization & User UI
- Phase 5.2: Student Module UI
- Phase 6.2: Class Module UI
- Phase 7.2: Attendance Module UI
- Phase 8.4: Financial Module UI
- Phase 9.3: Notification Integration
- Phase 10.2: Announcement Module UI
- Phase 11.2: Report UI
- Phase 12.2: Dashboard UI
- Phase 13.2: Settings Module UI

**Track C (DevOps & Testing):**
- Phase 1.4: Docker Setup
- Phase 14: Testing & Quality Assurance
- Phase 15: CI/CD Setup
- Phase 16: Production Deployment

---

## Milestones

### Milestone 1: Foundation Complete (End of Week 2)
- Project structure created
- Backend core setup
- Database schema ready
- Docker working

### Milestone 2: Authentication Complete (End of Week 3)
- Login/logout working
- JWT tokens implemented
- RBAC implemented
- Multi-tenancy working

### Milestone 3: Core Modules Complete (End of Week 7)
- Organization management
- User management
- Student management
- Class management

### Milestone 4: Operational Features Complete (End of Week 8)
- Attendance tracking
- All CRUD operations working

### Milestone 5: Financial System Complete (End of Week 10)
- Debt management
- Payment processing
- Receipt generation
- Financial reports

### Milestone 6: Communication System Complete (End of Week 12)
- Notification infrastructure
- Announcement system
- All notification channels working

### Milestone 7: Reporting & Dashboard Complete (End of Week 14)
- All reports working
- Dashboard with charts
- Export functionality

### Milestone 8: Production Ready (End of Week 18)
- All features complete
- Testing complete
- CI/CD working
- Production deployed

### Milestone 9: Handover Complete (End of Week 19)
- Documentation complete
- Training materials ready
- System handed over

---

## Risk Mitigation

### Technical Risks
- **Risk:** Integration with external notification providers fails
  - **Mitigation:** Implement adapter pattern early, test each provider independently

- **Risk:** Financial calculation errors
  - **Mitigation:** Use Decimal types, extensive testing, code reviews

- **Risk:** Performance issues with large datasets
  - **Mitigation:** Implement pagination, indexing, query optimization early

### Schedule Risks
- **Risk:** Development takes longer than estimated
  - **Mitigation:** Build in buffer time, prioritize MVP features

- **Risk:** Team member availability
  - **Mitigation:** Cross-train team members, document everything

### Quality Risks
- **Risk:** Insufficient test coverage
  - **Mitigation:** Enforce minimum coverage, require tests for PRs

- **Risk:** Security vulnerabilities
  - **Mitigation:** Regular security audits, dependency scanning

---

## Success Criteria

The project will be considered successful when:

1. **Functional Requirements:**
   - All planned features implemented and working
   - All user stories completed
   - Acceptance criteria met

2. **Non-Functional Requirements:**
   - System performance meets requirements
   - Security requirements met
   - System is scalable
   - System is maintainable

3. **Quality Requirements:**
   - Test coverage ≥ 80%
   - No critical bugs
   - Code review approved
   - Documentation complete

4. **Deployment Requirements:**
   - Successfully deployed to production
   - CI/CD pipeline working
   - Monitoring configured
   - Backup procedures in place

5. **User Acceptance:**
   - User testing completed
   - Feedback incorporated
   - Training completed
   - Sign-off received
