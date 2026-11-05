import random
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from fantasy.models import (
    Alineacion, Club, Equipo, EstadisticaPartido, Jornada, Jugador,
    Liga, Partido, Temporada, Usuario,
)

CLUBES = [
    ("Athletic Club", "Bilbao", 1898),
    ("Real Sociedad", "Donostia", 1909),
    ("Deportivo Alavés", "Vitoria-Gasteiz", 1921),
    ("SD Eibar", "Eibar", 1940),
]
NOMBRES = ["Mikel", "Iker", "Unai", "Ander", "Aitor", "Jon", "Asier", "Xabier",
           "Oier", "Beñat", "Gorka", "Imanol", "Julen", "Markel", "Egoitz"]
APELLIDOS = ["Etxeberria", "Goikoetxea", "Zubizarreta", "Urrutia", "Aranburu",
             "Lekue", "Irigoyen", "Mendizabal", "Otegi", "Ibarra", "Garmendia"]

# Con 4 equipos hay 3 jornadas: cada equipo juega una vez contra los demás
EMPAREJAMIENTOS = [
    [(0, 1), (2, 3)],
    [(0, 2), (1, 3)],
    [(0, 3), (1, 2)],
]


def posicion(dorsal):
    if dorsal == 1:
        return Jugador.Posicion.PORTERO
    if dorsal <= 5:
        return Jugador.Posicion.DEFENSA
    if dorsal <= 9:
        return Jugador.Posicion.CENTROCAMPISTA
    return Jugador.Posicion.DELANTERO


class Command(BaseCommand):
    help = "Carga datos de muestra en la base de datos"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Borra los datos antes de cargar")

    def handle(self, *args, **options):
        random.seed(42)  # mismos datos en cada ejecución

        if options["reset"]:
            for modelo in (EstadisticaPartido, Partido, Alineacion, Usuario,
                           Jugador, Equipo, Jornada, Liga, Club, Temporada):
                modelo.objects.all().delete()

        # Temporada y liga
        temporada, _ = Temporada.objects.get_or_create(
            fecha_inicio=date(2026, 9, 1), fecha_fin=date(2027, 6, 30),
        )
        liga, _ = Liga.objects.get_or_create(
            nombre="Juvenil Preferente Grupo 1",
            defaults={"temporada": temporada, "categoria": "Juvenil", "grupo": 1},
        )

        # Clubes, equipos y jugadores
        equipos = []
        for nombre, ciudad, anno in CLUBES:
            club, _ = Club.objects.get_or_create(
                nombre=nombre,
                defaults={"email": f"{slugify(nombre)}@ejemplo.com",
                          "direccion": f"Calle Mayor 1, {ciudad}"},
            )
            equipo, _ = Equipo.objects.get_or_create(
                nombre=f"{nombre} Juvenil A",
                defaults={"ciudad": ciudad, "anno_fundacion": anno,
                          "descripcion": f"Equipo juvenil del {nombre}",
                          "liga": liga, "club": club},
            )
            equipos.append(equipo)
            for dorsal in range(1, 15):
                Jugador.objects.get_or_create(
                    equipo=equipo, dorsal=dorsal,
                    defaults={"nombre": f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}",
                              "posicion": posicion(dorsal)},
                )

        # Jornadas y partidos (las 2 primeras ya jugadas, la 3ª pendiente)
        inicio = date(2026, 9, 12)
        for i, parejas in enumerate(EMPAREJAMIENTOS):
            sabado = inicio + timedelta(days=7 * i)
            jornada, _ = Jornada.objects.get_or_create(
                liga=liga, numero=i + 1,
                defaults={"fecha_inicio": sabado,
                          "fecha_fin": sabado + timedelta(days=1)},
            )
            jugada = i < 2
            for a, b in parejas:
                fecha = timezone.make_aware(datetime.combine(sabado, datetime.min.time())
                                            .replace(hour=17))
                partido, creado = Partido.objects.get_or_create(
                    jornada=jornada, local=equipos[a], visitante=equipos[b],
                    defaults={
                        "fecha": fecha,
                        "goles_local": random.randint(0, 4) if jugada else None,
                        "goles_visitante": random.randint(0, 4) if jugada else None,
                    },
                )
                if jugada and creado:
                    self.crear_estadisticas(partido)

        # Usuarios con su alineación de 11
        for alias, nombre, equipo in [("mikel10", "Mikel Ruiz", equipos[0]),
                                      ("ander_9", "Ander Soto", equipos[1]),
                                      ("fan_eibar", "Laura Gil", equipos[3])]:
            usuario, _ = Usuario.objects.get_or_create(
                alias=alias,
                defaults={"name": nombre, "email": f"{alias}@ejemplo.com",
                          "equipo": equipo},
            )
            alineacion, _ = Alineacion.objects.get_or_create(usuario=usuario)
            alineacion.jugadores.set(equipo.jugadores.order_by("dorsal")[:11])

        self.stdout.write(self.style.SUCCESS("Datos de muestra cargados."))

    def crear_estadisticas(self, partido):
        for equipo, goles_equipo, goles_rival in [
            (partido.local, partido.goles_local, partido.goles_visitante),
            (partido.visitante, partido.goles_visitante, partido.goles_local),
        ]:
            stats = {}
            for j in equipo.jugadores.all():
                stats[j.id] = {"jugador": j,
                               "minutos": random.choice([0, 20, 45, 90, 90, 90]),
                               "goles": 0,
                               "amarillas": random.choice([0, 0, 0, 1]),
                               "rojas": random.choice([0] * 19 + [1])}
            # Repartir los goles del equipo entre quienes jugaron
            jugaron = [s for s in stats.values() if s["minutos"] > 0]
            for _ in range(goles_equipo):
                random.choice(jugaron)["goles"] += 1

            for s in stats.values():
                puntos = ((1 if s["minutos"] > 0 else 0)
                          + (1 if s["minutos"] >= 60 else 0)
                          + s["goles"] * 4 - s["amarillas"] - s["rojas"] * 3)
                EstadisticaPartido.objects.create(
                    jugador=s["jugador"], partido=partido, minutos=s["minutos"],
                    goles=s["goles"], amarillas=s["amarillas"],
                    rojas=s["rojas"], puntos=puntos,
                )