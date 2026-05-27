import io
import fitz  # PyMuPDF
from PIL import Image

IMG_DPI   = 180
MAX_IMG_W = 5.5  # max image width in Word output (inches)


def pagina_para_imagem_bytes(fitz_doc, page_index: int) -> bytes:
    """Renders a full page as PNG and returns bytes."""
    page = fitz_doc[page_index]
    mat = fitz.Matrix(IMG_DPI / 72, IMG_DPI / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")


def para_png_bytes(raw_bytes: bytes, colorspace: str = "") -> bytes | None:
    """Converts any image (CMYK, palette, etc.) to RGB PNG via Pillow."""
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode in ("CMYK", "P", "L", "LA"):
            img = img.convert("RGB")
        elif img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None
