"""Importa los CSV de la FVF en los modelos de la app `fantasy`.

    python manage.py importar_fvf --dir ruta/a/los/csv

Archivos esperados en --dir:
    competiciones_fvf.csv, jornadas_fvf.csv,
    partidos_fvf_19_correcciones.csv (si existe) o partidos_fvf.csv,
    clubes_info.csv

Es idempotente: se puede ejecutar varias veces sin duplicar nada
(usa get_or_create / update_or_create con las restricciones únicas de tus modelos).

Orden: Temporada -> Liga (una por competición+grupo) -> Club -> Equipo
       -> Jornada -> Partido.
"""
import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date
from django.utils.text import slugify

from fantasy.models import Club, Equipo, Jornada, Liga, Partido, Temporada

F_COMPETICIONES = "competiciones_fvf.csv"
F_JORNADAS = "jornadas_fvf.csv"
F_PARTIDOS = "partidos_fvf.csv"
F_PARTIDOS_CORREGIDOS = "partidos_fvf_19_correcciones.csv"
F_CLUBES = "clubes_info.csv"

MINUSCULAS = {"de", "del", "la", "las", "los", "y", "e"}


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def leer(ruta, columnas):
    if not ruta.exists():
        raise CommandError(f"No existe {ruta}")
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        faltan = set(columnas) - set(lector.fieldnames or [])
        if faltan:
            raise CommandError(f"{ruta.name}: faltan columnas {sorted(faltan)}")
        return list(lector)


def limpio(texto):
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def norm(texto):
    return limpio(texto).upper()


def titulo(texto):
    """'DIVISIÓN DE HONOR CADETE' -> 'División de Honor Cadete'."""
    salida = []
    for i, palabra in enumerate(limpio(texto).lower().split()):
        if i and palabra in MINUSCULAS:
            salida.append(palabra)
        else:
            salida.append(re.sub(r"[^\W\d_]", lambda m: m.group().upper(), palabra, count=1))
    return " ".join(salida)


def categoria_es(categoria):
    """Parte en castellano de 'DIVISIÓN DE HONOR CADETE / KADETEEN OHOREZKO MAILA'."""
    return limpio(re.split(r"\s*/\s*", categoria)[0])


def familia(categoria):
    """Valor del campo Liga.categoria. Ajusta aquí si quieres otra clasificación."""
    c = categoria.upper()
    if re.search(r"FEMENIN|\bFEM\b", c):
        return "Femenino"
    if "CADETE" in c:
        return "Cadete"
    if "JUVENIL" in c:
        return "Juvenil"
    if "INFANTIL" in c:
        return "Infantil"
    if "REGIONAL" in c:
        return "Aficionado"
    return "Otras"


def numero_grupo(grupo):
    m = re.search(r"\d+", grupo or "")
    return int(m.group()) if m else None


def ciudad_de(direccion):
    """'48220, Abadiño, Vizcaya' -> 'Abadiño' (descarta basura tipo '0' o 'C.P: ...')."""
    partes = [p.strip() for p in (direccion or "").split(",")]
    if len(partes) >= 2:
        c = partes[1]
        if c and c != "0" and not c.upper().startswith("C.P"):
            return titulo(c) if c.isupper() else c
    return ""


def goles_csv(valor, campo, contexto):
    """Devuelve un entero o None si no hay goles; rechaza datos no válidos."""
    texto = limpio(valor)
    if not texto:
        return None
    if not texto.isdecimal():
        raise CommandError(f"Goles incorrectos en {contexto}: {campo}={texto!r}")
    goles = int(texto)
    if goles > 32767:
        raise CommandError(f"Goles fuera de rango en {contexto}: {campo}={goles}")
    return goles


