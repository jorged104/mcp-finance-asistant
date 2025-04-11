import sys
import os
import PyPDF2

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
            print(texto_total)
            return len(texto_total) > 0
    except Exception as e:
        print(f"Ocurrió un error al leer el PDF: {e}")
        return False

def main(ruta_pdf: str):
    if es_pdf_textual(ruta_pdf):
        print("Este PDF contiene texto seleccionable. Se puede usar PyPDF2 u otra librería para extraerlo directamente.")
    else:
        print("Este PDF parece ser escaneado o sin capa de texto. Se recomienda usar OCR.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python script.py <ruta_al_pdf>")
        sys.exit(1)

    ruta_pdf = sys.argv[1]
    main(ruta_pdf)
