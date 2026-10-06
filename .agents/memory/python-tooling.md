---
name: Tooling Python en el monorepo
description: Efectos de la instalación de paquetes Python y compatibilidad del cliente de pruebas HTTP.
---

Cuando se instalan paquetes Python en este workspace pnpm, el instalador de Replit puede crear archivos de inicio Python en la raíz y añadir una sección `[nix]` a `.replit`, aunque las dependencias del backend estén en su propio directorio. La versión reciente de Starlette también prefiere `httpx2` en `TestClient`; usar `httpx` provoca una advertencia de obsolescencia.

**Why:** una instalación orientada al backend dejó cambios de configuración fuera de su alcance, y las pruebas HTTP usaban el cliente de compatibilidad obsoleto.

**How to apply:** tras instalar paquetes Python, revisar `git status` y eliminar efectos secundarios no relacionados con el backend mediante el flujo de configuración validado. En este entorno, declarar `httpx2` para las pruebas `TestClient` de Starlette.
