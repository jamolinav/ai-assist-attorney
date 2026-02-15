from civil.lib.causas import ConsultaCausas
from civil.models import Competencia, Corte, Tribunal, Causa, LibroTipo
import logging, traceback
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from typing import Dict, Any, List
from pjud.celeryy import app
from datetime import datetime, timedelta
import os
from pathlib import Path
from chatbot.services.progress import new_progress, set_state, get_state

logger = logging.getLogger('mcp_app')

def send_step(user_id, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "chat.progress",
            "message": message
        }
    )

def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the get_demanda function with the provided parameters.
    
    Args:
        params (dict): A dictionary containing the parameters for the get_demanda function.
    """
    # Call the get_demanda function with the provided parameters

    print("Starting get_demanda execution")
    
    try:

        logger.info("Iniciando la función get_demanda.")
        if "RIT" not in arguments or "Competencia" not in arguments or "Corte" not in arguments or "Tribunal" not in arguments:
            error_msg = "Faltan parámetros obligatorios: RIT, Competencia, Corte, Tribunal"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        RIT = arguments.get("RIT") # formato "C-1234-2020"
        conTipoLibro = RIT[0]
        conRolCausa = RIT[2:-5]
        conEraCausa = RIT[-4:]
        conCorte = arguments.get("Corte")
        conTribunal = arguments.get("Tribunal")
        conCompetencia = arguments.get("Competencia", "Civil")
        logger.info(f"Parámetros recibidos: RIT={RIT}, Competencia={conCompetencia}, Corte={conCorte}, Tribunal={conTribunal}")
        print(f"Parámetros recibidos: RIT={RIT}, Competencia={conCompetencia}, Corte={conCorte}, Tribunal={conTribunal}")
        logger.info(f"Rol Causa: {conRolCausa}")
        logger.info(f"Tipo Causa: {conTipoLibro}")
        logger.info(f"Era Causa: {conEraCausa}")
        competencia = Competencia.objects.get(id=conCompetencia)
        corte = Corte.objects.get(id=conCorte)
        tribunal = Tribunal.objects.get(id=conTribunal)
        tipoLibro = LibroTipo.objects.get(competencia=competencia, nombre__startswith=conTipoLibro)
        strCompetencia = competencia.nombre
        strCorte = corte.nombre
        strTribunal = tribunal.nombre

        progress_key = arguments.get("progress_key", None)

        print("Parametros procesados: conRolCausa =", conRolCausa, ", conEraCausa =", conEraCausa, ", conCompetencia =", strCompetencia, ", conCorte =", strCorte, ", conTribunal =", strTribunal, ", conTipoLibro =", conTipoLibro)
       #if arguments.get("user_id"):
       #     send_step(arguments["user_id"], "Iniciando la consulta de causas...")
        logger.info("Iniciando la consulta de causas...")
        causa = Causa.objects.filter(competencia=competencia, corte=corte, tribunal=tribunal, tipo=tipoLibro, rol=conRolCausa, anio=conEraCausa).first()
        # causa updated within the last 24 hours
        if causa is not None:
            if causa.status == "ready" and causa.updated_at >= (datetime.now().astimezone() - timedelta(hours=24)):
                logger.info(f"Causa {RIT} procesada recientemente. lista para procesar consultas.")
                print(f"Causa {RIT} procesada recientemente. lista para procesar consultas.")
                return {
                    "causa_id": causa.id,
                    "status": "success",
                    "message": "Causa procesada recientemente. Disponible para procesar consultas.",
                    "updated_at": causa.updated_at.isoformat(),
                }
            if causa.status == "processing" and causa.updated_at >= (datetime.now().astimezone() - timedelta(minutes=1)):
                logger.info(f"Causa {RIT} está en proceso actualmente. Por favor, intente más tarde.")
                print(f"Causa {RIT} está en proceso actualmente. Por favor, intente más tarde.")
                return {
                    "causa_id": causa.id,
                    "status": "processing",
                    "message": "Causa está en proceso actualmente. Por favor, espera un momento.",
                    "updated_at": causa.updated_at.isoformat(),
                }
            if causa.status == "error":
                logger.info(f"Causa {RIT} tuvo un error en el procesamiento anterior. Reintentando...")
                print(f"Causa {RIT} tuvo un error en el procesamiento anterior. Reintentando...")
                causa.status = "pending"
                causa.save()
                return {
                    "causa_id": causa.id,
                    "status": "processing",
                    "message": "Causa tuvo un error en el procesamiento anterior. Reintentando...",
                    "updated_at": causa.updated_at.isoformat(),
                }
            if causa.status == "pending" and causa.updated_at >= (datetime.now().astimezone() - timedelta(minutes=1)):
                logger.info(f"Causa {RIT} está pendiente de procesamiento. Por favor, intente más tarde.")
                print(f"Causa {RIT} está pendiente de procesamiento. Por favor, intente más tarde.")
                return {
                    "causa_id": causa.id,
                    "status": "processing",
                    "message": "Causa está pendiente de procesamiento. Por favor, espera un momento.",
                    "updated_at": causa.updated_at.isoformat(),
                }
            # continue to process if older than 1 minute
            logger.info(f"Causa {RIT} encontrada en la base de datos. Procediendo a reintentar la descarga de datos.")
            print(f"Causa {RIT} encontrada en la base de datos. Procediendo a reintentar la descarga de datos.")

        else:
            logger.info(f"Causa {RIT} no encontrada en la base de datos. Procediendo a extraer toda la información desde el Poder Judicial.")
            print(f"Causa {RIT} no encontrada en la base de datos. Procediendo a extraer toda la información desde el Poder Judicial.")
            causa = Causa.objects.create(
                competencia=competencia,
                corte=corte,
                tribunal=tribunal,
                tipo=tipoLibro,
                rol=conRolCausa,
                anio=conEraCausa,
                titulo=f"Causa {RIT}",
                pdf_dir="",
                sqlite_path="",
                status="pending",
                created_by=None,
            )

            datos_causa = {
                "competencia_id": competencia.id,
                "corte_id": corte.id,
                "tribunal_id": tribunal.id,
                "tipo_id": tipoLibro.id,
                "rol": conRolCausa,
                "anio": conEraCausa,
                "titulo": f"Causa {RIT}",
            }
        
        # Preparar el destino del SQLite
        sqlite_path = Path(os.getenv("SQLITE_PATH"))
        date_yyyymmdd = datetime.now().strftime("%Y-%m-%d") # create directory per day
        sqlite_path = sqlite_path / date_yyyymmdd
        if not sqlite_path.exists():
            logger.warning(f"El directorio {sqlite_path} no existe")
        else:
            sqlite_path.mkdir(parents=True, exist_ok=True)
        db_path = sqlite_path / f"demand_{causa.id}.db"

        pdf_dir = Path(os.getenv("PDFS_PATH"))
        pdf_dir = pdf_dir / date_yyyymmdd / f"demand_{causa.id}"
        if not pdf_dir.exists():
            logger.warning(f"El directorio {pdf_dir} no existe")
        else:
            pdf_dir.mkdir(parents=True, exist_ok=True)

        causa.pdf_dir = f'/{date_yyyymmdd}/demand_{causa.id}'
        causa.sqlite_path = f'/{date_yyyymmdd}/demand_{causa.id}.db'
        causa.status = "pending"
        causa.save(update_fields=["pdf_dir", "sqlite_path", "status"])

        task_id = f'get_demanda_{RIT}'
        # exec by celery -A pjud worker -Q pjud -l info
        get_demanda.apply_async(task_id=task_id, queue='pjud', kwargs={
                                                                            "task_id": task_id,
                                                                            "causa_id": causa.id,
                                                                            "user_id": arguments.get("user_id"),
                                                                            "data": datos_causa,
                                                                            "progress_key": progress_key,
                                                                        })
        
        logger.info(f"Tarea get_demanda {task_id} iniciada para RIT {RIT}")
        print(f"Tarea get_demanda {task_id} iniciada para RIT {RIT}")
        return {"status": "processing", "message": "Iniciando consulta de causa, descargando datos..."}
    
    except Exception as e:
        logger.error(f"Error en la ejecución de get_demanda: {e}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}

@app.task
def update_demanda(task_id: str, data: Dict[str, Any], status: str) -> Dict[str, Any]:
    try:
        logger.info(f"Actualizando causa_id {data.get('causa_id')} con status {status}")
        causa = Causa.objects.get(competencia_id=data["competencia_id"], corte_id=data["corte_id"], tribunal_id=data["tribunal_id"], tipo_id=data["tipo_id"], rol=data["rol"], anio=data["anio"])
        causa.status = status
        if 'pdf_dir' in data:
            causa.pdf_dir = data['pdf_dir']
        if 'sqlite_path' in data:
            causa.sqlite_path = data['sqlite_path']
        causa.save(update_fields=["status", "pdf_dir", "sqlite_path"])
        logger.info(f"Causa {causa.id} actualizada a status {status}, pdf_dir {causa.pdf_dir}, sqlite_path {causa.sqlite_path}")
        return {"status": "success", "message": f"Causa {causa.id} actualizada a status {status}"}
    except Exception as e:
        logger.error(f"Error al actualizar causa: {e}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}

@app.task
def get_demanda(task_id: str, causa_id: int, user_id: int = None, data: Dict[str, Any] = {}, progress_key: str = None) -> Dict[str, Any]:

    try:
        logger.info(f"Inicio de la tarea get_demanda {task_id} para causa_id {causa_id}, user_id {user_id}")
        print(f"Inicio de la tarea get_demanda {task_id} para causa_id {causa_id}, user_id {user_id}")

        if Causa.objects.filter(competencia_id=data["competencia_id"], corte_id=data["corte_id"], tribunal_id=data["tribunal_id"], tipo_id=data["tipo_id"], rol=data["rol"], anio=data["anio"]).exists():
            causa = Causa.objects.get(competencia_id=data["competencia_id"], corte_id=data["corte_id"], tribunal_id=data["tribunal_id"], tipo_id=data["tipo_id"], rol=data["rol"], anio=data["anio"])
        else:
            causa = Causa.objects.create(
                competencia_id=data["competencia_id"],
                corte_id=data["corte_id"],
                tribunal_id=data["tribunal_id"],
                tipo_id=data["tipo_id"],
                rol=data["rol"],
                anio=data["anio"],
                titulo=data["titulo"],
                pdf_dir=f'/{datetime.now().strftime("%Y-%m-%d")}/demand_{causa_id}',
                sqlite_path=f'/{datetime.now().strftime("%Y-%m-%d")}/demand_{causa_id}.db',
                status="processing",
                created_by_id=user_id,
            )
        
        update_demanda.apply_async(task_id=f"update_demanda_{causa.id}", queue='pjud_azure', kwargs={
            "task_id": f"update_demanda_{causa.id}",
            "data": data,
            "status": "processing"
        })

        # 1) Crear progreso
        if progress_key:
            logger.info(f"Created progress tracker with key: {progress_key}")
            print(f"Created progress tracker with key: {progress_key}")
            set_state.apply_async(task_id=f"set_state_gathering_context_{causa.id}", queue='pjud_azure', kwargs={"key": progress_key, "state": "gathering_context", "extra": {"message": "Iniciando consulta de causa..."}})

        RIT = f"{causa.tipo.nombre[0]}-{str(causa.rol).zfill(4)}-{str(causa.anio)}"
        conTipoLibro = causa.tipo.nombre[0]
        conRolCausa = str(causa.rol).zfill(4)
        conEraCausa = str(causa.anio)
        strCompetencia = causa.competencia.nombre
        strCorte = causa.corte.nombre
        strTribunal = causa.tribunal.nombre
        logger.info(f"Parámetros para la tarea: RIT={RIT}, Competencia={strCompetencia}, Corte={strCorte}, Tribunal={strTribunal}")
        print(f"Parámetros para la tarea: RIT={RIT}, Competencia={strCompetencia}, Corte={strCorte}, Tribunal={strTribunal}")

        # Preparar el destino del SQLite
        download_dir = Path(os.getenv("PDFS_LOCAL_PATH")) / datetime.now().strftime("%Y-%m-%d") / f"demand_{causa.id}"
        download_dir.mkdir(parents=True, exist_ok=True)
    
        consulta = ConsultaCausas(browser_type="chrome", headless=False, 
                                  download_dir=str(download_dir), url="https://oficinajudicialvirtual.pjud.cl/indexN.php")
        logger.info("Navegador iniciado.")
        consulta.iniciar_navegador()
        existe = consulta.navegar_consulta_causas(conRolCausa, conEraCausa, strCompetencia, strCorte, strTribunal, conTipoLibro, max_reintentos=3)
        if not existe:

            consulta.close()
            
            logger.info(f"La causa con RIT {RIT} no existe.")
            print(f"La causa con RIT {RIT} no existe.")

            causa.status = "no_pjud_info_available_yet"
            causa.save(update_fields=["status"])

            if progress_key:
                set_state.apply_async(task_id=f"set_state_no_info_{causa.id}", queue='pjud_azure', kwargs={"key": progress_key, "state": "done", "extra": {"message": f"Causa con RIT {RIT} no encontrada en el Poder Judicial. Se marcará para reintento futuro."}})

            return {
                "status": "not_found",
                "message": f"La causa con RIT {RIT} no existe.",
            }

        consulta.goDetalleCausa()
        logger.info(f"Rol Causa encontrado: {conRolCausa}")
        
        result, pdf_demanda = consulta.download_pdf('/html/body/div[1]/div/div[2]/div[2]/div[1]/div/section/div[2]/div/div/div[2]/div/div[1]/table[2]/tbody/tr/td[1]/form/a', 'demanda.pdf')
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

        # Mostrar todas las filas con índice
        for idx, d in enumerate(table_detalle):
            print(f"{idx}: {d['folio']} - {d['tramite']}")
            consulta.descargar_pdf(table_detalle, idx, download_dir)

            if progress_key:
                set_state.apply_async(task_id=f"set_state_obteniendo_demanda_{causa.id}_{idx}", queue='pjud_azure', kwargs={"key": progress_key, "state": "obteniendo_demanda", "extra": {"message": f"Descargando trámite {d['tramite']} (folio {d['folio']})"}})

        consulta.close()
        logger.info("Navegador cerrado.")   
        print("Navegador cerrado.")

        from civil.lib.ingest_demand import ingest_demand
        options = {
            "demand_id": causa.id,
            "title": f"Causa {RIT}",
            "pdf_dir": str(download_dir),
            "create_if_missing": True,
            "created_by": user_id,
            "chunk_size": 1200,
            "overlap": 150,
            "batch": 64,
        }

        ingest_demand(None, **options)

        # upload sqlite to azure
        from mcp_app.lib.azure_utils import upload_file_to_azure_file_share

        date_yyyymmdd = datetime.now().strftime("%Y-%m-%d") # create directory per day

        local_db_path = Path(os.getenv("SQLITE_LOCAL_PATH")) / date_yyyymmdd / f"demand_{causa.id}.db"
        
        try:
            logger.info(f"Subiendo archivo a Azure File Share: {local_db_path}")
            upload_file_to_azure_file_share(
                connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
                share_name=os.getenv("AZURE_FILE_SHARE_NAME"),
                local_file_path=local_db_path,
                remote_file_path=f"{date_yyyymmdd}/demand_{causa.id}.db"
            )
        except Exception as e:
            logger.error(f"Error al subir archivo a Azure File Share: {e}")
            traceback.print_exc()

        logger.info(f"Tarea get_demanda {task_id} completada para RIT {RIT}. Actualizando estado a 'ready'.")

        # get causa again to get updated_at
        causa.refresh_from_db()
        data['pdf_dir'] = f'{causa.pdf_dir}'
        data['sqlite_path'] = f'{causa.sqlite_path}'
        update_demanda.apply_async(task_id=f"update_demanda_{causa.id}", queue='pjud_azure', kwargs={
            "task_id": f"update_demanda_{causa.id}",
            "data": data,
            "status": "ready"
        })

        if progress_key:
            set_state.apply_async(task_id=f"set_state_ready_{causa.id}", queue='pjud_azure', kwargs={"key": progress_key, "state": "done", "extra": {"message": f"Causa con RIT {RIT} procesada correctamente"}})

        logger.info(f"Tarea get_demanda {task_id} para RIT {RIT} actualizada a 'ready'.")
 
        return {
            "status": "success",
            "message": "Causa procesada correctamente."
        }
    
    except Exception as e:
        logger.error(f"Error en la tarea get_demanda {task_id} para RIT {RIT}: {e}")
        logger.error(traceback.format_exc())
        if progress_key:
            set_state.apply_async(task_id=f"set_state_error_{causa.id}", queue='pjud_azure', kwargs={"key": progress_key, "state": "error", "extra": {"message": str(e)}})
        return {
            "status": "error",
            "message": str(e)
        }
