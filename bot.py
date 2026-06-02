import os
import sys
import tempfile
import time
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter

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

def start(update: Update, context: CallbackContext):
    if not check_spam(update.effective_user.id):
        update.message.reply_text("⏳ انتظر قليلاً")
        return
    
    keyboard = [
        [InlineKeyboardButton("🖼 صورة إلى PDF", callback_data='img2pdf')],
        [InlineKeyboardButton("✂️ تقسيم PDF", callback_data='split')],
        [InlineKeyboardButton("🗜 ضغط PDF", callback_data='compress')],
        [InlineKeyboardButton("🔒 تشفير PDF", callback_data='encrypt')],
        [InlineKeyboardButton("📝 نص إلى PDF", callback_data='text2pdf')],
    ]
    
    update.message.reply_text(
        "🤖 *بوت PDF*\nاختر الخدمة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    context.user_data['action'] = query.data
    
    messages = {
        'img2pdf': "📤 أرسل الصورة",
        'split': "📤 أرسل ملف PDF",
        'compress': "📤 أرسل ملف PDF",
        'encrypt': "📤 أرسل ملف PDF ثم كلمة المرور",
        'text2pdf': "📤 أرسل النص",
    }
    query.edit_message_text(messages.get(query.data, "أرسل الملف"))

def handle_photo(update: Update, context: CallbackContext):
    if not check_spam(update.effective_user.id):
        return
    
    if context.user_data.get('action') != 'img2pdf':
        update.message.reply_text("⚠️ اختر 'صورة إلى PDF' أولاً")
        return
    
    update.message.reply_text("⏳ جاري التحويل...")
    
    try:
        photo = update.message.photo[-1]
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        photo.get_file().download(temp_img.name)
        
        img = Image.open(temp_img.name)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        img.save(temp_pdf.name, 'PDF')
        
        with open(temp_pdf.name, 'rb') as f:
            update.message.reply_document(document=f, filename="image.pdf")
        
        update.message.reply_text("✅ تم التحويل!")
        
        os.unlink(temp_pdf.name)
        os.unlink(temp_img.name)
    except Exception as e:
        update.message.reply_text(f"❌ خطأ: {str(e)}")
    
    context.user_data['action'] = None

def handle_document(update: Update, context: CallbackContext):
    if not check_spam(update.effective_user.id):
        return
    
    action = context.user_data.get('action')
    if not action:
        update.message.reply_text("⚠️ اختر خدمة أولاً")
        return
    
    doc = update.message.document
    if not doc.file_name.endswith('.pdf'):
        update.message.reply_text("❌ أرسل ملف PDF صالح")
        return
    
    update.message.reply_text("⏳ جاري المعالجة...")
    
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc.get_file().download(temp_input.name)
    
    try:
        if action == 'split':
            reader = PdfReader(temp_input.name)
            for i, page in enumerate(reader.pages):
                writer = PdfWriter()
                writer.add_page(page)
                temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                with open(temp_output.name, 'wb') as f:
                    writer.write(f)
                with open(temp_output.name, 'rb') as f:
                    update.message.reply_document(document=f, filename=f"page_{i+1}.pdf")
                os.unlink(temp_output.name)
            update.message.reply_text(f"✅ تم التقسيم إلى {len(reader.pages)} صفحات")
        
        elif action == 'compress':
            reader = PdfReader(temp_input.name)
            writer = PdfWriter()
            for page in reader.pages:
                page.compress_content_streams()
                writer.add_page(page)
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            with open(temp_output.name, 'wb') as f:
                writer.write(f)
            with open(temp_output.name, 'rb') as f:
                update.message.reply_document(document=f, filename="compressed.pdf")
            update.message.reply_text("✅ تم الضغط!")
            os.unlink(temp_output.name)
        
        elif action == 'encrypt':
            context.user_data['encrypt_file'] = temp_input.name
            update.message.reply_text("🔑 أرسل كلمة المرور:")
            return
        
        os.unlink(temp_input.name)
        
    except Exception as e:
        update.message.reply_text(f"❌ خطأ: {str(e)}")
    
    context.user_data['action'] = None

def handle_text(update: Update, context: CallbackContext):
    # معالجة التشفير
    if 'encrypt_file' in context.user_data:
        pdf_path = context.user_data.pop('encrypt_file')
        password = update.message.text
        
        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(password)
            
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            with open(temp_output.name, 'wb') as f:
                writer.write(f)
            
            with open(temp_output.name, 'rb') as f:
                update.message.reply_document(document=f, filename="encrypted.pdf")
            
            update.message.reply_text("✅ تم التشفير!")
            os.unlink(temp_output.name)
            os.unlink(pdf_path)
        except Exception as e:
            update.message.reply_text(f"❌ خطأ: {str(e)}")
        
        context.user_data['action'] = None
    
    # معالجة تحويل النص
    elif context.user_data.get('action') == 'text2pdf':
        text = update.message.text
        try:
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            
            c = canvas.Canvas(temp_pdf.name, pagesize=A4)
            y = 750
            for line in text.split('\n')[:40]:
                c.drawString(50, y, line[:80])
                y -= 20
            c.save()
            
            with open(temp_pdf.name, 'rb') as f:
                update.message.reply_document(document=f, filename="text.pdf")
            
            update.message.reply_text("✅ تم تحويل النص إلى PDF!")
            os.unlink(temp_pdf.name)
        except Exception as e:
            update.message.reply_text(f"❌ خطأ: {str(e)}")
        
        context.user_data['action'] = None

def main():
    print(f"✅ تشغيل البوت...")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(MessageHandler(Filters.document, handle_document))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    
    updater.start_polling()
    print(f"✅ البوت يعمل بنجاح!")
    updater.idle()

if __name__ == "__main__":
    main()
