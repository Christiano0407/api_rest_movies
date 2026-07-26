<div align="center">

# Secure Cinema API Gateway

### API Gateway empresarial para TMDB — JWT RS256 + RBAC + Redis Cache + Rate Limiting

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-CC0000?style=flat&logo=sqlalchemy&logoColor=white)](https://sqlalchemy.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-24-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![Nginx](https://img.shields.io/badge/Nginx-1.27-009639?style=flat&logo=nginx&logoColor=white)](https://nginx.com)
[![Alembic](https://img.shields.io/badge/Alembic-1.13-845ED7?style=flat&logo=alembic&logoColor=white)](https://alembic.sqlalchemy.org)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.1.0-6BA539?style=flat&logo=openapi&logoColor=white)](https://openapis.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)

</div>

---

## 📑 Índice

- [Visión General](#visión-general)
- [Arquitectura](#arquitectura)
- [Stack Tecnológico](#stack-tecnológico)
- [Pipeline de Request (Flujo Completo)](#pipeline-de-request)
- [Procesos Core](#procesos-core)
  - [1. Autenticación JWT RS256](#1-autenticación-jwt-rs256)
  - [2. RBAC por Roles (6 niveles)](#2-rbac-por-roles-6-niveles)
  - [3. Rate Limiting Dinámico (Redis + SlowAPI)](#3-rate-limiting-dinámico-redis--slowapi)
  - [4. Caché Inteligente Redis (Cache-Aside)](#4-caché-inteligente-redis-cache-aside)
  - [5. Proxy TMDB (httpx async)](#5-proxy-tmdb-httpx-async)
- [Endpoints API](#endpoints-api)
  - [Identity & Access](#identity--access)
  - [Cinema Discovery (Proxy TMDB)](#cinema-discovery-proxy-tmdb)
  - [User Account Sync](#user-account-sync)
  - [System](#system)
- [Modelo de Datos](#modelo-de-datos)
- [Manejo de Errores](#manejo-de-errores)
- [Variables de Entorno](#variables-de-entorno)
- [Instalación y Configuración](#instalación-y-configuración)
  - [Opción 1: Desarrollo Local](#opción-1-desarrollo-local-sin-docker)
  - [Opción 2: Docker (recomendado)](#opción-2-docker-recomendado)
- [Comandos Docker](#comandos-docker)
- [Comandos Alembic](#comandos-alembic)
- [Comandos de Desarrollo](#comandos-de-desarrollo)
- [Ejemplos de Uso (curl)](#ejemplos-de-uso-curl)
- [Decisiones de Arquitectura (ADRs)](#decisiones-de-arquitectura-adrs)
- [Roadmap](#roadmap)

---

## Visión General

**Secure Cinema API Gateway** es una API REST empresarial que actúa como intermediario seguro entre el frontend y la API de [TMDB (The Movie Database)](https://www.themoviedb.org/). No es un simple proxy: **inyecta capas transversales** de seguridad, control de acceso, rate limiting y caché inteligente antes de reenviar cada petición a TMDB.

### Problema que resuelve

Cada aplicación cliente (web, móvil, smart TV) necesita gestionar autenticación, límites de petición y caché de manera independiente. Esto multiplica la complejidad y expone las credenciales de TMDB. Este Gateway **centraliza toda la lógica transversal** en un solo punto de entrada.

### Capas que inyecta el Gateway

```
 ① Cliente (Browser/App)
        │
        ▼
 [  NGINX  ]       ← Reverse Proxy, TLS termination, load balancing
        │
        ▼
 [  AUTH  ]        ← JWT RS256 + RBAC (verifica identidad y permisos)
        │
        ▼
 [  RATE LIMIT  ]  ← SlowAPI + Redis (Admin=1000, User=60 req/min)
        │
        ▼
 [  CACHE  ]       ← Redis GET <2ms (Cache-Aside: HIT → respuesta, MISS → TMDB)
        │
        ▼
 [  TMDB PROXY  ]  ← httpx async con retry exponencial y timeout
        │
        ▼
 ⑧ Respuesta al Cliente (JSON + X-Cache, X-Request-ID, X-RateLimit-Remaining)
```

### Valor diferencial

| Característica | Beneficio |
|---|---|
| **JWT RS256 asimétrico** | La llave pública se distribuye libremente; solo el Gateway puede emitir tokens |
| **Cache-Aside <2ms** | Las respuestas en caché se sirven en milisegundos sin tocar TMDB |
| **Rate limiting por rol** | 6 niveles de cuota: Admin (1000), Manager (500), …, User (60) req/min |
| **RBAC granular** | 6 roles con permisos diferenciados |
| **Agregación concurrente** | `asyncio.gather()` para paralelizar llamadas a TMDB (detalles + créditos + videos) |
| **Contrato OpenAPI 3.1.0** | Documentación completa y generable con Swagger UI |

---

## Arquitectura

### Diagrama de Contenedores (C4)

```
                        ┌─────────────────────────────────────┐
                        │           INTERNET / CLIENTE         │
                        │    Web App · Mobile App · Smart TV   │
                        └──────────────┬──────────────────────┘
                                       │ HTTPS :443 / HTTP :8000
                        ┌──────────────▼──────────────────────┐
                        │         NGINX 1.27                  │
                        │   · Reverse Proxy                   │
                        │   · TLS Termination (producción)    │
                        │   · Load Balancing (workers)        │
                        └──────────────┬──────────────────────┘
                                       │ :80 (internal)
                                       │
                  ┌─────────────────────┼─────────────────────┐
                  │                     │                     │
         ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
         │   FastAPI App   │  │   FastAPI App   │  │   FastAPI App   │
         │   (uvicorn w1)  │  │   (uvicorn w2)  │  │   (uvicorn wN)  │
         │   :8000         │  │   :8001         │  │   :800N         │
         └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
                  │                     │                     │
                  └─────────────────────┼─────────────────────┘
                                       │
               ┌────────────────────────┼────────────────────────┐
               │                        │                        │
      ┌────────▼────────┐     ┌────────▼────────┐     ┌────────▼────────┐
      │  PostgreSQL 16  │     │    Redis 7      │     │   TMDB API      │
      │                 │     │                 │     │  (Externa)      │
      │  · users        │     │  · Cache (TLL)  │     │                 │
      │  · tmdb_sessions│     │  · Rate Limit   │     │  /3/movie/      │
      │  · token_block  │     │  · Blocklist    │     │  /3/search/     │
      │    _list        │     │                 │     │  /3/account/    │
      └─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Arquitectura Interna (Layers)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          FastAPI (ASGI)                                  │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐   │
│  │   Routes     │  │ Dependencies │  │      Middlewares              │   │
│  │   (API v1)   │  │  · Auth      │  │  · RequestLoggingMiddleware  │   │
│  │              │◄─┤  · RBAC      │  │    (X-Request-ID, timing)    │   │
│  │  auth/       │  │  · get_db    │  │  · CORSMiddleware            │   │
│  │  cinema/     │  │  · get_redis │  │                              │   │
│  │  account/    │  │  · get_cache │  │                              │   │
│  └──────┬───────┘  └──────────────┘  └──────────────────────────────┘   │
│         │                                                               │
│  ┌──────▼───────┐  ┌──────────────┐  ┌──────────────────────────────┐   │
│  │   Services   │  │   Schemas    │  │      Exceptions              │   │
│  │  (Business)  │  │  (Pydantic)  │  │  · NotFoundError  → 404     │   │
│  │              │  │              │  │  · ConflictError  → 409     │   │
│  │  · auth.py   │  │  · auth.py   │  │  · AuthError      → 401     │   │
│  │  · cache.py  │  │  · user.py   │  │  · ForbiddenError → 403     │   │
│  │  · tmdb_cli  │  │  · tmdb_*.py │  │  · BusinessError  → 400     │   │
│  │    ent.py    │  │              │  │  · Generic 500              │   │
│  └──────┬───────┘  └──────────────┘  └──────────────────────────────┘   │
│         │                                                               │
│  ┌──────▼───────┐  ┌──────────────┐  ┌──────────────────────────────┐   │
│  │  ORM Models  │  │   Session    │  │      Config / Logging        │   │
│  │ (SQLAlchemy  │  │  (Async      │  │  · Pydantic Settings v2     │   │
│  │  2.0 Mapped) │  │   Engine)    │  │  · structlog (JSON/Console)  │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Stack Tecnológico

| Capa | Tecnología | Versión | Propósito |
|------|-----------|---------|-----------|
| **Runtime** | Python | 3.12 | Lenguaje principal |
| **Framework** | FastAPI | 0.115+ | API asíncrona de alta performance |
| **ORM** | SQLAlchemy | 2.0+ | Mapeo objeto-relacional (async) |
| **Migraciones** | Alembic | 1.13+ | Control de esquema de base de datos |
| **BD Relacional** | PostgreSQL | 16 | Usuarios, sesiones TMDB, blocklist |
| **Caché / Rate Limit** | Redis | 7 | Caché de películas + rate limiting + sesiones |
| **Auth Tokens** | PyJWT (RS256) | 2.9+ | Tokens asimétricos (llave privada/pública) |
| **Password Hashing** | bcrypt | — | Hashing seguro con salt automático |
| **Validación** | Pydantic v2 | 2.6+ | Schemas de request/response + config |
| **HTTP Client** | httpx | 0.27+ | Cliente HTTP asíncrono para TMDB |
| **Rate Limiting** | SlowAPI | 0.1.9+ | Middleware de rate limiting con Redis |
| **Logging** | structlog | 24.1+ | Logging estructurado (JSON/colores) |
| **Proxy Reverso** | Nginx | 1.27 | Load balancing, TLS, routing |
| **Contenedores** | Docker | 24+ | Empaquetamiento multi-etapa |
| **Orquestación** | Docker Compose | — | Postgres + Redis + API + Nginx |
| **Linter/Formatter** | Ruff | 0.4+ | Linting y formato de código |
| **Type Checker** | mypy | 1.9+ | Verificación estática de tipos |
| **Testing** | pytest | 8.1+ | Tests unitarios y de integración |
| **Driver PG** | asyncpg | 0.29+ | Driver PostgreSQL asíncrono nativo |
| **Spec API** | OpenAPI | 3.1.0 | Contrato formal de la API |

---

## Pipeline de Request

Cada petición atraviesa 7 etapas dentro del Gateway:

```
 ┌──────┐
 │ CLIENTE │  Envía HTTP request (con o sin Authorization header)
 └───┬───┘
     │
 ┌───▼──────────────┐
 │ ① NGINX          │  Reverse proxy, TLS (prod), balanceo entre workers
 │    (opcional)     │
 └───┬──────────────┘
     │
 ┌───▼──────────────────┐
 │ ② MIDDLEWARE Logging  │  X-Request-ID (UUID), timing, log estructurado
 │    (ASGI)             │
 └───┬──────────────────┘
     │
 ┌───▼──────────────────┐
 │ ③ RATE LIMITER       │  SlowAPI + Redis: verifica cuota del rol
 │    (SlowAPI + Redis)  │  · dentro del límite → continúa
 │                      │  · excedido → 429 Too Many Requests
 └───┬──────────────────┘
     │
 ┌───▼──────────────┐
 │ ④ AUTH (JWT)     │  Decodifica y verifica el JWT (RS256)
 │    (Depends)      │  · firma inválida / expirado → 401
 │                  │  · jti en blocklist?         → 401
 └───┬──────────────┘
     │
 ┌───▼──────────────┐
 │ ⑤ RBAC           │  Verifica que el rol del usuario tiene
 │    (Depends)      │  permisos para este endpoint → 403 si no
 └───┬──────────────┘
     │
 ┌───▼──────────────────────┐
 │ ⑥ CACHE (Redis) + PROXY │  Cache-Aside:
 │    (CacheService)        │  · GET key → HIT (<2ms) → respuesta
 │                          │  · MISS → fetch TMDB → SETEX → respuesta
 └───┬──────────────────────┘
     │
 ┌───▼──────────┐
 │ ⑦ RESPUESTA  │  JSON + headers:
 │              │  · X-Cache: HIT | MISS
 │              │  · X-Request-ID: <uuid>
 │              │  · X-RateLimit-Limit: 60
 │              │  · X-RateLimit-Remaining: 42
 └──────────────┘
```

---

## Pipeline de Integración Continua (CI/CD)

### Diagrama de Etapas

Cada push a `main` o PR a `developer` dispara el siguiente pipeline automatizado:

```
  ┌──────────────┐
  │  Git Push    │  main / developer / feature/*
  │  / Pull Req  │
  └──────┬───────┘
         │
  ┌──────▼──────────────────────────────────────────┐
  │  ① SETUP                                         │
  │  · actions/checkout@v4                          │
  │  · actions/setup-python@v5 (Python 3.12)        │
  │  · Instalar uv + uv sync --frozen               │
  │  · Servicios: PostgreSQL 16 + Redis 7 (Docker)  │
  │  · Generar llaves RSA 2048 para tests           │
  └──────┬──────────────────────────────────────────┘
         │
  ┌──────▼──────┐
  │  ② LINT     │  ruff check .  (E, F, I, UP, B)
  │    (Ruff)   │  ruff format --check .
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │  ③ TYPE     │  mypy app/  (strict optional)
  │    (mypy)   │
  └──────┬──────┘
         │
  ┌──────▼──────────────────────────────────────┐
  │  ④ TEST                                      │
  │    (pytest)  │  pytest -v --cov=app --cov-report=term-missing
  │              │  · Tests unitarios (servicios, schemas, seguridad)
  │              │  · Tests de integración (httpx AsyncClient)
  │              │  · Coverage mínimo: 80%
  └──────┬──────┘
         │
  ┌──────▼──────────────────────────────────────┐
  │  ⑤ SECURITY                                  │
  │    (Dependabot) │  Escaneo automático de vulnerabilidades
  │                  │  Alertas en GitHub Security tab
  │                  │  PRs automáticos de fix
  └──────┬──────┘
         │
  ┌──────▼──────────────────────────────────────┐
  │  ⑥ BUILD                                     │
  │    (Docker)   │  docker build -t cinema-api .
  │              │  Multi-stage: uv install → runtime slim
  │              │  Tag: commit SHA + latest
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │  ⑦ DEPLOY   │  Opcional: push a registry +
  │    (opt)    │  deploy a staging/production
  └─────────────┘
```

### GitHub Actions Workflow (referencia)

```yaml
name: CI

on:
  push:
    branches: [main, developer]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"

jobs:
  quality:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: pip install uv

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: uv sync --frozen --no-dev

      - name: Generate RSA keys
        run: |
          mkdir -p keys
          openssl genpkey -algorithm RSA -out keys/private.pem \
            -pkeyopt rsa_keygen_bits:2048
          openssl rsa -pubout -in keys/private.pem -out keys/public.pem

      - name: Lint (Ruff)
        run: ruff check . && ruff format --check .

      - name: Type check (mypy)
        run: mypy app/

      - name: Test with pytest
        run: pytest -v --cov=app --cov-report=term-missing
        env:
          ENVIRONMENT: test
          JWT_PRIVATE_KEY_PATH: keys/private.pem
          JWT_PUBLIC_KEY_PATH: keys/public.pem
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379/0
```

---

## Procesos Core

### 1. Autenticación JWT RS256

El sistema usa **criptografía asimétrica (RS256)** — un par de llaves RSA:

```
 ┌─────────────────────┐       ┌─────────────────────┐
 │   PRIVATE KEY       │       │   PUBLIC KEY        │
 │   /app/keys/        │       │   /app/keys/        │
 │   private.pem       │       │   public.pem        │
 │                     │       │                     │
 │   jwt.encode()      │       │   jwt.decode()      │
 │   (FIRMA / EMITE)   │       │   (VERIFICA)        │
 └─────────┬───────────┘       └─────────┬───────────┘
           │                             │
           │  Solo este Gateway          │  Cualquier servicio
           │  puede EMITIR tokens        │  puede VERIFICAR (sin poder emitir)
           ▼                             ▼
     Access Token (30 min)          Verify RS256 signature
     Refresh Token (7 días)         Extract claims (sub, role, jti)
```

**¿Por qué RS256 y no HS256?**

| Aspecto | HS256 (simétrico) | RS256 (asimétrico) |
|---------|------------------|-------------------|
| Llaves | Una sola llave secreta | Par: privada (firma) + pública (verifica) |
| Distribución | Debe compartirse con cada servicio | La pública se distribuye libremente |
| Seguridad | Cualquiera con la llave puede emitir tokens | Solo quien tiene la privada emite |
| Uso en Gateway | ❌ No recomendado | ✅ Ideal (otros servicios verifican sin emitir) |

#### Migración: python-jose → PyJWT (Julio 2026)

En julio 2026 se migró de `python-jose[cryptography]` a `PyJWT[crypto]` para eliminar dependencias vulnerables y adoptar un backend criptográfico profesional basado en OpenSSL.

**Motivación:**

| Aspecto | `python-jose` | `PyJWT` |
|---------|---------------|---------|
| Backend criptográfico | `ecdsa` (Python puro) | `cryptography` (OpenSSL) |
| Mantenimiento | Último release 2021 | Activo (v2.13.0+) |
| Dependencias totales | 4 (`jose` + `ecdsa` + `pyasn1` + `rsa`) | 1 (`jwt`) |
| Vulnerabilidades conocidas | 3 CVEs altas (CVE-2024-23342, CVE-2026-59885, CVE-2026-59886) | 0 |
| Timing-attack safe | ❌ Vulnerable (Minerva) | ✅ Constant-time por OpenSSL |
| API | `from jose import jwt` | `import jwt` (estándar) |

**Resultado:** Se eliminaron 4 paquetes del árbol de dependencias y 3 vulnerabilidades de severidad alta fueron resueltas.

```diff
- "python-jose[cryptography]>=3.3.0"
+ "pyjwt[crypto]>=2.9.0"
```

#### Payload del Token (Claims)

```json
{
  "sub": "alma_cantu",
  "role": "Admin",
  "type": "access",
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "iat": 1720972800,
  "exp": 1720974600
}
```

| Claim | Tipo | Access Token | Refresh Token | Descripción |
|-------|------|:---:|:---:|-------------|
| `sub` | string | ✅ | ✅ | Username del usuario (subject) |
| `role` | string | ✅ | ✅ | Rol RBAC (`Admin`, `User`, etc.) |
| `type` | string | ✅ | ✅ | `"access"` o `"refresh"` |
| `jti` | string (UUIDv4) | ✅ | ✅ | Identificador único para blocklist |
| `iat` | int (epoch) | ✅ | ✅ | Fecha/hora de emisión |
| `exp` | int (epoch) | ✅ | ✅ | Fecha/hora de expiración |
| TTL | — | **30 min** | **7 días** | Configurable via `.env` |

#### Generación de llaves

```bash
mkdir -p keys

# Llave privada RSA 2048 bits
openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048

# Llave pública derivada
openssl rsa -pubout -in keys/private.pem -out keys/public.pem

# Verificación
openssl rsa -in keys/private.pem -check -noout   # ← Debe decir "RSA key ok"
openssl rsa -in keys/public.pem -pubin -noout     # ← No debe dar error
```

#### Flujo de Refresh Token (Rotación)

```
  POST /auth/refresh { refresh_token: "..." }
       │
       ▼
  jwt.decode(refresh_token, PUBLIC_KEY, RS256)
       │
       ├── inválido/expirado ──→ 401
       │
       ├── type != "refresh"  ──→ 401
       │
       ├── jti en token_blocklist? ──→ 401 (ya fue usado = replay attack)
       │
       ▼
  INSERT jti INTO token_blocklist  (revocar el refresh USADO)
       │
       ▼
  jwt.encode(access_token, PRIVATE_KEY)   ← nuevo (30 min)
  jwt.encode(refresh_token, PRIVATE_KEY)  ← nuevo (7 días)
       │
       ▼
  200 OK { access_token, refresh_token }
```

**Seguridad:** Cada refresh token se puede usar **una sola vez**. Al rotar, el anterior se agrega al blocklist. Si un atacante intercepta un refresh token, solo puede usarlo antes de que el legítimo lo rote.

---

### 2. RBAC por Roles (6 niveles)

```
     ┌──────────┐
     │  Admin   │  1000 req/min  ← Acceso total
     └────┬─────┘
          │
     ┌────▼──────┐
     │  Manager  │  500 req/min  ← Gestión
     └────┬──────┘
          │
     ┌────▼──────┐
     │  Editor   │  300 req/min  ← Edición
     └────┬──────┘
          │
     ┌────▼────────┐
     │  Moderator  │  300 req/min  ← Moderación
     └────┬────────┘
          │
     ┌────▼──────┐
     │  Premium  │  120 req/min  ← Suscriptores
     └────┬──────┘
          │
     ┌────▼──────┐
     │   User    │   60 req/min  ← Básico (default)
     └───────────┘
```

#### Implementación

```python
# app/api/deps.py

require_admin = require_roles(RoleEnum.ADMIN)
require_editor_or_admin = require_roles(RoleEnum.ADMIN, RoleEnum.EDITOR)

# Uso en endpoints:
@router.get("/admin", dependencies=[Depends(require_admin)])
@router.put("/movies/{id}", dependencies=[Depends(require_editor_or_admin)])
```

---

### 3. Rate Limiting Dinámico (Redis + SlowAPI)

```
  Request → SlowAPI → Redis INCR "rate:{ip}:{minute}"
                        │
                        ├── ≤ límite del rol ──→ 200 OK
                        │
                        └── > límite ──→ 429 Too Many Requests
                                          + Retry-After header
```

**Límites por rol (peticiones/minuto):**

| Rol | Límite | Intervalo mínimo |
|-----|:------:|:----------------:|
| Admin | 1,000 | 60ms |
| Manager | 500 | 120ms |
| Editor | 300 | 200ms |
| Moderator | 300 | 200ms |
| Premium | 120 | 500ms |
| User | 60 | 1,000ms |

**Headers de respuesta:**

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
```

---

### 4. Caché Inteligente Redis (Cache-Aside)

Implementa el patrón **Cache-Aside** (Lazy Loading):

```
  GET /cinema/movies/popular?page=1
       │
       ▼
  Redis GET "cinema:movies:popular:1"
       │
       ├── HIT ──→ Deserializar Pydantic model_validate_json()
       │           Response + X-Cache: HIT  (< 2ms)
       │
       └── MISS ──→ httpx GET TMDB /3/movie/popular?page=1
                       │
                       ▼
                   Redis SETEX "cinema:movies:popular:1" EX 120
                       │
                       ▼
                   Response + X-Cache: MISS  (~200-500ms)
```

#### CacheService API

```python
# services/cache.py

class CacheService:
    async def get_or_set(
        key: str,
        factory: Callable[[], Awaitable[GatewayPaginationResponse]],
        ttl: int | None = None,
    ) -> tuple[GatewayPaginationResponse, from_cache: bool]:
        """Cache-Aside genérico: acepta cualquier key"""

    async def get_cached_or_fetch(
        category: str,
        page: int,
        factory: Callable[[], Awaitable[GatewayPaginationResponse]],
    ) -> tuple[GatewayPaginationResponse, from_cache: bool]:
        """Cache-Aside específico para movies por categoría"""
```

**Key naming:**

| Recurso | Key |
|---------|-----|
| Películas por categoría | `cinema:movies:{category}:{page}` |
| Búsqueda | `cinema:movies:search:{query}:{page}` |

**TTL:** `CACHE_TTL_SECONDS=120` (configurable en `.env`)

---

### 5. Proxy TMDB (httpx async)

El Gateway traduce los endpoints internos a llamadas a la API de TMDB:

```
  GET /cinema/movies/popular?page=1
       ↓
  httpx GET https://api.themoviedb.org/3/movie/popular?page=1
       ↓
  GatewayPaginationResponse {
    page, results[], total_pages, total_results,
    from_cache: bool,          ← inyectado por Gateway
    rate_limiting_remaining: int  ← inyectado por Gateway
  }
```

**Endpoints mapeados:**

| Gateway | TMDB | Método |
|---------|------|--------|
| `/cinema/movies/{category}` | `/3/movie/{category}` | GET |
| `/cinema/movies/search?query=` | `/3/search/movie` | GET |
| `/cinema/movies/{id}/complementary` | `/3/movie/{id}` + `/credits` + `/videos` | GET (concurrente) |
| `/account/watchlist` | `/3/account/{id}/watchlist` | POST |

#### Retry con Exponential Backoff

```
  Request a TMDB
       │
       ├── Éxito ──→ 200 OK
       │
       └── Error de red / timeout
            │
            wait 2^0 = 1s → Reintento 1
            │
            wait 2^1 = 2s → Reintento 2
            │
            wait 2^2 = 4s → Reintento 3
            │
            ├── Éxito ──→ 200 OK
            │
            └── Fallo ──→ 503 BusinessLogicError
```

---

## Endpoints API

### Identity & Access

| Método | Endpoint | Descripción | Auth | Request | Response |
|--------|----------|-------------|:----:|---------|----------|
| `POST` | `/api/v1/auth/register` | Registro de usuario | No | `UserRegister` JSON | `UserResponse` (201) |
| `POST` | `/api/v1/auth/login` | Inicio de sesión (OAuth2 Password Flow) | No | `application/x-www-form-urlencoded` | `TokenResponse` (200) |
| `POST` | `/api/v1/auth/refresh` | Rotar refresh token (emite nuevo par) | No | `{ refresh_token }` | `TokenResponse` (200) |
| `POST` | `/api/v1/auth/logout` | Revocar access token (blocklist) | Bearer | — | 204 No Content |
| `POST` | `/api/v1/auth/tmdb/request-token` | Solicitar request_token TMDB | Bearer | — | `{ request_token, tmdb_authorize_url }` |
| `POST` | `/api/v1/auth/tmdb/link` | Vincular cuenta TMDB (canjear token) | Bearer | `{ request_token }` | `TMDBSessionResponse` (201) |

### Cinema Discovery (Proxy TMDB)

| Método | Endpoint | Descripción | Auth | Caché | Response |
|--------|----------|-------------|:----:|:----:|----------|
| `GET` | `/api/v1/cinema/movies/{category}` | Películas por categoría | Bearer | ✅ Redis | `GatewayPaginationResponse` |
| `GET` | `/api/v1/cinema/movies/search` | Búsqueda por texto | Bearer | ✅ Redis | `GatewayPaginationResponse` |
| `GET` | `/api/v1/cinema/movies/{id}/complementary` | Detalles + créditos + videos | Bearer | ❌ | `MovieComplementaryData` |

**Categorías disponibles:** `popular`, `now_playing`, `top_rated`, `upcoming`

### User Account Sync

| Método | Endpoint | Descripción | Auth | Request | Response |
|--------|----------|-------------|:----:|---------|----------|
| `POST` | `/api/v1/account/watchlist` | Sincronizar watchlist con TMDB | Bearer | `WatchlistPayload` | `{ success, status_message }` |

### System

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|:----:|
| `GET` | `/api/v1/health` | Health check (status, version, environment) | No |
| `GET` | `/docs` | Swagger UI (solo en development/staging) | No |

---

## Modelo de Datos

```
┌──────────────────────────────────────────────────┐
│                      users                        │
├──────────────────────────────────────────────────┤
│ id              SERIAL       PRIMARY KEY          │
│ username        VARCHAR(30)  UNIQUE NOT NULL      │
│ email           VARCHAR(255) UNIQUE NOT NULL      │
│ hashed_password TEXT         NOT NULL              │
│ role            VARCHAR(20)  NOT NULL DEFAULT 'User'│
│ is_active       BOOLEAN      DEFAULT true          │
│ is_verified     BOOLEAN      DEFAULT false         │
│ created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()│
│ updated_at      TIMESTAMPTZ  DEFAULT now()         │
└────────────────────┬─────────────────────────────┘
                     │ 1
                     │
                     │ * (cascade delete)
┌────────────────────▼─────────────────────────────┐
│                  tmdb_sessions                    │
├──────────────────────────────────────────────────┤
│ id              SERIAL       PRIMARY KEY          │
│ user_id         INTEGER      FK → users.id       │
│ session_id      VARCHAR(255) NOT NULL              │
│ account_id      INTEGER                            │
│ access_token    VARCHAR(500)                       │
│ expires_at      TIMESTAMPTZ                        │
│ connected_at    TIMESTAMPTZ  NOT NULL DEFAULT now()│
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│                 token_blocklist                   │
├──────────────────────────────────────────────────┤
│ id              SERIAL       PRIMARY KEY          │
│ jti             VARCHAR(255) UNIQUE NOT NULL      │
│ token_type      VARCHAR(20)  NOT NULL              │
│ user_id         INTEGER      FK → users.id       │
│ expires_at      TIMESTAMPTZ  NOT NULL              │
│ revoked_at      TIMESTAMPTZ  NOT NULL DEFAULT now()│
└──────────────────────────────────────────────────┘
```

### Enumeraciones

**`user_role`:** `Admin`, `Manager`, `Editor`, `Moderator`, `Premium`, `User`

---

## Manejo de Errores

Todos los errores siguen un formato JSON consistente:

```json
{
  "error": true,
  "status_code": 401,
  "detail": "Credenciales Inválidas o han Expirado (Token - JWT)"
}
```

| Código | Error | Cuándo ocurre |
|:------:|-------|---------------|
| **400** | `BusinessLogicError` | Error de lógica de negocio (ej: TMDB rate limit, cuenta no vinculada) |
| **401** | `AuthenticationError` | Token inválido, expirado, revocado, o malformed |
| **403** | `AuthorizationError` | Rol sin permisos para el endpoint (RBAC) |
| **404** | `NotFoundError` | Recurso no encontrado en TMDB |
| **409** | `ConflictError` | Username o email ya existen en registro |
| **422** | `RequestValidationError` | Datos de entrada inválidos (Pydantic) |
| **429** | `HTTPException` | Rate limit excedido (SlowAPI) |
| **500** | `Exception` (genérico) | Error interno no esperado |

---

## Variables de Entorno

```bash
cp .env.example .env
```

| Variable | Default | Descripción |
|----------|---------|-------------|
| **App** | | |
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `API_V1_PREFIX` | `/api/v1` | Prefijo base de la API |
| `DEBUG` | `false` | Modo debug |
| `LOG_LEVEL` | `INFO` | Nivel de logging |
| **PostgreSQL** | | |
| `POSTGRES_USER` | `postgres` | Usuario |
| `POSTGRES_PASSWORD` | `cinema_db_api_gateway` | Contraseña |
| `POSTGRES_DB` | `cinema_db` | Base de datos |
| `POSTGRES_HOST` | `postgres` | Host (nombre del servicio Docker) |
| `POSTGRES_PORT` | `5432` | Puerto |
| **Redis** | | |
| `REDIS_URL` | `redis://redis:6379/0` | URL de conexión |
| `CACHE_TTL_SECONDS` | `120` | TTL del caché de películas |
| **JWT (RS256)** | | |
| `JWT_PRIVATE_KEY_PATH` | `/app/keys/private.pem` | Ruta a la llave privada |
| `JWT_PUBLIC_KEY_PATH` | `/app/keys/public.pem` | Ruta a la llave pública |
| `JWT_ALGORITHM` | `RS256` | Algoritmo |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | TTL del access token |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | TTL del refresh token |
| **CORS** | | |
| `CORS_ORIGIN` | `["http://localhost:3000"]` | Orígenes permitidos |
| **Rate Limiting** | | |
| `RATE_LIMIT_PUBLIC` | `30` | Límite público (req/min) |
| `RATE_LIMIT_AUTH` | `10` | Límite autenticado base |
| **TMDB** | | |
| `TMDB_API_KEY` | — | API Key de TMDB |
| `TMDB_ACCESS_TOKEN` | — | Access Token de TMDB |
| `TMDB_TIMEOUT_SECONDS` | `10` | Timeout HTTP |
| `TMDB_MAX_RETRIES` | `3` | Reintentos máximos |

---

## Instalación y Configuración

### Requisitos Previos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes) o pip
- Docker + Docker Compose (opcional, recomendado)
- PostgreSQL 16 (si no usas Docker)
- Redis 7 (si no usas Docker)
- OpenSSL (para generar llaves RS256)

### Opción 1: Desarrollo Local (sin Docker)

```bash
# 1. Clonar
git clone <url-del-repositorio>
cd api_rest_movies

# 2. Virtualenv con uv (recomendado)
uv venv
source .venv/bin/activate

# 3. Instalar dependencias
uv sync

# 4. Variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 5. Generar llaves RS256
mkdir -p keys
openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in keys/private.pem -out keys/public.pem

# 6. Base de datos (asegúrate de tener PostgreSQL corriendo)
createdb cinema_db

# 7. Migraciones
alembic upgrade head

# 8. Iniciar servidor de desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Opción 2: Docker (recomendado)

```bash
# 1. Clonar
git clone <url-del-repositorio>
cd api_rest_movies

# 2. Variables de entorno
cp .env.example .env

# 3. Generar llaves RS256
mkdir -p keys
openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in keys/private.pem -out keys/public.pem

# 4. Levantar todo
docker compose up -d --build

# 5. Verificar
docker compose ps
curl http://localhost:8000/api/v1/health
```

---

## Comandos Docker

```bash
# ─── Inicio / Detención ───
docker compose up -d                  # Background
docker compose up -d --build          # Rebuild + background
docker compose down                   # Detener + limpiar contenedores
docker compose down -v                # + eliminar volúmenes (BORRA DATOS)

# ─── Logs ───
docker compose logs -f api            # API en tiempo real
docker compose logs -f postgres       # PostgreSQL
docker compose logs -f redis          # Redis

# ─── Rebuild ───
docker compose build --no-cache       # Completo
docker compose build api              # Solo API

# ─── Acceso a servicios ───
docker compose exec postgres psql -U cinema_admin -d cinema_db
docker compose exec redis redis-cli
docker compose exec api bash

# ─── Migraciones (dentro del contenedor) ───
docker compose exec api alembic upgrade head
docker compose exec api alembic revision --autogenerate -m "descripción"

# ─── Health ───
curl http://localhost:8000/api/v1/health
```

### Arquitectura Docker

```
┌────────────────────────────────────────────────────────────┐
│                   cinema_net (bridge)                      │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │   postgres   │  │    redis     │  │       api        │ │
│  │   :5432      │  │   :6379      │  │    (uvicorn)     │ │
│  │   cinema_db  │  │   db 0       │  │    :8000         │ │
│  └──────────────┘  └──────────────┘  └────────┬─────────┘ │
│                                                │           │
│                                        ┌───────▼─────────┐ │
│                                        │     nginx       │ │
│                                        │   :80 → :8000   │ │
│                                        └───────┬─────────┘ │
└────────────────────────────────────────────────┼────────────┘
                                                 │
                                        Host :8000 → Container :80
```

---

## Comandos Alembic

```bash
# ─── Aplicar migraciones ───
alembic upgrade head                    # Todas las pendientes
alembic upgrade +1                      # Solo la siguiente
alembic upgrade <revision_id>           # Hasta revisión específica

# ─── Revertir ───
alembic downgrade -1                    # La última
alembic downgrade <revision_id>         # Hasta revisión
alembic downgrade base                  # Todas (vaciar BD)

# ─── Generar ───
alembic revision --autogenerate -m "descripción"
alembic revision -m "descripción"       # Manual (vacía)

# ─── Información ───
alembic history                         # Historial completo
alembic heads                           # Revisiones "punta"
alembic current                         # Revisión actual de la BD
alembic branches                        # Ramas (si existen)
```

---

## Comandos de Desarrollo

```bash
# ─── Servidor ───
uvicorn app.main:app --reload                           # Hot-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000         # Accesible en red
uvicorn app.main:app --workers 4                        # Producción

# ─── Linting y Formato (Ruff) ───
ruff check .                              # Verificar
ruff check . --fix                        # Corregir automáticamente
ruff format .                             # Formatear
ruff format --check .                     # Verificar sin modificar

# ─── Type Checking (mypy) ───
mypy app/

# ─── Tests ───
pytest                                    # Todos
pytest -v                                 # Verbose
pytest -x                                 # Parar en primer fallo
pytest --cov=app --cov-report=html        # Coverage HTML
pytest --cov=app --cov-report=term-missing  # Coverage terminal
```

---

## Ejemplos de Uso (curl)

### Registro

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alma_cantu",
    "email": "alma@example.com",
    "password": "SecurePass123!"
  }'

# Response: 201
{
  "id": 1,
  "username": "alma_cantu",
  "email": "alma@example.com",
  "role": "User",
  "is_active": true,
  "created_at": "2026-07-24T12:00:00Z"
}
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=alma_cantu&password=SecurePass123!"

# Response: 200
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer"
}
```

### Obtener Películas Populares

```bash
# Primer request (MISS → va a TMDB, ~300ms)
curl -s http://localhost:8000/api/v1/cinema/movies/popular?page=1 \
  -H "Authorization: Bearer <access_token>" | jq '.from_cache'

# → false

# Segundo request (HIT → Redis, <2ms)
curl -s http://localhost:8000/api/v1/cinema/movies/popular?page=1 \
  -H "Authorization: Bearer <access_token>" | jq '.from_cache'

# → true
```

### Buscar Películas

```bash
curl -s "http://localhost:8000/api/v1/cinema/movies/search?query=Star+Wars&page=1" \
  -H "Authorization: Bearer <access_token>" | jq '.results[0].title'

# → "Star Wars"
```

### Sincronizar Watchlist

```bash
curl -X POST http://localhost:8000/api/v1/account/watchlist \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "media_type": "movie",
    "media_id": 11,
    "watchlist": true
  }'

# Response: 200
{
  "success": true,
  "status_message": "Success."
}
```

### Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'

# Response: 200 (nuevo par de tokens, el anterior queda revocado)
```

### Logout

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>"

# Response: 204 No Content
```

---

## Decisiones de Arquitectura (ADRs)

### ADR-01: JWT RS256 en lugar de HS256

**Contexto:** Necesitamos que múltiples servicios (frontend, otros backends) puedan verificar la validez de los tokens sin poder emitirlos.

**Decisión:** Usar RS256 (RSA Signature with SHA-256).

**Consecuencias:**
- La llave privada se guarda solo en el Gateway (`/app/keys/private.pem`)
- La llave pública se distribuye libremente a cualquier servicio que necesite verificar
- Los tokens son ~250 bytes más grandes que HS256 (por la firma RSA)
- Mayor costo computacional en verificación (marginal en la práctica)

### ADR-02: Cache-Aside en lugar de Write-Through

**Contexto:** El Gateway debe cachear respuestas de TMDB para reducir latencia y evitar rate limits de la API externa.

**Decisión:** Patrón Cache-Aside (Lazy Loading).

**Fundamento:**
- Las películas no se modifican desde el Gateway (solo lectura)
- No hay evento de invalidación desde TMDB
- El TTL (120s) es suficiente para reducir drásticamente las llamadas a TMDB
- Implementación simple: GET → MISS → SETEX

### ADR-03: SQLAlchemy Async + asyncpg en lugar de sync

**Contexto:** FastAPI es asíncrono. Usar un ORM síncrono obligaría a usar hilos (`run_in_executor`).

**Decisión:** SQLAlchemy 2.0 con engine asíncrono + asyncpg.

**Consecuencias:**
- Las operaciones de BD no bloquean el event loop
- Mayor complejidad en sesiones (async context manager)
- asyncpg es el driver PostgreSQL asíncrono más rápido

### ADR-04: SlowAPI para rate limiting

**Contexto:** Necesitamos rate limiting por IP con almacenamiento en Redis.

**Decisión:** SlowAPI (wrapper de FastAPI sobre Flask-Limiter).

**Alternativa considerada:** Redis INCR/EXPIRE manual — se descartó porque SlowAPI ya maneja sliding windows, headers y configuraciones.

### ADR-05: structlog en lugar de logging estándar

**Contexto:** Necesitamos logs estructurados para debugging y observabilidad.

**Decisión:** structlog con salida JSON (producción) y ConsoleRenderer (desarrollo).

**Beneficios:**
- Formato consistente en todos los logs
- Fácil integración con sistemas de logging (ELK, Datadog, Grafana Loki)
- Bindings por contexto (`logger.bind(request_id=...)`)

### ADR-06: PyJWT en lugar de python-jose

**Contexto:** La librería `python-jose` usa `ecdsa` (Python puro) como backend criptográfico, el cual es vulnerable a un ataque de timing (Minerva, CVE-2024-23342) sin fix disponible por parte del mantenedor. Además, sus dependencias transitivas `pyasn1` acumulaban 2 CVEs altas adicionales (CVE-2026-59885, CVE-2026-59886). El proyecto ya había evaluado esta migración previamente (`core/security.py`).

**Decisión:** Migrar de `python-jose[cryptography]` a `PyJWT[crypto]`.

**Fundamento:**
- `PyJWT` usa `cryptography` (OpenSSL) como backend, con implementaciones constant-time inmunes a timing attacks
- `PyJWT` tiene mantenimiento activo (v2.13.0+), mientras que `python-jose` no recibe releases desde 2021
- La API es compatible: ambas librerías exponen `jwt.encode()` y `jwt.decode()` con la misma semántica
- El proyecto ya tenía `PyJWT` como dependencia directa; solo se eliminó `python-jose`

**Resultado:** Se eliminaron 4 paquetes del árbol de dependencias y 3 vulnerabilidades de severidad alta fueron resueltas.

```diff
- "python-jose[cryptography]>=3.3.0"
+ "pyjwt[crypto]>=2.9.0"
```

---

## Roadmap

### Fase 1: Core (✅ Completada)

- [x] Pydantic Settings v2 (configuración tipada)
- [x] SQLAlchemy 2.0 async (models + session)
- [x] JWT RS256 (emisión, verificación, blocklist, rotación)
- [x] RBAC por roles (6 niveles)
- [x] Hashing bcrypt (con protección 72-byte truncation)
- [x] Exception handlers personalizados (7 tipos)
- [x] Structured logging (structlog JSON/Console)
- [x] Redis client async + connection pool
- [x] Middleware de logging (X-Request-ID + timing)
- [x] CacheService (Cache-Aside: get_or_set, get_cached_or_fetch)
- [x] TMDBClient (retry exponencial, timeout, rate limit detection)
- [x] SlowAPI rate limiter con Redis
- [x] Docker multi-stage build (uv + Python slim)
- [x] Docker Compose (Postgres + Redis + API + Nginx)
- [x] Especificación OpenAPI 3.1.0 completa
- [x] Alembic migrations (2 versiones aplicadas)
- [x] Migración PyJWT (python-jose → PyJWT, 3 CVEs resueltas)

### Fase 2: Endpoints (✅ Completada)

- [x] `POST /auth/register` — Registro de usuario
- [x] `POST /auth/login` — Login (OAuth2 Password Flow)
- [x] `POST /auth/refresh` — Refresh token con rotación
- [x] `POST /auth/logout` — Revocar access token
- [x] `POST /auth/tmdb/request-token` — Solicitar token TMDB
- [x] `POST /auth/tmdb/link` — Vincular cuenta TMDB
- [x] `GET /cinema/movies/{category}` — Películas por categoría (cacheado)
- [x] `GET /cinema/movies/search` — Búsqueda (cacheado)
- [x] `GET /cinema/movies/{id}/complementary` — Datos complementarios (concurrente)
- [x] `POST /account/watchlist` — Sincronizar watchlist TMDB

### Fase 3: Quality & Testing (✅ Completada)

- [x] Tests unitarios (pytest + pytest-asyncio)
- [x] Tests de integración (httpx AsyncClient)
- [x] Factory Boy fixtures para tests
- [x] Coverage mínimo 80%
- [x] mypy strict mode
- [x] Ruff linting en CI
- [x] Health check endpoint (/health)
- [x] Pipeline CI/CD (GitHub Actions — lint + type + test + security + build)

### Fase 4: DevOps & Producción (⬜ Pendiente)

- [ ] TLS/SSL (Let's Encrypt + Certbot)
- [ ] Monitoring (Prometheus metrics)
- [ ] Structured tracing (OpenTelemetry)
- [ ] Rate limit middleware ASGI (reemplazar SlowAPI)
- [ ] Endpoints de administración (CRUD usuarios)
- [ ] Script de backup de PostgreSQL
- [ ] Deploy en cloud (AWS/GCP/Azure)

---

<div align="center">

**Secure Cinema API Gateway** &mdash; Built with FastAPI + SQLAlchemy + Redis + Docker

Documentación OpenAPI: [`openapi/openapi.yml`](openapi/openapi.yml)

</div>
