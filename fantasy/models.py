from django.db import models

# Create your models here.

class Liga(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    categoria=models.CharField(max_length=100,unique=True)
    grupo=models.PositiveIntegerField(null=True, blank=True)
    class Meta: # Para visualizar el nombre en singular y plural del modelo en ADMIN
            verbose_name = "Liga"
            verbose_name_plural = "Ligas"
    
    def __str__(self):
        return f"{self.nombre}"

class Club(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    email = email = models.EmailField(unique=True)
    direccion = models.CharField(max_length=255, blank=True)
    camiseta_1color = models.CharField(max_length=30, blank=True)
    pantalon_1color = models.CharField(max_length=30, blank=True)
    medias_1color = models.CharField(max_length=30, blank=True)
    camiseta_2color = models.CharField(max_length=30, blank=True)
    pantalon_2color = models.CharField(max_length=30, blank=True)
    medias_2color = models.CharField(max_length=30, blank=True)
    class Meta: # Para visualizar el nombre en singular y plural del modelo en ADMIN
        verbose_name = "Club"
        verbose_name_plural = "Clubes"
     
    def __str__(self):
        return self.nombre


class Equipo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    ciudad = models.CharField(max_length=100, unique=True)
    anno_fundacion = models.PositiveIntegerField(null=True, blank=True)
    descripcion = models.CharField(max_length=300, unique=True)
    liga = models.ForeignKey(Liga, on_delete=models.CASCADE, related_name="ligas",null=True,blank=True)
    club = models.ForeignKey(Club,on_delete=models.CASCADE,related_name="clubes",null=True,blank=True)
    class Meta: # Para visualizar el nombre en singular y plural del modelo en ADMIN
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

    def __str__(self):
        return self.nombre


class Jugador(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    posicion = models.CharField(max_length=100, unique=True)
    dorsal =  models.PositiveIntegerField(null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name="equipos")
    class Meta: # Para visualizar el nombre en singular y plural del modelo en ADMIN
            verbose_name = "Jugador"
            verbose_name_plural = "Jugadores"
    
    def __str__(self):
        return f"{self.equipo.nombre} {self.nombre}"


