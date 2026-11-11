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

    path("ligas/<int:pk>/", views.detalle_liga, name="detalle_liga"),
]
