---
name: Forma de trabajo de Co-Piloto de Duelo
description: Restricciones y metodología indicadas por el usuario para el proyecto universitario.
---

Trabajar únicamente en `care-co-pilot-back` y `care-co-pilot-front`. Mantener backend y frontend separados y usar el stack indicado por el usuario: Python/FastAPI/SQLAlchemy/PostgreSQL/Pydantic/JWT en backend y Angular/TypeScript/HTML/CSS en frontend. No introducir tecnologías innecesarias o no conocidas por el usuario.

Avanzar progresivamente: analizar antes de cambiar, modificar una parte a la vez, ejecutar y probar antes de continuar, conservar lo que funcione y evitar generar todo el sistema de golpe. Cada cambio funcional importante debe quedar en un commit claro en español; no agrupar todo en un commit gigante.

Nunca pedir credenciales reales de PostgreSQL ni escribirlas en el código o repositorios. Configurar variables de entorno y mantener un `.env.example` sin contraseñas reales; no subir `.env`.

**Why:** el usuario pidió explícitamente mantener esta metodología durante todo el desarrollo de su proyecto universitario.

**How to apply:** antes de cada fase, revisar los dos repositorios objetivo, proponer el cambio acotado, implementarlo y verificarlo antes del siguiente cambio; no ampliar el alcance a otros artefactos o repositorios.
