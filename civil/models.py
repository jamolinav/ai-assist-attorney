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

class LibroTipo(models.Model):
    nombre = models.CharField(max_length=100)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE, related_name="tipos")

    def __str__(self):
        return self.nombre

class Causa(models.Model):
    STATUS_CHOICES = [
        ("pending", "pending"),
        ("processing", "processing"),
        ("ready", "ready"),
        ("error", "error"),
    ]
    usuarios = models.ManyToManyField(User, related_name="causas")
    competencia = models.ForeignKey(Competencia, on_delete=models.PROTECT)
    corte = models.ForeignKey(Corte, on_delete=models.PROTECT)
    tribunal = models.ForeignKey(Tribunal, on_delete=models.PROTECT)
    tipo = models.ForeignKey(LibroTipo, on_delete=models.PROTECT)

    rol = models.PositiveIntegerField()
    anio = models.PositiveIntegerField(default=datetime.now().year)

    titulo = models.CharField(max_length=255)

    pdf_dir = models.CharField(max_length=2000)  # location of PDFs of the demand
    sqlite_path = models.CharField(max_length=2000)  # path to per-demand SQLite
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["competencia", "corte", "tribunal", "tipo", "rol", "anio"]),
        ]

    def __str__(self):
        return f"{self.id} - {self.rol}-{self.anio} ({self.tribunal.nombre})"
    