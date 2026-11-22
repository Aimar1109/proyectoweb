from typing import Counter

from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Alineacion, Grupo, Jugador, Membresia

FORMACION = {"POR": 1, "DEF":4, "MED": 3, "DEL": 3}


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


def guardar_alineacion(membresia, jornada, ids):
    try:
        ids = {int(i) for i in ids}
    except (TypeError, ValueError):
        raise ValidationError("Selección no válida")

    if len(ids) != 11:
        raise ValidationError("Debes elegir exactamente 11 jugadores.")
    if jornada.liga_id != membresia.grupo.liga_id:
        raise ValidationError("La jornada no es de la liga del grupo.")
    if jornada.partidos.filter(goles_local__isnull=False).exists():
        raise ValidationError("Esta jornada ya se ha jugado.")

    jugadores = list(Jugador.objects.filter(pk__in=ids, equipo__liga_id=jornada.liga_id)) # ???

    if len(jugadores) != 11:
        raise ValidationError("Todos los jugadores deben ser de la liga del grupo.")
    if dict(Counter(j.posicion for j in jugadores)) != FORMACION:
        raise ValidationError("La formación debe ser 1 portero, 4 defensas, 3 centrocampistas y 3 delanteros.")

    with transaction.atomic():
        alineacion, _ = Alineacion.objects.get_or_create(membresia=membresia, jornada=jornada)
        alineacion.jugadores.set(jugadores)
    return alineacion
