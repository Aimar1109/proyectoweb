from django.contrib import admin

from . import servicios
from .models import Alineacion, EstadisticaPartido, Grupo, Jornada, Liga, Equipo, Jugador,Club, Membresia, Partido, Temporada, Usuario
from django.contrib.auth.admin import UserAdmin

admin.site.register(Liga)
admin.site.register(Equipo)
admin.site.register(Jugador)
admin.site.register(Club)
admin.site.register(Temporada)
admin.site.register(Alineacion)
admin.site.register(Partido)
admin.site.register(EstadisticaPartido)
admin.site.register(Grupo)
admin.site.register(Membresia)

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Fantasy", {"fields": ("alias",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Fantasy", {"fields": ("email", "alias")}),)
    list_display = ("alias", "email", "is_staff")

@admin.register(Jornada)
class JornadaAdmin(admin.ModelAdmin):
    actions = ["calcular_puntos"]

    @admin.action(description="Calcular puntos de las jornada seleccionadas")
    def calcular_puntos(self, request, queryset):
        for jornada in queryset:
            servicios.calcular_puntos_jornada(jornada)
        self.message_user(request, "Puntos calculados.")