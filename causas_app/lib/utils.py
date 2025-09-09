from causas_app.lib.causas import *
from causas_app.models import *
import logging
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import time
import traceback

# Configuración del logger
logger = logging.getLogger('causas_app')

def send_step(user_id, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "chat.progress",
            "message": message
        }
    )

def get_demanda(request, competencia, corte, tribunal, conRolCausa, conTipoCausa, conEraCausa):
    
    try:

        logger.info("Iniciando la función get_demanda.")
        logger.info(f"Competencia: {competencia}")
        logger.info(f"Corte: {corte}")
        logger.info(f"Tribunal: {tribunal}")
        logger.info(f"Rol Causa: {conRolCausa}")
        logger.info(f"Tipo Causa: {conTipoCausa}")
        logger.info(f"Era Causa: {conEraCausa}")

        if request.user.is_authenticated:
            send_step(request.user.id, "Iniciando la consulta de causas...")
        
        logger.info("Iniciando la consulta de causas...")

        consulta = ConsultaCausas(browser_type="chrome", headless=False, download_dir="download", url="https://oficinajudicialvirtual.pjud.cl/indexN.php")
        browser = consulta.iniciar_navegador()
        existe = consulta.navegar_consulta_causas(conRolCausa, conEraCausa, competencia, corte, tribunal, conTipoCausa)

        consulta.goDetalleCausa()
        logger.info(f"Rol Causa encontrado: {conRolCausa}")
        
        result, pdf_demanda = consulta.download_pdf('/html/body/div[1]/div/div[2]/div[2]/div[1]/div/section/div[2]/div/div/div[2]/div/div[1]/table[2]/tbody/tr/td[1]/form/a')
        logger.info(f'PDF descargado: {pdf_demanda}')
        if pdf_demanda:
            logger.info("PDF descargado correctamente.")
        else:
            logger.warning("No se pudo descargar el PDF.")

        table_detalle = consulta.loadDetalleCausa('/html/body/div[1]/div/div[2]/div[2]/div[1]/div/section/div[2]/div/div/div[2]/div/div[4]/div[1]/div/div/table')
        if table_detalle:
            logger.info("Tabla de detalle cargada correctamente.")
        else:
            logger.warning("No se pudo cargar la tabla de detalle.")

        # Aquí puedes agregar más lógica para procesar la tabla de detalle si es necesario
        response = {
            "status": "success",
            "message": "Consulta de causas finalizada.",
            "pdf_demanda": pdf_demanda,
            "data": table_detalle
        }
        return table_detalle
    
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        logger.error(traceback.format_exc())
        logger.info("Consulta de causas finalizada.")

    finally:
        if 'consulta' in locals():
            consulta.close()
        if 'browser' in locals():
            browser.quit()