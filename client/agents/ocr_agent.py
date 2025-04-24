from langchain_core.runnables import Runnable, RunnableConfig
from agents.schemas import State
from mistralai import Mistral
import os
import json
import base64
import requests
import time
import PyPDF2

class ocr_node:
    def __init__(self, api_mistral : str):
        self.api_mistral = api_mistral

    def __call__(self, state : State , config : RunnableConfig):
      
        print(state["messages"][-1])
        client = Mistral(api_key=self.api_mistral)

        if  state["messages"][-1].content.split(".")[1] == "png" or state["messages"][-1].content.split(".")[1] == "jpg":
            base64_image = self.encode_image(state["messages"][-1].content)
            ocr_response = client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{base64_image}" 
                }
            )
            print(ocr_response)
            return{
                 "markdown": "nice",
            }

        file_path= state["messages"][-1].content
        
        texto = self.es_pdf_textual(file_path)
        if len(texto) > 0:
            all_markdown = texto
            return {
            "messages": [("system", "Markdown combinado de todas las páginas extraído.")],
            "markdown": all_markdown,
            }

        uploaded_pdf = client.files.upload(
            file={
                "file_name": "upload_byagent.pdf",
                "content": open("files/"+file_path, "rb"),
            },
            purpose="ocr"
        )
        client.files.retrieve(file_id=uploaded_pdf.id)
        signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": signed_url.url,
            },
            include_image_base64=True
        )

        
        print("======================== Extraxted Markdown ============== ")
       
        all_markdown = "/n\n".join(page.markdown for page in ocr_response.pages)
        print(all_markdown)

        return {
            "messages": [("system", "Markdown combinado de todas las páginas extraído.")],
            "markdown": all_markdown,
        }

    def encode_image(self, image_path):
        """Encode the image to base64."""
        try:
            with open("files/"+image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            print(f"Error: The file {image_path} was not found.")
            return None
        except Exception as e:  # Added general exception handling
            print(f"Error: {e}")
            return None
        
    def es_pdf_textual(ruta_pdf: str) -> bool:
        """
        Devuelve True si el PDF tiene texto seleccionable.
        Devuelve False si no se encontró texto (probablemente escaneado).
        """
        if not os.path.isfile(ruta_pdf):
            print(f"El archivo {ruta_pdf} no existe.")
            return False

        try:
            with open(ruta_pdf, 'rb') as archivo:
                lector = PyPDF2.PdfReader(archivo)
                # Extraer texto de todas las páginas
                texto_total = ""
                for pagina in lector.pages:
                    texto = pagina.extract_text()
                    if texto:
                        texto_total += texto.strip()

                # Si encontramos algo de texto, asumimos que es un PDF con capa de texto
                
                return texto_total
        except Exception as e:
            print(f"Ocurrió un error al leer el PDF: {e}")
            return False


