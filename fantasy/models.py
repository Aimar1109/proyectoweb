from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class Temporada(models.Model):
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)

    class Meta: # Para visualizar el nombre en singular y plural del modelo en ADMIN
        verbose_name = "Temporada"
        verbose_name_plural = "Temporadas"
      
    def __str__(self):
        return f"{self.fecha_inicio.year} - {self.fecha_fin.year}"


class Liga(models.Model):
    temporada = models.ForeignKey(Temporada, on_delete=models.CASCADE, related_name="ligas",null=True,blank=True)
    nombre = models.CharField(max_length=100)
    categoria=models.CharField(max_length=100)
    grupo=models.PositiveSmallIntegerField(null=True, blank=True)
    class Meta: # Para visualizar el nombre en singular y plural del modelo en ADMIN
            verbose_name = "Liga"
            verbose_name_plural = "Ligas"

            constraints = [ models.UniqueConstraint(
                fields=["temporada", "nombre"],
                name="liga_unica_por_temporada"
            ),
            ]
    
    def __str__(self):
        return f"{self.nombre} ({self.temporada})"


class Club(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    anno_fundacion = models.PositiveIntegerField(null=True, blank=True)
    email = models.EmailField(unique=True)
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
    nombre = models.CharField(max_length=100) # He borrado el unique true, porque un nuestra base de datos Athletic 2022/2023 es distinto de Athletic 2023/2024
    ciudad = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=300)
    liga = models.ForeignKey(Liga, on_delete=models.SET_NULL, related_name="equipos",null=True,blank=True) # Si se elimina la liga el equipo sigue existiendo
    club = models.ForeignKey(Club,on_delete=models.CASCADE,related_name="equipos",null=True,blank=True)
    class Meta: # Para visualizar el nombre en singular y plural del modelo en ADMIN
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

        constraints = [ models.UniqueConstraint(
            fields = ["nombre", "liga"],
            name =  "equipo_unico_por_liga"
        ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.liga})"

class Usuario(AbstractUser):
    email = models.EmailField(unique=True)
    alias = models.CharField(max_length=30, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "alias"]

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.alias

class Grupo(models.Model):
    nombre = models.CharField(max_length=100)
    creador = models.ForeignKey(Usuario, null=True, on_delete=models.SET_NULL, related_name="grupos_creados")
    liga = models.ForeignKey(Liga, on_delete=models.CASCADE, related_name="grupos")
    fecha_alta = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Grupo"
        verbose_name_plural = "Grupos"
        constraints = [ models.UniqueConstraint(
                fields=["creador", "nombre"],
                name="nombre_grupo_unico_por_creador"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.liga})"


class Membresia(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="membresias")
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name="membresias")
    fecha_alta = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Membresia"
        verbose_name_plural = "Membresias"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "grupo"],
                name="un_usuario_una_membresia_por_grupo"),
        ]

    def __str__(self):
        return f"{self.usuario} ({self.grupo})"
    

class Participacion(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="participaciones")
    liga = models.ForeignKey(Liga, on_delete=models.CASCADE, related_name="participaciones")
    fecha_alta = models.DateField(auto_now_add=True)
    puntos = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Participacion"
        verbose_name_plural = "Participaciones"
        ordering = ["-puntos"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "liga"],
                name="una_participacion_por_liga"),
        ]

    def __str__(self):
        return f"{self.usuario} ({self.liga})"

class Jugador(models.Model):
    class Posicion(models.TextChoices):
        PORTERO = "POR", "Portero"
        DEFENSA = "DEF", "Defensa"
        CENTROCAMPISTA = "MED", "Centrocampista"
        DELANTERO = "DEL", "Delantero"

    nombre = models.CharField(max_length=100)
    posicion = models.CharField(max_length=3, choices=Posicion.choices)
    dorsal = models.PositiveSmallIntegerField(null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="jugadores")

    class Meta:
        verbose_name = "Jugador"
        verbose_name_plural = "Jugadores"
        constraints = [
            models.UniqueConstraint(fields=["equipo", "dorsal"], name="dorsal_unico_por_equipo"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.equipo.nombre})"

        


class Jornada(models.Model):
    liga = models.ForeignKey(
        "Liga", on_delete=models.CASCADE, related_name="jornadas",
    )
    numero = models.PositiveSmallIntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    class Meta:
        verbose_name = "Jornada"
        verbose_name_plural = "Jornadas"

        constraints = [
            models.UniqueConstraint(fields=["liga", "numero"], name="jornada_unica_por_liga"),
        ]

    def __str__(self):
        return f"Jornada {self.numero} - {self.liga}"

        

class Alineacion(models.Model):
    usuario = models.OneToOneField(
        "Usuario", on_delete=models.CASCADE, related_name="alineacion",
    )
    jugadores = models.ManyToManyField(
        "Jugador", blank=True, related_name="elegido_en",
    )
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Alineación"
        verbose_name_plural = "Alineaciones"

    def __str__(self):
        return f"Alineación de {self.usuario}"


class Partido(models.Model):
    jornada = models.ForeignKey(
        "Jornada", on_delete=models.CASCADE, related_name="partidos",
    )
    local = models.ForeignKey(
        "Equipo", on_delete=models.PROTECT, related_name="partidos_local",
    )
    visitante = models.ForeignKey(
        "Equipo", on_delete=models.PROTECT, related_name="partidos_visitante",
    )
    fecha = models.DateTimeField(null=True, blank=True)
    goles_local = models.PositiveSmallIntegerField(null=True, blank=True)
    goles_visitante = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Partido"
        verbose_name_plural = "Partidos"

        constraints = [
            models.CheckConstraint(
                condition=~models.Q(local=models.F("visitante")),
                name="local_distinto_visitante",
            ),

            models.UniqueConstraint(
                fields=["jornada", "local", "visitante"],
                name="partido_unico_por_jornada",
            ),
            ]

    def __str__(self):
        return f"{self.local} vs {self.visitante}"

class EstadisticaPartido(models.Model):
    jugador = models.ForeignKey(
        "Jugador", on_delete=models.CASCADE, related_name="estadisticas",
    )
    partido = models.ForeignKey(
        "Partido", on_delete=models.CASCADE, related_name="estadisticas",
    )
    minutos = models.PositiveSmallIntegerField(default=0)
    goles = models.PositiveSmallIntegerField(default=0)
    amarillas = models.PositiveSmallIntegerField(default=0)
    rojas = models.PositiveSmallIntegerField(default=0)
    puntos = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Estadística de partido"
        verbose_name_plural = "Estadísticas de partido"

        constraints = [
            models.UniqueConstraint(fields=["jugador", "partido"], name="una_estadistica_por_jugador_y_partido"),
        ]

    def __str__(self):
        return f"{self.jugador} - {self.partido}"