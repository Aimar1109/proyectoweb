import random
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from fantasy.models import (
    Alineacion, Club, Equipo, EstadisticaPartido, Grupo, Jornada, Jugador,
    Liga, Membresia, Partido, Temporada, Usuario,
)

PASSWORD = "fantasy1234"

CLUBES = [
    ("Athletic Club", "Bilbao", 1898),
    ("Real Sociedad", "Donostia", 1909),
    ("Deportivo Alavés", "Vitoria-Gasteiz", 1921),
    ("SD Eibar", "Eibar", 1940),
    ("Barakaldo CF", "Barakaldo", 1917),
    ("Real Unión", "Irun", 1915),
]

NOMBRES = ["Mikel", "Iker", "Unai", "Ander", "Aitor", "Jon", "Asier", "Xabier",
           "Oier", "Beñat", "Gorka", "Imanol", "Julen", "Markel", "Egoitz", "Eneko"]
APELLIDOS = ["Etxeberria", "Goikoetxea", "Zubizarreta", "Urrutia", "Aranburu",
             "Lekue", "Irigoyen", "Mendizabal", "Otegi", "Ibarra", "Garmendia",
             "Aguirre", "Larrañaga", "Ugarte", "Elorza", "Bengoetxea"]

# 16 jugadores por equipo: 2 porteros, 5 defensas, 5 medios y 4 delanteros
POSICIONES_POR_DORSAL = [
    "POR", "DEF", "DEF", "DEF", "DEF", "MED", "MED", "MED",
    "DEL", "DEL", "DEL", "POR", "DEF", "MED", "MED", "DEL",
]

# Formación de los once: 1 portero, 4 defensas, 3 medios, 3 delanteros
FORMACION = {"POR": 1, "DEF": 4, "MED": 3, "DEL": 3}

# Probabilidad relativa de marcar según la posición
PESO_GOL = {"DEF": 1, "MED": 3, "DEL": 6}

USUARIOS = [
    ("mikel10", "Mikel", "Ruiz"),
    ("ander9", "Ander", "Soto"),
    ("laura_gil", "Laura", "Gil"),
    ("unai_k", "Unai", "Korta"),
    ("nerea", "Nerea", "Arana"),
    ("jon_a", "Jon", "Aldama"),
]

# (nombre, creador, código fijo o None, miembros además del creador)
GRUPOS = [
    ("Los del cole", "mikel10", None, ["ander9", "unai_k", "nerea"]),
    ("Primos", "laura_gil", None, ["mikel10", "jon_a"]),
    ("Ingeniería Web", "laura_gil", "DEUSTO26", ["jon_a"]),
]

JORNADAS_JUGADAS = 4  # de 5 jornadas; la última queda pendiente


