# Threat Model & Security Architecture Specification

**Project:** Containerized AppSec Microservices Benchmark  
**Author:** Application Security Lead  
**Classification:** Executive / Technical Architecture Document  
**Framework:** Microsoft STRIDE / NIST SP 800-53 / OWASP Top 10 & API Security Top 10  
**Status:** Remediated & Verified  

---

## 1. Executive Summary

This document provides a formal threat model and risk assessment for the multi-tenant containerized microservices platform. The architecture comprises two core microservices—**Auth Service** (Identity, Token Management, User Lifecycle) and **Core Resource API Service** (Multi-tenant Resource CRUD, Caching, External Webhook Integrations)—supported by a PostgreSQL 16 relational database engine and a Redis 7 caching tier, orchestrated on an isolated Docker bridge network (`appsec-net`).

The objective of this threat modeling exercise is to:
1. Define architectural trust boundaries and sensitive asset boundaries.
2. Identify adversarial threat actors, vectors, and STRIDE risk profiles.
3. Systematically evaluate attack surfaces across authentication, authorization, caching, and external networking.
4. Document the technical mechanisms implemented to mitigate identified vulnerabilities.

---

## 2. System Architecture & Trust Boundaries

```
  ================================ TRUST ZONE 0: UNTRUSTED / PUBLIC INTERNET ================================
                                              |
                                              | HTTPS / REST Calls (JSON)
                                              v
  ================================ TRUST ZONE 1: INGRESS & DMZ GATEWAY ======================================
                                              |
                     +------------------------+------------------------+
                     |                                                 |
                     v                                                 v
  +-------------------------------------+           +-------------------------------------+
  |          Auth Service               |           |         Core Resource API           |
  |  Port: 8001 | Framework: FastAPI   |           |  Port: 8002 | Framework: FastAPI     |
  |  - User Registration & Passwords    |           |  - Multi-Tenant Resource Engine     |
  |  - Bcrypt Hashing & JWT Minting     |           |  - Distributed Redis Caching        |
  |  - Token Verification API           |           |  - Webhook Dispatcher (Outbound)    |
  +------------------+------------------+           +------------------+------------------+
                     |                                                 |
  ===================|==================== TRUST ZONE 2: INTERNAL MESH |==================================
                     |  PostgreSQL Wire Protocol                      |  PostgreSQL & RESP Protocols
                     |  (Port 5432)                                   |  (Ports 5432 & 6379)
                     |                                                 |
                     v                                                 v
  +-------------------------------------+           +-------------------------------------+
  |         PostgreSQL 16 DB            |           |             Redis 7 Cache           |
  |  Port: 5432 | DB: appsec_db         |           |  Port: 6379 | In-Memory Key-Value   |
  |  - Users & Credentials Table        |           |  - Per-Tenant Record Cache          |
  |  - Tenant Records Table             |           |  - Tenant-Isolated Key Namespaces   |
  +-------------------------------------+           +-------------------------------------+
  ================================ TRUST ZONE 3: PERSISTENCE & DATA AT REST =================================
```

### Trust Zones Definition

| Trust Zone | Zone Identifier | Components Included | Security Posture & Exposure |
| :--- | :--- | :--- | :--- |
| **Zone 0: Public / External** | `TZ-0` | External API Consumers, Web Clients, Adversaries | Zero-trust. All inputs are unverified, untrusted, and potentially hostile. |
| **Zone 1: Service Ingress** | `TZ-1` | Auth Service (`:8001`), API Service (`:8002`) | Reverse-proxy/FastAPI edge. Responsible for request schema validation, authentication gatekeeping, and rate limiting. |
| **Zone 2: Internal Mesh** | `TZ-2` | Container Bridge Network (`appsec-net`) | Internal container-to-container network. Non-routable from host except via exposed ports. |
| **Zone 3: Persistence Layer**| `TZ-3` | PostgreSQL Data Volume, Redis In-Memory Store | Highest sensitivity. Contains raw password hashes, tenant metadata, records, and cached business data. |

