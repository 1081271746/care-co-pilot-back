---
name: Autenticación del proveedor Git
description: Diferenciar la autorización declarada por una integración de la autenticación efectiva al subir commits.
---

Una conexión GitHub marcada saludable y con permisos de escritura no demuestra
que Git o GitHub CLI estén autenticados en el entorno. Confirmar siempre la
operación real y el hash remoto antes de afirmar que una subida tuvo éxito.

**Why:** la conexión del proveedor Git declaró estar activa después de renovar
la autorización, pero Git siguió rechazando la autenticación y GitHub CLI no
tenía sesión. El formulario de reconexión estándar también rechazó esa conexión
como no conectada. Repetir el mismo formulario no resolvió la discrepancia.

**How to apply:** seguir las instrucciones específicas del proveedor Git, no
suponer que es un conector API estándar ni pedir credenciales por chat. Consultar
la documentación actual sobre Git Providers frente a Connected Services cuando
fallen los mecanismos disponibles. No reescribir historia para sortear un fallo
de autenticación.
