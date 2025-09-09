import requests
import json

with open("descargas_pjud.json", "r") as f:
    data = json.load(f)

cookies = data["cookies"]
detalle = data["detalle"]

def descargar_pdf(entry, index):
    if not entry["doc_url"] or not entry["dtaDoc"]:
        print(f"Fila {index} no tiene documento válido.")
        return

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(entry["doc_url"], data={"dtaDoc": entry["dtaDoc"]}, headers=headers, cookies=cookies)

    if response.status_code == 200:
        nombre = f"{entry['folio'].strip('[]') or 'doc'}_{index}.pdf"
        with open(nombre, "wb") as f:
            f.write(response.content)
        print(f"✅ Archivo descargado: {nombre}")
    else:
        print(f"❌ Error HTTP {response.status_code} al descargar fila {index}")

# Ejemplo: descargar todos los documentos
for i, item in enumerate(detalle):
    descargar_pdf(item, i)
