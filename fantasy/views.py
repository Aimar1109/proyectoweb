from pyexpat.errors import messages

from django.shortcuts import redirect, render, get_object_or_404

from . import servicios

from .forms import RegistroForm
from .models import Club, Equipo, Grupo, Temporada,Liga,Usuario, Partido, Jugador

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
    if request.method == ["POST"]:
        try:
            liga = Liga.objects.filter(pk=request.POST.get("liga") or None).first()
        except ValueError:
            liga = None
        if liga is None:
            messages.error(request, "Elige una liga.")
        else:
            try:
                grupo = servicios.crear_grupo(request.user, liga, request.POST.get("nombre", ""))
                return redirect("clasificacion.html", pk = grupo.pk)
            except ValidationError as e:
                messages.error(request, e.message)
    return render(request, "fantasy/grupos/crear_grupo.html", {"ligas": ligas})

@login_required
def unirse_grupo(request):
    if request.method == "POST":
        try:
            grupo = servicios.unirse_a_grupo(request.user, request.POST.get("codigo", ""))
            return redirect("detalle_grupo", pk=grupo.pk)
        except ValidationError as e:
            messages.error(request, e.message)
    return render(request, "fantasy/grupos/unirse_grupo.html")

@login_required
def clasificacion_grupo(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    if not grupo.membresias.filter(usuario=request.user).exists():
        return redirect("unirse_grupo")  # solo los miembros ven el grupo
    ranking = (
        grupo.membresias
        .select_related("usuario")
        .order_by("-puntos", "usuario__alias")
    )
    return render(request, "fantasy/grupos/clasificacion.html",
                  {"grupo": grupo, "ranking": ranking})

@login_required
@require_POST
def salir_grupo(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    if grupo.creador_id == request.user.pk:
        messages.error(request, "El creador no puede abandonar el grupo.")
        return redirect("detalle_grupo", pk=pk)
    grupo.membresias.filter(usuario=request.user).delete()
    return redirect("mis_grupos")