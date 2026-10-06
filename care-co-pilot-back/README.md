# Co-Piloto de Duelo — Backend

Base del proyecto universitario con Python, FastAPI, Pydantic y PostgreSQL.
La aplicación es de acompañamiento: no realiza diagnósticos ni sustituye
atención profesional o servicios de emergencia.

## Alcance actual

- Configuración mediante `APP_NAME`, `APP_ENV` y `DATABASE_URL`.
- Motor SQLAlchemy y sesiones PostgreSQL creados bajo demanda.
- Comprobación manual de la base mediante `SELECT 1`, sin crear tablas.
- `GET /health`: respuesta `{"status":"ok"}` para comprobar que la API responde.
- Documentación automática en `/docs` y contrato OpenAPI en `/openapi.json`.
- Pruebas de configuración, conexión y HTTP con `unittest`.

Esta etapa no crea tablas ni incorpora autenticación JWT o IA. El endpoint
`/health` confirma únicamente que la API responde; no comprueba PostgreSQL.

## Estructura

```text
app/
├── core/        # Configuración; seguridad en etapas posteriores
├── database/    # Motor, sesiones y comprobación de PostgreSQL
├── models/      # Modelos SQLAlchemy futuros
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

Las pruebas HTTP inician y detienen su propio servidor Uvicorn en un puerto libre.
No requieren que ejecutes la API manualmente ni una base PostgreSQL. Para probar
la conexión real desde el backend, con `DATABASE_URL` configurada, ejecuta:

```powershell
python -c "from app.database import verify_database_connection; verify_database_connection()"
```

La comprobación abre una conexión y ejecuta `SELECT 1`; si falla, informa un
error sin mostrar la URL ni los detalles de autenticación.
