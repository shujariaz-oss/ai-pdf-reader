import io
import fitz
from PIL import Image
import pytesseract

def extract_text_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    combined_text = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        native_text = page.get_text().strip()
        
        if len(native_text) >= 50:
            combined_text.append(native_text)
        else:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(image_data))
            
            ocr_text = pytesseract.image_to_string(image, lang="eng+hin+tam+ben")
            combined_text.append(ocr_text.strip())
            
    doc.close()
    return "\n\n--- Page Break ---\n\n".join(combined_text)
