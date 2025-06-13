import os
import base64
import requests
import tempfile
import PyPDF2
from mistralai import Mistral
from langchain_core.runnables import RunnableConfig
from agents.schemas import State

class ocr_node:
    def __init__(self, api_mistral: str):
        self.api_mistral = api_mistral

    def __call__(self, state: State, config: RunnableConfig):
        client = Mistral(api_key=self.api_mistral)
        user_input = state["messages"][-1].content.strip()
        print(f"Archivo recibido: {user_input}")

        if user_input.startswith("http"):
            return self._procesar_url_remota(user_input, client)

        ext = user_input.lower().split(".")[-1]
        if ext in ["png", "jpg", "jpeg"]:
            return self._procesar_imagen_local(user_input, client)

        elif ext == "pdf":
            return self._procesar_pdf_local(user_input, client)

        else:
            return {"messages": [("system", f"Formato de archivo no soportado: {ext}")]}

    def _procesar_imagen_local(self, path, client):
        base64_image = self.encode_image(path)
        if not base64_image:
            return {"messages": [("system", "Error al procesar imagen local")]}
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
        )
        markdown = "\n\n".join(page.markdown for page in ocr_response.pages)
        return {"messages": [("system", "Markdown combinado de todas las páginas extraído.")], "markdown": markdown}

    def _procesar_pdf_local(self, path, client):
        texto = self.es_pdf_textual(path)
        if texto:
            return {"messages": [("system", "Markdown combinado de todas las páginas extraído.")], "markdown": texto}
        with open(path, "rb") as file_obj:
            uploaded_pdf = client.files.upload(file={"file_name": "upload.pdf", "content": file_obj}, purpose="ocr")
        signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "document_url", "document_url": signed_url.url},
            include_image_base64=True
        )
        markdown = "\n\n".join(page.markdown for page in ocr_response.pages)
        return {"messages": [("system", "Markdown combinado de todas las páginas extraído.")], "markdown": markdown}

    def _procesar_url_remota(self, url: str, client):
        ext = url.split("?")[0].lower().split(".")[-1]
        if ext in ["png", "jpg", "jpeg"]:
            ocr_response = client.ocr.process(
                model="mistral-ocr-latest",
                document={"type": "image_url", "image_url": url}
            )
            markdown = "\n\n".join(page.markdown for page in ocr_response.pages)
            return {"messages": [("system", "Markdown extraído de imagen remota.")], "markdown": markdown}

        elif ext == "pdf":
            try:
                response = requests.get(url)
                if response.status_code != 200:
                    raise Exception("Error al descargar el PDF remoto")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(response.content)
                    tmp_path = tmp_file.name

                return self._procesar_pdf_local(tmp_path, client)

            except Exception as e:
                return {"messages": [("system", f"Error procesando PDF remoto: {e}")]}
        else:
            return {"messages": [("system", f"Formato remoto no soportado: {ext}")]}
        
    def encode_image(self, path):
        try:
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            print(f"Error al codificar imagen: {e}")
            return None

    def es_pdf_textual(self, path: str) -> str:
        if not os.path.isfile(path):
            print(f"El archivo {path} no existe.")
            return ""
        try:
            with open(path, "rb") as archivo:
                lector = PyPDF2.PdfReader(archivo)
                texto_total = ""
                for pagina in lector.pages:
                    texto = pagina.extract_text()
                    if texto:
                        texto_total += texto.strip()
                return texto_total
        except Exception as e:
            print(f"Error al leer el PDF: {e}")
            return ""
