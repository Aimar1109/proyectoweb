from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Grupo, Membresia


def crear_grupo(usuario, liga, nombre):
    nombre = nombre.strip()
    if not nombre:
        raise ValidationError("El nombre no puede estar vacío.")
    if Grupo.objects.filter(creador=usuario, nombre=nombre).exists():
        raise ValidationError("Ya tienes un grupo con ese nombre.")
    with transaction.atomic():
        grupo = Grupo.objects.create(nombre=nombre, creador=usuario, liga=liga)
        Membresia.objects.create(usuario=usuario, grupo=grupo)  # el creador es el primer miembro
    return grupo


def unirse_a_grupo(usuario, codigo):
    try:
        grupo = Grupo.objects.get(codigo=codigo.strip().upper())
    except Grupo.DoesNotExist:
        raise ValidationError("No existe ningún grupo con ese código.")
    with transaction.atomic():
        grupo = Grupo.objects.select_for_update().get(pk=grupo.pk)
        if grupo.membresias.filter(usuario=usuario).exists():
            raise ValidationError("Ya eres miembro de este grupo.")
        if grupo.membresias.count() >= Grupo.MAX_MIEMBROS:
            raise ValidationError("El grupo está lleno.")
        Membresia.objects.create(usuario=usuario, grupo=grupo)
    return grupo

def calcular_puntos_jornada(jornada):
    with transaction.atomic():
        membresias = set()
        for alineacion in jornada.alineaciones.select_related("membresia"):
            alineacion.calcular_puntos()
            membresias.add(alineacion.membresia)
        for membresia in membresias:
            membresia.recalcular_puntos()