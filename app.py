import re
import os
import pytesseract
import streamlit as st
from pdf2image import convert_from_bytes
from PIL import Image, ImageDraw
from io import BytesIO

# Caminho do Tesseract local (apenas se estiver rodando offline)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Regex para CPF e RG
CPF_REGEX = re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')
RG_REGEX = re.compile(r'\b([A-Z]{2}-)?\d{1,2}\.?\d{3}\.?\d{3}-?\d?\b', re.IGNORECASE)

def apenas_digitos(s: str) -> str:
    return re.sub(r'\D', '', s or '')

def aplicar_tarjas_na_imagem(img: Image.Image, ignorar_chars: str) -> Image.Image:
    draw = ImageDraw.Draw(img)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang='por')

    for i in range(len(data['level'])):
        text = (data['text'][i] or "").strip()
        if not text:
            continue
        if any(c in text for c in ignorar_chars):
            continue  # ignora se contiver caractere bloqueado

        norm = apenas_digitos(text)
        is_cpf = bool(CPF_REGEX.search(text)) or (len(norm) == 11 and norm.isdigit())
        is_rg = bool(RG_REGEX.search(text)) or (7 <= len(norm) <= 9 and norm.isdigit())

        if is_cpf or is_rg:
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            draw.rectangle([x, y, x + w, y + h], fill="black")
    return img


st.set_page_config(page_title="Tarjador LGPD", page_icon="🕵️‍♂️", layout="centered")
st.title("🕵️‍♂️ Tarjador LGPD - CPF / RG")

uploaded_file = st.file_uploader("Selecione um arquivo PDF", type=["pdf"])
ignorar_chars = st.text_input("Caracteres a ignorar durante a varredura (ex: - , / \\ º : @)", "-,/:\\º:@")

if uploaded_file is not None:
    if st.button("Processar PDF"):
        with st.spinner("Processando, aguarde..."):
            try:
                images = convert_from_bytes(uploaded_file.read(), dpi=300)
                imgs_processadas = []
                for idx, img in enumerate(images, start=1):
                    st.write(f"Página {idx} processada.")
                    img_rgb = img.convert("RGB")
                    img_tarjada = aplicar_tarjas_na_imagem(img_rgb, ignorar_chars)
                    imgs_processadas.append(img_tarjada)

                output = BytesIO()
                imgs_processadas[0].save(output, format="PDF", save_all=True, append_images=imgs_processadas[1:])
                output.seek(0)
                st.success("✅ PDF processado com sucesso!")
                st.download_button("📥 Baixar PDF Tarjado", output, file_name="documento_tarjado.pdf")
            except Exception as e:
                st.error(f"Erro: {e}")
