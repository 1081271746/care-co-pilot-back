"""Contactos públicos verificados para Colombia, sin inferir ubicación."""

from datetime import date

from app.schemas.safety import HelpResource

VERIFIED_ON = date(2026, 10, 6)
NATIONAL_EMERGENCY_SOURCE = (
    "https://www.policia.gov.co/noticia/"
    "policia-nacional-sensibiliza-comunidad-sobre-uso-las-lineas-emergencia-123-155"
)
MENTAL_HEALTH_SOURCE = (
    "https://www.minsalud.gov.co/salud/publica/salud-mental/Paginas/linea-106.aspx"
)
BOGOTA_SOURCE = (
    "https://bogota.gov.co/mi-ciudad/salud/"
    "linea-106-para-apoyo-psicologico-y-mas-informacion-en-bogota-este-2025"
)
DIRECTORY_SOURCE = (
    "https://minsalud.gov.co/sites/rid/Lists/BibliotecaDigital/RIDE/VS/PP/ET/"
    "directorio-salud-mental-prevencion-suicidio-minsalud.pdf"
)


def colombia_resources() -> list[HelpResource]:
    return [
        HelpResource(
            title="Emergencias en Colombia: 123",
            phone="123", country_code="CO", coverage="Nacional",
            availability="Gratuita, 24 horas, todos los días",
            url=NATIONAL_EMERGENCY_SOURCE, verified_on=VERIFIED_ON,
            description=(
                "Si hay peligro inmediato, llama al 123 o acude a urgencias. "
                "Si es seguro, pide a alguien de confianza que permanezca contigo."
            ),
        ),
        HelpResource(
            title="Orientación en salud mental: 106",
            phone="106", country_code="CO", coverage="Colombia; atención nacional y territorial",
            availability="Gratuita, 24 horas, todos los días",
            url=MENTAL_HEALTH_SOURCE, verified_on=VERIFIED_ON,
            description=(
                "Apoyo emocional y orientación de profesionales de salud mental. "
                "No sustituye al 123 cuando existe peligro inmediato. Si no puedes "
                "comunicarte, consulta los canales territoriales oficiales."
            ),
        ),
        HelpResource(
            title="WhatsApp de la Línea 106 de Bogotá",
            phone="+573007548933", country_code="CO", coverage="Bogotá D.C., no nacional",
            availability="Servicio distrital de orientación, 24 horas, todos los días",
            url=BOGOTA_SOURCE, verified_on=VERIFIED_ON,
            description="Canal distrital de apoyo emocional. No es un número nacional ni reemplaza emergencias.",
        ),
        HelpResource(
            title="Directorio oficial de líneas territoriales de salud mental",
            country_code="CO", coverage="Consulta por departamento o municipio",
            url=DIRECTORY_SOURCE, verified_on=VERIFIED_ON,
            description="Revisa el contacto y horario de tu territorio; la cobertura puede variar.",
        ),
    ]
