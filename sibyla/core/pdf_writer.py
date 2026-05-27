"""
Escritor de PDF via ReportLab.

Recebe a mesma lista de páginas que text_writer:
  paginas: list[dict]  — cada item:
    {
      "num":     int,
      "blocos":  list[{texto, tamanho, negrito, italico, x0, y_top, y_bot}],
      "imagens": list[{bytes, y_top}]
    }
"""
from __future__ import annotations

import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    PageBreak, HRFlowable,
)
from reportlab.platypus.flowables import KeepTogether

_PAGE_W, _PAGE_H = A4
_MARGIN = 56          # ~2 cm in points (1 pt = 1 ReportLab unit)
_MAX_IMG_W = _PAGE_W - 2 * _MARGIN

# ── Estilos ───────────────────────────────────────────────────────────────────

def _build_styles() -> dict:
    base = getSampleStyleSheet()

    normal = ParagraphStyle(
        "sibyla_normal",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    h1 = ParagraphStyle(
        "sibyla_h1",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=24,
        spaceBefore=10,
        spaceAfter=6,
        textColor=HexColor("#1a1a2e"),
    )
    h2 = ParagraphStyle(
        "sibyla_h2",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=20,
        spaceBefore=8,
        spaceAfter=4,
        textColor=HexColor("#16213e"),
    )
    h3 = ParagraphStyle(
        "sibyla_h3",
        parent=base["Normal"],
        fontName="Helvetica-BoldOblique",
        fontSize=12,
        leading=17,
        spaceBefore=6,
        spaceAfter=4,
    )
    page_header = ParagraphStyle(
        "sibyla_page_header",
        parent=base["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=HexColor("#888888"),
        alignment=1,  # CENTER
        spaceAfter=4,
    )
    return {
        "normal": normal,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "page_header": page_header,
    }


def _estilo_bloco(bloco: dict, estilos: dict) -> ParagraphStyle:
    """Escolhe o estilo ReportLab adequado para o bloco."""
    tamanho = bloco.get("tamanho", 11)
    negrito = bloco.get("negrito", False)
    italico = bloco.get("italico", False)
    texto   = bloco.get("texto", "")

    if tamanho >= 22 and len(texto) < 120:
        return estilos["h1"]
    if tamanho >= 16 and len(texto) < 120:
        return estilos["h2"]
    if tamanho >= 13 and len(texto) < 120:
        return estilos["h3"]

    # Cria variação inline se necessário
    if negrito and italico:
        return ParagraphStyle(
            "_bi", parent=estilos["normal"], fontName="Helvetica-BoldOblique")
    if negrito:
        return ParagraphStyle(
            "_b", parent=estilos["normal"], fontName="Helvetica-Bold")
    if italico:
        return ParagraphStyle(
            "_i", parent=estilos["normal"], fontName="Helvetica-Oblique")
    return estilos["normal"]


_MAX_IMG_H = _PAGE_H - 2 * _MARGIN - 20  # margem de segurança


def _img_flowable(img_bytes: bytes) -> RLImage | None:
    """Converte bytes PNG para flowable ReportLab com largura e altura máximas."""
    try:
        from PIL import Image as PILImage
        pil = PILImage.open(io.BytesIO(img_bytes))
        w, h = pil.size
        ratio = min(_MAX_IMG_W / w, _MAX_IMG_H / h, 1.0)
        rl_img = RLImage(io.BytesIO(img_bytes),
                         width=w * ratio, height=h * ratio)
        rl_img.hAlign = "CENTER"
        return rl_img
    except Exception:
        return None


# ── Escritor principal ────────────────────────────────────────────────────────

# Mapeamento de fontes do usuário para as built-in do ReportLab
# Cada entrada: (normal, bold, italic, bold-italic)
_RL_FONT_MAP: dict[str, tuple[str, str, str, str]] = {
    "Arial":           ("Helvetica",   "Helvetica-Bold",        "Helvetica-Oblique",       "Helvetica-BoldOblique"),
    "Helvetica":       ("Helvetica",   "Helvetica-Bold",        "Helvetica-Oblique",       "Helvetica-BoldOblique"),
    "Verdana":         ("Helvetica",   "Helvetica-Bold",        "Helvetica-Oblique",       "Helvetica-BoldOblique"),
    "Calibri":         ("Helvetica",   "Helvetica-Bold",        "Helvetica-Oblique",       "Helvetica-BoldOblique"),
    "Tahoma":          ("Helvetica",   "Helvetica-Bold",        "Helvetica-Oblique",       "Helvetica-BoldOblique"),
    "Times New Roman": ("Times-Roman", "Times-Bold",            "Times-Italic",            "Times-BoldItalic"),
    "Georgia":         ("Times-Roman", "Times-Bold",            "Times-Italic",            "Times-BoldItalic"),
    "Garamond":        ("Times-Roman", "Times-Bold",            "Times-Italic",            "Times-BoldItalic"),
    "Courier New":     ("Courier",     "Courier-Bold",          "Courier-Oblique",         "Courier-BoldOblique"),
}

_RL_ALIGN = {
    "left":    0,
    "center":  1,
    "right":   2,
    "justify": 4,
}


def salvar_pdf(paginas: list[dict], caminho: str,
               alinhamento: str = "original",
               tamanho_fonte: int | None = None,
               fonte: str | None = None) -> None:
    """Salva tradução como PDF usando ReportLab."""
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)

    doc = SimpleDocTemplate(
        caminho,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN,
        bottomMargin=_MARGIN,
        title="Tradução SibylaTranslate",
    )

    estilos = _build_styles()

    # Resolve família de fontes para ReportLab
    rl_fonts: tuple[str, str, str, str] | None = None
    if fonte and fonte in _RL_FONT_MAP:
        rl_fonts = _RL_FONT_MAP[fonte]

    # Aplica alinhamento e/ou fonte base nos estilos
    if alinhamento in _RL_ALIGN or rl_fonts:
        align_val = _RL_ALIGN.get(alinhamento)
        for key, estilo in estilos.items():
            if key == "page_header":
                continue
            kw: dict = {}
            if align_val is not None:
                kw["alignment"] = align_val
            if rl_fonts:
                kw["fontName"] = rl_fonts[0]  # normal por defeito
            estilos[key] = ParagraphStyle(estilo.name + "_custom", parent=estilo, **kw)

    story: list = []

    for pag in paginas:
        num     = pag["num"]
        blocos  = pag["blocos"]
        imagens = pag.get("imagens", [])

        if num > 1:
            story.append(PageBreak())

        # Intercala blocos e imagens por y_top
        itens: list[tuple[float, str, dict]] = []
        for b in blocos:
            itens.append((b["y_top"], "bloco", b))
        for img in imagens:
            itens.append((img["y_top"], "img", img))
        itens.sort(key=lambda x: x[0])

        for _, tipo, dado in itens:
            if tipo == "img":
                fl = _img_flowable(dado["bytes"])
                if fl:
                    story.append(Spacer(1, 6))
                    story.append(fl)
                    story.append(Spacer(1, 6))
            else:
                texto = dado.get("texto", "").strip()
                if not texto:
                    story.append(Spacer(1, 4))
                    continue
                # Escapa caracteres especiais XML do ReportLab
                texto_esc = (texto
                             .replace("&", "&amp;")
                             .replace("<", "&lt;")
                             .replace(">", "&gt;"))
                estilo = _estilo_bloco(dado, estilos)
                overrides: dict = {}
                if tamanho_fonte:
                    overrides["fontSize"] = tamanho_fonte
                    overrides["leading"] = tamanho_fonte * 1.4
                if rl_fonts:
                    negrito = dado.get("negrito", False)
                    italico = dado.get("italico", False)
                    if negrito and italico:
                        overrides["fontName"] = rl_fonts[3]
                    elif negrito:
                        overrides["fontName"] = rl_fonts[1]
                    elif italico:
                        overrides["fontName"] = rl_fonts[2]
                    else:
                        overrides["fontName"] = rl_fonts[0]
                if overrides:
                    estilo = ParagraphStyle(estilo.name + "_ov", parent=estilo, **overrides)
                story.append(Paragraph(texto_esc, estilo))

    doc.build(story)
