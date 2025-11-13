import re
from io import BytesIO
from flask import Flask, request, send_file, render_template_string
from pdf2image import convert_from_path
from PIL import Image, ImageDraw
import pytesseract
import os

app = Flask(__name__)

# Caminho do executável do Tesseract (ajuste se necessário)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Regexs de CPF e RG
CPF_REGEX = re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')
RG_REGEX = re.compile(r'\b([A-Z]{2}-)?\d{1,2}\.?\d{3}\.?\d{3}-?\d?\b', re.IGNORECASE)

def apenas_digitos(s: str) -> str:
    return re.sub(r'\D', '', s or '')

def aplicar_tarjas_na_imagem(img: Image.Image, ignorar_chars: str) -> Image.Image:
    draw = ImageDraw.Draw(img)
    try:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang='por')
    except Exception:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    n_boxes = len(data['level'])
    for i in range(n_boxes):
        text = (data['text'][i] or "").strip()
        if not text:
            continue

        # ignora se contiver algum caractere digitado pelo usuário
        if any(ch in text for ch in ignorar_chars):
            continue

        norm = apenas_digitos(text)
        if not norm.isdigit():
            continue

        # detecta CPF (11 dígitos, não confundir com CNPJ)
        is_cpf = len(norm) == 11
        # detecta RG (7 a 9 dígitos, normalmente sem padrão fixo)
        is_rg = 7 <= len(norm) <= 9

        if is_cpf or is_rg:
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            margem_x = int(w * 0.15)
            margem_y = int(h * 0.3)
            box = [x - margem_x, y - margem_y, x + w + margem_x, y + h + margem_y]
            draw.rectangle(box, fill="black")

    return img

@app.route("/", methods=["GET", "POST"])
def index():
    html = """
    <!doctype html>
    <html lang="pt-BR">
    <head>
    <meta charset="utf-8">
    <title>Tarjador LGPD</title>
    <style>
      body { font-family: Arial, sans-serif; background: #f4f4f4; color: #333; padding: 30px; }
      .container { max-width: 650px; margin: auto; background: #fff; padding: 25px 30px; border-radius: 10px;
                   box-shadow: 0 0 15px rgba(0,0,0,0.1); }
      h2 { color: #004080; text-align: center; }
      input[type="file"], input[type="text"] { width: 100%; padding: 10px; margin: 10px 0; }
      button { background-color: #004080; color: #fff; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
      button:hover { background-color: #0059b3; }
      p.note { color: gray; font-size: 0.9em; text-align: center; }
    </style>
    </head>
    <body>
      <div class="container">
        <h2>Tarjador de CPF / RG (LGPD)</h2>
        <form method="post" enctype="multipart/form-data">
          <p>Selecione um PDF:</p>
          <input type="file" name="file" accept="application/pdf" required>
          <label>Caracteres a serem ignorados (ex: - , / \\ º : @):</label>
          <input type="text" name="ignorar" value="-,/\\\\º:@">
          <br><br>
          <button type="submit">Processar e baixar</button>
        </form>
        <p class="note">Obs: processamento pode demorar alguns segundos dependendo do tamanho do PDF.</p>
      </div>
    </body>
    </html>
    """

    if request.method == "POST":
        arquivo = request.files.get("file")
        if not arquivo:
            return "Nenhum arquivo enviado", 400

        ignorar_chars = request.form.get("ignorar", "-,/\\º:@")

        temp_in_path = "temp_input.pdf"
        arquivo.save(temp_in_path)

        try:
            images = convert_from_path(temp_in_path, dpi=300)
        except Exception as e:
            os.remove(temp_in_path)
            return f"Erro ao converter PDF: {e}", 500

        imagens_processadas = []
        for idx, img in enumerate(images, start=1):
            print(f"Processando página {idx}...")
            img_rgb = img.convert("RGB")
            img_tarjada = aplicar_tarjas_na_imagem(img_rgb, ignorar_chars)
            imagens_processadas.append(img_tarjada)

        output_bytes = BytesIO()
        imagens_processadas[0].save(output_bytes, format="PDF", save_all=True, append_images=imagens_processadas[1:])
        output_bytes.seek(0)
        os.remove(temp_in_path)

        return send_file(output_bytes, download_name="documento_tarjado.pdf", as_attachment=True, mimetype="application/pdf")

    return render_template_string(html)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
