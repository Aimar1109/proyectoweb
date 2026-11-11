from django.shortcuts import render, get_object_or_404

from .forms import RegistroForm
from .models import Club, Equipo, Temporada,Liga,Usuario

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib.auth import login

# Create your views here.


from django.views.generic import CreateView, TemplateView
from django.utils import timezone

from .models import Club, Equipo, Jugador, Usuario, Partido


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