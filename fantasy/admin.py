from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Liga, Equipo, Jugador,Club

admin.site.register(Liga)
admin.site.register(Equipo)
admin.site.register(Jugador)
admin.site.register(Club)