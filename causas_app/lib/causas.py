import os
import logging
import traceback
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

logger = logging.getLogger('causas_app')
MAX_RETRIES = 3

class ConsultaCausaException(Exception):
    pass

class ConsultaCausas:
    def __init__(
        self,
        browser_type="chrome",
        headless=False,
        download_dir="download",
        url="https://oficinajudicialvirtual.pjud.cl/indexN.php"
    ):
        self.browser_type = browser_type
        self.headless = headless
        self.download_dir = download_dir
        self.url = url
        self.browser = None
        self.logger = logger
        self.btn_xpath_consulta_causas = '/html/body/div[9]/div/section[1]/div/div[2]/div/div[3]/div/button'

        self.logger.info(f"ConsultaCausas initialized with browser_type: {self.browser_type}, headless: {self.headless}")

    def _prepare_download_dir(self):
        abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.download_dir)
        os.makedirs(abs_path, exist_ok=True)
        self.logger.info(f"Using download directory: {abs_path}")
        return abs_path

    def get_chrome_browser(self):
        try:
            download_path = self._prepare_download_dir()
            chrome_options = Options()
            
            chrome_prefs = {
                "download.default_directory": download_path,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True
            }
            chrome_options.add_experimental_option("prefs", chrome_prefs)

            if self.headless:
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")

            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            self.logger.info("Launching Chrome browser...")
            browser = webdriver.Chrome(options=chrome_options)
            browser.set_window_position(0, 0)

            return browser

        except Exception as e:
            self.logger.error(f"Failed to create Chrome browser: {e}")
            self.logger.debug(traceback.format_exc())
            return None

    def start_browser(self):
        try:
            if self.browser_type == "chrome":
                self.browser = self.get_chrome_browser()
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")

            if not self.url:
                raise ValueError("No URL specified to open.")
            
            self.browser.get(self.url)
            self.logger.info(f"Browser navigated to {self.url}")
            return self.browser

        except Exception as e:
            self.logger.error(f"Error starting browser: {e}")
            self.logger.debug(traceback.format_exc())
            return None

    def go_consulta_causas(self, competencia, conCorte, conTribunal, conTipoCausa, conRolCausa, conEraCausa):
        try:
            if not self.browser:
                raise RuntimeError("Browser is not initialized.")
            
            self.browser.implicitly_wait(5)
            btn = self.browser.find_element("xpath", self.btn_xpath_consulta_causas)
            btn.click()
            self.logger.info("Clicked on Consulta Causas button.")

            # Esperar y seleccionar competencia
            try:
                select_element = wait(self.browser, 15).until(
                    EC.presence_of_element_located((By.ID, "competencia"))
                )
                select = Select(select_element)
                opciones_disponibles = [opt.text.strip() for opt in select.options]

                if competencia not in opciones_disponibles:
                    self.logger.warning(f"La competencia '{competencia}' no está en las opciones disponibles: {opciones_disponibles}")
                    return False, False

                select.select_by_visible_text(competencia)
                self.logger.info(f"Selected competencia: {competencia}")

            except Exception as e:
                self.logger.error("No se pudo seleccionar la competencia.")
                self.logger.debug(traceback.format_exc())
                return False, False

            time.sleep(1)
            # Esperar y seleccionar corte
            try:
                select_element = wait(self.browser, 15).until(
                    EC.presence_of_element_located((By.ID, "conCorte"))
                )
                select = Select(select_element)
                opciones_disponibles = [opt.text.strip() for opt in select.options]

                if conCorte not in opciones_disponibles:
                    self.logger.warning(f"La Corte '{conCorte}' no está en las opciones disponibles: {opciones_disponibles}")
                    return False, False

                select.select_by_visible_text(conCorte)
                self.logger.info(f"Selected Corte: {conCorte}")

            except Exception as e:
                self.logger.error("No se pudo seleccionar la Corte.")
                self.logger.debug(traceback.format_exc())
                return False, False

            time.sleep(1)
            # Esperar y seleccionar Tribunal
            try:
                select_element = wait(self.browser, 15).until(
                    EC.presence_of_element_located((By.ID, "conTribunal"))
                )
                select = Select(select_element)
                opciones_disponibles = [opt.text.strip() for opt in select.options]

                if conTribunal not in opciones_disponibles:
                    self.logger.warning(f"El Tribunal '{conTribunal}' no está en las opciones disponibles: {opciones_disponibles}")
                    return False, False

                select.select_by_visible_text(conTribunal)
                self.logger.info(f"Selected Tribunal: {conTribunal}")

            except Exception as e:
                self.logger.error("No se pudo seleccionar la Tribunal.")
                self.logger.debug(traceback.format_exc())
                return False, False
            
            time.sleep(1)
            # Esperar y seleccionar TipoCausa
            try:
                select_element = wait(self.browser, 15).until(
                    EC.presence_of_element_located((By.ID, "conTipoCausa"))
                )
                select = Select(select_element)
                opciones_disponibles = [opt.text.strip() for opt in select.options]

                if conTipoCausa not in opciones_disponibles:
                    self.logger.warning(f"La TipoCausa '{conTipoCausa}' no está en las opciones disponibles: {opciones_disponibles}")
                    return False, False

                select.select_by_visible_text(conTipoCausa)
                self.logger.info(f"Selected TipoCausa: {conTipoCausa}")

            except Exception as e:
                self.logger.error("No se pudo seleccionar la TipoCausa.")
                self.logger.debug(traceback.format_exc())
                return False, False
            
            time.sleep(1)
            self.browser.find_element("id", 'conRolCausa').send_keys(conRolCausa)
            print(f'conEraCausa: {conEraCausa}')
            time.sleep(1)
            self.browser.find_element("id", 'conEraCausa').send_keys(conEraCausa)

            # btnConConsulta
            time.sleep(1)
            self.browser.find_element(By.ID, 'btnConConsulta').click()
            time.sleep(2)

            try:
                text = self.browser.find_element(By.XPATH, '/html/body/div[1]/div/div[2]/div[2]/div[1]/div/section/div[1]/div/div[2]/div[1]/div[4]/div/div/table/tbody/tr/td').text
                print(text)
                if 'No se han encontrado resultados' in text:
                    print('no tiene causas')
                    return True, False
            except Exception as e:
                pass
            

            return True, True
        
        except Exception as e:
            self.logger.error("Error en navegación a Consulta Causas.")
            self.logger.debug(traceback.format_exc())
            return False, False

    def go_consulta_new_rol(self, conRolCausa):
        try:

            time.sleep(1)
            self.browser.implicitly_wait(5)
            # clear conRolCausa
            self.browser.find_element("id", 'conRolCausa').clear()
            self.browser.find_element("id", 'conRolCausa').send_keys(conRolCausa)

            # btnConConsulta
            time.sleep(1)
            self.browser.find_element(By.ID, 'btnConConsulta').click()
            time.sleep(2)

            try:
                text = self.browser.find_element(By.XPATH, '/html/body/div[1]/div/div[2]/div[2]/div[1]/div/section/div[1]/div/div[2]/div[1]/div[4]/div/div/table/tbody/tr/td').text
                print(text)
                if 'No se han encontrado resultados' in text:
                    print('no tiene causas')
                    return True, False
            except Exception as e:
                pass
            
            return True, True
        
        except Exception as e:
            self.logger.error("Error en navegación a Consulta Causas.")
            self.logger.debug(traceback.format_exc())
            return False, False
        
    def goDetalleCausa(self):
        # /html/body/div[1]/div/div[2]/div[2]/div[1]/div/section/div[1]/div/div[2]/div[1]/div[4]/div/div/table/tbody/tr[1]/td[1]/a
        try:
            self.browser.implicitly_wait(5)
            # clear conRolCausa
            self.browser.find_element("xpath", '/html/body/div[1]/div/div[2]/div[2]/div[1]/div/section/div[1]/div/div[2]/div[1]/div[4]/div/div/table/tbody/tr[1]/td[1]/a').click()
            time.sleep(2)

            return True
        except Exception as e:
            self.logger.error("Error en navegación a Detalle Causa.")
            self.logger.debug(traceback.format_exc())
            return False
        
    def download_pdf(self, xpath):
        try:
            self.browser.implicitly_wait(5)
            self.browser.find_element("xpath", xpath).click()
            time.sleep(2)
            # Esperar a que el PDF se descargue
            # Aquí puedes agregar lógica para verificar si el PDF se ha descargado correctamente
            # get last file in download dir
            download_path = self._prepare_download_dir()
            files = os.listdir(download_path)
            files = [f for f in files if f.endswith('.pdf')]
            if files:
                last_file = max([os.path.join(download_path, f) for f in files], key=os.path.getctime)
                self.logger.info(f"PDF downloaded: {last_file}")
            else:
                self.logger.warning("No PDF files found in the download directory.")
                return False, None
            return True, last_file
        except Exception as e:
            self.logger.error("Error al descargar PDF.")
            self.logger.debug(traceback.format_exc())
            return False, None
        
    def close(self):
        try:
            if self.browser:
                self.browser.quit()
                self.browser = None
                self.logger.info("Browser closed successfully.")
            else:
                self.logger.warning("Browser was not active.")
        except Exception as e:
            self.logger.error(f"Error closing browser: {e}")
            self.logger.debug(traceback.format_exc())

    def iniciar_navegador(self, intentos=MAX_RETRIES):
        for i in range(intentos):
            browser = self.start_browser()
            if browser:
                return browser
            logging.warning(f"[{i+1}/{intentos}] Fallo al iniciar navegador. Reintentando en 3s...")
            time.sleep(3)
        raise ConsultaCausaException("No se pudo iniciar el navegador tras varios intentos")

    def navegar_consulta_causas(self, conRolCausa, conEraCausa, competencia, conCorte, conTribunal, conTipoCausa, max_reintentos=MAX_RETRIES):
        for i in range(max_reintentos):
            noerror, existe = self.go_consulta_causas(
                competencia=competencia, 
                conCorte=conCorte, 
                conTribunal=conTribunal,
                conTipoCausa=conTipoCausa,
                conRolCausa=conRolCausa, 
                conEraCausa=conEraCausa
            )
            if noerror:
                return existe
            logging.warning(f"[{i+1}/{max_reintentos}] Error navegando a Consulta Causas. Reintentando...")
            self.close()
            time.sleep(3)
            self.start_browser()
        raise ConsultaCausaException("No se pudo navegar a Consulta Causas tras varios intentos")

    def buscar_siguiente_existente(self, conRolCausa):
        while True:
            conRolCausa += 1
            noerror, existe = self.go_consulta_new_rol(conRolCausa=conRolCausa)
            if not noerror:
                logging.warning("Error al buscar nuevo rol, reiniciando navegador...")
                self.close()
                time.sleep(3)
                self.start_browser()
                continue
            if existe:
                break
        return conRolCausa
    
    def loadDetalleCausa(self, xpath):
        try:

            selenium_cookies = self.browser.get_cookies()
            self.cookies = {self.cookie['name']: self.cookie['value'] for self.cookie in selenium_cookies}
            self.logger.info(f"Cookies: {self.cookies}")

            data = []
            self.browser.implicitly_wait(5)
            table = self.browser.find_element("xpath", xpath)
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f'total rows: {len(rows)}')
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) > 0:
                    form_elements = cols[1].find_elements(By.TAG_NAME, 'form')
                    if form_elements:
                        form = form_elements[0]
                        action = form.get_attribute('action')
                        dta_input = form.find_element(By.NAME, 'dtaDoc')
                        dta_doc_value = dta_input.get_attribute('value')

                        doc_url = action if action.startswith("http") else f"https://oficinajudicialvirtual.pjud.cl{action}"
                    else:
                        doc_url = None
                        dta_doc_value = None
                        self.logger.warning(f"No se encontró formulario en fila con folio {cols[0].text}")

                    data.append({
                        'folio': cols[0].text,
                        'doc_url': doc_url,
                        'dtaDoc': dta_doc_value,
                        'anexo': cols[2].text,
                        'etapa': cols[3].text,
                        'tramite': cols[4].text,
                        'desctramite': cols[5].text,
                        'foja': cols[6].text,
                        'geo': cols[7].text
                    })


            self.logger.info("Detalle Causa loaded successfully.")
            return data
        except Exception as e:
            self.logger.error("Error loading Detalle Causa.")
            self.logger.error(traceback.format_exc())
            print(traceback.format_exc())
            return None

    def descargar_pdf(self, detalle, fila):

        import json

        with open("descargas_pjud.json", "w") as f:
            json.dump({
                "cookies": self.cookies,   # cookies es el dict que extrajiste de Selenium
                "detalle": detalle    # tu lista de documentos con doc_url y dtaDoc
            }, f, indent=4)


        entry = detalle[fila]
        if not entry['doc_url'] or not entry['dtaDoc']:
            print(f"No hay documento descargable en la fila {fila}")
            return

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = {'dtaDoc': entry['dtaDoc']}

        response = requests.post(entry['doc_url'], data=data, headers=headers, cookies=self.cookies)
        
        if response.status_code == 200:
            nombre_archivo = f"{entry['folio'].strip('[]')}_{fila}.pdf"
            with open(nombre_archivo, 'wb') as f:
                f.write(response.content)
            print(f"Archivo guardado: {nombre_archivo}")
        else:
            print(f"Error al descargar: {response.status_code}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    consulta = ConsultaCausas(
        browser_type="chrome", 
        headless=True, 
        download_dir="download", 
        url="https://oficinajudicialvirtual.pjud.cl/indexN.php"
    )

    conRolCausa = 3
    conEraCausa = 2025

    try:
        browser = consulta.iniciar_navegador()
        existe = consulta.navegar_consulta_causas(conRolCausa, conEraCausa)

        if not existe:
            conRolCausa = consulta.buscar_siguiente_existente(conRolCausa)

        consulta.goDetalleCausa()
        logger.info(f"Rol Causa encontrado: {conRolCausa}")
        
        #consulta.download_pdf('/html/body/div[1]/div/div[2]/div[2]/div[1]/div/section/div[2]/div/div/div[2]/div/div[1]/table[2]/tbody/tr/td[1]/form/a')
        #logger.info("Descarga del PDF iniciada.")

        table_detalle = consulta.loadDetalleCausa('/html/body/div[1]/div/div[2]/div[2]/div[1]/div/section/div[2]/div/div/div[2]/div/div[4]/div[1]/div/div/table')
        if table_detalle:
            logger.info("Tabla de detalle cargada correctamente.")
        else:
            logger.warning("No se pudo cargar la tabla de detalle.")

        #print("Detalle de la causa:")
        #for row in table_detalle:
        #    print(row)

        # Mostrar todas las filas con índice
        for idx, d in enumerate(table_detalle):
            print(f"{idx}: {d['folio']} - {d['tramite']}")

        # Pedir al usuario elegir
        fila = int(input("Ingrese el número de fila a descargar: "))
        consulta.descargar_pdf(table_detalle, fila)


        time.sleep(500)

    except ConsultaCausaException as e:
        logger.error(f"Error crítico: {e}")

    finally:
        consulta.close()

