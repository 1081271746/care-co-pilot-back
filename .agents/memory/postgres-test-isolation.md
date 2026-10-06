---
name: Aislamiento de integración PostgreSQL
description: Límites de seguridad para comprobar privacidad con una base real.
---

La integración de privacidad debe usar PostgreSQL desechable local y una conexión
explícita, nunca la configuración de conexión de la aplicación. Mantener las
pruebas rápidas independientes de la disponibilidad de PostgreSQL.

**Why:** el usuario exigió comprobar migraciones y privacidad con PostgreSQL de
pruebas, nunca producción y sin credenciales en archivos versionados. Se eligió
restringir la integración a loopback para reducir el riesgo de apuntar a una base
remota real; un esquema aislado por sí solo no distingue pruebas de producción.

**How to apply:** conservar ese límite al ampliar la integración. Para validar
contra una base remota o relajar las guardas, acordar antes un mecanismo que
demuestre que la base es exclusivamente de pruebas.
