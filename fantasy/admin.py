from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Alineacion, EstadisticaPartido, Jornada, Liga, Equipo, Jugador,Club, Partido, Temporada, Usuario

admin.site.register(Liga)
admin.site.register(Equipo)
admin.site.register(Jugador)
admin.site.register(Club)
admin.site.register(Temporada)
admin.site.register(Usuario)
admin.site.register(Alineacion)
admin.site.register(Jornada)
admin.site.register(Partido)
admin.site.register(EstadisticaPartido)

