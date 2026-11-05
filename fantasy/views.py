from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from .models import Club, Equipo, Temporada, Jugador,Liga

# Create your views here.


def index(request):
    return HttpResponse("hola")

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



