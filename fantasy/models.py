from django.db import models

# Create your models here.
class Equipo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    ciudad = models.CharField(max_length=100, unique=True)
    anno_fundacion = models.PositiveIntegerField(null=True, blank=True)
    descripcion = models.CharField(max_length=300, unique=True)

    class Meta: # Para visualizar el nombre en singular y plural del modelo en ADMIN
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

    def __str__(self):
        return self.nombre


class Jugador(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    posicion = models.CharField(max_length=100, unique=True)
    dorsal =  models.PositiveIntegerField(null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name="gamas")
    class Meta: # Para visualizar el nombre en singular y plural del modelo en ADMIN
            verbose_name = "Jugador"
            verbose_name_plural = "Jugadores"
    
    def __str__(self):
        return f"{self.equipo.nombre} {self.nombre}"
