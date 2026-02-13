import os
import logging, traceback
from azure.storage.fileshare import ShareServiceClient
from azure.core.exceptions import ResourceExistsError

logger = logging.getLogger('mcp_app')

def upload_file_to_azure_file_share(
    connection_string: str,
    share_name: str,
    local_file_path: str,
    remote_file_path: str,
):
    """
    Sube un archivo a Azure File Share.
    Si la carpeta remota no existe, la crea automáticamente.

    :param connection_string: Connection string del Storage Account
    :param share_name: Nombre del File Share
    :param local_file_path: Ruta local del archivo a subir
    :param remote_file_path: Ruta remota completa dentro del share (ej: carpeta1/carpeta2/archivo.txt)
    """

    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"No existe el archivo local: {local_file_path}")

    # Crear cliente del servicio
    service_client = ShareServiceClient.from_connection_string(connection_string)
    share_client = service_client.get_share_client(share_name)

    # Separar directorio y nombre archivo
    directory_path, file_name = os.path.split(remote_file_path)

    # Crear estructura de carpetas si no existe
    current_dir_client = share_client.get_directory_client("")

    if directory_path:
        for directory in directory_path.split("/"):
            current_dir_client = current_dir_client.get_subdirectory_client(directory)
            try:
                current_dir_client.create_directory()
            except ResourceExistsError:
                pass  # Si ya existe, continuar

    # Crear cliente de archivo
    file_client = current_dir_client.get_file_client(file_name)

    # Subir archivo
    with open(local_file_path, "rb") as data:
        file_size = os.path.getsize(local_file_path)
        file_client.create_file(file_size)
        file_client.upload_file(data)

    print(f"✅ Archivo subido correctamente a: {share_name}/{remote_file_path}")


if __name__ == "__main__":
    # Ejemplo de uso
    try:
        upload_file_to_azure_file_share(
            connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
            share_name=os.getenv("AZURE_FILE_SHARE_NAME"),
            local_file_path=os.path.join(os.getenv("SQLITE_LOCAL_PATH"), "2026-02-13", "demand_7.db"),
            remote_file_path="2026-02-13/demand_7.db"
        )
    except Exception as e:
        logger.error(f"Error al subir archivo a Azure File Share: {e}")
        traceback.print_exc()