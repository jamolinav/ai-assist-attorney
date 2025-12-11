from django.urls import path
from . import views

urlpatterns = [
    path('api/competencias/', views.get_competencia_data),
    path('api/cortes/<int:competencia_id>/', views.get_cortes_por_competencia),
    path('api/tribunales/<int:corte_id>/', views.get_tribunales_por_corte),
    path('api/tipos/<int:competencia_id>/', views.get_tipos_por_competencia),
    path('api/procesar_causa/', views.procesar_causa),
    path('api/listar_causas/', views.listar_causas),

]
