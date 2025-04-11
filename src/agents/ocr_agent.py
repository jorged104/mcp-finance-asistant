from langchain_core.runnables import Runnable, RunnableConfig
from agents.schemas import State
from mistralai import Mistral
import os
import json
import base64
import requests
import time
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

    def ocr_image(self, image_base64):

        client = Mistral(api_key=self.api_mistral)
        ocr_response = client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "image_url",
                    "image_url": f"{image_base64}" 
                }
            )
        print("extrating image result")
        str_markdown = "\n\n".join(page.markdown for page in ocr_response.pages)
        print(str_markdown)
        return 

    def get_combined_markdown(self , ocr_response) -> str:
        markdowns: list[str] = []
        # Extract images from page
        for page in ocr_response.pages:
            image_data = {}
            for img in page.images:
                print("Image ID:", img.id)
                time.sleep(1)  # Rate limit
                image_data[img.id] = self.ocr_image(img.image_base64)
            # Replace image placeholders with actual images
            markdowns.append(self.replace_images_in_markdown(page.markdown, image_data))

        return "\n\n".join(markdowns)

    def replace_images_in_markdown(self, markdown_str: str, images_dict: dict) -> str:
        """
        Replace image placeholders in markdown with base64-encoded images.

        Args:
            markdown_str: Markdown text containing image placeholders
            images_dict: Dictionary mapping image IDs to base64 strings

        Returns:
            Markdown text with images replaced by base64 data
        """
        for img_name, base64_str in images_dict.items():
            markdown_str = markdown_str.replace(
                f"![{img_name}]({img_name})", f"![{img_name}]({base64_str})"
            )
        return markdown_str

