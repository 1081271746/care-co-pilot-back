# Co-Piloto de Duelo — Backend

Backend del proyecto universitario con Python, FastAPI, SQLAlchemy, Pydantic y PostgreSQL.
La aplicación es de acompañamiento: no realiza diagnósticos ni sustituye
atención profesional o servicios de emergencia.

## Alcance actual

- Configuración mediante `APP_NAME`, `APP_ENV`, `DATABASE_URL`, `JWT_SECRET_KEY` y `CORS_ORIGINS`.
- Motor SQLAlchemy y sesiones PostgreSQL creados bajo demanda.
- Comprobación manual de la base mediante `SELECT 1`, sin crear tablas.
- Cuenta persistida: correo único, hash Argon2, estado activo y fecha de creación.
- Migraciones Alembic explícitas; la API no crea ni modifica tablas al iniciar.
- Registro y login con validación de correo, hashing y emisión de JWT solo tras autenticar.
- Validación de tokens de acceso JWT firmados con HS256 y una clave del entorno.
- Usuario actual y logout con revocación persistente del token cerrado.
- Comprobación reutilizable de propiedad de registros que responde 404 para
  registros ajenos.
- `GET /health`: respuesta `{"status":"ok"}` para comprobar que la API responde.
- Documentación automática en `/docs` y contrato OpenAPI en `/openapi.json`.
- Diario emocional privado, revisión inicial de seguridad y recomendaciones.
- Biblioteca persistente de recursos y ejercicios, con carga inicial explícita.
- Historial privado de ejercicios, preferencias, dashboard y actividad diaria.
- Pruebas HTTP con `unittest` sobre SQLite temporal y PostgreSQL real desechable.

El inicio de sesión responde con el mismo error genérico si el correo no existe o
la contraseña no coincide o la cuenta está desactivada. Las contraseñas nuevas usan
`pwdlib` con Argon2; las antiguas PBKDF2 siguen siendo válidas y se actualizan al
iniciar sesión correctamente. Nunca se devuelven contraseñas ni hashes.
Las rutas privadas exigen `get_active_user` y consultan por registro y propietario
antes de leer, modificar o eliminar. Un recurso ajeno recibe el mismo 404 que uno
inexistente. Los errores 422 omiten el dato recibido y los errores de base devuelven
un 503 genérico; las respuestas incluyen `Cache-Control: no-store`.

## Estado del análisis y límites de seguridad

**No hay un proveedor de IA conectado todavía.** Las entradas se guardan de verdad,
pero no se inventan estimaciones emocionales: `estimated_stage` y `analysis_result`
permanecen nulos, con `analysis_status: pending`.

Al guardar o modificar el contenido se ejecutan reglas locales conservadoras para
expresiones como «quiero morir», «quiero hacerme daño», «no quiero seguir» y «no puedo
más». Su resultado indica `source: local_safety_rules`: no es IA ni evaluación
clínica. `unassessed` significa que no se reconocieron las expresiones contempladas,
**no** que el riesgo sea bajo o que la persona esté a salvo. Las reglas pueden
omitir señales o generar falsas alarmas, por ejemplo ante citas o negaciones.

Una señal produce `safety_priority` y ayuda humana/profesional antes de cualquier
ejercicio. `/help` está disponible sin login. Los números de emergencia por país
están pendientes de definir y verificar; no se asume el país del usuario.

`POST /journal/{id}/analyze` exige propiedad y consentimiento explícito booleano.
Si hay riesgo devuelve primero la orientación de seguridad, sin enviar contenido
a terceros. Sin riesgo y sin consentimiento devuelve 422; con consentimiento pero
sin proveedor devuelve 503 y conserva la entrada. No se realizan solicitudes
externas de análisis en esta versión.

Las etapas orientativas no representan diagnósticos ni un proceso obligatorio
o lineal. `intense_sadness` no significa una depresión diagnosticada.

## API disponible

Todas las rutas salvo salud, ayuda, registro, login y documentación requieren
`Authorization: Bearer <token>`.

