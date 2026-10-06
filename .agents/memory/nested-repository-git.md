---
name: Alcance Git de los clones
description: Evitar que operaciones sobre los repositorios del usuario terminen en el repositorio contenedor de Replit.
---

Antes de ejecutar operaciones Git sobre un clon, comprobar que su raíz corresponde al repositorio objetivo. No asumir que `git -C` identifica un repositorio independiente cuando falta su metadata.

**Why:** los archivos de los clones se conservaron sin su `.git`; Git resolvió silenciosamente al repositorio contenedor. El puntero `.git` recreado tampoco resultó disponible en una comprobación posterior.

**How to apply:** usar metadata independiente y pasar explícitamente `--git-dir` y `--work-tree` cuando el clon no conserve su `.git`. Buscar y verificar la metadata local en `.local/repository-metadata/` antes de operar. Nunca incluir cambios del contenedor en un commit destinado al backend o frontend del usuario. Los commits locales no equivalen a un push a GitHub.