# --------------------------------------------------------------------------
class Command(BaseCommand):
    help = "Importa competiciones, clubes, equipos, jornadas y todos los partidos (también pendientes)."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=".", help="Carpeta con los CSV (por defecto, la actual).")
        parser.add_argument("--partidos", default=None, help=(
            "Nombre del CSV de partidos dentro de --dir. Por defecto, usa el "
            "CSV de 19 correcciones si existe; si no, partidos_fvf.csv."))
        parser.add_argument("--solo-con-calendario", action="store_true",
                            help="Importa solo los grupos que tienen jornadas o partidos en los CSV.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Ejecuta todo y deshace los cambios al final (para probar).")
        parser.add_argument("--informe", default="informe_importacion_fvf.txt",
                            help="Fichero donde se guardan los avisos.")

    # ----------------------------------------------------------------------
    def handle(self, *args, **o):
        carpeta = Path(o["dir"])
        comp = leer(carpeta / F_COMPETICIONES,
                    ["Competición", "Grupo", "Club", "Equipo", "Categoría", "cod_competicion", "cod_grupo"])
        jor = leer(carpeta / F_JORNADAS, ["cod_grupo", "numero", "fecha_inicio", "fecha_fin"])
        archivo_partidos = o["partidos"] or (
            F_PARTIDOS_CORREGIDOS if (carpeta / F_PARTIDOS_CORREGIDOS).exists()
            else F_PARTIDOS
        )
        self.stdout.write(f"CSV de partidos: {carpeta / archivo_partidos}")
        par = leer(carpeta / archivo_partidos,
                   ["cod_grupo", "jornada", "local", "visitante", "goles_local", "goles_visitante"])
        info = leer(carpeta / F_CLUBES, ["codigo_club", "nombre", "email", "direccion"])

        self.avisos = []
        try:
            with transaction.atomic():
                self.importar(comp, jor, par, info, o)
                if o["dry_run"]:
                    raise _DryRun()
        except _DryRun:
            self.stdout.write(self.style.WARNING("--dry-run: cambios deshechos."))

        if self.avisos:
            Path(o["informe"]).write_text("\n".join(self.avisos) + "\n", encoding="utf-8")
            self.stdout.write(self.style.WARNING(
                f"{len(self.avisos)} avisos guardados en {o['informe']}"))

    # ----------------------------------------------------------------------
    def importar(self, comp, jor, par, info, o):

        comp = [
            r for r in comp
            if "INFANTIL" not in r["Categoría"].upper()
            and "INFANTIL" not in r["Competición"].upper()
        ]
        # ---- Qué grupos entran
        con_calendario = {r["cod_grupo"] for r in jor} | {r["cod_grupo"] for r in par}
        if o["solo_con_calendario"]:
            comp = [r for r in comp if r["cod_grupo"] in con_calendario]

        # ---- Temporada (rango tomado de las jornadas del CSV)
        inicios = [parse_date(r["fecha_inicio"]) for r in jor]
        fines = [parse_date(r["fecha_fin"]) for r in jor]
        if not inicios:
            raise CommandError("jornadas_fvf.csv está vacío: no se puede deducir la temporada.")
        temporada, creada = Temporada.objects.get_or_create(
            fecha_inicio=min(inicios), fecha_fin=max(fines))
        self.stdout.write(f"Temporada {temporada} ({'creada' if creada else 'ya existía'})")

        # ---- Ligas (una por cod_grupo)
        definicion = {}
        for r in comp:
            d = {
                "cat": categoria_es(r["Categoría"]),
                "grupo": numero_grupo(r["Grupo"]),
                "grupo_txt": limpio(r["Grupo"]),
            }
            if r["cod_grupo"] in definicion and definicion[r["cod_grupo"]] != d:
                self.avisos.append(f"cod_grupo {r['cod_grupo']} con datos inconsistentes en competiciones")
            definicion[r["cod_grupo"]] = d

        liga_de = {}
        n_ligas = 0
        for cod, d in definicion.items():
            nombre = titulo(d["cat"]) + (f" - {titulo(d['grupo_txt'])}" if d["grupo_txt"] else "")
            liga, creada = Liga.objects.get_or_create(
                temporada=temporada, nombre=nombre,
                defaults={"categoria": familia(d["cat"]), "grupo": d["grupo"]})
            liga_de[cod] = liga
            n_ligas += creada
        self.stdout.write(f"Ligas: {len(liga_de)} ({n_ligas} nuevas)")

        # ---- Clubes
        info_de = {norm(r["nombre"]): r for r in info}
        nombres = {}
        for r in comp:
            nombres.setdefault(norm(r["Club"]), limpio(r["Club"]))
        ordenados = sorted(nombres, key=lambda k: (int(info_de[k]["codigo_club"]) if k in info_de
                                                   and info_de[k]["codigo_club"].isdigit() else 10**9, k))
        emails_usados = {e.lower() for e in Club.objects.values_list("email", flat=True)}
        club_de = {}
        n_clubes = n_sin_info = 0
        for k in ordenados:
            nombre = nombres[k]
            fila = info_de.get(k)
            club = Club.objects.filter(nombre=nombre).first()
            if club is None:
                email = limpio(fila["email"]).lower() if fila else ""
                if not email:
                    email = f"sin-email-{slugify(nombre)}@fvf.invalid"
                    self.avisos.append(f"Club sin email: {nombre} -> {email}")
                elif email in emails_usados:
                    nuevo = f"sin-email-{slugify(nombre)}@fvf.invalid"
                    self.avisos.append(f"Email repetido ({email}) en {nombre} -> {nuevo}")
                    email = nuevo
                emails_usados.add(email)
                club = Club.objects.create(
                    nombre=nombre, email=email,
                    direccion=limpio(fila["direccion"]) if fila else "")
                n_clubes += 1
            if not fila:
                n_sin_info += 1
                self.avisos.append(f"Club sin ficha en clubes_info.csv: {nombre}")
            club_de[k] = club
        self.stdout.write(f"Clubes: {len(club_de)} ({n_clubes} nuevos, {n_sin_info} sin ficha de info)")

        # ---- Equipos
        equipo_de = {}   # (liga_id, nombre normalizado) -> Equipo
        n_equipos = 0
        for r in comp:
            liga = liga_de[r["cod_grupo"]]
            club = club_de[norm(r["Club"])]
            fila = info_de.get(norm(r["Club"]))
            nombre = limpio(r["Equipo"])
            equipo, creado = Equipo.objects.get_or_create(
                nombre=nombre, liga=liga,
                defaults={
                    "club": club,
                    "ciudad": ciudad_de(fila["direccion"]) if fila else "",
                    "descripcion": f"Equipo {nombre} del club {club.nombre} en {liga.nombre}"[:300],
                })
            equipo_de[(liga.id, norm(nombre))] = equipo
            n_equipos += creado
        self.stdout.write(f"Equipos: {len(equipo_de)} ({n_equipos} nuevos)")

        # ---- Jornadas
        jornada_de = {}
        n_jor = saltadas = 0
        for r in jor:
            liga = liga_de.get(r["cod_grupo"])
            if liga is None:
                saltadas += 1
                continue
            jornada, creada = Jornada.objects.get_or_create(
                liga=liga, numero=int(r["numero"]),
                defaults={"fecha_inicio": parse_date(r["fecha_inicio"]),
                          "fecha_fin": parse_date(r["fecha_fin"])})
            jornada_de[(liga.id, jornada.numero)] = jornada
            n_jor += creada
        self.stdout.write(f"Jornadas: {len(jornada_de)} ({n_jor} nuevas, {saltadas} saltadas)")

        # ---- Partidos
        clubes_norm = list(club_de)
        n_par = n_act = n_pendientes = 0
        for r in par:
            liga = liga_de.get(r["cod_grupo"])
            if liga is None:
                continue
            jornada = jornada_de.get((liga.id, int(r["jornada"])))
            if jornada is None:
                self.avisos.append(f"Partido sin jornada definida: grupo {r['cod_grupo']} J{r['jornada']}")
                continue
            local = self._equipo(equipo_de, liga, r["local"], club_de, clubes_norm)
            visit = self._equipo(equipo_de, liga, r["visitante"], club_de, clubes_norm)
            if local.id == visit.id:
                self.avisos.append(f"Partido con el mismo equipo: {r['local']} (grupo {r['cod_grupo']})")
                continue
            contexto = f"grupo {r['cod_grupo']} J{r['jornada']}: {r['local']} - {r['visitante']}"
            gl = goles_csv(r["goles_local"], "goles_local", contexto)
            gv = goles_csv(r["goles_visitante"], "goles_visitante", contexto)
            if (gl is None) != (gv is None):
                self.avisos.append(f"Marcador incompleto: {contexto}; se deja sin goles")
                gl = gv = None

            # No sobrescribir marcadores existentes con celdas vacías del CSV.
            # Todos los partidos se guardan sin fecha individual, incluidos los antiguos.
            defaults = {"fecha": None}
            if gl is not None and gv is not None:
                defaults.update(goles_local=gl, goles_visitante=gv)
            partido, creado = Partido.objects.update_or_create(
                jornada=jornada, local=local, visitante=visit,
                defaults=defaults)
            n_par += creado
            n_act += not creado
            if partido.goles_local is None and partido.goles_visitante is None:
                n_pendientes += 1
        self.stdout.write(f"Partidos: {n_par} nuevos, {n_act} actualizados; "
                          f"{n_pendientes} pendientes sin marcador")
        self.stdout.write(self.style.SUCCESS("Importación terminada."))

    # ----------------------------------------------------------------------
    def _equipo(self, equipo_de, liga, nombre, club_de, clubes_norm):
        """Busca el equipo en su liga; si el partido lo menciona pero no está en
        competiciones (p. ej. equipo retirado), lo crea y avisa."""
        clave = (liga.id, norm(nombre))
        if clave in equipo_de:
            return equipo_de[clave]
        candidatos = [c for c in clubes_norm if c.startswith(norm(nombre) + " ")]
        club = club_de[candidatos[0]] if len(candidatos) == 1 else None
        equipo, _ = Equipo.objects.get_or_create(
            nombre=limpio(nombre), liga=liga,
            defaults={"club": club, "ciudad": "",
                      "descripcion": f"Equipo {limpio(nombre)} en {liga.nombre}"[:300]})
        equipo_de[clave] = equipo
        self.avisos.append(
            f"Equipo creado desde partidos (no estaba en competiciones): {nombre} en {liga.nombre}"
            f" -> club {club.nombre if club else 'sin asignar'}")
        return equipo


class _DryRun(Exception):
    pass
