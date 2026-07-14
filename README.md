<div align="center">

# Secure Cinema API Gateway

### API Gateway empresarial de alta velocidad para TMDB

Auth JWT RS256 + RBAC + Rate Limiting por rol + Cache Redis + Proxy TMDB

---

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-CC0000?style=flat&logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-24-2496ED?style=flat&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-1.27-009639?style=flat&logo=nginx&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-1.13-845ED7?style=flat&logo=alembic&logoColor=white)

</div>

---

## Indice

- [Vision General](#vision-general)
- [Arquitectura](#arquitectura)
- [Stack Tecnologico](#stack-tecnologico)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Pipeline de Request (Flujo Completo)](#pipeline-de-request)
- [Procesos Core](#procesos-core)
  - [Autenticacion JWT RS256](#1-autenticacion-jwt-rs256)
  - [RBAC por Roles](#2-rbac-por-roles)
  - [Rate Limiting Dinamico](#3-rate-limiting-dinamico)
  - [Cache Inteligente Redis](#4-cache-inteligente-redis)
  - [Proxy TMDB](#5-proxy-tmdb)
- [Diagramas](#diagramas)
- [Endpoints API](#endpoints-api)
- [Modelo de Datos](#modelo-de-datos)
- [Variables de Entorno](#variables-de-entorno)
- [Instalacion y Configuracion](#instalacion-y-configuracion)
- [Comandos Docker](#comandos-docker)
- [Comandos Alembic (Migraciones)](#comandos-alembic)
- [Comandos de Desarrollo](#comandos-de-desarrollo)
- [Roadmap](#roadmap)

---

## Vision General

**Secure Cinema API Gateway** es una API REST empresarial que actua como intermediario entre el frontend y la API de TMDB (The Movie Database). No es un simple proxy: inyecta capas transversales de seguridad, control de acceso, rate limiting y cache inteligente antes de reenviar las peticiones a TMDB.

**Problema que resuelve:** Evita que cada cliente (web, movil, smart TV) gestione autenticacion, cache y limites de peticion de forma independiente. Centraliza toda la logica transversal en un solo punto de entrada.

**Capas que inyecta el Gateway:**

```
Cliente (Browser/App)
       |
       v
  [  NGINX  ]  <-- Reverse Proxy, TLS termination, load balancing
       |
       v
  [  AUTH  ]    <-- JWT RS256 + RBAC (verifica identidad y permisos)
       |
       v
  [  RATE LIMITING  ]  <-- Redis INCR/EXPIRE por rol (Admin=1000, User=60, etc.)
       |
       v
  [  CACHE  ]   <-- Redis <2ms (cachea respuestas de TMDB)
       |
       v
  [  TMDB PROXY  ]  <-- httpx async (fetch a TMDB si no esta en cache)
       |
       v
  Respuesta al Cliente (con headers X-Cache, X-Request-ID)
```

---

## Arquitectura

```
                        ┌─────────────────────────────────────┐
                        │           INTERNET                  │
                        └──────────────┬──────────────────────┘
                                       │
                              :8000 :443
                                       │
                        ┌──────────────▼──────────────────────┐
                        │         NGINX 1.27                  │
                        │   Reverse Proxy / Load Balancer     │
                        └──────────────┬──────────────────────┘
                                       │ :80
                 ┌─────────────────────┼─────────────────────┐
                 │                     │                     │
        ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
        │   FastAPI App   │  │   FastAPI App   │  │   FastAPI App   │
        │   (Worker 1)    │  │   (Worker 2)    │  │   (Worker N)    │
        └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
                 │                     │                     │
                 └─────────────────────┼─────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
     ┌────────▼────────┐     ┌────────▼────────┐     ┌────────▼────────┐
     │  PostgreSQL 16  │     │    Redis 7      │     │   TMDB API      │
     │   (RDB Users,   │     │  (Cache, Rate   │     │  (Externa)      │
     │    Sessions,    │     │   Limiting,     │     │                 │
     │    Blocklist)   │     │   Sessions)     │     │                 │
     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

**Arquitectura de datos:**

```
┌──────────────────────────────────────────────────────────────────┐
│                        FastAPI (Async)                           │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │   Routes    │  │ Dependencies │  │     Middlewares         │  │
│  │   (API v1)  │◄─┤  (Auth,      │  │  - RequestLogging      │  │
│  │             │  │   RBAC,      │  │  - CORS                │  │
│  │             │  │   get_db)    │  │  - TrustedHost         │  │
│  └──────┬──────┘  └──────────────┘  └────────────────────────┘  │
│         │                                                        │
│  ┌──────▼──────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Services   │  │   Schemas    │  │      Exceptions        │  │
│  │  (Business  │  │  (Pydantic)  │  │  (Custom Handlers)     │  │
│  │   Logic)    │  │              │  │                        │  │
│  └──────┬──────┘  └──────────────┘  └────────────────────────┘  │
│         │                                                        │
│  ┌──────▼──────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  ORM Models │  │   Session    │  │      Config            │  │
│  │ (SQLAlchemy │  │  (Async      │  │  (Pydantic Settings)   │  │
│  │  2.0 Mapped)│  │   Engine)    │  │                        │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Stack Tecnologico

| Capa | Tecnologia | Version | Proposito |
|------|-----------|---------|-----------|
| **Runtime** | Python | 3.12 | Lenguaje principal |
| **Framework** | FastAPI | 0.115+ | API async de alta performance |
| **ORM** | SQLAlchemy | 2.0+ | Mapeo objeto-relacional (async) |
| **Migraciones** | Alembic | 1.13+ | Control de esquema de BD |
| **BD Relacional** | PostgreSQL | 16 | Users, roles, sessions, blocklist |
| **Cache / Rate Limit** | Redis | 7 | Cache de peliculas, rate limiting, sesiones |
| **Auth** | PyJWT (RS256) | 2.9+ | Tokens asimetricos (private/public key) |
| **Password Hash** | bcrypt | - | Hashing seguro de contrasenas |
| **Validacion** | Pydantic v2 | 2.6+ | Validacion de datos y settings |
| **HTTP Client** | httpx | 0.27+ | Requests async a TMDB API |
| **Proxy Reverso** | Nginx | 1.27 | Load balancing, TLS, routing |
| **Contenedorizacion** | Docker | 24+ | Empaquetamiento de la aplicacion |
| **Orquestacion** | Docker Compose | - | Multi-servicio (API, PG, Redis, Nginx) |
| **Struct Logging** | structlog | 24.1+ | Logging estructurado JSON/Console |
| **Linter** | Ruff | 0.4+ | Linting y formato de codigo |
| **Testing** | pytest | 8.1+ | Tests unitarios y de integracion |
| **Spec API** | OpenAPI | 3.1.0 | Contrato de la API |

---

## Estructura del Proyecto

```
api_rest_movies/
│
├── app/                            # Codigo fuente de la aplicacion
│   ├── main.py                     # Punto de entrada FastAPI (app = FastAPI())
│   ├── enums.py                    # RoleEnum: Admin, Manager, Editor, Moderator, Premium, User
│   │
│   ├── api/                        # Capa de transport HTTP
│   │   ├── deps.py                 # Dependencias: auth, RBAC, get_db
│   │   └── v1/
│   │       └── router.py           # Router principal API v1
│   │
│   ├── core/                       # Infraestructura transversal
│   │   ├── config.py               # Pydantic Settings (DB, JWT, Redis, TMDB, CORS)
│   │   ├── security.py             # JWT RS256, bcrypt, CurrentUser, RBAC
│   │   ├── exceptions.py           # Excepciones custom + handlers FastAPI
│   │   ├── logging.py              # structlog (JSON prod / Console dev)
│   │   └── redis_client.py         # Connection pool Redis async
│   │
│   ├── db/                         # Capa de persistencia
│   │   ├── base.py                 # DeclarativeBase (SQLAlchemy 2.0)
│   │   └── session.py              # AsyncEngine singleton + AsyncSession factory
│   │
│   ├── middlewares/                 # Middlewares ASGI
│   │   ├── logging.py              # RequestLoggingMiddleware (X-Request-ID, timing)
│   │   └── rate_limit.py           # Rate limiting por rol (pendiente)
│   │
│   ├── models/                     # Modelos ORM (SQLAlchemy 2.0 Mapped)
│   │   └── orm.py                  # Users, TMDBSessions, TokenBlocklist
│   │
│   ├── schemas/                    # Schemas Pydantic v2 (request/response)
│   │   ├── auth.py                 # LoginRequest, RegisterRequest, TokenResponse
│   │   ├── user.py                 # UserCreate, UserUpdate, UserResponse, HealthOut
│   │   ├── tmdb_session.py         # TMDBSessionCreate, TMDBSessionResponse
│   │   └── token_blocklist.py      # TokenBlockListCreate, TokenBlockListResponse
│   │
│   └── services/                   # Logica de negocio
│       ├── auth.py                 # Servicio de autenticacion (pendiente)
│       ├── admin.py                # Servicio admin (pendiente)
│       ├── cache.py                # Servicio cache Redis (pendiente)
│       └── tmdb_client.py          # Cliente TMDB async (pendiente)
│
├── alembic/                        # Migraciones de BD
│   ├── env.py                      # Runner async (asyncpg + Alembic)
│   ├── script.py.mako              # Template para nuevas migraciones
│   └── versions/                   # Archivos de migracion generados
│       ├── 0001_initial_schema.py
│       └── 0002_users_update_at_and_rename_role_enum.py
│
├── openapi/                        # Especificacion OpenAPI 3.1.0
│   ├── openapi.yml                 # Archivo raiz
│   ├── paths/                      # Definiciones de endpoints
│   │   └── paths.yml               # Auth, Cinema, Watchlist endpoints
│   └── components/                 # Schemas, parameters, security
│       ├── schemas/                # UserRegister, TokenScheme, TMDBMovieResult, etc.
│       └── parameters/             # MovieCategoryParam, MovieIdParam, MoviePageParam
│
├── cinema-gateway/                 # Docker (Dockerfile + docker-compose)
│   ├── Dockerfile                  # Multi-stage build (builder + runtime)
│   ├── docker-compose.yml          # Postgres, Redis, API, Nginx
│   ├── pyproject.toml              # Dependencias del proyecto (uv)
│   └── uv.lock                     # Lockfile de dependencias
│
├── api_gateway/                    # Configuracion Nginx
│   ├── Dockerfile
│   ├── nginx.conf
│   └── conf.d/
│       └── api-gateway.conf        # Upstream + routing rules
│
├── db/
│   └── postgres-sql/
│       └── init.sql                # Script de inicializacion de BD
│
├── scripts/                        # Scripts utilitarios
├── tests/                          # Suite de tests
│
├── .env                            # Variables de entorno (NO commitear)
├── .env.example                    # Template de variables de entorno
├── .python-version                 # 3.12
├── alembic.ini                     # Configuracion Alembic
├── docker-compose.yml              # Docker Compose (raiz)
├── .gitignore                      # Reglas de ignorados
└── README.md                       # Este archivo
```

---

## Pipeline de Request

Cada peticion que llega al Gateway atraviesa un pipeline de 7 etapas:

```
 ① CLIENTE                    Envia peticion HTTP/HTTPS
     │
     ▼
 ② NGINX                      Reverse proxy: TLS, rate limit global, load balance
     │
     ▼
 ③ MIDDLEWARE (Logging)        X-Request-ID, timing, log estructurado
     │
     ▼
 ④ DEPENDENCY (Auth)           Decodifica JWT RS256, extrae user_id + role
     │
     ▼
 ⑤ DEPENDENCY (RBAC)           Verifica que el rol tiene permisos para el endpoint
     │
     ▼
 ⑥ SERVICE (Rate Limiting)     Redis INCR/EXPIRE: verifica cuota del rol por minuto
     │
     ▼
 ⑦ SERVICE (Cache / Proxy)     Redis GET (cache <2ms) ──hit──> Respuesta
     │                              │
     │                         miss │
     │                              ▼
     │                         httpx GET TMDB ──> Redis SET (guarda en cache)
     │
     ▼
 ⑧ RESPUESTA                   JSON + headers (X-Cache, X-Request-ID, Rate-Limit-Remaining)
```

### Pipeline Detallado: Autenticacion

```
  Request llega con Authorization: Bearer <token>
     │
     ▼
  HTTPBearer (FastAPI) ──> Extrae token del header
     │
     ▼
  jwt.decode(token, PUBLIC_KEY, RS256)
     │
     ├── Firma invalida ──> 401 Unauthorized
     │
     ├── Token expirado ──> 401 Unauthorized
     │
     ├── type != "access" ──> 401 (se requiere access token)
     │
     ├── jti en TokenBlocklist? ──> 401 (token revocado)
     │
     ▼
  CurrentUser(user_id, role) ──> Inyectado en el endpoint
```

### Pipeline Detallado: Cache HIT/MISS

```
  GET /api/v1/cinema/movies/popular?page=1
     │
     ▼
  Redis GET "cinema:movies:popular:1"
     │
     ├── HIT (<2ms) ──> Respuesta directa + X-Cache: HIT
     │
     └── MISS
          │
          ▼
     httpx.get("https://api.themoviedb.org/3/movie/popular?page=1")
          │
          ▼
     Redis SET "cinema:movies:popular:1" EX 120  (TTL configurable)
          │
          ▼
     Respuesta + X-Cache: MISS
```

---

## Procesos Core

### 1. Autenticacion JWT RS256

El sistema usa **claves asimetricas** (RS256) en lugar de simetricas (HS256):

```
┌──────────────┐         ┌──────────────┐
│ PRIVATE KEY  │         │  PUBLIC KEY  │
│  (Firma)     │         │ (Verifica)   │
│  /app/keys/  │         │  /app/keys/  │
│  private.pem │         │  public.pem  │
└──────┬───────┘         └──────┬───────┘
       │                        │
       │  Solo el servidor      │  Cualquier servicio
       │  puede EMITIR tokens   │  puede VERIFICAR tokens
       │                        │
       ▼                        ▼
  jwt.encode()             jwt.decode()
  (emision)                (verificacion)
```

**Ventaja sobre HS256:** En un patron Gateway con multiples servicios, la llave publica se puede distribuir libremente. Otros servicios pueden verificar tokens sin poder emitirlos.

**Payload del token (Claims):**

```json
{
  "sub": "user_id",
  "role": "Admin",
  "type": "access",
  "jti": "uuid-unico",
  "iat": "2026-07-14T12:00:00Z",
  "exp": "2026-07-14T12:30:00Z"
}
```

| Claim | Descripcion | Access Token | Refresh Token |
|-------|------------|--------------|---------------|
| `sub` | ID del usuario | 30 minutos | 7 dias |
| `role` | Rol RBAC | Si | Si |
| `type` | "access" o "refresh" | "access" | "refresh" |
| `jti` | UUID unico (para blocklist) | Si | Si |
| `exp` | Fecha de expiracion | 30 min | 7 dias |

### 2. RBAC por Roles

Sistema de control de acceso basado en roles con 6 niveles jerarquicos:

```
  ┌─────────┐
  │  Admin   │  ← Acceso total (1000 req/min)
  └────┬─────┘
       │
  ┌────▼─────┐
  │ Manager  │  ← Gestion (500 req/min)
  └────┬─────┘
       │
  ┌────▼─────┐
  │  Editor  │  ← Edicion (300 req/min)
  └────┬─────┘
       │
  ┌────▼──────┐
  │ Moderator │  ← Moderacion (300 req/min)
  └────┬──────┘
       │
  ┌────▼──────┐
  │  Premium  │  ← Premium (120 req/min)
  └────┬──────┘
       │
  ┌────▼─────┐
  │   User   │  ← Basico (60 req/min)
  └──────────┘
```

**Uso en endpoints:**

```python
# Solo admin puede gestionar usuarios
@router.get("/admin/users", dependencies=[Depends(require_admin)])

# Admin o editor pueden modificar contenido
@router.put("/movies/{id}", dependencies=[Depends(require_editor_or_admin)])

# Cualquier usuario autenticado puede ver peliculas
@router.get("/cinema/movies/{category}", dependencies=[Depends(CurrentUser.get_current_user)])
```

### 3. Rate Limiting Dinamico

Implementado con Redis `INCR` + `EXPIRE` ( sliding window de 1 minuto ):

```
  Request llega ──> Redis INCR "rate:{user_id}:{minute}"
                      │
                      ├── Contador <= Limite del rol ──> Permitir
                      │
                      └── Contador > Limite del rol ──> 429 Too Many Requests
```

**Limites por rol (peticiones/minuto):**

| Rol | Limite | Segundos entre requests |
|-----|--------|------------------------|
| Admin | 1000 | 0.06s |
| Manager | 500 | 0.12s |
| Editor | 300 | 0.2s |
| Moderator | 300 | 0.2s |
| Premium | 120 | 0.5s |
| User | 60 | 1s |

### 4. Cache Inteligente Redis

- **TTL configurable:** `MOVIE_CACHE_TTL_SECONDS=120` (default 2 minutos)
- **Key format:** `cinema:movies:{category}:{page}`
- **Header de respuesta:** `X-Cache: HIT` o `X-Cache: MISS`
- **Invalidacion:** Automatica por TTL (no hay invalidacion manual ainda)

### 5. Proxy TMDB

El Gateway actua como proxy transparente contra la API de TMDB:

```
  Frontend ──> GET /api/v1/cinema/movies/popular
                    │
                    ▼
  Gateway ──> GET https://api.themoviedb.org/3/movie/popular
                    │
                    ▼
  Respuesta enriquecida:
  {
    "page": 1,
    "results": [...],
    "total_pages": 500,
    "total_results": 1000,
    "from_cache": false,
    "rate_limiting_remaining": 54
  }
```

**Endpoints TMDB mapeados:**

| Endpoint Gateway | Endpoint TMDB | Descripcion |
|-----------------|---------------|-------------|
| `GET /cinema/movies/{category}` | `GET /movie/{category}` | Listas: popular, now_playing, top_rated, upcoming |
| `GET /cinema/movies/{id}/complementary` | `GET /movie/{id}` + `/credits` + `/videos` | Agregacion concurrente (asyncio.gather) |
| `POST /account/watchlist` | `POST /account/{id}/watchlist` | Mutacion de watchlist del usuario |

---

## Diagramas

### Diagrama de Secuencia: Login

```
  Cliente              API Gateway           PostgreSQL          Redis
    │                      │                     │                  │
    │  POST /auth/login    │                     │                  │
    │  (email + password)  │                     │                  │
    │─────────────────────>│                     │                  │
    │                      │  SELECT user        │                  │
    │                      │  WHERE email = ?    │                  │
    │                      │────────────────────>│                  │
    │                      │  user + hash        │                  │
    │                      │<────────────────────│                  │
    │                      │                     │                  │
    │                      │  bcrypt.checkpw()   │                  │
    │                      │  (verifica hash)    │                  │
    │                      │                     │                  │
    │                      │  jwt.encode()       │                  │
    │                      │  (RS256, 30min)     │                  │
    │                      │                     │                  │
    │  200 OK              │                     │                  │
    │  {access_token,      │                     │                  │
    │   refresh_token}     │                     │                  │
    │<─────────────────────│                     │                  │
```

### Diagrama de Secuencia: Peliculas con Cache

```
  Cliente              API Gateway           Redis              TMDB API
    │                      │                    │                    │
    │  GET /cinema/movies/ │                    │                    │
    │  popular?page=1      │                    │                    │
    │  Authorization: Bearer <token>            │                    │
    │─────────────────────>│                    │                    │
    │                      │                    │                    │
    │                      │  [JWT Verifica]    │                    │
    │                      │  [RBAC Check]      │                    │
    │                      │  [Rate Limit Check]│                    │
    │                      │                    │                    │
    │                      │  GET cinema:       │                    │
    │                      │  movies:popular:1  │                    │
    │                      │───────────────────>│                    │
    │                      │                    │                    │
    │          ┌─── HIT ───┤  <value>           │                    │
    │          │           │                    │                    │
    │  200 OK  │           │                    │                    │
    │  X-Cache: HIT        │                    │                    │
    │<─────────┘           │                    │                    │
    │                      │                    │                    │
    │          ┌─── MISS ──┤  None              │                    │
    │          │           │                    │  GET /movie/       │
    │          │           │─────────────────────────────────────── >│
    │          │           │                    │  TMDB Response     │
    │          │           │<───────────────────────────────────────│
    │          │           │                    │                    │
    │          │           │  SET cinema:movies:│                    │
    │          │           │  popular:1 EX 120  │                    │
    │          │           │───────────────────>│                    │
    │  200 OK  │           │                    │                    │
    │  X-Cache: MISS       │                    │                    │
    │<─────────┘           │                    │                    │
```

### Diagrama de Secuencia: Watchlist Sync

```
  Cliente              API Gateway           PostgreSQL          TMDB API
    │                      │                     │                  │
    │  POST /account/      │                     │                  │
    │  watchlist            │                     │                  │
    │  {media_type,        │                     │                  │
    │   media_id, watchlist}│                     │                  │
    │─────────────────────>│                     │                  │
    │                      │                     │                  │
    │                      │  [JWT + RBAC]       │                  │
    │                      │                     │                  │
    │                      │  SELECT tmdb_session │                  │
    │                      │  WHERE user_id = ?  │                  │
    │                      │────────────────────>│                  │
    │                      │  tmdb_session_id    │                  │
    │                      │<────────────────────│                  │
    │                      │                     │                  │
    │                      │  POST /account/     │                  │
    │                      │  {id}/watchlist     │                  │
    │                      │───────────────────────────────────────>│
    │                      │  TMDB Response      │                  │
    │                      │<───────────────────────────────────────│
    │                      │                     │                  │
    │  200 OK              │                     │                  │
    │  {success: true,     │                     │                  │
    │   status_message}    │                     │                  │
    │<─────────────────────│                     │                  │
```

---

## Endpoints API

### Identity & Access

| Metodo | Endpoint | Descripcion | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/v1/auth/register` | Registro de usuario (bcrypt hash) | No |
| `POST` | `/api/v1/auth/login` | Login (OAuth2 Password Flow) | No |
| `POST` | `/api/v1/auth/refresh` | Renovar access token | Refresh Cookie |
| `POST` | `/api/v1/auth/logout` | Revocar token (blocklist) | Bearer |

### Cinema Discovery (Proxy TMDB)

| Metodo | Endpoint | Descripcion | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/v1/cinema/movies/{category}` | Listar peliculas por categoria | Bearer |
| `GET` | `/api/v1/cinema/movies/{movie_id}/complementary` | Datos complementarios (detalles + creditos + videos) | Bearer |

**Categorias disponibles:** `popular`, `now_playing`, `top_rated`, `upcoming`

### User Account Sync

| Metodo | Endpoint | Descripcion | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/v1/account/watchlist` | Sincronizar watchlist con TMDB | Bearer |

### System

| Metodo | Endpoint | Descripcion | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Health check (status, version, environment) | No |
| `GET` | `/docs` | Swagger UI (solo en development/staging) | No |

---

## Modelo de Datos

```
┌─────────────────────────────────────┐
│              users                  │
├─────────────────────────────────────┤
│ id          SERIAL PRIMARY KEY      │
│ user_name   VARCHAR(50) UNIQUE      │
│ email       VARCHAR(255) UNIQUE     │
│ password_hash VARCHAR(255)          │
│ role        user_role ENUM          │
│ is_active   BOOLEAN DEFAULT true    │
│ created_at  TIMESTAMPTZ             │
│ updated_at  TIMESTAMPTZ             │
└──────────────┬──────────────────────┘
               │ 1
               │
               │ *
┌──────────────▼──────────────────────┐
│          tmdb_sessions              │
├─────────────────────────────────────┤
│ id              SERIAL PRIMARY KEY  │
│ user_id         INT FK → users.id   │
│ tmdb_account_id VARCHAR(100)        │
│ tmdb_session_id VARCHAR(255)        │
│ connected_at    TIMESTAMPTZ         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         token_blocklist             │
├─────────────────────────────────────┤
│ id          SERIAL PRIMARY KEY      │
│ jti         VARCHAR(255) UNIQUE     │
│ exp         TIMESTAMPTZ             │
│ blocked_at  TIMESTAMPTZ             │
└─────────────────────────────────────┘
```

**Enum `user_role`:**
`Admin` | `Manager` | `Editor` | `Moderator` | `Premium` | `User`

---

## Variables de Entorno

Copiar `.env.example` a `.env` y completar:

```bash
cp .env.example .env
```

| Variable | Default | Descripcion |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `API_V1_PREFIX` | `/api/v1` | Prefijo base de la API |
| `POSTGRES_USER` | `cinema_admin` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | `cinema_db_api_gateway` | Contrasena de PostgreSQL |
| `POSTGRES_DB` | `cinema_db` | Nombre de la base de datos |
| `POSTGRES_HOST` | `postgres` | Host de PostgreSQL (Docker service name) |
| `POSTGRES_PORT` | `5432` | Puerto de PostgreSQL |
| `REDIS_URL` | `redis://redis:6379/0` | URL de conexion Redis |
| `MOVIE_CACHE_TTL_SECONDS` | `120` | TTL del cache de peliculas (segundos) |
| `JWT_SECRET_KEY` | *(requerido)* | Secreto JWT (min 32 caracteres) |
| `JWT_PRIVATE_KEY_PATH` | `/app/keys/private.pem` | Ruta a la llave privada RS256 |
| `JWT_PUBLIC_KEY_PATH` | `/app/keys/public.pem` | Ruta a la llave publica RS256 |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | TTL del access token |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | TTL del refresh token |

---

## Instalacion y Configuracion

### Requisitos Previos

- Python 3.12+
- uv (gestor de paquetes) o pip
- Docker + Docker Compose
- PostgreSQL 16 (local o en Docker)
- Redis 7 (local o en Docker)

### Opcion 1: Desarrollo Local (sin Docker)

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd api_rest_movies

# 2. Crear virtualenv con uv (recomendado) o venv
uv venv
source .venv/bin/activate

# 3. Instalar dependencias
uv sync

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 5. Generar llaves RS256
mkdir -p keys
openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in keys/private.pem -out keys/public.pem

# 6. Crear la base de datos
createdb cinema_db

# 7. Ejecutar migraciones
alembic upgrade head

# 8. Iniciar el servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Opcion 2: Con Docker (recomendado)

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd api_rest_movies

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 3. Generar llaves RS256
mkdir -p keys
openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in keys/private.pem -out keys/public.pem

# 4. Levantar todos los servicios
docker compose up -d

# 5. Verificar que todo este funcionando
docker compose ps
curl http://localhost:8000/health
```

---

## Comandos Docker

```bash
# ─── Levantar servicios ───
docker compose up -d                    # Levantar en background
docker compose up -d --build            # Rebuild + levantar
docker compose up                       # Levantar con logs en foreground

# ─── Detener servicios ───
docker compose down                     # Detener y eliminar contenedores
docker compose down -v                  # Detener + eliminar volumenes (BORRA DATOS)

# ─── Ver estado ───
docker compose ps                       # Estado de los servicios
docker compose logs -f api              # Logs en tiempo real del API
docker compose logs -f postgres         # Logs de PostgreSQL
docker compose logs -f redis            # Logs de Redis

# ─── Reconstruir ───
docker compose build --no-cache         # Rebuild completo sin cache
docker compose build api                # Rebuild solo del API

# ─── Acceder a servicios ───
docker compose exec postgres psql -U cinema_admin -d cinema_db   # Shell PostgreSQL
docker compose exec redis redis-cli                                # Shell Redis
docker compose exec api bash                                        # Shell del API

# ─── Verificar salud ───
docker compose ps --format json         # Estado JSON
curl http://localhost:8000/health       # Health check API
```

### Arquitectura Docker

```
┌──────────────────────────────────────────────────┐
│               cinema_net (bridge)                │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ postgres │  │  redis   │  │      api     │   │
│  │ :5436    │  │  :6379   │  │   (internal) │   │
│  │ → 5432   │  │          │  │   → :8000    │   │
│  └──────────┘  └──────────┘  └──────┬───────┘   │
│                                     │            │
│                              ┌──────▼───────┐   │
│                              │    nginx     │   │
│                              │  :8000 → :80 │   │
│                              └──────────────┘   │
└──────────────────────────────────────────────────┘
         │
    Puerto 8000 expuesto al host
```

---

## Comandos Alembic

```bash
# ─── Configuracion inicial ───
alembic init alembic                     # Inicializar Alembic (ya hecho)

# ─── Generar migraciones ───
alembic revision --autogenerate -m "descripcion"   # Auto-generar desde modelos
alembic revision -m "descripcion"                   # Migracion manual (en blanco)

# ─── Aplicar migraciones ───
alembic upgrade head                     # Aplicar todas las migraciones pendientes
alembic upgrade +1                       # Aplicar solo la siguiente migracion
alembic upgrade <revision_id>            # Aplicar hasta una revision especifica

# ─── Revertir migraciones ───
alembic downgrade -1                     # Revertir la ultima migracion
alembic downgrade <revision_id>          # Revertir hasta una revision especifica
alembic downgrade base                   # Revertir todas las migraciones

# ─── Informacion ───
alembic history                          # Ver historial de migraciones
alembic heads                            # Ver revisiones head (punta)
alembic current                          # Ver revision actual de la BD
alembic branches                         # Ver ramas de migraciones

# ─── Dentro del container ───
docker compose exec api alembic upgrade head
docker compose exec api alembic revision --autogenerate -m "add feature X"
```

---

## Comandos de Desarrollo

### Linting y Formato

```bash
# Ruff (linting + formato)
ruff check .                             # Verificar errores de linting
ruff check . --fix                       # Corregir errores automaticamente
ruff format .                            # Formatear codigo
ruff format --check .                    # Verificar formato sin modificar

# Type checking (mypy)
mypy app/                                # Verificar tipos
```

### Testing

```bash
# Ejecutar tests
pytest                                   # Ejecutar todos los tests
pytest -v                                # Modo verbose
pytest -x                                # Detener en primer fallo
pytest --tb=short                        # Traceback corto

# Coverage
pytest --cov=app --cov-report=html       # Coverage con reporte HTML
pytest --cov=app --cov-report=term-missing  # Coverage en terminal
```

### Ejecucion Local

```bash
# uvicorn (desarrollo)
uvicorn app.main:app --reload            # Con hot-reload
uvicorn app.main:app --reload --port 9000  # Puerto personalizado
uvicorn app.main:app --host 0.0.0.0 --port 8000  # Accesible en red

# uvicorn (produccion)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Generacion de Llaves RS256

```bash
# Generar llave privada
openssl genpkey -algorithm RSA -out keys/private.pem -pkeyopt rsa_keygen_bits:2048

# Generar llave publica desde la privada
openssl rsa -pubout -in keys/private.pem -out keys/public.pem

# Verificar llaves
openssl rsa -in keys/private.pem -check -noout
openssl rsa -in keys/public.pem -pubin -noout
```

---

## Roadmap

### Fase 1: Core (Completada)

- [x] Configuracion Pydantic Settings v2
- [x] SQLAlchemy 2.0 async (Models + Session)
- [x] JWT RS256 (emision, verificacion, blocklist)
- [x] RBAC por roles (6 niveles)
- [x] Hashing bcrypt
- [x] Exception handlers personalizados
- [x] Structured logging (structlog)
- [x] Redis client async
- [x] Middleware de logging (X-Request-ID)
- [x] Docker multi-stage build
- [x] Docker Compose (Postgres + Redis + API + Nginx)
- [x] Especificacion OpenAPI 3.1.0

### Fase 2: Endpoints (En Progreso)

- [ ] `POST /auth/register` - Registro de usuario
- [ ] `POST /auth/login` - Login + tokens
- [ ] `POST /auth/refresh` - Renovar access token
- [ ] `POST /auth/logout` - Revocar token
- [ ] `GET /cinema/movies/{category}` - Listar peliculas
- [ ] `GET /cinema/movies/{id}/complementary` - Datos complementarios
- [ ] `POST /account/watchlist` - Sync watchlist TMDB

### Fase 3: Services (Pendiente)

- [ ] Servicio de autenticacion (auth.py)
- [ ] Servicio de cache Redis (cache.py)
- [ ] Cliente TMDB async (tmdb_client.py)
- [ ] Rate limiting por rol (rate_limit.py)
- [ ] Servicio admin (admin.py)

### Fase 4: Calidad (Pendiente)

- [ ] Tests unitarios (pytest)
- [ ] Tests de integracion
- [ ] mypy strict mode
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Health check endpoints
- [ ] Swagger UI funcional

### Fase 5: Produccion (Futuro)

- [ ] TLS/SSL (Let's Encrypt)
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Tracing (OpenTelemetry)
- [ ] CI/CD automatizado
- [ ] Deploy en cloud (AWS/GCP/Azure)

---

<div align="center">

**Secure Cinema API Gateway** &mdash; Built with FastAPI + SQLAlchemy + Redis + Docker

</div>
