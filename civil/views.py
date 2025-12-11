from django.shortcuts import render
from django.http import JsonResponse
from .models import Competencia, Corte, Tribunal, LibroTipo, Causa
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from civil.models import Causa  # ajusta el modelo real
import logging
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

def send_step(user_id, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "chat.progress",
            "message": message
        }
    )

logger = logging.getLogger('civil')

# Create your views here.

@require_GET
@login_required
def listar_causas(request):
    causas = Causa.objects.filter(usuario=request.user).order_by('-anio')
    data = [{
        "id": causa.id,
        "tipo": causa.tipo.nombre,
        "rol": causa.rol,
        "anio": causa.anio,
        "tribunal": causa.tribunal.nombre
    } for causa in causas]
    return JsonResponse({"causas": data})

@csrf_exempt
@require_POST
def procesar_causa(request):
    from causas_app.lib.utils import get_demanda

    data = json.loads(request.body)
    # Aquí puedes hacer el procesamiento real con la causa
    logger.info(f"Causa recibida: {data}")
    # Causa recibida: {'competencia': '1', 'corte': '1', 'tribunal': '1', 'tipo': '1', 'rol': 9, 'anio': 2023}
    competencia_id = data.get("competencia")
    corte_id = data.get("corte")
    tribunal_id = data.get("tribunal")
    conRolCausa = data.get("rol")
    conLibroTipo = data.get("tipo")
    conEraCausa = data.get("anio", "2025")
    send_step(request.user.id, "Procesando causa...")

    competencia = Competencia.objects.get(id=competencia_id).nombre
    corte = Corte.objects.get(id=corte_id).nombre
    tribunal = Tribunal.objects.get(id=tribunal_id).nombre
    tipo_causa = LibroTipo.objects.get(id=conLibroTipo).nombre if conLibroTipo else "C"
    logger.info(f"Procesando causa: {competencia}, {corte}, {tribunal}, {conRolCausa}, {tipo_causa}, {conEraCausa}")
    send_step(request.user.id, f"Competencia: {competencia}<br>Corte: {corte}<br>Tribunal: {tribunal}<br>Rol Causa: {conRolCausa}<br>Tipo Causa: {tipo_causa}<br>Era Causa: {conEraCausa}")

    get_demanda(request, competencia, corte, tribunal, conRolCausa, tipo_causa, conEraCausa)
    return JsonResponse({"status": "ok"})

@require_GET
def get_competencia_data(request):
    print("Obteniendo competencias")
    send_step(request.user.id, "Obteniendo competencias")
    competencias = list(Competencia.objects.values("id", "nombre"))
    print(f"Competencias obtenidas: {competencias}")
    return JsonResponse({"competencias": competencias})

@require_GET
def get_cortes_por_competencia(request, competencia_id=None):
    print(f"Obteniendo cortes para competencia_id: {competencia_id}")
    #competencia_id = request.GET.get("competencia_id", competencia_id)
    cortes = list(Corte.objects.filter(competencia_id=competencia_id).values("id", "nombre"))
    return JsonResponse({"cortes": cortes})

@require_GET
def get_tribunales_por_corte(request, corte_id=None):
    print(f"Obteniendo tribunales para corte_id: {corte_id}")
    tribunales = list(Tribunal.objects.filter(corte_id=corte_id).values("id", "nombre"))
    return JsonResponse({"tribunales": tribunales})

@require_GET
def get_tipos_por_competencia(request, competencia_id=None):
    print(f"Obteniendo tipos para competencia_id: {competencia_id}")
    tipos = list(LibroTipo.objects.filter(competencia_id=competencia_id).values("id", "nombre"))
    return JsonResponse({"tipos": tipos})
