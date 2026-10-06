---
name: Verificar cuentas de GitHub
description: Evitar falsas discrepancias entre la cuenta indicada por el usuario y el propietario de un repositorio.
---

No interpretar el «nombre» de una cuenta proporcionado por el usuario como su login de GitHub. Antes de declarar que una URL corresponde a otra cuenta, comparar el propietario canónico del repositorio y el nombre visible de su perfil.

**Why:** en este proyecto, el nombre visible y el login eran diferentes; comparar solo la URL con el nombre visible produjo preguntas repetidas y una comprobación contra un destino equivocado.

**How to apply:** consultar de forma acotada el propietario del repositorio y su perfil público; distinguir login, nombre visible, identidad de autor del commit y permisos de autenticación. No persistir correos ni datos personales del perfil.
