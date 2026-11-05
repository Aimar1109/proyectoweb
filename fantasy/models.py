from django.db import models

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
    nombre = models.CharField(max_length=100, unique=True)
    ciudad = models.CharField(max_length=100)
    anno_fundacion = models.PositiveIntegerField(null=True, blank=True)
    descripcion = models.CharField(max_length=300, unique=True)
    liga = models.ForeignKey(Liga, on_delete=models.CASCADE, related_name="equipos",null=True,blank=True)
    club = models.ForeignKey(Club,on_delete=models.CASCADE,related_name="equipos",null=True,blank=True)
    class Meta: # Para visualizar el nombre en singular y plural del modelo en ADMIN
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"

    def __str__(self):
        return self.nombre

class Usuario(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    alias = models.CharField(max_length=30, unique=True)

    equipo = models.ForeignKey(
        "Equipo", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="usuario_equipo",
    )

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.alias



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
    usuario = models.ForeignKey("Usuario", on_delete=models.CASCADE, related_name="alineaciones")
    jornada = models.ForeignKey("Jornada", on_delete=models.CASCADE, related_name="alineaciones")
    jugadores = models.ManyToManyField("Jugador", blank=True, related_name="elegido_en")
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Alineación"
        verbose_name_plural = "Alineaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "jornada"],
                name="una_alineacion_por_usuario_y_jornada",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.jornada}"


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