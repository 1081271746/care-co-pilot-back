# Co-Piloto de Duelo — Backend

Base del proyecto universitario con Python, FastAPI, Pydantic y PostgreSQL.
La aplicación es de acompañamiento: no realiza diagnósticos ni sustituye
atención profesional o servicios de emergencia.

## Alcance actual

- Configuración mediante `APP_NAME`, `APP_ENV` y `DATABASE_URL`.
- Motor SQLAlchemy y sesiones PostgreSQL creados bajo demanda.
- Comprobación manual de la base mediante `SELECT 1`, sin crear tablas.
- Modelo mínimo de cuenta: correo único, hash de contraseña y fecha de creación.
- Migraciones Alembic explícitas; la API no crea ni modifica tablas al iniciar.
- `POST /auth/login`: verifica las credenciales contra una cuenta persistida y
  devuelve un JWT únicamente cuando ambas son válidas.
- Validación de tokens de acceso JWT firmados con HS256 y una clave del entorno.
- `GET /auth/me`: devuelve la identidad solo cuando el bearer token es válido.
- Comprobación reutilizable de propiedad de registros que responde 404 para
  registros ajenos.
- `GET /health`: respuesta `{"status":"ok"}` para comprobar que la API responde.
- Documentación automática en `/docs` y contrato OpenAPI en `/openapi.json`.
- Pruebas de configuración, conexión y HTTP con `unittest`, incluido el login sobre
  una base SQLite temporal.

El inicio de sesión responde con el mismo error genérico si el correo no existe o
la contraseña no coincide. Las contraseñas se almacenan mediante PBKDF2-HMAC-SHA256
con una sal aleatoria; nunca se guardan en texto plano. Las rutas de datos deben
exigir `get_current_user` y comprobar la propiedad antes de devolver, modificar o
eliminar registros. El endpoint `/health` confirma únicamente que la API responde;
no comprueba PostgreSQL.

## Estructura

```text
app/
├── core/        # Configuración, seguridad JWT y autorización por propietario
├── database/    # Motor, sesiones y comprobación de PostgreSQL
├── models/      # Modelos SQLAlchemy
├── migrations/  # Cambios versionados del esquema con Alembic
├── routers/     # Endpoints
├── schemas/     # Validación y respuestas Pydantic
├── services/    # Lógica de negocio futura
└── main.py      # Creación de FastAPI y registro de rutas
tests/          # Pruebas
```

## Ejecutar en tu computador

Usa Python 3.11 o superior. Ejecuta los comandos desde la raíz de este repositorio.

### 1. Crear y activar el entorno local

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias

```powershell
python -m pip install -r requirements.txt
```

### 3. Preparar configuración

```powershell
Copy-Item .env.example .env
```

`APP_ENV` admite `development`, `test` o `production`. `DATABASE_URL` es
opcional para iniciar la API; configúrala para usar PostgreSQL. Las variables
del entorno tienen prioridad sobre `.env`; un valor inválido impide iniciar la
API.

Configura `JWT_SECRET_KEY` en el gestor seguro de variables del entorno (o en
`.env` local, que no debe subirse al repositorio). Debe contener al menos 32
bytes aleatorios; puede generarse con `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
El archivo `.env.example` deja esta variable vacía. La autenticación rechaza
tokens si el secreto no está configurado o es demasiado corto.

La URL suele tener el formato
`postgresql+psycopg://USUARIO:CONTRASEÑA@HOST:5432/BASE`. Replit puede
proporcionar `DATABASE_URL` al habilitar su PostgreSQL. No escribas credenciales
en el repositorio ni subas `.env`; `.env.example` deja la URL vacía.

El controlador instalado es `psycopg` 3 (distribución `psycopg[binary]`).
SQLAlchemy no incluye un controlador PostgreSQL y, sin indicarlo, suele intentar
usar `psycopg2`. Esta configuración convierte las URL `postgresql://` al
controlador `postgresql+psycopg` de forma explícita.

### 4. Iniciar FastAPI

```powershell
python -m uvicorn app.main:app --reload
```

- Salud: <http://127.0.0.1:8000/health>
- Swagger: <http://127.0.0.1:8000/docs>

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

## Aplicar o revertir el esquema

Desde la raíz del backend y con `DATABASE_URL` configurada, aplica únicamente
las migraciones versionadas con:

```powershell
alembic upgrade head
```

Para revertir la migración inicial y eliminar la tabla `users`:

```powershell
alembic downgrade base
```

La API no ejecuta esos comandos ni modifica el esquema durante el inicio.

Las pruebas HTTP inician y detienen su propio servidor Uvicorn en un puerto libre.
No requieren que ejecutes la API manualmente ni una base PostgreSQL. Para probar
la conexión real desde el backend, con `DATABASE_URL` configurada, ejecuta:

```powershell
python -c "from app.database import verify_database_connection; verify_database_connection()"
```

La comprobación abre una conexión y ejecuta `SELECT 1`; si falla, informa un
error sin mostrar la URL ni los detalles de autenticación.
