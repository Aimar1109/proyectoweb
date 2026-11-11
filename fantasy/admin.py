from django.contrib import admin
from .models import Alineacion, EstadisticaPartido, Grupo, Jornada, Liga, Equipo, Jugador,Club, Membresia, Participacion, Partido, Temporada, Usuario
from django.contrib.auth.admin import UserAdmin

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Fantasy", {"fields": ("alias",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Fantasy", {"fields": ("email", "alias")}),)
    list_display = ("alias", "email", "is_staff")

admin.site.register(Liga)
admin.site.register(Equipo)
admin.site.register(Jugador)
admin.site.register(Club)
admin.site.register(Temporada)
admin.site.register(Alineacion)
admin.site.register(Jornada)
admin.site.register(Partido)
admin.site.register(EstadisticaPartido)
admin.site.register(Grupo)
admin.site.register(Membresia)
admin.site.register(Participacion)

