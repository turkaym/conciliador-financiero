# Usamos Python 3.11-slim para un balance óptimo entre peso y estabilidad
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y asegura que los logs salgan en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# 1. Instalación de dependencias del sistema
# Necesarias para: psycopg2 (Postgres), cryptography (Seguridad), lxml (XML/AFIP) y OpenSSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    pkg-config \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# 2. Gestión de dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 🌟 FIX PRIVILEGIOS: Erradicamos la ejecución como root para prevenir RCE/Docker Escapes.
# Creamos un usuario de sistema sin acceso a shell y su respectivo grupo.
RUN groupadd -r conciliador_grp && useradd -r -g conciliador_grp app_user

# 3. Copia de código fuente y asignación de permisos al nuevo usuario
COPY . .
RUN chown -R app_user:conciliador_grp /app

# 🌟 DROP PRIVILEGES: De aquí en adelante, el contenedor (API y Celery) corre sin privilegios root.
USER app_user

# El puerto 80 es nuestro estándar para el balanceador de Traefik
EXPOSE 80

# Comando de inicio por defecto (sobreescribible en docker-compose si es necesario)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]