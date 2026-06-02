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
        [InlineKeyboardButton("🖼 دمج صور مع PDF", callback_data='merge_img_pdf')],
        [InlineKeyboardButton("✂️ تقسيم PDF", callback_data='split')],
        [InlineKeyboardButton("🔄 إعادة ترتيب PDF", callback_data='reorder')],
        [InlineKeyboardButton("🗜 ضغط PDF", callback_data='compress')],
        [InlineKeyboardButton("🖼 استخراج صور", callback_data='extract')],
        [InlineKeyboardButton("🔒 تشفير PDF", callback_data='encrypt')],
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
        'text2pdf': "📤 أرسل النص",
        'merge': "📤 أرسل ملفات PDF المراد دمجها (واحداً تلو الآخر، ثم اكتب /done)",
        'merge_img_pdf': "📤 أرسل ملف PDF أولاً، ثم أرسل الصور",
        'split': "📤 أرسل ملف PDF لتقسيمه",
        'reorder': "📤 أرسل ملف PDF لإعادة ترتيبه ثم أرسل الأرقام (مثال: 3,1,2,4)",
        'compress': "📤 أرسل ملف PDF لضغطه",
        'extract': "📤 أرسل ملف PDF لاستخراج النص منه",
        'encrypt': "📤 أرسل ملف PDF ثم سأطلب منك كلمة المرور",
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
    file_ext = document.file_name.split('.')[-1].lower()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}")
    file_path = temp_file.name
    file_obj = await document.get_file()
    await file_obj.download_to_drive(file_path)
    
    # معالجة دمج الصور مع PDF (تحتاج تخزين PDF أولاً)
    if action == 'merge_img_pdf':
        context.user_data['pdf_for_merge'] = file_path
        context.user_data['merge_images'] = []
        await update.message.reply_text("✅ تم استلام PDF. الآن أرسل الصور (أرسلها واحدة تلو الأخرى، ثم اكتب /done)")
        return
    
    # إنشاء مجلد مؤقت للنتائج
    with tempfile.TemporaryDirectory() as temp_dir:
        
        if action == 'split':
            output_files = await split_pdf(file_path, temp_dir)
            for out_file in output_files:
                with open(out_file, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=os.path.basename(out_file)
                    )
            await update.message.reply_text(f"✅ تم التقسيم إلى {len(output_files)} صفحات")
        
        elif action == 'compress':
            output_path = os.path.join(temp_dir, "compressed.pdf")
            await compress_pdf(file_path, output_path)
            with open(output_path, 'rb') as f:
                await update.message.reply_document(document=f, filename="compressed.pdf")
            await update.message.reply_text("✅ تم ضغط الملف")
        
        elif action == 'encrypt':
            context.user_data['pending_encrypt'] = file_path
            await update.message.reply_text("🔑 أرسل كلمة المرور لتشفير الملف:")
            return
        
        elif action == 'reorder':
            context.user_data['reorder_file'] = file_path
            await update.message.reply_text(
                "📝 أرسل ترتيب الصفحات المطلوب\n"
                "مثال: 3,1,2,4\n"
                "(يعني: الصفحة 3 ثم 1 ثم 2 ثم 4)"
            )
            return
        
        else:
            await update.message.reply_text("⏳ جاري المعالجة...")
    
    # تنظيف الملف المؤقت إذا لم يكن في انتظار
    if action not in ['encrypt', 'reorder', 'merge_img_pdf']:
        if os.path.exists(file_path):
            os.unlink(file_path)

async def handle_photos_for_merge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الصور لدمجها مع PDF"""
    if context.user_data.get('action') != 'merge_img_pdf':
        return
    
    if 'merge_images' not in context.user_data:
        context.user_data['merge_images'] = []
    
    photo = update.message.photo[-1]
    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    await photo.get_file().download_to_drive(temp_img.name)
    context.user_data['merge_images'].append(temp_img.name)
    
    await update.message.reply_text(f"✅ تم استلام الصورة {len(context.user_data['merge_images'])}. أرسل المزيد أو /done")

async def handle_reorder_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ترتيب الصفحات"""
    if 'reorder_file' not in context.user_data:
        return
    
    pdf_path = context.user_data.pop('reorder_file')
    order_text = update.message.text
    
    try:
        # تحويل النص إلى قائمة أرقام
        order = [int(x.strip()) for x in order_text.split(',')]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "reordered.pdf")
            pages_count = await reorder_pdf(pdf_path, output_path, order)
            
            with open(output_path, 'rb') as f:
                await update.message.reply_document(document=f, filename="reordered.pdf")
            
            await update.message.reply_text(f"✅ تم إعادة ترتيب {pages_count} صفحة بنجاح")
        
        os.unlink(pdf_path)
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {str(e)}\nالرجاء إرسال الأرقام بشكل صحيح (مثال: 3,1,2,4)")

async def handle_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنهاء تجميع الملفات"""
    action = context.user_data.get('action')
    
    if action == 'merge' and 'merge_files' in context.user_data:
        files = context.user_data['merge_files']
        if len(files) >= 2:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "merged.pdf")
                await merge_pdfs(files, output_path)
                with open(output_path, 'rb') as f:
                    await update.message.reply_document(document=f, filename="merged.pdf")
                await update.message.reply_text(f"✅ تم دمج {len(files)} ملفات")
            
            # تنظيف الملفات المؤقتة
            for f in files:
                try:
                    os.unlink(f)
                except:
                    pass
            context.user_data['merge_files'] = []
        else:
            await update.message.reply_text("❌ أرسل ملفين PDF على الأقل للدمج")
    
    elif action == 'merge_img_pdf' and 'pdf_for_merge' in context.user_data:
        pdf_path = context.user_data.pop('pdf_for_merge')
        images = context.user_data.get('merge_images', [])
        
        if images:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = os.path.join(temp_dir, "merged_with_images.pdf")
                await merge_images_with_pdf(pdf_path, images, output_path, 'after')
                with open(output_path, 'rb') as f:
                    await update.message.reply_document(document=f, filename="merged_with_images.pdf")
                await update.message.reply_text(f"✅ تم دمج {len(images)} صورة مع PDF")
            
            # تنظيف
            for img in images:
                try:
                    os.unlink(img)
                except:
                    pass
            os.unlink(pdf_path)
            context.user_data['merge_images'] = []
        else:
            await update.message.reply_text("❌ لم يتم إرسال أي صور")
    
    context.user_data['action'] = None
    await update.message.reply_text("✅ تم الإنهاء")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة النصوص"""
    # معالجة التشفير
    if 'pending_encrypt' in context.user_data:
        pdf_path = context.user_data.pop('pending_encrypt')
        password = update.message.text
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output_path = tmp.name
            await encrypt_pdf(pdf_path, output_path, password)
            with open(output_path, 'rb') as f:
                await update.message.reply_document(document=f, filename="encrypted.pdf")
            os.unlink(output_path)
        
        os.unlink(pdf_path)
        await update.message.reply_text("✅ تم تشفير الملف")
        context.user_data['action'] = None
    
    # معالجة تحويل النص إلى PDF
    elif context.user_data.get('action') == 'text2pdf':
        text = update.message.text
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output_path = tmp.name
            await text_to_pdf(text, output_path)
            with open(output_path, 'rb') as f:
                await update.message.reply_document(document=f, filename="text.pdf")
            os.unlink(output_path)
        context.user_data['action'] = None
        await update.message.reply_text("✅ تم تحويل النص إلى PDF")
    
    # معالجة إعادة الترتيب
    elif 'reorder_file' in context.user_data:
        await handle_reorder_text(update, context)