---

## 3. Asset Identification & Classification

| Asset ID | Asset Description | Confidentiality | Integrity | Availability | Primary Storage Location |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **AST-01** | **User Passwords & Hashes** | **CRITICAL** | **HIGH** | **HIGH** | PostgreSQL `users` table (`hashed_password` via bcrypt) |
| **AST-02** | **JWT Signing Secret** | **CRITICAL** | **CRITICAL** | **HIGH** | Service Environment (`JWT_SECRET_KEY`) |
| **AST-03** | **Tenant Business Records** | **HIGH** | **HIGH** | **HIGH** | PostgreSQL `records` table & Redis cache keys |
| **AST-04** | **Tenant Identity & Context** | **HIGH** | **CRITICAL** | **MEDIUM** | JWT Token Claims (`tenant_id`, `sub`, `role`) |
| **AST-05** | **Redis Cache Store** | **HIGH** | **MEDIUM** | **MEDIUM** | Redis in-memory key space (`record:{tenant_id}:{record_id}`) |
| **AST-06** | **Cloud Host & Metadata APIs** | **CRITICAL** | **CRITICAL** | **HIGH** | Host Network / Cloud Provider (`169.254.169.254`, Localhost) |

---

## 4. Threat Actor Profiles

| Threat Actor | Motivation | Capabilities & Access Level | Target Assets |
| :--- | :--- | :--- | :--- |
| **Unauthenticated External Attacker** | Financial gain, reconnaissance, denial of service | No credentials. Interacts with public endpoints (`/auth/register`, `/auth/login`, `/health`). | AST-01, AST-02, AST-06 |
| **Malicious Authenticated Tenant** | Cross-tenant espionage, data tampering, privilege escalation | Valid tenant credentials. Interacts with authenticated endpoints (`/records/*`, `/integrations/*`). | AST-03, AST-04, AST-06 |
| **Network Eavesdropper / MITM** | Interception of tokens and PII in transit | Interception on non-TLS communication channels or compromised network hops. | AST-01, AST-02, AST-04 |
| **Compromised Internal Microservice** | Lateral movement within mesh | Internal container access on `appsec-net` bridge. | AST-03, AST-05, AST-06 |

---

## 5. STRIDE Threat Analysis Matrix

The system components were evaluated across the six STRIDE threat categories:
- **S** - Spoofing Identity
- **T** - Tampering with Data
- **R** - Repudiation
- **I** - Information Disclosure
- **D** - Denial of Service
- **E** - Elevation of Privilege

### 5.1. Authentication Service (`services/auth`)

| STRIDE Category | Threat Scenario & Vector | Risk Rating | Technical Mechanism & Mitigation | Verification Gate |
| :--- | :--- | :---: | :--- | :--- |
| **Spoofing** | Adversary presents unsigned JWT with `"alg": "none"` to impersonate arbitrary users or administrators. | **CRITICAL** | PyJWT signature verification explicitly enforced (`algorithms=["HS256"]`, `options={"verify_signature": True, "verify_exp": True}`). Tokens without valid HMAC-SHA256 signature are rejected (401). | `test_exploit_jwt_none_algorithm_auth_bypass` |
| **Tampering** | Modification of JWT payload claims (`tenant_id`, `role`) in transit. | **HIGH** | Cryptographic token signing with server-side `JWT_SECRET_KEY`. Any header or payload alteration invalidates HMAC signature. | `test_auth_api.py` |
| **Repudiation** | User registers or logs in; actions cannot be traced to a specific subject. | **MEDIUM** | Structured logs record authentication timestamps, user UUID (`sub`), username, and tenant identifier. | `test_auth_service.py` |
| **Information Disclosure** | Exposure of plaintext passwords via database breach or logs. | **CRITICAL** | One-way password hashing using `bcrypt` with automatic cryptographic salting (`bcrypt.gensalt()`). Plaintext passwords never stored or logged. | `test_auth_service.py` |
| **Denial of Service** | Resource exhaustion via excessive registration / password hashing cycles. | **MEDIUM** | Password length bounded by Pydantic schemas; database uniqueness constraints on username and email with fast indexed lookups. | `test_auth_api.py` |
| **Elevation of Privilege** | Normal user assigns self `admin` or target tenant role during registration. | **HIGH** | Default role enforcement (`user`); token generation strictly bounds role claims against database record on authentication. | `test_auth_api.py` |

