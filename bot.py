import os
import sys
import tempfile
import time
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)

# قراءة التوكن من متغيرات البيئة
TOKEN = os.environ.get('BOT_TOKEN')

# التحقق من التوكن
if not TOKEN:
    print("❌ خطأ: BOT_TOKEN غير موجود")
    print("الرجاء إضافة BOT_TOKEN في متغيرات البيئة على Railway")
    sys.exit(1)

# حماية السبام
user_commands = {}
SPAM_LIMIT = 2

def check_spam(user_id):
    now = time.time()
    if user_id in user_commands:
        if now - user_commands[user_id] < SPAM_LIMIT:
            return False
    user_commands[user_id] = now
    return True

# وظائف PDF
async def images_to_pdf(image_path, output_path):
    try:
        img = Image.open(image_path)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(output_path, 'PDF')
        return True
    except:
        return False

async def text_to_pdf(text, output_path):
    c = canvas.Canvas(output_path, pagesize=A4)
    y = 750
    for line in text.split('\n')[:40]:
        c.drawString(50, y, line[:80])
        y -= 20
    c.save()

async def split_pdf(pdf_path, output_dir):
    reader = PdfReader(pdf_path)
    files = []
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        out = os.path.join(output_dir, f"page_{i+1}.pdf")
        with open(out, 'wb') as f:
            writer.write(f)
        files.append(out)
    return files

async def compress_pdf(input_path, output_path):
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        page.compress_content_streams()
        writer.add_page(page)
    with open(output_path, 'wb') as f:
        writer.write(f)

async def encrypt_pdf(input_path, output_path, password):
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    with open(output_path, 'wb') as f:
        writer.write(f)

# معالجات البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_spam(update.effective_user.id):
        await update.message.reply_text("⏳ انتظر قليلاً")
        return
    
    keyboard = [
        [InlineKeyboardButton("🖼 صورة إلى PDF", callback_data='img2pdf')],
        [InlineKeyboardButton("✂️ تقسيم PDF", callback_data='split')],
        [InlineKeyboardButton("🗜 ضغط PDF", callback_data='compress')],
        [InlineKeyboardButton("🔒 تشفير PDF", callback_data='encrypt')],
        [InlineKeyboardButton("📝 نص إلى PDF", callback_data='text2pdf')],
    ]
    
    await update.message.reply_text(
        "🤖 *بوت PDF*\nاختر الخدمة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['action'] = query.data
    
    messages = {
        'img2pdf': "📤 أرسل الصورة",
        'split': "📤 أرسل ملف PDF",
        'compress': "📤 أرسل ملف PDF",
        'encrypt': "📤 أرسل ملف PDF ثم كلمة المرور",
        'text2pdf': "📤 أرسل النص",
    }
    await query.edit_message_text(messages.get(query.data, "أرسل الملف"))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_spam(update.effective_user.id):
        return
    
    if context.user_data.get('action') != 'img2pdf':
        await update.message.reply_text("⚠️ اختر 'صورة إلى PDF' أولاً")
        return
    
    await update.message.reply_text("⏳ جاري التحويل...")
    
    try:
        photo = update.message.photo[-1]
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        await photo.get_file().download_to_drive(temp_img.name)
        
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        success = await images_to_pdf(temp_img.name, temp_pdf.name)
        
        if success:
            with open(temp_pdf.name, 'rb') as f:
                await update.message.reply_document(document=f, filename="image.pdf")
            await update.message.reply_text("✅ تم التحويل!")
        else:
            await update.message.reply_text("❌ فشل التحويل")
        
        os.unlink(temp_pdf.name)
        os.unlink(temp_img.name)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {str(e)}")
    
    context.user_data['action'] = None

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_spam(update.effective_user.id):
        return
    
    action = context.user_data.get('action')
    if not action:
        await update.message.reply_text("⚠️ اختر خدمة أولاً")
        return
    
    doc = update.message.document
    if not doc.file_name.endswith('.pdf'):
        await update.message.reply_text("❌ أرسل ملف PDF صالح")
        return
    
    await update.message.reply_text("⏳ جاري المعالجة...")
    
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    await doc.get_file().download_to_drive(temp_input.name)
    
    try:
        if action == 'split':
            output_dir = tempfile.mkdtemp()
            files = await split_pdf(temp_input.name, output_dir)
            for f in files:
                with open(f, 'rb') as file:
                    await update.message.reply_document(document=file, filename=os.path.basename(f))
            await update.message.reply_text(f"✅ تم التقسيم إلى {len(files)} صفحات")
        
        elif action == 'compress':
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            await compress_pdf(temp_input.name, temp_output.name)
            with open(temp_output.name, 'rb') as f:
                await update.message.reply_document(document=f, filename="compressed.pdf")
            await update.message.reply_text("✅ تم الضغط!")
            os.unlink(temp_output.name)
        
        elif action == 'encrypt':
            context.user_data['encrypt_file'] = temp_input.name
            await update.message.reply_text("🔑 أرسل كلمة المرور:")
            return
        
        os.unlink(temp_input.name)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {str(e)}")
    
    context.user_data['action'] = None

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # معالجة التشفير
    if 'encrypt_file' in context.user_data:
        pdf_path = context.user_data.pop('encrypt_file')
        password = update.message.text
        
        try:
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            await encrypt_pdf(pdf_path, temp_output.name, password)
            
            with open(temp_output.name, 'rb') as f:
                await update.message.reply_document(document=f, filename="encrypted.pdf")
            
            await update.message.reply_text("✅ تم التشفير!")
            os.unlink(temp_output.name)
            os.unlink(pdf_path)
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {str(e)}")
        
        context.user_data['action'] = None
    
    # معالجة تحويل النص
    elif context.user_data.get('action') == 'text2pdf':
        text = update.message.text
        try:
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            await text_to_pdf(text, temp_pdf.name)
            
            with open(temp_pdf.name, 'rb') as f:
                await update.message.reply_document(document=f, filename="text.pdf")
            
            await update.message.reply_text("✅ تم تحويل النص إلى PDF!")
            os.unlink(temp_pdf.name)
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {str(e)}")
        
        context.user_data['action'] = None

async def main():
    print("✅ تشغيل البوت...")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ البوت يعمل بنجاح!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
