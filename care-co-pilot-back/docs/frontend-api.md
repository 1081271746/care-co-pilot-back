# Contrato del backend para el futuro frontend Angular

Esta guía no implementa frontend. Describe cómo consumir el backend terminado
para el alcance actual: cuentas, diario privado, biblioteca, ejercicios, perfil,
historial, dashboard, seguridad y administración de catálogo.

## Arranque para desarrollo sin PostgreSQL

Desde la raíz del backend, ejecuta `python -m app.demo`.
La base de API es `http://127.0.0.1:8000`, sin prefijo `/api`.
Angular local puede ejecutarse en `http://localhost:4200` o `http://127.0.0.1:4200`.
Los otros orígenes deben configurarse explícitamente para la API normal.
La demo solo habilita estos dos orígenes locales.

El contrato completo, con campos y validaciones, está en `GET /openapi.json`;
Swagger en `/docs`. No mantener una copia manual de esos esquemas en esta guía.
Para cambiar después a PostgreSQL, inicia `app.main:app` como indica el README,
con su configuración propia, migraciones y catálogo. No importar cuentas,
contraseñas ni diarios de demo a la base real.

## Autenticación y permisos

1. `POST /auth/register` recibe `email` y `password` (12–1024 caracteres).
   Devuelve 201 con `id` (texto), `email` y `created_at`. No inicia sesión.
2. `POST /auth/login` recibe `email` y `password`. Devuelve:

   ```json
   {"access_token": "<JWT obtenido tras autenticar>", "token_type": "bearer"}
   ```

3. Las rutas privadas reciben `Authorization: Bearer <access_token>`.
4. `GET /auth/me` devuelve `id`, `email`, `created_at` y `role` (`user` o `admin`).
   El rol se lee de la base, no de un claim del token. Sirve para decidir qué
   navegación mostrar; el backend sigue validando todos los permisos.
5. `POST /auth/logout` devuelve 204 y revoca solo el token usado. El cliente debe
   borrar ese token. También debe cerrar su sesión local ante un 401.

No enviar `role` al registrarse: se rechaza, al igual que otros campos desconocidos.
Ni siquiera un administrador puede leer diarios o notas de otro propietario.

## Pantallas y operaciones disponibles

| Pantalla futura | Endpoints |
| --- | --- |
| Perfil | `GET/PATCH/DELETE /profile` |
| Inicio | `GET /dashboard` |
| Diario | `GET/POST /journal`, `GET/PATCH/DELETE /journal/{id}` |
| Acompañamiento de una entrada | `GET /journal/{id}/recommendations` |
| Biblioteca | `GET /resources`, `GET /resources/{id}` |
| Ejercicios | `GET /exercises`, `GET /exercises/{id}` |
| Registrar un ejercicio | `POST /exercises/{id}/completions` |
| Progreso y notas privadas | `GET /progress/exercises`, `GET/PATCH/DELETE /progress/exercises/{id}` |
| Historial | `GET /history?days=30` |
| Ayuda pública | `GET /help?country_code=CO` |
| Catálogo administrativo | `GET/POST /admin/resources`, `GET/PATCH/DELETE /admin/resources/{id}`, y equivalentes de `/admin/exercises` |

`DELETE /profile` restablece preferencias: no borra la cuenta.
Cada finalización puede tener su propia nota y borrarse sin eliminar el ejercicio.
En administración, DELETE desactiva el elemento; PATCH con `is_active: true`
lo reactiva. El historial ya registrado permanece.

## Paginación

Diario, catálogo, administración y progreso reciben `limit` (1–100) y
`before_id` (entero positivo). Leer `items`, `has_more` y `next_cursor`.
Para la siguiente página, enviar `before_id=next_cursor`. Detenerse cuando
`has_more` sea false. Los identificadores de estos elementos son enteros.
El endpoint heredado `/records` usa `limit` y `offset`, no cursor.
Las fechas se serializan como ISO 8601; la agrupación de `/history` es por día UTC.
No presentar los conteos o las etapas como una puntuación de salud.

## IA aplazada y seguridad

La demo no llama a OpenAI ni inventa análisis. Una entrada normal tiene:

```json
{
  "analysis_status": "pending",
  "estimated_stage": null,
  "analysis_result": null,
  "analyzed_at": null
}
```

Mostrar “Sin análisis de IA” para estos registros. Las recomendaciones
`mode: general` no son personalización por IA.

Una señal local produce `analysis_status: safety_priority`.
Si `safety_result.requires_help` es true o las recomendaciones tienen
`mode: safety`, mostrar primero ayuda humana y recursos de emergencia;
no mostrar una etapa estimada ni ejercicios normales. `unassessed` no
significa que la persona esté a salvo. Las reglas locales no son evaluación clínica.

Dejar la acción de análisis externo fuera del flujo inicial del frontend.
Cuando se habilite por separado: mostrar `GET /help/privacy`, recoger
consentimiento explícito y usar `POST /journal/{id}/analyze` con la versión
vigente del aviso. Nunca poner una clave de OpenAI en Angular.
En demo, el análisis con consentimiento válido responde 503 y conserva la entrada.

## Errores y estados de interfaz

- 401: falta sesión, token inválido/vencido/revocado o cuenta inactiva.
- 403: cuenta sin privilegios administrativos.
- 404: registro inexistente o ajeno, con el mismo mensaje.
- 409: correo/slug en conflicto o entrada modificada durante el análisis.
- 422: datos inválidos, campos desconocidos o consentimiento ausente.
- 502: respuesta externa no válida, sin resultado guardado.
- 503: configuración o servicio no disponibles; no afirmar éxito.
- 204: operación completada sin cuerpo; no intentar analizar JSON.

Los errores HTTP normales incluyen `detail`; los 422 incluyen una lista
de problemas de validación sin devolver los valores recibidos.
Los errores de infraestructura no revelan credenciales. Mostrar un mensaje
comprensible, conservar el texto que se estaba editando ante un fallo y no
registrar JWT, contraseñas ni contenido de diarios en la consola.