---

### 5.2. Core Resource API Service (`services/api`)

| STRIDE Category | Threat Scenario & Vector | Risk Rating | Technical Mechanism & Mitigation | Verification Gate |
| :--- | :--- | :---: | :--- | :--- |
| **Spoofing** | Attacker issues resource requests with forged Bearer headers or spoofed tenant claims. | **CRITICAL** | Mandatory FastAPI dependency `get_current_user` decodes and cryptographically validates JWT token claims before routing to handlers. | `test_records_api.py` |
| **Tampering** | **BOLA / IDOR:** Tenant B updates, overwrites, or deletes records owned by Tenant A via `PUT /records/{id}` or `DELETE /records/{id}`. | **CRITICAL** | SQL queries enforce tenant compound predicates: `WHERE id = :id AND tenant_id = :tenant_id`. Non-matching records return 404 Not Found without modifying target entity. | `test_exploit_bola_unauthorized_record_mutation` |
| **Repudiation** | Unauthorized record updates occur without audit trail of authoring tenant/user. | **MEDIUM** | Every record creation embeds immutable `tenant_id` and `owner_id` derived directly from authenticated JWT claims (`AuthenticatedUser`). | `test_record_service.py` |
| **Information Disclosure** | **BOLA / IDOR:** Tenant B accesses sensitive business data of Tenant A via `GET /records/{id}` or enumeration. | **CRITICAL** | Repository enforces tenant-scoped query filtering. Direct primary key lookups without tenant clause are eliminated and blocked by Semgrep rule `idor-missing-tenant-filter`. | `test_exploit_bola_unauthorized_record_access` |
| **Information Disclosure** | **Cache Poisoning / Leakage:** Tenant B retrieves Tenant A's record from Redis cache. | **HIGH** | Redis cache keys enforce tenant namespace isolation (`record:{tenant_id}:{record_id}`). Cross-tenant cache keys cannot collide or be queried across tenants. | `test_record_service.py` |
| **Denial of Service** | Large pagination requests or unbounded payload creation causing memory exhaustion. | **MEDIUM** | Pydantic validation on payloads; strict database pagination defaults (`limit=50, offset=0`) with max bounds. | `test_records_api.py` |
| **Elevation of Privilege** | Tenant user accesses administrative records or mutates cross-tenant boundaries. | **HIGH** | Contextual authorization: all data operations are strictly isolated to the caller's verified `tenant_id`. | `test_records_api.py` |

---

### 5.3. External Integrations & Webhook Dispatcher (`services/api/src/services/integration_service.py`)

| STRIDE Category | Threat Scenario & Vector | Risk Rating | Technical Mechanism & Mitigation | Verification Gate |
| :--- | :--- | :---: | :--- | :--- |
| **Spoofing** | Attacker crafts malicious URLs resolving to internal loopback (`127.0.0.1`) or local daemon ports. | **CRITICAL** | **SSRF Prevention Engine (`validate_safe_url`):** Resolves hostname via DNS and evaluates IP against `RESTRICTED_NETWORKS` before initiating network socket. Blocks `127.0.0.0/8`, `::1/128`. | `test_exploit_ssrf_internal_loopback_access` |
| **Information Disclosure** | **Cloud Metadata Theft:** Attacker supplies `http://169.254.169.254/latest/meta-data/` to exfiltrate IAM credentials or instance tokens. | **CRITICAL** | Link-local network `169.254.0.0/16` and IPv6 `fe80::/10` explicitly blocked. Any request resolving to metadata IPs triggers HTTP 400 Bad Request. | `test_exploit_ssrf_internal_loopback_access` |
| **Information Disclosure** | **Internal Network Scanning:** Attacker targets internal microservices or databases on RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`). | **HIGH** | Full RFC 1918 and RFC 6598 (CGNAT `100.64.0.0/10`) CIDR blocks blocked. Pre-flight DNS validation detects both IPv4 and IPv6 addresses. | `test_network_security.py` |
| **Tampering** | Scheme smuggling using `file://`, `gopher://`, or `ftp://` to access local filesystem or services. | **HIGH** | Strict scheme whitelist: only `http` and `https` schemes permitted. All other protocols rejected immediately. | `test_network_security.py` |
| **Denial of Service** | Slowloris or hanging connection to slow external host. | **MEDIUM** | Strict timeout enforcement on outbound HTTP requests (`timeout=5.0s`, `follow_redirects=False`). | `test_network_security.py` |

