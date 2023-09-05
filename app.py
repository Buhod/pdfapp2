import os
import tempfile
import shutil
import random
import string
from flask import Flask, request, render_template, send_from_directory
import fitz
from PIL import Image
import zipfile

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

@app.route('/convertidorpdf/download/<filename>')
def download(filename):
    directory = os.path.join(app.root_path, 'static', 'separated_files')
    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/convertidorpdf/download/zip')
def download_zip():
    directory = os.path.join(app.root_path, 'static', 'separated_files')
    zip_filename = 'separated_files.zip'
    zip_filepath = os.path.join(directory, zip_filename)
    
    # Crear un archivo ZIP con todos los archivos en el directorio
    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, directory))

    return send_from_directory(directory, zip_filename, as_attachment=True)

@app.route('/', methods=['GET', 'POST'])
def convert_pdf():
    if request.method == 'POST':
        if 'pdfFile' in request.files and 'convertFormat' in request.form:
            pdf_file = request.files['pdfFile']
            convert_format = request.form['convertFormat']
            
            if pdf_file.filename == '':
                print('No se ha seleccionado un archivo PDF para convertir.')
                return render_template('error.html', message='No se ha seleccionado un archivo PDF para convertir.')

            if convert_format not in ALLOWED_EXTENSIONS:
                print('El formato de conversión no es válido.')
                return render_template('error.html', message='El formato de conversión no es válido.')

            # Obtener el nombre base del archivo PDF sin extensión
            pdf_filename = os.path.splitext(pdf_file.filename)[0]
            temp_dir = tempfile.mkdtemp()
            pdf_path = os.path.join(temp_dir, pdf_filename + '.pdf')
            pdf_file.save(pdf_path)

            pdf_document = fitz.open(pdf_path)

            num_pages = pdf_document.page_count

            separated_files = []
            for page_number in range(num_pages):
                output_file_extension = convert_format.lower()

                # Crear el nombre del archivo generado con el formato: nombre_base_numero
                output_filename = f'{pdf_filename}_pagina_{page_number + 1}.{output_file_extension}'
                output_path = os.path.join(temp_dir, output_filename)

                if output_file_extension == 'pdf':
                    output_pdf = fitz.open()
                    output_pdf.insert_pdf(pdf_document, from_page=page_number, to_page=page_number)
                    output_pdf.save(output_path)
                    print(f'Se ha convertido la página {page_number + 1} a PDF: {output_path}')
                elif output_file_extension in {'png', 'jpg', 'jpeg'}:
                    page = pdf_document.load_page(page_number)
                    pix = page.get_pixmap()

                    # Convertir la extensión a minúsculas
                    output_file_extension = output_file_extension.lower()

                    # Usar Pillow para guardar la imagen en formato JPEG o PNG
                    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    image.save(output_path, format=output_file_extension)
                    print(f'Se ha convertido la página {page_number + 1} a imagen {output_file_extension}: {output_path}')

                separated_files.append(output_path)

            target_dir = os.path.join(app.root_path, 'static', 'separated_files')
            shutil.rmtree(target_dir, ignore_errors=True)
            os.makedirs(target_dir, exist_ok=True)

            moved_files = []
            for file_path in separated_files:
                new_file_path = os.path.join(target_dir, os.path.basename(file_path))
                os.rename(file_path, new_file_path)
                moved_files.append(new_file_path)

            pdf_document.close()
            shutil.rmtree(temp_dir)

            return render_template('result.html', pdf_path=pdf_path, pdf_filename=pdf_filename,
                                   separated_files=moved_files, os=os)

    return render_template('index.html')

def generate_random_string(length=8):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for _ in range(length))

app.run(host='0.0.0.0', debug=False)
