---
name: Alcance y seguridad del acompañamiento
description: Requisitos del usuario para diario, análisis, privacidad y orientación de riesgo.
---

Co-Piloto de Duelo es acompañamiento estructurado, no terapia ni diagnóstico. El backend debe soportar diario emocional, estimaciones orientativas, recursos y ejercicios adaptados, historial y evolución, y perfil emocional sin información innecesaria.

**Why:** el usuario volvió a proporcionar el prompt completo y pidió conservar estos límites durante todo el desarrollo.

**How to apply:** distinguir análisis real de IA de reglas locales y de estados sin analizar; no presentar resultados simulados como IA. Las etapas del duelo no son obligatorias ni lineales; expresar tristeza intensa sin diagnosticar depresión.

Las señales de ideación suicida, autolesión, crisis grave o peligro inmediato deben priorizar mensajes de seguridad, ayuda profesional y recursos de emergencia sobre ejercicios normales. No minimizar expresiones como «quiero morir», «no quiero seguir», «quiero hacerme daño» o «no puedo más». No afirmar que el sistema puede tratar una crisis.

**Why:** el usuario señaló la detección de riesgo como crítica; la información emocional es sensible y debe permanecer privada por propietario.

**How to apply:** probar esas expresiones y los accesos entre propietarios, explicar las limitaciones de cualquier detector y no asumir que la ausencia de señales confirma seguridad. Priorizar funcionamiento local y PostgreSQL antes de despliegue. Preferir pwdlib con Argon2 conservando la compatibilidad con hashes anteriores.

El usuario eligió OpenAI con su propia cuenta como proveedor de IA y Colombia como país atendido por la aplicación.

**Why:** decisión explícita del usuario al definir la conexión de IA y la ayuda de emergencia.

**How to apply:** no sustituir por Replit AI Integrations ni otro proveedor sin consultarlo. No interpretar Colombia como una ubicación personal del creador ni de todos los usuarios. Verificar los contactos oficiales y distinguir las líneas nacionales de los canales distritales.
