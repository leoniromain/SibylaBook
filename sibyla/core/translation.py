from __future__ import annotations
import re
import time
from deep_translator import GoogleTranslator

SOURCE_LANG = "en"
TARGET_LANG = "pt"
CHUNK_SIZE  = 4500   # caracteres por chunk (limite Google Translate: 5000)
DELAY_SEC   = 0.5    # pausa entre requisições


def _make_translator(src: str, dst: str, engine: str = "google", api_key: str | None = None):
    if engine == "deepl":
        from deep_translator import DeeplTranslator
        return DeeplTranslator(api_key=api_key or "", source=src, target=dst)
    if engine == "libretranslate":
        from deep_translator import LibreTranslateTranslator
        return LibreTranslateTranslator(source=src, target=dst, api_key=api_key or "")
    return GoogleTranslator(source=src, target=dst)

# Palavras/expressões que NUNCA devem ser traduzidas (nomes próprios fixos)
NOMES_PROTEGIDOS: set[str] = set()

# Padrão: sequências de palavras em Title Case (2+ palavras, 2+ letras cada)
_RE_NOME_PROPRIO = re.compile(
    r'\b([A-Z][a-záàâãéêíóôõúüçñ\'\-]{1,}(?:\s+[A-Z][a-záàâãéêíóôõúüçñ\'\-]{1,})+)\b'
)


def _proteger_nomes(texto: str) -> tuple[str, dict]:
    """
    Substitui nomes próprios detectados por placeholders únicos (§0§, §1§…).
    Retorna (texto_com_placeholders, mapa_de_restauração).
    """
    mapa: dict = {}
    idx = [0]

    def substituir(match):
        nome = match.group(0)
        placeholder = f"\u00a7{idx[0]}\u00a7"
        mapa[placeholder] = nome
        idx[0] += 1
        return placeholder

    for nome in sorted(NOMES_PROTEGIDOS, key=len, reverse=True):
        texto = re.sub(re.escape(nome), substituir, texto, flags=re.IGNORECASE)

    texto = _RE_NOME_PROPRIO.sub(substituir, texto)
    return texto, mapa


def _restaurar_nomes(texto: str, mapa: dict) -> str:
    for placeholder, nome in mapa.items():
        texto = texto.replace(placeholder, nome)
    return texto


def traduzir_texto(texto: str,
                   src: str = SOURCE_LANG,
                   dst: str = TARGET_LANG,
                   engine: str = "google",
                   api_key: str | None = None) -> str:
    """Traduz texto preservando nomes próprios e quebras de parágrafo."""
    if not texto.strip():
        return texto

    texto_protegido, mapa = _proteger_nomes(texto)
    translator = _make_translator(src, dst, engine, api_key)
    paragrafos = texto_protegido.split("\n")
    resultado = []
    buffer = ""

    for para in paragrafos:
        if len(buffer) + len(para) + 1 > CHUNK_SIZE:
            if buffer.strip():
                try:
                    resultado.extend((translator.translate(buffer) or buffer).split("\n"))
                    time.sleep(DELAY_SEC)
                except Exception as e:
                    print(f"\n  [AVISO] {e} — mantendo original.")
                    resultado.extend(buffer.split("\n"))
            buffer = para
        else:
            buffer = (buffer + "\n" + para) if buffer else para

    if buffer.strip():
        try:
            resultado.extend((translator.translate(buffer) or buffer).split("\n"))
            time.sleep(DELAY_SEC)
        except Exception as e:
            print(f"\n  [AVISO] {e} — mantendo original.")
            resultado.extend(buffer.split("\n"))

    return _restaurar_nomes("\n".join(resultado), mapa)


# Marcador que separa blocos no modo página-inteira.
# Escolhido para sobreviver ao Google Translate sem ser traduzido.
_SEP = "⟦{}⟧"
_SEP_RE = re.compile(r"⟦(\d+)⟧")


def traduzir_blocos_pagina(blocos: list[dict],
                            src: str = SOURCE_LANG,
                            dst: str = TARGET_LANG,
                            engine: str = "google",
                            api_key: str | None = None) -> list[dict]:
    """
    Traduz todos os blocos de uma página em uma única chamada ao Google.
    Usa marcadores numerados (⟦0⟧, ⟦1⟧…) para recompor os blocos depois.
    Se o Google alterar os marcadores, cai automaticamente para bloco a bloco.
    """
    if not blocos:
        return blocos

    # Monta texto único: ⟦0⟧\ntexto0\n⟦1⟧\ntexto1\n...
    partes = []
    for i, b in enumerate(blocos):
        partes.append(f"{_SEP.format(i)}\n{b['texto']}")
    texto_unido = "\n".join(partes)

    traduzido = traduzir_texto(texto_unido, src, dst, engine, api_key)

    # Tenta recompor — divide pelo padrão ⟦N⟧
    segmentos: dict[int, str] = {}
    posicoes = [(m.start(), int(m.group(1))) for m in _SEP_RE.finditer(traduzido)]

    if len(posicoes) == len(blocos):
        for k, (pos, idx) in enumerate(posicoes):
            fim = posicoes[k + 1][0] if k + 1 < len(posicoes) else len(traduzido)
            conteudo = traduzido[pos:fim]
            # Remove o marcador da linha inicial
            conteudo = _SEP_RE.sub("", conteudo, count=1).strip()
            segmentos[idx] = conteudo

        return [{**b, "texto": segmentos.get(i, b["texto"])}
                for i, b in enumerate(blocos)]

    # Fallback: marcadores não sobreviveram — traduz bloco a bloco
    print("\n  [INFO] marcadores alterados pelo tradutor, usando fallback bloco a bloco.")
    return [
        {**b, "texto": traduzir_texto(b["texto"], src, dst, engine, api_key)}
        for b in blocos
    ]