def calendario(n):
    """Todos contra todos (método del círculo). Devuelve n-1 rondas."""
    ids = list(range(n))
    rondas = []
    for r in range(n - 1):
        parejas = [(ids[i], ids[n - 1 - i]) for i in range(n // 2)]
        if r % 2:
            parejas = [(b, a) for a, b in parejas]
        rondas.append(parejas)
        ids = [ids[0]] + [ids[-1]] + ids[1:-1]
    return rondas


class Command(BaseCommand):
    help = "Carga datos de muestra: liga, equipos, jugadores, jornadas jugadas, estadísticas, usuarios y grupos"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Borra todos los datos antes de cargar")

    def handle(self, *args, **options):
        random.seed(42)

        if options["reset"]:
            for modelo in (Alineacion, EstadisticaPartido, Partido, Jornada,
                           Membresia, Grupo, Usuario, Jugador, Equipo, Liga,
                           Club, Temporada):
                modelo.objects.all().delete()

        liga, equipos = self.crear_liga_y_equipos()
        jornadas = self.crear_jornadas_y_partidos(liga, equipos)
        usuarios = self.crear_usuarios()
        self.crear_grupos(liga, usuarios)
        self.crear_alineaciones(liga, jornadas)

        self.stdout.write(self.style.SUCCESS("Datos de muestra cargados."))
        self.stdout.write(f"Login con el email del usuario y la contraseña '{PASSWORD}'.")
        self.stdout.write("Superusuario: admin@ejemplo.com / admin1234")
        self.stdout.write("Código para probar 'Unirse a un grupo': DEUSTO26")

    # ---------- Liga, clubes, equipos y jugadores ----------

    def crear_liga_y_equipos(self):
        temporada, _ = Temporada.objects.get_or_create(
            fecha_inicio=date(2026, 9, 1), fecha_fin=date(2027, 6, 30),
        )
        liga, _ = Liga.objects.get_or_create(
            temporada=temporada, nombre="Juvenil Preferente Grupo 1",
            defaults={"categoria": "Juvenil", "grupo": 1},
        )
        equipos = []
        for i, (nombre, ciudad, anno) in enumerate(CLUBES):
            club, _ = Club.objects.get_or_create(
                nombre=nombre,
                defaults={"anno_fundacion": anno,
                          "email": f"club{i + 1}@ejemplo.com",
                          "direccion": f"Calle Mayor 1, {ciudad}"},
            )
            equipo, _ = Equipo.objects.get_or_create(
                nombre=f"{nombre} Juvenil A", liga=liga,
                defaults={"ciudad": ciudad, "club": club,
                          "descripcion": f"Equipo juvenil del {nombre}"},
            )
            equipos.append(equipo)
            for dorsal, posicion in enumerate(POSICIONES_POR_DORSAL, start=1):
                Jugador.objects.get_or_create(
                    equipo=equipo, dorsal=dorsal,
                    defaults={"nombre": f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}",
                              "posicion": posicion},
                )
        return liga, equipos

    # ---------- Jornadas, partidos y estadísticas ----------

    def crear_jornadas_y_partidos(self, liga, equipos):
        rondas = calendario(len(equipos))
        ultimo_sabado = date(2026, 11, 14)  # la jornada pendiente
        jornadas = []
        for numero, parejas in enumerate(rondas, start=1):
            sabado = ultimo_sabado - timedelta(weeks=len(rondas) - numero)
            jornada, _ = Jornada.objects.get_or_create(
                liga=liga, numero=numero,
                defaults={"fecha_inicio": sabado,
                          "fecha_fin": sabado + timedelta(days=1)},
            )
            jornadas.append(jornada)
            jugada = numero <= JORNADAS_JUGADAS
            for k, (a, b) in enumerate(parejas):
                fecha = timezone.make_aware(
                    datetime.combine(sabado, time(hour=(12, 16, 18)[k % 3])))
                partido, creado = Partido.objects.get_or_create(
                    jornada=jornada, local=equipos[a], visitante=equipos[b],
                    defaults={
                        "fecha": fecha,
                        "goles_local": random.choice([0, 0, 1, 1, 2, 2, 3, 4]) if jugada else None,
                        "goles_visitante": random.choice([0, 0, 1, 1, 2, 2, 3, 4]) if jugada else None,
                    },
                )
                if jugada and creado:
                    self.crear_estadisticas(partido)
        return jornadas

    def crear_estadisticas(self, partido):
        filas = []
        lados = [
            (partido.local, partido.goles_local, partido.goles_visitante),
            (partido.visitante, partido.goles_visitante, partido.goles_local),
        ]
        for equipo, goles_equipo, goles_rival in lados:
            jugadores = list(equipo.jugadores.all())
            por_posicion = {p: [j for j in jugadores if j.posicion == p] for p in FORMACION}
            titulares = set()
            for posicion, cuantos in FORMACION.items():
                titulares.update(j.id for j in random.sample(por_posicion[posicion], cuantos))

            stats = {}
            for j in jugadores:
                if j.id in titulares:
                    minutos = random.choice([90, 90, 90, 90, 75, 60])
                else:
                    minutos = random.choice([0, 0, 15, 25, 30])
                amarillas = 1 if minutos > 0 and random.random() < 0.12 else 0
                rojas = 0
                if minutos > 0 and random.random() < 0.02:
                    rojas = 1
                    minutos = min(minutos, random.randint(30, 80))
                stats[j.id] = {"jugador": j, "minutos": minutos, "goles": 0,
                               "amarillas": amarillas, "rojas": rojas}

            # Repartir los goles del equipo entre los jugadores de campo que jugaron
            candidatos = [s for s in stats.values()
                          if s["minutos"] > 0 and s["jugador"].posicion != "POR"]
            pesos = [PESO_GOL[s["jugador"].posicion] for s in candidatos]
            for _ in range(goles_equipo):
                random.choices(candidatos, weights=pesos)[0]["goles"] += 1

            for s in stats.values():
                j = s["jugador"]
                est = EstadisticaPartido(
                    jugador=j, partido=partido, minutos=s["minutos"],
                    goles=s["goles"], amarillas=s["amarillas"], rojas=s["rojas"],
                    porteria_cero=(j.posicion == "POR" and s["minutos"] > 0 and goles_rival == 0),
                )
                est.calcular_puntos()
                filas.append(est)
        EstadisticaPartido.objects.bulk_create(filas)

    # ---------- Usuarios, grupos y alineaciones ----------

    def crear_usuarios(self):
        if not Usuario.objects.filter(email="admin@ejemplo.com").exists():
            Usuario.objects.create_superuser(
                username="admin", email="admin@ejemplo.com",
                password="admin1234", alias="admin",
            )
        usuarios = {}
        for alias, nombre, apellido in USUARIOS:
            email = f"{alias}@ejemplo.com"
            usuario = Usuario.objects.filter(email=email).first()
            if usuario is None:
                usuario = Usuario.objects.create_user(
                    username=alias, email=email, password=PASSWORD,
                    alias=alias, first_name=nombre, last_name=apellido,
                )
            usuarios[alias] = usuario
        return usuarios

    def crear_grupos(self, liga, usuarios):
        for nombre, creador, codigo, miembros in GRUPOS:
            defaults = {"liga": liga}
            if codigo:
                defaults["codigo"] = codigo
            grupo, _ = Grupo.objects.get_or_create(
                creador=usuarios[creador], nombre=nombre, defaults=defaults,
            )
            for alias in [creador] + miembros:
                Membresia.objects.get_or_create(usuario=usuarios[alias], grupo=grupo)

    def crear_alineaciones(self, liga, jornadas):
        por_posicion = {p: list(Jugador.objects.filter(equipo__liga=liga, posicion=p))
                        for p in FORMACION}
        jugadas = [j for j in jornadas if j.numero <= JORNADAS_JUGADAS]

        for membresia in Membresia.objects.filter(grupo__liga=liga):
            for jornada in jugadas:
                alineacion, creada = Alineacion.objects.get_or_create(
                    membresia=membresia, jornada=jornada,
                )
                if creada:
                    once = []
                    for posicion, cuantos in FORMACION.items():
                        once += random.sample(por_posicion[posicion], cuantos)
                    alineacion.jugadores.set(once)
                    alineacion.calcular_puntos()
            membresia.recalcular_puntos()
