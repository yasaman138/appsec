# Containerized AppSec Microservices Stack

A production-grade, containerized microservices baseline built for application security benchmarking, multi-tenant isolation, and automated verification.

---

## 🏛️ System Architecture

The stack consists of two decoupled FastAPI services, a PostgreSQL relational backend, and a Redis caching cluster communicating over an isolated Docker bridge network (`appsec-net`):

```
                       +-------------------------------+
                       |   HTTP Clients / API Consumers |
                       +---------------+---------------+
                                       |
              +------------------------+------------------------+
              |                                                 |
              v                                                 v
    +-------------------+                             +-------------------+
    |   Auth Service    |                             |  Core API Service |
    |   (Port 8001)     |                             |   (Port 8002)     |
    +---------+---------+                             +---------+---------+
              |                                                 |
              |                                        +--------+--------+
              |                                        |                 |
              v                                        v                 v
   +--------------------+                    +------------------+ +-------------+
   | PostgreSQL Engine  |<-------------------| PostgreSQL Engine| | Redis Cache |
   | (appsec_auth_data) |                    | (appsec_records) | | (Port 6379) |
   +--------------------+                    +------------------+ +-------------+
```

### Services Overview

1. **Auth Service (`services/auth`)**:
   - **Port**: `8001`
   - **Capabilities**: User registration, password hashing (`bcrypt`), login authentication, and JWT issuance (`PyJWT` HS256).
   - **Endpoints**:
     - `POST /auth/register` - Create user with username, email, password, and tenant_id
     - `POST /auth/login` - Authenticate credentials and receive Bearer JWT
     - `GET /auth/me` - Retrieve current user profile
     - `GET /auth/verify` - Validate token claims
     - `GET /health` - Service health status

2. **Core Resource API Service (`services/api`)**:
   - **Port**: `8002`
   - **Capabilities**: Multi-tenant resource management, tenant data isolation, Redis-backed read caching, automatic cache invalidation on write/delete.
   - **Endpoints**:
     - `POST /records` - Create new tenant-scoped record
     - `GET /records` - List records for caller's tenant (with pagination)
     - `GET /records/{id}` - Fetch single record (with Redis caching)
     - `PUT /records/{id}` - Update tenant record & refresh cache
     - `DELETE /records/{id}` - Delete tenant record & evict cache
     - `GET /health` - Service and cache health status

3. **Infrastructure**:
   - **Database**: PostgreSQL 16 Alpine
   - **Cache**: Redis 7 Alpine
   - **Network**: `appsec-net` isolated bridge network

---

## 📂 Project Directory Structure

```
appsec/
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
├── README.md
├── requirements.txt
├── services/
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/
│   │       ├── __init__.py
│   │       ├── cache.py
│   │       ├── config.py
│   │       ├── database.py
│   │       ├── main.py
│   │       ├── security.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   └── record.py
│   │       ├── repositories/
│   │       │   ├── __init__.py
│   │       │   └── record_repository.py
│   │       ├── routers/
│   │       │   ├── __init__.py
│   │       │   ├── health.py
│   │       │   └── records.py
│   │       ├── schemas/
│   │       │   ├── __init__.py
│   │       │   └── record.py
│   │       └── services/
│   │           ├── __init__.py
│   │           └── record_service.py
│   └── auth/
│       ├── Dockerfile
│       ├── requirements.txt
│       └── src/
│           ├── __init__.py
│           ├── config.py
│           ├── database.py
│           ├── main.py
│           ├── models/
│           │   ├── __init__.py
│           │   └── user.py
│           ├── repositories/
│           │   ├── __init__.py
│           │   └── user_repository.py
│           ├── routers/
│           │   ├── __init__.py
│           │   └── auth.py
│           ├── schemas/
│           │   ├── __init__.py
│           │   └── auth.py
│           └── services/
│               ├── __init__.py
│               └── auth_service.py
└── tests/
    ├── conftest.py
    ├── integration/
    │   ├── test_auth_api.py
    │   ├── test_records_api.py
    │   └── test_stack_flow.py
    └── unit/
        ├── test_auth_service.py
        └── test_record_service.py
```

---

## 🚀 Quickstart & Deployment

### 1. Boot the Stack via Docker Compose
```bash
docker compose up --build -d
```

### 2. Verify Service Health
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
```

---

## 🧪 Automated Testing

Run the full automated test suite (unit tests, isolated integration tests, and cross-service end-to-end workflows):

```bash
python3 -m pytest -v tests/
```

Or execute within the running container environment:
```bash
docker compose exec -T api pytest tests/
```
