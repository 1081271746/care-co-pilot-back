# Co-Piloto de Duelo — Backend

Base inicial del proyecto universitario con Python, FastAPI y Pydantic.
La aplicación es de acompañamiento: no realiza diagnósticos ni sustituye
atención profesional o servicios de emergencia.

## Alcance actual

- Configuración mediante `APP_NAME` y `APP_ENV`.
- `GET /health`: respuesta `{"status":"ok"}` para comprobar que la API responde.
- Documentación automática en `/docs` y contrato OpenAPI en `/openapi.json`.
- Pruebas de configuración y HTTP con `unittest`, incluido en Python.

Todavía no hay conexión a PostgreSQL, modelos de datos, autenticación ni IA.
El endpoint de salud no comprueba la base de datos.

## Estructura

```text
app/
├── core/        # Configuración; seguridad en etapas posteriores
├── database/    # Conexión a PostgreSQL en la siguiente etapa
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

Los valores del ejemplo no contienen credenciales. `APP_ENV` admite
`development`, `test` o `production`. Las variables del entorno tienen prioridad
sobre `.env`; un valor inválido impide iniciar la API.

No subas `.env` a GitHub. No se requieren credenciales de PostgreSQL en esta etapa.

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
No requieren que ejecutes la API manualmente ni utilizan una base de datos.
