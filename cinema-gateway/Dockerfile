# ---------- Docker: Multi Stage ----------
# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv 

WORKDIR /app

# Solo el manifiesto + lockfile: esta capa se cachea mientras las dependencias no cambien,
# sin importar cuántas veces cambie el código de app/.
COPY cinema-gateway/pyproject.toml cinema-gateway/uv.lock ./

RUN uv venv /opt/venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \ 
    PATH="/opt/venv/bin:$PATH"

# --no-install-project instala SOLO las dependencias resueltas en uv.lock.
# No requiere el código fuente de app/ (que todavía no existe en esta capa) ni [build-system].
RUN  uv sync --frozen --no-install-project --no-dev

# Ahora sí copiamos el código y lo instalamos (no editable) en el mismo venv.
COPY cinema-gateway/ .
COPY app/ ./app/
RUN uv sync --frozen --no-dev


# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

# curl es necesario para el HEALTHCHECK; se instala solo en runtime, no en builder.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN mkdir -p /app/keys && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \ 
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]