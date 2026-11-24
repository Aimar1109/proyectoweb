"""Datos demo de Fantasy. Ejecutar después de generar_estadisticas.
python manage.py generar_usuarios --usuarios 100 --grupos-por-liga 2 --miembros 10
Los usuarios demo tienen contraseña compartida: solo para desarrollo.
"""
import random
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.contrib.auth.hashers import make_password
from fantasy.models import (Usuario, Grupo, Membresia, Alineacion, Liga,
                            Jornada, Jugador, Partido, EstadisticaPartido)

NOMBRES = 'Iker Unai Aitor Ander Mikel Jon Gorka Asier Eneko Julen Markel Ibai Amaia Ainhoa Nerea Leire Irati Ane June Maialen'.split()
APELLIDOS = 'Aguirre Bilbao Arana Lasa Urrutia Uriarte Zabala Ibarra Landa Ortiz García López Martínez Ruiz'.split()
FORMACIONES = [(1, 4, 3, 3)]  # Siempre 4-3-3
POSICIONES = ('POR', 'DEF', 'MED', 'DEL')
DOMINIO = '@fantasy-demo.invalid'

class Command(BaseCommand):
    help = 'Genera usuarios, grupos, membresías y alineaciones históricas ficticias.'

    def add_arguments(self, parser):
        parser.add_argument('--usuarios', type=int, default=100)
        parser.add_argument('--grupos-por-liga', type=int, default=2)
        parser.add_argument('--miembros', type=int, default=10, help='Miembros por grupo, incluido el creador.')
        parser.add_argument('--seed', type=int, default=42)
        parser.add_argument('--password', default='FantasyDemo2026!')
        parser.add_argument('--liga', type=int, help='Limitar a una liga por ID.')
        parser.add_argument('--dry-run', action='store_true')

    @transaction.atomic
    def handle(self, *args, **o):
        if not 1 <= o['miembros'] <= min(o['usuarios'], Grupo.MAX_MIEMBROS):
            raise CommandError('Miembros debe estar entre 1 y el mínimo de usuarios y MAX_MIEMBROS.')
        if o['grupos_por_liga'] < 1 or not o['password']:
            raise CommandError('Indica al menos un grupo por liga y una contraseña no vacía.')
        jugados = Partido.objects.filter(goles_local__isnull=False, goles_visitante__isnull=False)
        ligas = Liga.objects.filter(Exists(jugados.filter(jornada__liga_id=OuterRef('pk')))).order_by('pk')
        if o['liga'] is not None:
            ligas = ligas.filter(pk=o['liga'])
        ligas = list(ligas)
        if not ligas:
            raise CommandError('No hay ligas con partidos jugados. Ejecuta importar_fvf primero.')
        pendientes = jugados.filter(jornada__liga__in=ligas).annotate(
            tiene_stats=Exists(EstadisticaPartido.objects.filter(partido_id=OuterRef('pk')))
        ).filter(tiene_stats=False)
        if pendientes.exists():
            raise CommandError('Hay partidos jugados sin estadísticas. Ejecuta generar_jugadores y generar_estadisticas primero.')

        usuarios = []
        nuevos = grupos = membresias = alineaciones = 0
        password_hash = make_password(o['password'])
        for i in range(1, o['usuarios'] + 1):
            rnd = random.Random(f"{o['seed']}-usuario-{i}")
            nombre, apellidos = rnd.choice(NOMBRES), ' '.join(rnd.sample(APELLIDOS, 2))
            email = f'demo{i:04d}{DOMINIO}'
            alias = f'FantasyDemo{i:04d}'
            u, creado = Usuario.objects.get_or_create(email=email, defaults={
                'username': f'fantasy_demo_{i:04d}', 'alias': alias,
                'first_name': nombre, 'last_name': apellidos, 'password': password_hash,
                'is_staff': False, 'is_superuser': False,
            })
            if not creado and (u.username != f'fantasy_demo_{i:04d}' or u.is_staff or u.is_superuser):
                raise CommandError(f'El email {email} pertenece a una cuenta no reconocida como demo.')
            usuarios.append(u)
            nuevos += creado

        for liga in ligas:
            jornadas = list(Jornada.objects.filter(liga=liga).filter(
                Exists(jugados.filter(jornada_id=OuterRef('pk')))
            ).order_by('numero'))
            if not jornadas:
                continue
            plantilla = defaultdict(list)
            for jugador in Jugador.objects.filter(equipo__liga=liga).order_by('pk'):
                plantilla[jugador.posicion].append(jugador.pk)
            formaciones = [f for f in FORMACIONES if all(len(plantilla[p]) >= n for p,n in zip(POSICIONES,f))]
            if not formaciones:
                raise CommandError(f'No hay suficientes jugadores para formar un once en {liga.nombre}.')
            # Reparto rotatorio: evita concentrar todos los grupos en los mismos usuarios.
            orden = usuarios.copy()
            random.Random(f"{o['seed']}-reparto").shuffle(orden)
            for indice in range(1, o['grupos_por_liga'] + 1):
                nombre_grupo = f'[DEMO] Liga {liga.pk} - Grupo {indice}'
                grupo = Grupo.objects.filter(liga=liga, nombre=nombre_grupo,
                    creador__email__endswith=DOMINIO, creador__username__startswith='fantasy_demo_').first()
                if grupo is None:
                    inicio = (grupos * o['miembros']) % len(orden)
                    elegidos = [orden[(inicio+k) % len(orden)] for k in range(o['miembros'])]
                    grupo = Grupo.objects.create(nombre=nombre_grupo, liga=liga, creador=elegidos[0])
                else:
                    existentes = list(grupo.membresias.values_list('usuario_id', flat=True))
                    elegidos = [grupo.creador]
                    disponibles = [u for u in orden if u.pk not in existentes and u.pk != grupo.creador_id]
                    random.Random(f"{o['seed']}-grupo-{grupo.pk}").shuffle(disponibles)
                    faltan = max(0, o['miembros'] - len(set(existentes) | {grupo.creador_id}))
                    elegidos.extend(disponibles[:faltan])
                grupos += 1
                for u in elegidos:
                    if not grupo.membresias.filter(usuario=u).exists() and grupo.membresias.count() >= Grupo.MAX_MIEMBROS:
                        raise CommandError(f'Grupo {grupo.pk} lleno; no se puede añadir al creador o miembro.')
                    m, creado = Membresia.objects.get_or_create(grupo=grupo, usuario=u)
                    membresias += creado
                    if creado:
                        Membresia.objects.filter(pk=m.pk).update(fecha_alta=jornadas[0].fecha_inicio)
                # Fechas históricas ficticias, solo para grupos recién generados con fecha posterior.
                if grupo.fecha_alta > jornadas[0].fecha_inicio:
                    Grupo.objects.filter(pk=grupo.pk).update(fecha_alta=jornadas[0].fecha_inicio)
                for m in grupo.membresias.filter(usuario__email__endswith=DOMINIO,
                                                  usuario__username__startswith='fantasy_demo_'):
                    for jornada in jornadas:
                        a, creado = Alineacion.objects.get_or_create(membresia=m, jornada=jornada)
                        if creado:
                            rnd = random.Random(f"{o['seed']}-{m.usuario_id}-{grupo.pk}-{jornada.pk}")
                            formacion = rnd.choice(formaciones)
                            ids = [pk for p,n in zip(POSICIONES,formacion) for pk in rnd.sample(plantilla[p], n)]
                            a.jugadores.set(ids)
                            alineaciones += 1
                        a.calcular_puntos()
                    m.recalcular_puntos()
            self.stdout.write(f'{liga.nombre}: {len(jornadas)} jornadas procesadas.')
        self.stdout.write(self.style.SUCCESS(
            f'{nuevos} usuarios nuevos, {grupos} grupos procesados, {membresias} membresías nuevas, {alineaciones} alineaciones nuevas.'))
        if o['dry_run']:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING('Dry-run: cambios deshechos.'))
        else:
            self.stdout.write('Cuentas demo: demo0001@fantasy-demo.invalid, demo0002@fantasy-demo.invalid, etc.')
            self.stdout.write('Contraseña: la indicada en --password (o la predeterminada para cuentas nuevas).')
