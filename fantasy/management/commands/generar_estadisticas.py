"""Genera EstadisticaPartido INVENTADAS, coherentes con el resultado real de cada partido.

    python manage.py generar_estadisticas [--seed 42]

Como los jugadores son inventados, sus estadísticas también lo son. Lo único real es el
marcador: los goles repartidos entre los jugadores de cada equipo suman exactamente
goles_local / goles_visitante.

Por partido y equipo: once titular (1 POR, 4 DEF, 4 MED, 2 DEL), hasta 3 suplentes que
entran cuando un titular sale, tarjetas al azar y portería a cero si no encaja goles.
Los puntos se calculan con EstadisticaPartido.calcular_puntos().

Idempotente: los partidos que ya tienen estadísticas se saltan. Determinista con --seed.
"""
import random
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from fantasy.models import EstadisticaPartido, Jugador, Partido

PESO_GOL = {"POR": 0.02, "DEF": 1, "MED": 3, "DEL": 6}
TITULARES = {"POR": 1, "DEF": 4, "MED": 4, "DEL": 2}


class Command(BaseCommand):
    help = "Crea estadísticas inventadas de jugadores para los partidos ya jugados."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **o):
        plantillas = defaultdict(lambda: defaultdict(list))   # equipo_id -> pos -> [jugadores]
        for j in Jugador.objects.all().order_by("dorsal"):
            plantillas[j.equipo_id][j.posicion].append(j)

        partidos = (Partido.objects.filter(goles_local__isnull=False, estadisticas__isnull=True)
                    .distinct().order_by("id"))
        filas = []
        n_partidos = 0
        for p in partidos:
            rnd = random.Random(f"{o['seed']}-{p.id}")
            for equipo_id, a_favor, en_contra in ((p.local_id, p.goles_local, p.goles_visitante),
                                                  (p.visitante_id, p.goles_visitante, p.goles_local)):
                filas += self._equipo(rnd, p, plantillas[equipo_id], a_favor, en_contra)
            n_partidos += 1

        with transaction.atomic():
            EstadisticaPartido.objects.bulk_create(filas, batch_size=5000)
        self.stdout.write(self.style.SUCCESS(
            f"{len(filas)} estadísticas inventadas creadas para {n_partidos} partidos."))

    # ----------------------------------------------------------------------
    def _equipo(self, rnd, partido, plantilla, a_favor, en_contra):
        titulares = []
        for pos, cuantos in TITULARES.items():
            pool = plantilla.get(pos, [])
            titulares += rnd.sample(pool, min(cuantos, len(pool)))
        suplentes_pool = [j for lista in plantilla.values() for j in lista if j not in titulares]
        suplentes_pool = [j for j in suplentes_pool if j.posicion != "POR"]
        rnd.shuffle(suplentes_pool)

        # minutos: algunos titulares salen y entran suplentes (máx. 3)
        minutos = {}
        salidas = 0
        for j in titulares:
            if salidas < 3 and j.posicion != "POR" and rnd.random() < 0.25 and suplentes_pool:
                m = rnd.randint(46, 85)
                minutos[j.id] = m
                minutos[suplentes_pool.pop().id] = 90 - m
                salidas += 1
            else:
                minutos[j.id] = 90
        jugadores = {j.id: j for j in plantilla_flat(plantilla) if j.id in minutos}

        # goles repartidos según posición y minutos jugados
        goles = defaultdict(int)
        ids = list(minutos)
        pesos = [PESO_GOL[jugadores[i].posicion] * minutos[i] for i in ids]
        for _ in range(a_favor):
            goles[rnd.choices(ids, pesos)[0]] += 1

        portero = next((j for j in titulares if j.posicion == "POR"), None)
        filas = []
        for i in ids:
            j = jugadores[i]
            rojas = 1 if rnd.random() < 0.005 else 0
            amarillas = 0 if rojas else (1 if rnd.random() < 0.08 else 0)
            m = min(minutos[i], rnd.randint(30, 85)) if rojas else minutos[i]
            e = EstadisticaPartido(
                jugador=j, partido=partido, minutos=m, goles=goles.get(i, 0),
                amarillas=amarillas, rojas=rojas,
                porteria_cero=bool(portero and j.id == portero.id and en_contra == 0 and m >= 60))
            e.calcular_puntos()
            filas.append(e)
        return filas


def plantilla_flat(plantilla):
    return [j for lista in plantilla.values() for j in lista]
