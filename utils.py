import os
import asyncio
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

async def images_to_pdf(image_paths: list, output_path: str) -> bool:
    """تحويل قائمة صور إلى PDF واحد (Non-blocking)"""
    def _process():
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
    return await asyncio.to_thread(_process)

async def text_to_pdf(text: str, output_path: str):
    """تحويل نص إلى PDF مع دعم أساسي مبسط (Non-blocking)"""
    def _process():
        c = canvas.Canvas(output_path, pagesize=A4)
        y = 800
        for line in text.split('\n')[:50]:
            c.drawString(50, y, line[:100])
            y -= 20
            if y < 50:
                c.showPage()
                y = 800
        c.save()
    await asyncio.to_thread(_process)

async def merge_pdfs(pdf_paths: list, output_path: str):
    """دمج عدة ملفات PDF (Non-blocking)"""
    def _process():
        writer = PdfWriter()
        for path in pdf_paths:
            try:
                if os.path.exists(path):
                    reader = PdfReader(path)
                    for page in reader.pages:
                        writer.add_page(page)
            except Exception:
                pass
        with open(output_path, 'wb') as f:
            writer.write(f)
    await asyncio.to_thread(_process)

async def split_pdf(pdf_path: str, output_dir: str) -> list:
    """تقسيم PDF إلى صفحات منفصلة (Non-blocking)"""
    def _process():
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
    return await asyncio.to_thread(_process)

async def compress_pdf(input_path: str, output_path: str):
    """ضغط PDF (Non-blocking)"""
    def _process():
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.compress_content_streams()
            writer.add_page(page)
        with open(output_path, 'wb') as f:
            writer.write(f)
    await asyncio.to_thread(_process)

async def encrypt_pdf(input_path: str, output_path: str, password: str):
    """تشفير PDF بكلمة مرور (Non-blocking)"""
    def _process():
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)
        with open(output_path, 'wb') as f:
            writer.write(f)
    await asyncio.to_thread(_process)

async def reorder_pdf(input_path: str, output_path: str, order: list) -> int:
    """إعادة ترتيب صفحات PDF (Non-blocking)"""
    def _process():
        reader = PdfReader(input_path)
        writer = PdfWriter()
        total_pages = len(reader.pages)
        for page_num in order:
            if 1 <= page_num <= total_pages:
                writer.add_page(reader.pages[page_num - 1])
        with open(output_path, 'wb') as f:
            writer.write(f)
        return len(writer.pages)
    return await asyncio.to_thread(_process)

async def merge_images_with_pdf(pdf_path: str, image_paths: list, output_path: str, position: str = 'after'):
    """دمج صور مع PDF (Non-blocking)"""
    temp_img_pdf = os.path.join(os.path.dirname(output_path), "temp_img_conversion.pdf")
    try:
        success = await images_to_pdf(image_paths, temp_img_pdf)
        if success:
            if position == 'before':
                await merge_pdfs([temp_img_pdf, pdf_path], output_path)
            else:
                await merge_pdfs([pdf_path, temp_img_pdf], output_path)
    finally:
        if os.path.exists(temp_img_pdf):
            os.unlink(temp_img_pdf)

async def extract_text_from_pdf(pdf_path: str) -> str:
    """استخراج النصوص من ملف PDF (بديل دالة الصور الناقصة)"""
    def _process():
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for i, page in enumerate(reader.pages[:10]):  # حد أقصى أول 10 صفحات لمنع الأداء الضعيف
                content = page.extract_text()
                if content:
                    text += f"--- الصفحة {i+1} ---\n{content}\n\n"
            return text if text.strip() else "❌ لم يتم العثور على نصوص قابلة للاستخراج في هذا الملف."
        except Exception as e:
            return f"❌ فشل استخراج النص: {str(e)}"
    return await asyncio.to_thread(_process)
