from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

class Competencia(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Corte(models.Model):
    nombre = models.CharField(max_length=100)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE, related_name="cortes")

    def __str__(self):
        return f"{self.nombre} ({self.competencia.nombre})"

class Tribunal(models.Model):
    nombre = models.CharField(max_length=150)
    corte = models.ForeignKey(Corte, on_delete=models.CASCADE, related_name="tribunales")

    def __str__(self):
        return f"{self.nombre} ({self.corte.nombre})"

class TipoCausa(models.Model):
    nombre = models.CharField(max_length=100)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE, related_name="tipos")

    def __str__(self):
        return self.nombre

class Causa(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="causas")
    competencia = models.ForeignKey(Competencia, on_delete=models.PROTECT)
    corte = models.ForeignKey(Corte, on_delete=models.PROTECT)
    tribunal = models.ForeignKey(Tribunal, on_delete=models.PROTECT)
    tipo = models.ForeignKey(TipoCausa, on_delete=models.PROTECT)

    rol = models.PositiveIntegerField()
    anio = models.PositiveIntegerField(default=datetime.now().year)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tipo.nombre} {self.rol}-{self.anio} ({self.tribunal.nombre})"
