from django.contrib import messages

from django.db.models.aggregates import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render, get_object_or_404

from . import servicios

from .forms import RegistroForm
from .models import Alineacion, Club, Equipo, EstadisticaPartido, Grupo, Membresia, Temporada,Liga,Usuario, Partido, Jugador

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib.auth import login

from django.contrib.auth.decorators import login_required

from django.views.generic import CreateView, TemplateView
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST


class IndexView(TemplateView):
    template_name = 'fantasy/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_clubes'] = Club.objects.count()
        context['total_equipos'] = Equipo.objects.count()
        context['total_jugadores'] = Jugador.objects.count()
        context['total_usuarios'] = Usuario.objects.count()

        context['proximos_partidos'] = Partido.objects.filter(
            fecha__gte=timezone.now()
        ).select_related(
            'local', 'visitante'
        ).order_by('fecha')[:2]

        return context

#CLUB 

def lista_clubes(request):
    clubes = Club.objects.all().order_by("nombre")
    return render(request,"fantasy/clubes/lista_clubes.html",{"clubes":clubes})

def detalle_club(request,pk):
    club = get_object_or_404(Club,pk=pk)
    equipos = club.equipos.all().order_by("nombre")

    return render(request,"fantasy/clubes/detalle_club.html",{"club":club,"equipos":equipos})

#EQUIPO | solo detalle porque queremos lista de clubs no de equipos

def detalle_equipo(request,pk):
    equipo = get_object_or_404(Equipo,pk=pk)
    jugadores = equipo.jugadores.all().order_by("dorsal")

    return render(request,"fantasy/equipos/detalle_equipo.html",{"equipo":equipo,"jugadores":jugadores})

#TEMPORADA 

def lista_temporadas(request):
    temporadas = Temporada.objects.all()
    return render(request,"fantasy/temporadas/lista_temporada.html",{"temporadas":temporadas})

def detalle_temporada(request,pk):
    temporada = get_object_or_404(Temporada,pk=pk)
    ligas = temporada.ligas.all()
    return render(request,"fantasy/temporadas/detalle_temporada.html",{"temporada":temporada,"ligas":ligas})

#LIGA | solo detalle porque tenemos la lista de ligas en el detalle de la temporada

def detalle_liga(request,pk):
    liga = get_object_or_404(Liga,pk=pk)
    equipos = liga.equipos.all()
    return render(request,"fantasy/ligas/detalle_liga.html",{"liga":liga,"equipos":equipos})

#USUARIO

# LOGIN

class UsuarioLoginView(LoginView):
    template_name = "fantasy/user/login.html"
    redirect_authenticated_user = True
    next_page = reverse_lazy("index")

# LOGOUT
class UsuarioLogoutView(LogoutView):
    next_page = reverse_lazy('index')

#REGISTRO
class RegistroView(CreateView):
    model = Usuario
    form_class = RegistroForm
    template_name = 'fantasy/user/registro.html'
    success_url = reverse_lazy('index')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

# GRUPOS

@login_required
def mis_grupos(request):
    grupos = Grupo.objects.filter(membresias__usuario=request.user).select_related("liga")
    return render(request, "fantasy/grupos/mis_grupos.html", {"grupos": grupos})

@login_required
def crear_grupo(request):
    ligas = Liga.objects.select_related("temporada")
    if request.method == "POST":
        try:
            liga = Liga.objects.filter(pk=request.POST.get("liga") or None).first()
        except ValueError:
            liga = None
        if liga is None:
            messages.error(request, "Elige una liga.")
        else:
            try:
                grupo = servicios.crear_grupo(request.user, liga, request.POST.get("nombre", ""))
                return redirect("clasificacion", pk = grupo.pk)
            except ValidationError as e:
                messages.error(request, e.message)
    return render(request, "fantasy/grupos/crear_grupo.html", {"ligas": ligas})

@login_required
def unirse_grupo(request):
    if request.method == "POST":
        try:
            grupo = servicios.unirse_a_grupo(request.user, request.POST.get("codigo", ""))
            return redirect("clasificacion", pk=grupo.pk)
        except ValidationError as e:
            messages.error(request, e.message)
    return render(request, "fantasy/grupos/unirse_grupo.html")

