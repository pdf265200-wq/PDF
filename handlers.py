import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import TEMP_DIR
from utils import *
from spam_protection import spam_protection

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
        [InlineKeyboardButton("📝 استخراج نصوص", callback_data='extract')],
        [InlineKeyboardButton("🔒 تشفير PDF", callback_data='encrypt')],
    ]
    
    # تصفير البيانات عند البدء الجديد لتفادي تداخل العمليات
    context.user_data.clear()
    
    await update.message.reply_text(
        "🤖 *مرحباً بك في بوت PDF الشامل لعام 2026*\n\n"
        "اختر الخدمة التي تريدها من الأزرار أدناه:",
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
        'img2pdf': "📤 أرسل الصور الآن (واحدة تلو الأخرى، ثم اكتب /done عند الانتهاء)",
        'text2pdf': "📤 أرسل النص الذي تود تحويله إلى ملف PDF",
        'merge': "📤 أرسل ملفات PDF المراد دمجها (واحداً تلو الآخر، ثم اكتب /done)",
        'merge_img_pdf': "📤 أرسل ملف PDF أولاً، ثم سأطلب منك إرسال الصور",
        'split': "📤 أرسل ملف PDF لتقسيمه إلى صفحات منفصلة",
        'reorder': "📤 أرسل ملف PDF لإعادة ترتيبه أولاً",
        'compress': "📤 أرسل ملف PDF لضغطه وتقليل حجمه",
        'extract': "📤 أرسل ملف PDF لاستخراج النصوص الرقمية منه",
        'encrypt': "📤 أرسل ملف PDF المراد حمايته بكلمة مرور",
    }
    
    await query.edit_message_text(messages.get(action, "أرسل الملف المطلوب"))

async def handle_documents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الملفات المرسلة"""
    if not await spam_protection.check(update, context):
        return
    
    action = context.user_data.get('action')
    if not action:
        await update.message.reply_text("⚠️ الرجاء اختيار خدمة أولاً من القائمة /start")
        return
    
    document = update.message.document
    if not document:
        await update.message.reply_text("❌ يرجى إرسال ملف صالح")
        return
    
    # تحميل وتخزين الملف بأمان
    file_ext = document.file_name.split('.')[-1].lower() if document.file_name else 'pdf'
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}", dir=TEMP_DIR)
    file_path = temp_file.name
    temp_file.close()
    
    file_obj = await document.get_file()
    await file_obj.download_to_drive(file_path)
    
    # [إصلاح الثغرة المنطقية للدمج المتعدد]
    if action == 'merge':
        if 'merge_files' not in context.user_data:
            context.user_data['merge_files'] = []
        context.user_data['merge_files'].append(file_path)
        await update.message.reply_text(f"✅ تم استلام ملف PDF رقم {len(context.user_data['merge_files'])}. أرسل ملفاً آخر أو اكتب /done للدمج.")
        return

    if action == 'merge_img_pdf':
        context.user_data['pdf_for_merge'] = file_path
        context.user_data['merge_images'] = []
        await update.message.reply_text("✅ تم استلام ملف PDF. الآن أرسل الصور التي تريد إضافتها إليه، ثم اكتب /done")
        return
    
    if action == 'encrypt':
        context.user_data['pending_encrypt'] = file_path
        await update.message.reply_text("🔑 أرسل كلمة المرور التي تريد قفل الملف بها الآن:")
        return
        
    if action == 'reorder':
        context.user_data['reorder_file'] = file_path
        await update.message.reply_text("📝 أرسل ترتيب الصفحات المطلوب مفصولاً بفاصلة\nمثال: `3,1,2,4`")
        return

    # معالجة فورية للميزات المباشرة لحماية الذاكرة والمجلدات المؤقتة
    await update.message.reply_text("⏳ جاري معالجة طلبك، يرجى الانتظار...")
    
    try:
        if action == 'split':
            with tempfile.TemporaryDirectory(dir=TEMP_DIR) as temp_dir:
                output_files = await split_pdf(file_path, temp_dir)
                for out_file in output_files:
                    with open(out_file, 'rb') as f:
                        await update.message.reply_document(document=f, filename=os.path.basename(out_file))
                await update.message.reply_text(f"✅ تم تقسيم الملف إلى {len(output_files)} صفحات بنجاح.")
                
        elif action == 'compress':
            out_compressed = file_path + "_comp.pdf"
            await compress_pdf(file_path, out_compressed)
            with open(out_compressed, 'rb') as f:
                await update.message.reply_document(document=f, filename="Compressed_File.pdf")
            if os.path.exists(out_compressed): os.unlink(out_compressed)
            await update.message.reply_text("✅ تم ضغط وتخفيض حجم الملف بنجاح.")
            
        elif action == 'extract':
            extracted_text = await extract_text_from_pdf(file_path)
            await update.message.reply_text(extracted_text)
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء المعالجة: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.unlink(file_path)

async def handle_photos_for_merge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الصور لخدمات (img2pdf) و (merge_img_pdf)"""
    action = context.user_data.get('action')
    if action not in ['img2pdf', 'merge_img_pdf']:
        return
        
    if 'merge_images' not in context.user_data:
        context.user_data['merge_images'] = []
        
    photo = update.message.photo[-1]
    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", dir=TEMP_DIR)
    img_path = temp_img.name
    temp_img.close()
    
    await photo.get_file().download_to_drive(img_path)
    context.user_data['merge_images'].append(img_path)
    
    await update.message.reply_text(f"✅ تم استقبال الصورة رقم {len(context.user_data['merge_images'])}. أرسل المزيد أو اكتب /done للتنفيذ.")

