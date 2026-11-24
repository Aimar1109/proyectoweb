from .models import Membresia

# Páginas que pertenecen a un grupo
URLS_DE_GRUPO = {"clasificacion", "alineacion", "lista_puntos"}


def grupo_activo(request):
    if not request.user.is_authenticated:
        return {}
    match = request.resolver_match
    if match is None or match.url_name not in URLS_DE_GRUPO:
        return {}
    grupo_id = request.session.get("grupo_activo_id")
    if not grupo_id:
        return {}
    membresia = (
        Membresia.objects
        .filter(usuario=request.user, grupo_id=grupo_id)
        .select_related("grupo")
        .first()
    )
    if membresia is None:
        return {}
    return {"grupo_activo": membresia.grupo, "membresia_activa": membresia}