@login_required
def clasificacion_grupo(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    if not grupo.membresias.filter(usuario=request.user).exists():
        return redirect("unirse_grupo")

    ranking = (
        grupo.membresias
        .select_related("usuario")
        .order_by("-puntos", "usuario__alias")
    )
    return render(request, "fantasy/grupos/clasificacion.html",
                  {"grupo": grupo, "ranking": ranking})

@login_required
def alineacion(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    membresia = grupo.membresias.filter(usuario=request.user).first()
    if not membresia:
        return redirect("unirse_grupo")

    request.session["grupo_activo_id"] = grupo.pk

    jornada = (grupo.liga.jornadas.filter(partidos__goles_local__isnull=True)
                                    .order_by("numero")
                                    .first()
                                    )

    if request.method == "POST" and jornada:

        try:
            servicios.guardar_alineacion(membresia, jornada, request.POST.getlist("jugadores"))
            messages.success(request, "Alineacion guardada")
            return redirect("alineacion", pk=grupo.pk) 
        
        except ValidationError as e:
            messages.error(request, e.messages)

    jugadores = list(
        Jugador.objects.filter(equipo__liga = grupo.liga)
                       .annotate(total_puntos = Coalesce(Sum("estadisticas__puntos"), 0))
                       .order_by("equipo__nombre", "dorsal")
                       .values("id", "nombre", "posicion", "dorsal", "equipo_id",
                               "equipo__nombre", "total_puntos")
    )    

    elegidos = []
    precargada_de = None
    if jornada:
        actual = Alineacion.objects.filter(membresia=membresia, jornada=jornada).first()
        if actual:
            elegidos = list(actual.jugadores.values_list("id", flat=True)) # ?????????????
        else:
            anterior = (
                Alineacion.objects.filter(membresia=membresia, jornada__numero__lt =jornada.numero)
                                  .select_related("jornada")
                                  .order_by("-jornada__numero")
                                  .first()
            )

            if anterior:
                elegidos = list(anterior.jugadores.values_list("id", flat=True))
                precargada_de = anterior.jornada

    return render(request, "fantasy/grupos/alineacion.html", {
        "grupo": grupo,
        "membresia": membresia,
        "jornada": jornada,
        "jugadores": jugadores,
        "elegidos": elegidos,
        "precargada_de": precargada_de,
        "equipos": Equipo.objects.filter(liga=grupo.liga).order_by("nombre"),
    })

@login_required
@require_POST
def salir_grupo(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    if grupo.creador_id == request.user.pk:
        messages.error(request, "El creador no puede abandonar el grupo.")
        return redirect("clasificacion", pk=pk)
    grupo.membresias.filter(usuario=request.user).delete()
    return redirect("mis_grupos")


@login_required
def lista_puntos(request, pk):
    membresia = get_object_or_404(
        Membresia.objects.select_related("usuario", "grupo"),
        pk=pk
    )
    if not membresia.grupo.membresias.filter(usuario=request.user).exists():
        return redirect("unirse_grupo")

    alineaciones = (
        membresia.alineaciones
        .select_related("jornada")
        .order_by("jornada__numero")
    )
    return render(request, "fantasy/grupos/lista_puntos.html", {
        "membresia": membresia,
        "alineaciones": alineaciones,
    })


@login_required
def detalle_puntos(request, pk, jornada_pk):
    alineacion = get_object_or_404(
        Alineacion.objects.select_related("membresia__usuario", "membresia__grupo", "jornada"),
        membresia_id=pk,
        jornada_id=jornada_pk
    )
    if not alineacion.membresia.grupo.membresias.filter(usuario=request.user).exists():
        return redirect("unirse_grupo")

    stats = EstadisticaPartido.objects.filter(
        jugador__in=alineacion.jugadores.all(),
        partido__jornada=alineacion.jornada
    )
    puntos_por_jugador = {}
    for stat in stats:
        puntos_por_jugador[stat.jugador_id] = puntos_por_jugador.get(stat.jugador_id, 0) + stat.puntos

    jugadores_con_puntos = [
        {
            "jugador": jugador,
            "puntos": puntos_por_jugador.get(jugador.id, 0)
        }
        for jugador in alineacion.jugadores.select_related("equipo").all()
    ]

    return render(request, "fantasy/grupos/detalle_puntos.html", {
        "alineacion": alineacion,
        "jugadores_con_puntos": jugadores_con_puntos,
    })