---

## 6. Security Controls & Defense-in-Depth Architecture

```
+---------------------------------------------------------------------------------------+
|                                DEFENSE-IN-DEPTH LAYERS                                |
+---------------------------------------------------------------------------------------+
| 1. Static Gate (Shift-Left)   | Gitleaks (Secrets) + Semgrep SAST + Trivy (SCA/Images) |
| 2. Edge / Ingress Gate        | HTTP Method / Scheme Whitelist + Pydantic Validation  |
| 3. Authentication Gate        | Bcrypt Salted Hash + PyJWT Strict Algorithm (HS256)   |
| 4. Context Authorization Gate | Multi-tenant Token Claims Injection (tenant_id)       |
| 5. Business Logic Gate        | Scoped Data Repositories (WHERE id AND tenant_id)     |
| 6. Cache Isolation Gate       | Namespaced Keys (record:{tenant_id}:{record_id})      |
| 7. Outbound Network Gate      | DNS Pre-resolution + RFC 1918 / Metadata IP Firewall  |
+---------------------------------------------------------------------------------------+
```

### Summary of Verified Mitigations

1. **Broken Object-Level Authorization (BOLA / IDOR):**
   - Eliminated single-parameter database lookups (`select(Record).where(Record.id == id)`).
   - Enforced compound tenant query filtering in `RecordRepository` (`get_by_id_and_tenant`, `list_by_tenant`).
   - Automated SAST enforcement via custom Semgrep rule `idor-missing-tenant-filter.yml`.

2. **Insecure JWT Token Validation:**
   - Enforced strict algorithm whitelist (`algorithms=["HS256"]`) in `AuthService` and `security.py`.
   - Enabled mandatory signature and expiration checks (`verify_signature: True`, `verify_exp: True`).
   - Forged or unsigned tokens (`alg: none`) are deterministically rejected with HTTP 401 Unauthorized.

3. **Server-Side Request Forgery (SSRF):**
   - Implemented DNS resolution and IP address sanitization in `validate_safe_url()`.
   - Blocked all private subnets (RFC 1918 Class A/B/C), Carrier-Grade NAT (RFC 6598), Link-Local / AWS/GCP metadata (`169.254.0.0/16`), and loopback (`127.0.0.0/8`, `::1`).
   - Automated SAST enforcement via custom Semgrep rule `ssrf-unvalidated-http-client.yml`.

---

## 7. Residual Risks & Future Roadmap

| Residual Risk | Impact | Recommended Future Enhancement |
| :--- | :---: | :--- |
| **DNS Rebinding (TOCTOU)** | Medium | Implement an egress proxy / custom HTTP transport adapter that pins the resolved socket IP directly at connection time. |
| **Secret Management** | High | Migrate `JWT_SECRET_KEY` and database credentials from `.env` / container environment to HashiCorp Vault or AWS Secrets Manager with automated rotation. |
| **Rate Limiting & DDoS** | Medium | Implement Redis-backed Token Bucket rate limiting middleware on `/auth/login` and `/integrations/webhook-test`. |
| **Database Encryption at Rest**| Medium | Enable transparent disk encryption (LUKS / AWS KMS) on PostgreSQL storage volumes. |
