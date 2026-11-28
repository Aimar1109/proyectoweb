from django.contrib import admin
from django.urls import path

from fantasy import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),

    path("login/", views.UsuarioLoginView.as_view(), name="login"),
    path('logout/', views.UsuarioLogoutView.as_view(), name='logout'),
    path('registro/', views.RegistroView.as_view(), name='registro'),

    path("clubes/",views.lista_clubes,name="lista_clubes"),
    path("clubes/<int:pk>/",views.detalle_club,name="detalle_club"),

    path("equipos/<int:pk>/",views.detalle_equipo,name="detalle_equipo"),

    path("temporadas/", views.lista_temporadas, name="lista_temporadas"),
    path("temporadas/<int:pk>/", views.detalle_temporada, name="detalle_temporada"),

    path("ligas/", views.ligas_actuales, name="ligas_actuales"),
    path("ligas/<int:pk>/", views.detalle_liga, name="detalle_liga"),
    path("ligas/<int:pk>/jornadas/", views.jornadas_liga, name="jornadas_liga"),

    path("grupos/", views.mis_grupos, name="mis_grupos"),
    path("grupos/unirse/", views.unirse_grupo, name="unirse_grupo"),
    path("grupos/<int:pk>/", views.clasificacion_grupo, name="clasificacion"),
    path("grupos/<int:pk>/alineacion/", views.alineacion, name="alineacion"),
    path("grupos/<int:pk>/salir/", views.salir_grupo, name="salir_grupo"),
    path("grupos/nuevo/", views.crear_grupo, name="crear_grupo"),

    path("grupos/membresia/<int:pk>/puntos/", views.lista_puntos, name="lista_puntos"),
    path("grupos/membresia/<int:pk>/puntos/<int:jornada_pk>/", views.lista_puntos, name="lista_puntos"),

]