async def handle_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إقفال وتجميع العمليات المتعددة"""
    action = context.user_data.get('action')
    
    if action == 'merge' and 'merge_files' in context.user_data:
        files = context.user_data['merge_files']
        if len(files) >= 2:
            await update.message.reply_text("⏳ جاري دمج ملفات PDF...")
            out_merged = os.path.join(TEMP_DIR, "merged_final.pdf")
            try:
                await merge_pdfs(files, out_merged)
                with open(out_merged, 'rb') as f:
                    await update.message.reply_document(document=f, filename="Merged_Document.pdf")
            finally:
                for f in files: 
                    if os.path.exists(f): os.unlink(f)
                if os.path.exists(out_merged): os.unlink(out_merged)
            await update.message.reply_text("✅ تم دمج الملفات بنجاح.")
        else:
            await update.message.reply_text("❌ يجب إرسال ملفين PDF على الأقل ليتم الدمج.")
            return
            
    elif action == 'img2pdf' and 'merge_images' in context.user_data:
        images = context.user_data['merge_images']
        if images:
            await update.message.reply_text("⏳ جاري إنتاج ملف PDF من الصور...")
            out_pdf = os.path.join(TEMP_DIR, "images_converted.pdf")
            try:
                success = await images_to_pdf(images, out_pdf)
                if success:
                    with open(out_pdf, 'rb') as f:
                        await update.message.reply_document(document=f, filename="Images_Report.pdf")
            finally:
                for img in images: 
                    if os.path.exists(img): os.unlink(img)
                if os.path.exists(out_pdf): os.unlink(out_pdf)
            await update.message.reply_text("✅ تم تحويل صورك إلى مستند PDF.")
        else:
            await update.message.reply_text("❌ لم تقم بإرسال أي صور بعد.")
            return

    elif action == 'merge_img_pdf' and 'pdf_for_merge' in context.user_data:
        pdf_path = context.user_data.pop('pdf_for_merge')
        images = context.user_data.get('merge_images', [])
        if images:
            await update.message.reply_text("⏳ جاري دمج الصور الملحقة مع ملف الـ PDF...")
            out_mixed = os.path.join(TEMP_DIR, "mixed_output.pdf")
            try:
                await merge_images_with_pdf(pdf_path, images, out_mixed, 'after')
                with open(out_mixed, 'rb') as f:
                    await update.message.reply_document(document=f, filename="Mixed_Document.pdf")
            finally:
                for img in images: 
                    if os.path.exists(img): os.unlink(img)
                if os.path.exists(pdf_path): os.unlink(pdf_path)
                if os.path.exists(out_mixed): os.unlink(out_mixed)
            await update.message.reply_text("✅ تم إلحاق الصور بالملف بنجاح.")
        else:
            if os.path.exists(pdf_path): os.unlink(pdf_path)
            await update.message.reply_text("❌ لم يتم إرسال أي صور لدمجها.")
            return

    context.user_data.clear()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأوامر والمستندات النصية والمدخلات الحرة"""
    # 1. التشفير بكلمة مرور
    if 'pending_encrypt' in context.user_data:
        pdf_path = context.user_data.pop('pending_encrypt')
        password = update.message.text
        await update.message.reply_text("🔒 جاري تشفير الملف وتثبيت الحماية...")
        out_encrypted = pdf_path + "_secured.pdf"
        try:
            await encrypt_pdf(pdf_path, out_encrypted, password)
            with open(out_encrypted, 'rb') as f:
                await update.message.reply_document(document=f, filename="Protected_File.pdf")
        finally:
            if os.path.exists(pdf_path): os.unlink(pdf_path)
            if os.path.exists(out_encrypted): os.unlink(out_encrypted)
        await update.message.reply_text("✅ تم تشفير وقفل المستند بنجاح.")
        context.user_data.clear()
        return

    # 2. إعادة ترتيب الصفحات
    if 'reorder_file' in context.user_data:
        pdf_path = context.user_data.pop('reorder_file')
        order_text = update.message.text
        try:
            order = [int(x.strip()) for x in order_text.split(',')]
            await update.message.reply_text("⏳ جاري إعادة فرز وبناء الترتيب الجديد...")
            out_reordered = pdf_path + "_reorder.pdf"
            pages_count = await reorder_pdf(pdf_path, out_reordered, order)
            with open(out_reordered, 'rb') as f:
                await update.message.reply_document(document=f, filename="Reordered_File.pdf")
            if os.path.exists(out_reordered): os.unlink(out_reordered)
            await update.message.reply_text(f"✅ تمت العملية. إجمالي الصفحات المعاد صياغتها: {pages_count}")
        except Exception as e:
            await update.message.reply_text("❌ خطأ بالترتيب. يرجى كتابة أرقام صحيحة، مثال: 3,1,2")
        finally:
            if os.path.exists(pdf_path): os.unlink(pdf_path)
        context.user_data.clear()
        return

    # 3. تحويل النص المباشر لـ PDF
    if context.user_data.get('action') == 'text2pdf':
        text = update.message.text
        out_txt_pdf = os.path.join(TEMP_DIR, "text_doc.pdf")
        await text_to_pdf(text, out_txt_pdf)
        with open(out_txt_pdf, 'rb') as f:
            await update.message.reply_document(document=f, filename="Text_Document.pdf")
        if os.path.exists(out_txt_pdf): os.unlink(out_txt_pdf)
        await update.message.reply_text("✅ تم تحويل النص المكتوب إلى ملف PDF.")
        context.user_data.clear()
