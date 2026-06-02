import os
import tempfile
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def save_telegram_file(file, temp_dir):
    """حفظ ملف مستلم من تلجرام"""
    file_path = os.path.join(temp_dir, file.file_name or "file.pdf")
    return file_path

async def images_to_pdf(image_paths: list, output_path: str):
    """تحويل قائمة صور إلى PDF واحد"""
    images = []
    for path in image_paths:
        if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            img = Image.open(path)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            images.append(img)
    
    if images:
        images[0].save(output_path, save_all=True, append_images=images[1:], format='PDF')
        return True
    return False

async def text_to_pdf(text: str, output_path: str):
    """تحويل نص إلى PDF"""
    c = canvas.Canvas(output_path, pagesize=A4)
    y = 800
    for line in text.split('\n')[:50]:
        c.drawString(50, y, line[:100])
        y -= 20
        if y < 50:
            c.showPage()
            y = 800
    c.save()

async def merge_pdfs(pdf_paths: list, output_path: str):
    """دمج عدة ملفات PDF"""
    writer = PdfWriter()
    for path in pdf_paths:
        try:
            reader = PdfReader(path)
            for page in reader.pages:
                writer.add_page(page)
        except:
            pass
    
    with open(output_path, 'wb') as f:
        writer.write(f)

async def split_pdf(pdf_path: str, output_dir: str):
    """تقسيم PDF إلى صفحات منفصلة"""
    reader = PdfReader(pdf_path)
    output_files = []
    
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        out_path = os.path.join(output_dir, f"page_{i+1}.pdf")
        with open(out_path, 'wb') as f:
            writer.write(f)
        output_files.append(out_path)
    
    return output_files

async def compress_pdf(input_path: str, output_path: str):
    """ضغط PDF"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    for page in reader.pages:
        page.compress_content_streams()
        writer.add_page(page)
    
    with open(output_path, 'wb') as f:
        writer.write(f)

async def encrypt_pdf(input_path: str, output_path: str, password: str):
    """تشفير PDF بكلمة مرور"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    
    for page in reader.pages:
        writer.add_page(page)
    
    writer.encrypt(password)
    
    with open(output_path, 'wb') as f:
        writer.write(f)

async def reorder_pdf(input_path: str, output_path: str, order: list):
    """إعادة ترتيب صفحات PDF"""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    total_pages = len(reader.pages)
    
    for page_num in order:
        if 1 <= page_num <= total_pages:
            writer.add_page(reader.pages[page_num - 1])
    
    with open(output_path, 'wb') as f:
        writer.write(f)
    return len(writer.pages)

async def merge_images_with_pdf(pdf_path: str, image_paths: list, output_path: str, position: str = 'after'):
    """دمج صور مع PDF (الصور بعد أو قبل PDF)"""
    # أولاً: تحويل الصور إلى PDF
    temp_images_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    await images_to_pdf(image_paths, temp_images_pdf.name)
    
    # ثانياً: دمج PDF الأصلي مع صور PDF
    if position == 'before':
        await merge_pdfs([temp_images_pdf.name, pdf_path], output_path)
    else:  # after
        await merge_pdfs([pdf_path, temp_images_pdf.name], output_path)
    
    os.unlink(temp_images_pdf.name)

async def extract_images_from_pdf(pdf_path: str, output_dir: str):
    """استخراج الصور من PDF (نسخة مبسطة)"""
    # هذه نسخة مبسطة - للاستخدام الكامل تحتاج pdf2image
    return []