| Módulo | Rutas |
| --- | --- |
| Cuentas | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` |
| Diario | `POST/GET /journal`, `GET/PATCH/DELETE /journal/{id}` |
| Análisis y acompañamiento | `POST /journal/{id}/analyze`, `GET /journal/{id}/recommendations` |
| Biblioteca | `GET /resources`, `GET /resources/{id}`, `GET /exercises`, `GET /exercises/{id}` |
| Ejercicios realizados | `POST /exercises/{id}/completions`, `GET /progress/exercises`, `GET/PATCH/DELETE /progress/exercises/{id}` |
| Preferencias | `GET/PATCH/DELETE /profile` |
| Resúmenes | `GET /dashboard`, `GET /history?days=30` |
| Registros genéricos previos | `POST/GET /records`, `GET/PATCH/DELETE /records/{id}` |
| Operación y ayuda | `GET /health`, `GET /health/ready`, `GET /help` |

Registro acepta `email` y `password` (entre 12 y 1024 caracteres); después se inicia
sesión por separado. JWT caduca a los 30 minutos. Logout devuelve 204 y revoca
solo el token actual: otras sesiones siguen funcionando. El backend almacena
únicamente su SHA-256 y expiración, nunca el JWT completo; limpia revocaciones
vencidas al cerrar sesiones. El frontend deberá borrar su token al recibir 204.

Los nombres opcionales, país y objetivo de acompañamiento se guardan con
`PATCH /profile`. `country_code` acepta dos letras mayúsculas (normaliza minúsculas)
o null para limpiarlo; todavía no configura números de emergencia. Borrar el
perfil restablece preferencias, **no** elimina la cuenta ni el diario.

Diario, catálogo e historial de ejercicios usan `limit` (1–100) y `before_id`
(cursor positivo). Las páginas están ordenadas por id descendente, con
`items`, `has_more` y `next_cursor`. Para seguir, enviar
`before_id=<next_cursor>`. Las inserciones nuevas no desplazan las páginas ya
recorridas. El diario conserva contenido; editarlo reinicia un análisis anterior
y vuelve a revisar seguridad. Los campos de propietario, riesgo y análisis no
son editables por el cliente.

`/history` acepta entre 1 y 365 días, devuelve fechas UTC, incluye días sin actividad
y agrega entradas, ejercicios y señales. Sus conteos no son una escala de salud.
`/dashboard` resume solo la cuenta actual. Las recomendaciones sin IA son
generales; las de una entrada con riesgo tienen listas de ejercicios y recursos
normales vacías, y ayuda de seguridad en `safety_result.resources`.

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

Primero prepara las tablas y carga el catálogo:

```powershell
python -m alembic upgrade head
python -m app.services.catalog_seed
```

La carga es idempotente: agrega material educativo inicial que falta sin duplicar
ni sobrescribir recursos existentes. Este contenido es orientativo, no una terapia,
y requiere revisión profesional antes de uso público. La API no modifica esquemas
ni carga contenido automáticamente al iniciar.

```powershell
python -m uvicorn app.main:app --reload
```

- Salud: <http://127.0.0.1:8000/health>
- Swagger: <http://127.0.0.1:8000/docs>
- Disponibilidad completa: <http://127.0.0.1:8000/health/ready>

`/health` solo comprueba que la API responde. `/health/ready` verifica PostgreSQL,
tablas/columnas requeridas y configuración JWT; devuelve 503 si falta preparación,
sin exponer credenciales ni aplicar migraciones.

En desarrollo, CORS permite `http://localhost:4200` y `http://127.0.0.1:4200`.
Configura otros orígenes exactos mediante `CORS_ORIGINS`, separados por comas.
No se aceptan comodines, rutas ni credenciales en esos orígenes. En producción,
si no se define la variable, no se autoriza ningún origen externo. No utiliza
cookies de sesión: el cliente envía el bearer token.

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

**Destructivo:** para revertir todas las migraciones y eliminar las tablas y sus
datos, únicamente en una base donde esa pérdida sea intencional:

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
