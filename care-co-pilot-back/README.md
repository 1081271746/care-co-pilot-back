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

## Consultar registros privados por páginas

`GET /records` requiere un JWT válido y devuelve exclusivamente registros de la
cuenta autenticada. Acepta `limit` (entero entre 1 y 100, por defecto 20) y
`offset` (entero no negativo, por defecto 0). Los parámetros inválidos reciben 422.
El orden es `created_at` descendente y, si las fechas coinciden, `id` descendente.

La respuesta deja de ser una lista directa y pasa a ser un objeto:

```json
{"items": [], "limit": 20, "offset": 0, "has_more": false}
```

Cada elemento de `items` conserva el contrato del registro individual. Para
consultar la página siguiente, aumenta `offset` en `limit` mientras `has_more`
sea verdadero. Una cuenta sin registros o un desplazamiento fuera del historial
devuelve `items: []` y `has_more: false`. Este indicador solo considera registros
propios; la consulta carga como máximo `limit + 1` filas, no todo el historial.

El orden es determinista mientras los datos no cambien: al crear o eliminar
registros entre peticiones, la paginación por desplazamiento puede repetir u
omitir elementos. No representa una instantánea del historial.

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

### Integración con PostgreSQL real (nunca producción)

Las pruebas rápidas SQLite se conservan. Las pruebas `test_postgres*.py` usan
las mismas rutas HTTP y las migraciones Alembic completas, no `create_all`.
Sin configuración explícita, las pruebas que requieren PostgreSQL se omiten;
las guardas de seguridad siempre se prueban.

Con PostgreSQL instalado (`initdb`, `pg_ctl` y `createdb` en PATH), ejecuta:

```sh
python tests/run_postgres.py
```

Este comando crea un clúster temporal en un puerto libre de loopback, ejecuta
la integración y lo detiene y elimina incluso si fallan las pruebas. No necesita
contraseñas ni lee `DATABASE_URL`. Usa autenticación local trust únicamente para
datos ficticios en ese clúster desechable; no usar esta configuración para la API.
No se ejecuta como root.

También puedes usar **una base PostgreSQL local dedicada exclusivamente a pruebas**
con nombre terminado en `_test`. Configura en tu gestor seguro de variables:

- `TEST_DATABASE_URL`: URL PostgreSQL con psycopg, sin parámetros adicionales.
  No reutilices la base de desarrollo ni de producción.
- `APP_ENV=test`.
- `TEST_POSTGRES_ALLOW_MIGRATIONS=1`: autorización explícita de DDL en la base de pruebas.

```sh
python -m unittest discover -s tests -p 'test_postgres*.py' -v
```

Solo se aceptan `localhost`, `127.0.0.1` o `::1`; no se permiten hosts remotos,
SQLite, parámetros que redirijan el host ni un entorno de producción. La suite
lee su configuración de conexión directamente del proceso, **no del archivo
`.env`**, y nunca recurre a `DATABASE_URL` para conectarse. Si se autoriza DDL sin URL o se configura una URL insegura,
falla en lugar de omitir silenciosamente la integración.

Cada prueba crea un esquema aleatorio exclusivo y lo elimina al terminar. El
usuario de pruebas necesita permisos de conexión y creación de esquemas; no
necesita privilegios de superusuario. La conexión explícita de Alembic asegura que
tablas, índices y `alembic_version` se creen solo en ese esquema, sin tocar `public`.
Una interrupción forzada del proceso puede dejar esquemas `private_test_*`; usa una
base desechable, no una base compartida. Nunca guardes URL reales o contraseñas en
archivos versionados; `.env.example` deja la variable vacía.

La integración verifica CRUD de ambos propietarios, rechazo de cambios de dueño,
JWT inválidos, 404 idénticos para registros ajenos/inexistentes, restricciones
de claves foráneas (inserción y actualización), borrado en cascada limitado al
propietario eliminado y downgrade/upgrade conservando las cuentas.

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
