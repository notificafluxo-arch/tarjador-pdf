import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image, ImageDraw
import re

st.set_page_config(page_title="Tarjador de PDF", page_icon="🕵️", layout="wide")

st.title("🕵️ Tarjador Inteligente de PDFs")

st.markdown("Envie um PDF e o sistema aplicará tarjas automáticas em CPFs, RGs e outros padrões confidenciais.")

# Campo para ignorar caracteres
ignored_chars = st.text_input("Caracteres a serem ignorados (não tarjar):", "-, /, \\ , º, :, @")
ignored_set = set([c.strip() for c in ignored_chars.split(",") if c.strip()])

uploaded_file = st.file_uploader("📄 Envie um arquivo PDF", type=["pdf"])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    output_pdf = fitz.open()

    total_trejados = 0

    # Expressões regulares para detectar CPFs e RGs
    patterns = [
        r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",  # CPF
        r"\b\d{2}\.\d{3}\.\d{3}-\d{1}\b",  # RG com pontos
        r"\b\d{7,9}\b"                     # RG numérico simples
    ]

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        # Texto da página para identificar padrões
        text = page.get_text("text")

        # Aplica regex para encontrar padrões
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                encontrado = match.group()

                # Ignorar se contiver algum dos caracteres escolhidos
                if any(ch in encontrado for ch in ignored_set):
                    continue

                # Localizar posição visual do texto
                areas = page.search_for(encontrado)
                for rect in areas:
                    total_trejados += 1
                    draw = ImageDraw.Draw(img)
                    draw.rectangle(
                        [(rect.x0, rect.y0), (rect.x1, rect.y1)],
                        fill="black"
                    )

        # Converte imagem modificada de volta para PDF
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PDF")
        temp_doc = fitz.open("pdf", img_bytes.getvalue())
        output_pdf.insert_pdf(temp_doc)

    # Exporta PDF final
    output_buffer = io.BytesIO()
    output_pdf.save(output_buffer)
    st.success(f"✅ PDF processado com sucesso! {total_trejados} áreas tarjadas.")

    st.download_button(
        label="⬇️ Baixar PDF Tarjado",
        data=output_buffer.getvalue(),
        file_name="tarjado.pdf",
        mime="application/pdf"
    )
