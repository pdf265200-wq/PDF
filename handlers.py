import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import TEMP_DIR
from utils import *
from spam_protection import spam_protection

# إنشاء المجلد المؤقت إذا لم يكن موجوداً
os.makedirs(TEMP_DIR, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة الأوامر الرئيسية"""
    if not await spam_protection.check(update, context):
        return
    
    keyboard = [
        [InlineKeyboardButton("🖼 صورة → PDF", callback_data='img2pdf')],
        [InlineKeyboardButton("📝 نص → PDF", callback_data='text2pdf')],
        [InlineKeyboardButton("🔗 دمج PDF", callback_data='merge')],
        [InlineKeyboardButton("✂️ تقسيم PDF", callback_data='split')],
        [InlineKeyboardButton("🗜 ضغط PDF", callback_data='compress')],
        [InlineKeyboardButton("🖼 استخراج صور", callback_data='extract')],
        [InlineKeyboardButton("🔒 تشفير PDF", callback_data='encrypt')],
        [InlineKeyboardButton("🔢 أرقام صفحات", callback_data='numbers')],
    ]
    
    await update.message.reply_text(
        "🤖 *مرحباً بك في بوت PDF الشامل*\n\n"
        "اختر الخدمة التي تريدها:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على الأزرار"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    context.user_data['action'] = action
    
    messages = {
        'img2pdf': "📤 أرسل الصور (يمكنك إرسال عدة صور دفعة واحدة)",
        'text2pdf': "📤 أرسل النص أو ملف txt",
        'merge': "📤 أرسل ملفات PDF المراد دمجها (واحداً تلو الآخر، ثم اكتب /done)",
        'split': "📤 أرسل ملف PDF لتقسيمه",
        'compress': "📤 أرسل ملف PDF لضغطه",
        'extract': "📤 أرسل ملف PDF لاستخراج الصور منه",
        'encrypt': "📤 أرسل ملف PDF ثم سأطلب منك كلمة المرور",
        'numbers': "📤 أرسل ملف PDF لإضافة أرقام الصفحات",
    }
    
    await query.edit_message_text(messages.get(action, "أرسل الملف المطلوب"))

async def handle_documents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الملفات المرسلة"""
    if not await spam_protection.check(update, context):
        return
    
    action = context.user_data.get('action')
    if not action:
        await update.message.reply_text("⚠️ الرجاء اختيار خدمة أولاً من /start")
        return
    
    document = update.message.document
    if not document:
        await update.message.reply_text("❌ يرجى إرسال ملف صالح")
        return
    
    # تحميل الملف
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{document.file_name.split('.')[-1]}")
    file_path = temp_file.name
    file_obj = await document.get_file()
    await file_obj.download_to_drive(file_path)
    
    # إنشاء مجلد مؤقت للنتائج
    with tempfile.TemporaryDirectory() as temp_dir:
        
        if action == 'split':
            output_files = await split_pdf(file_path, temp_dir)
            for out_file in output_files:
                await update.message.reply_document(
                    open(out_file, 'rb'),
                    filename=os.path.basename(out_file)
                )
            await update.message.reply_text("✅ تم التقسيم بنجاح!")
        
        elif action == 'compress':
            output_path = os.path.join(temp_dir, "compressed.pdf")
            await compress_pdf(file_path, output_path)
            await update.message.reply_document(
                open(output_path, 'rb'),
                filename="compressed.pdf"
            )
        
        elif action == 'extract':
            output_files = await extract_images_from_pdf(file_path, temp_dir)
            for img_path in output_files[:10]:  # حد أقصى 10 صور
                await update.message.reply_photo(open(img_path, 'rb'))
            await update.message.reply_text(f"✅ تم استخراج {len(output_files)} صورة")
        
        elif action == 'encrypt':
            context.user_data['pending_encrypt'] = file_path
            await update.message.reply_text("🔑 أرسل كلمة المرور لتشفير الملف:")
        
        else:
            await update.message.reply_text("⏳ جاري المعالجة...")
            # باقي الميزات يمكن إضافتها بنفس الطريقة
    
    # تنظيف الملف المؤقت
    if os.path.exists(file_path):
        os.unlink(file_path)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة النصوص (لكلمة المرور أو النص المراد تحويله)"""
    if 'pending_encrypt' in context.user_data:
        pdf_path = context.user_data['pending_encrypt']
        password = update.message.text
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output_path = tmp.name
            await encrypt_pdf(pdf_path, output_path, password)
            await update.message.reply_document(
                open(output_path, 'rb'),
                filename="encrypted.pdf"
            )
            os.unlink(output_path)
        
        os.unlink(pdf_path)
        del context.user_data['pending_encrypt']
    
    elif context.user_data.get('action') == 'text2pdf':
        text = update.message.text
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output_path = tmp.name
            await text_to_pdf(text, output_path)
            await update.message.reply_document(
                open(output_path, 'rb'),
                filename="text.pdf"
            )
            os.unlink(output_path)
        context.user_data['action'] = None
