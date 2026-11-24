"""Genera jugadores INVENTADOS para cada equipo (no hay datos reales por protección de datos).

    python manage.py generar_jugadores [--por-equipo 18] [--seed 42] [--solo-con-partidos]

- Nombre = nombre + dos apellidos, combinados al azar de listas de nombres comunes
  (nombres femeninos en las ligas de categoría "Femenino"). Cualquier parecido con
  una persona real es pura coincidencia.
- Reparto por posiciones equilibrado y dorsales únicos por equipo.
- Determinista: con la misma --seed salen siempre los mismos jugadores.
- Idempotente: los equipos que ya tienen jugadores se saltan (no se borra nada).
"""
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from fantasy.models import Equipo, Jugador

POR, DEF, MED, DEL = (Jugador.Posicion.PORTERO, Jugador.Posicion.DEFENSA,
                      Jugador.Posicion.CENTROCAMPISTA, Jugador.Posicion.DELANTERO)

# (posición, dorsal). Cualquier prefijo de 14 a 22 elementos queda equilibrado;
# con 18 salen 2 porteros, 6 defensas, 6 centrocampistas y 4 delanteros.
PLANTILLA = [
    (POR, 1), (DEF, 2), (DEF, 3), (DEF, 4), (DEF, 5), (MED, 6), (DEL, 7),
    (MED, 8), (DEL, 9), (MED, 10), (DEL, 11), (POR, 13), (DEF, 14), (DEF, 15),
    (MED, 16), (MED, 17), (DEL, 18), (MED, 19), (DEF, 20), (MED, 21),
    (POR, 22), (DEL, 12),
]

NOMBRES_M = """Iker Unai Aitor Ander Mikel Jon Gorka Xabier Asier Eneko Imanol Oier Beñat Julen
Markel Aratz Gaizka Haritz Iñigo Koldo Lander Peru Urko Xanti Alex Adrián Álvaro Daniel David
Diego Hugo Javier Jorge Lucas Marcos Mario Pablo Pedro Raúl Rubén Sergio Víctor Óscar Samuel
Nicolás Gonzalo Ismael Rodrigo Ibai Aimar Egoitz Ekain Endika Jokin Oihan Telmo""".split()

NOMBRES_F = """Amaia Ainhoa Maite Nerea Leire Irati Itziar Naiara Uxue Ane June Maialen Oihane
Izaro Garazi Lucía Paula Sara Laura Marta Carmen Elena Clara Nuria Claudia Alba Andrea Irene
Julia Noa Ainara Eider Haizea Idoia Jone Miren Nahia Olaia Saioa Udane Ziortza Aitana
Ariane Beatriz Cristina Eva Inés Lorea Mireia""".split()

APELLIDOS = """Etxebarria Goikoetxea Zubiaurre Aguirre Urrutia Arriola Ibarra Lasa Mendizabal Uriarte
Garmendia Landa Olabarria Bilbao Ortiz Gorostiza Larrañaga Elorriaga Unamuno Zabala Arana Barrena
Basterretxea Belaustegi Etxeberria Gallastegi Iturbe Jauregi Lekue Madariaga Mugika Orbea Otxoa
Sagarna Telleria Urkiza Zugazagoitia García Fernández González Rodríguez López Martínez Sánchez
Pérez Gómez Ruiz Díaz Moreno Muñoz Álvarez Romero Alonso Gutiérrez Navarro Torres Domínguez Vázquez
Ramos Gil Serrano Blanco Molina Castro Ortega Rubio Marín Sanz Iglesias Medina Cortés Garrido""".split()


class Command(BaseCommand):
    help = "Crea jugadores inventados (nombre, posición, dorsal) para cada equipo sin plantilla."

    def add_arguments(self, parser):
        parser.add_argument("--por-equipo", type=int, default=18, help="Jugadores por equipo (14-22).")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--solo-con-partidos", action="store_true",
                            help="Solo equipos de ligas que tienen partidos cargados.")

    def handle(self, *args, **o):
        n = o["por_equipo"]
        if not 14 <= n <= len(PLANTILLA):
            raise CommandError(f"--por-equipo debe estar entre 14 y {len(PLANTILLA)}")

        equipos = Equipo.objects.select_related("liga").filter(jugadores__isnull=True)
        if o["solo_con_partidos"]:
            equipos = equipos.filter(liga__jornadas__partidos__isnull=False).distinct()

        nuevos = []
        n_equipos = 0
        for equipo in equipos.order_by("id"):
            rnd = random.Random(f"{o['seed']}-{equipo.id}")
            femenino = bool(equipo.liga and equipo.liga.categoria == "Femenino")
            nombres = NOMBRES_F if femenino else NOMBRES_M
            usados = set()
            for pos, dorsal in PLANTILLA[:n]:
                while True:
                    ap1, ap2 = rnd.sample(APELLIDOS, 2)
                    nombre = f"{rnd.choice(nombres)} {ap1} {ap2}"
                    if nombre not in usados:
                        usados.add(nombre)
                        break
                nuevos.append(Jugador(nombre=nombre, posicion=pos, dorsal=dorsal, equipo=equipo))
            n_equipos += 1

        with transaction.atomic():
            Jugador.objects.bulk_create(nuevos, batch_size=2000)
        self.stdout.write(self.style.SUCCESS(
            f"{len(nuevos)} jugadores inventados creados para {n_equipos} equipos."))
