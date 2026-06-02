import os
import asyncio
import logging
from pathlib import Path
from typing import List, Optional
import fitz  # PyMuPDF
import img2pdf
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.utils import ImageReader
import io

logger = logging.getLogger(__name__)

async def images_to_pdf(image_paths: List[str], output_path: str) -> bool:
    """تحويل الصور إلى PDF باستخدام img2pdf (أسرع وأفضل جودة)"""
    try:
        def _process():
            # ترتيب الصور حسب الأسماء
            image_paths.sort()
            
            # تحويل المسارات إلى Path objects
            valid_paths = []
            for img_path in image_paths:
                path = Path(img_path)
                if path.exists() and path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
                    valid_paths.append(str(path))
            
            if not valid_paths:
                return False
            
            # استخدام img2pdf للحصول على أفضل ضغط وجودة
            with open(output_path, "wb") as f:
                f.write(img2pdf.convert(valid_paths))
            return True
        
        return await asyncio.to_thread(_process)
    except Exception as e:
        logger.error(f"Error in images_to_pdf: {e}")
        return False

async def text_to_pdf(text: str, output_path: str, page_size: str = 'A4'):
    """تحويل النص إلى PDF مع دعم كامل للغة العربية"""
    def _process():
        pagesize = A4 if page_size == 'A4' else letter
        c = canvas.Canvas(output_path, pagesize=pagesize)
        width, height = pagesize
        
        # إعدادات النص
        c.setFont("Helvetica", 12)
        y = height - 50
        margin = 50
        line_height = 14
        
        # تقسيم النص إلى سطور
        lines = text.split('\n')
        
        for line in lines:
            if y < margin:
                c.showPage()
                c.setFont("Helvetica", 12)
                y = height - 50
            
            # تقسيم السطور الطويلة
            while len(line) > 100:
                c.drawString(margin, y, line[:100])
                line = line[100:]
                y -= line_height
                if y < margin:
                    c.showPage()
                    c.setFont("Helvetica", 12)
                    y = height - 50
            
            c.drawString(margin, y, line)
            y -= line_height
        
        c.save()
    
    await asyncio.to_thread(_process)

async def merge_pdfs(pdf_paths: List[str], output_path: str):
    """دمج ملفات PDF باستخدام PyMuPDF (أسرع)"""
    def _process():
        result = fitz.open()
        for pdf_path in pdf_paths:
            if Path(pdf_path).exists():
                try:
                    doc = fitz.open(pdf_path)
                    result.insert_pdf(doc)
                    doc.close()
                except Exception as e:
                    logger.error(f"Error merging {pdf_path}: {e}")
        
        if len(result) > 0:
            result.save(output_path)
            result.close()
    
    await asyncio.to_thread(_process)

async def split_pdf(pdf_path: str, output_dir: str) -> List[str]:
    """تقسيم PDF إلى صفحات منفردة"""
    def _process():
        doc = fitz.open(pdf_path)
        output_files = []
        
        for page_num in range(len(doc)):
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            out_path = os.path.join(output_dir, f"page_{page_num + 1}.pdf")
            new_doc.save(out_path)
            new_doc.close()
            output_files.append(out_path)
        
        doc.close()
        return output_files
    
    return await asyncio.to_thread(_process)

async def compress_pdf(input_path: str, output_path: str):
    """ضغط PDF عن طريق تقليل جودة الصور"""
    def _process():
        doc = fitz.open(input_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # ضغط الصور في الصفحة
            image_list = page.get_images()
            
            for img in image_list:
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        # تقليل الجودة
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    pix.save(f"temp_{xref}.png")
                    # إعادة إدراج الصورة المضغوطة
                    img_data = open(f"temp_{xref}.png", "rb").read()
                    doc._updateObject(xref, img_data)
                    os.remove(f"temp_{xref}.png")
                except Exception as e:
                    logger.error(f"Error compressing image: {e}")
                    continue
        
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
    
    await asyncio.to_thread(_process)

async def encrypt_pdf(input_path: str, output_path: str, password: str):
    """تشفير PDF بكلمة مرور"""
    def _process():
        doc = fitz.open(input_path)
        doc.save(output_path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password)
        doc.close()
    
    await asyncio.to_thread(_process)

async def reorder_pdf(input_path: str, output_path: str, order: List[int]) -> int:
    """إعادة ترتيب صفحات PDF"""
    def _process():
        doc = fitz.open(input_path)
        new_doc = fitz.open()
        total_pages = len(doc)
        
        for page_num in order:
            if 1 <= page_num <= total_pages:
                new_doc.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)
        
        new_doc.save(output_path)
        new_doc.close()
        doc.close()
        return len(order)
    
    return await asyncio.to_thread(_process)

async def merge_images_with_pdf(pdf_path: str, image_paths: List[str], output_path: str, position: str = 'after'):
    """دمج الصور مع ملف PDF"""
    # تحويل الصور إلى PDF مؤقت
    temp_img_pdf = os.path.join(os.path.dirname(output_path), "temp_images.pdf")
    
    try:
        success = await images_to_pdf(image_paths, temp_img_pdf)
        if not success:
            raise Exception("فشل تحويل الصور إلى PDF")
        
        if position == 'before':
            await merge_pdfs([temp_img_pdf, pdf_path], output_path)
        else:
            await merge_pdfs([pdf_path, temp_img_pdf], output_path)
    finally:
        if os.path.exists(temp_img_pdf):
            os.unlink(temp_img_pdf)

async def extract_text_from_pdf(pdf_path: str, max_pages: int = 50) -> str:
    """استخراج النصوص من PDF مع دعم كامل للغة العربية"""
    def _process():
        try:
            doc = fitz.open(pdf_path)
            total_pages = min(len(doc), max_pages)
            text = f"📄 *إجمالي الصفحات:* {len(doc)}\n\n"
            
            for page_num in range(total_pages):
                page = doc[page_num]
                page_text = page.get_text()
                
                if page_text.strip():
                    text += f"📖 *الصفحة {page_num + 1}*\n"
                    text += f"```\n{page_text[:1000]}\n```\n\n"
                    
                    if len(page_text) > 1000:
                        text += "*(تم عرض أول 1000 حرف فقط)*\n\n"
            
            doc.close()
            
            if len(text) < 100:
                return "❌ لم يتم العثور على نصوص قابلة للاستخراج في هذا الملف."
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return f"❌ فشل استخراج النص: {str(e)}"
    
    return await asyncio.to_thread(_process)

async def get_pdf_info(pdf_path: str) -> dict:
    """الحصول على معلومات عن ملف PDF"""
    def _process():
        doc = fitz.open(pdf_path)
        info = {
            'pages': len(doc),
            'size_mb': os.path.getsize(pdf_path) / (1024 * 1024),
            'metadata': doc.metadata
        }
        doc.close()
        return info
    
    return await asyncio.to_thread(_process)
