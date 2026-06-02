import os
import logging
import tempfile
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import TEMP_DIR, MAX_FILE_SIZE, MAX_IMAGES_MERGE
from utils import *
from spam_protection import spam_protection

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TEMP_DIR.mkdir(parents=True, exist_ok=True)

# القائمة الرئيسية
MAIN_MENU = [
   # [InlineKeyboardButton("🖼 صور → PDF", callback_data='img2pdf')],
   # [InlineKeyboardButton("📝 نص → PDF", callback_data='text2pdf')],
    [InlineKeyboardButton("🔗 دمج PDF", callback_data='merge')],
 #   [InlineKeyboardButton("🖼 دمج صور مع PDF", callback_data='merge_img_pdf')],
    [InlineKeyboardButton("✂️ تقسيم PDF", callback_data='split')],
    [InlineKeyboardButton("🔄 إعادة ترتيب PDF", callback_data='reorder')],
   # [InlineKeyboardButton("🗜 ضغط PDF", callback_data='compress')],
  #  [InlineKeyboardButton("📝 استخراج نصوص", callback_data='extract')],
    [InlineKeyboardButton("🔒 تشفير PDF", callback_data='encrypt')],
    [InlineKeyboardButton("ℹ️ معلومات PDF", callback_data='info')],
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة الأوامر الرئيسية"""
    if not await spam_protection.check(update, context):
        return
    
    # تنظيف البيانات القديمة
    await cleanup_user_data(context)
    
    await update.message.reply_text(
        "🤖 *مرحباً بك في بوت PDF  *\n\n"
        "✨ *المميزات:*\n"

        "• دمج وتقسيم ملفات PDF\n"
        "• ضغط وتشفير PDF\n"
        "• معالجة سريعة وآمنة\n\n"
        "👇 *اختر الخدمة:*",
        reply_markup=InlineKeyboardMarkup(MAIN_MENU),
        parse_mode='Markdown'
    )

async def cleanup_user_data(context: ContextTypes.DEFAULT_TYPE):
    """تنظيف الملفات المؤقتة للمستخدم"""
    user_data = context.user_data
    
    # تنظيف ملفات الدمج
    if 'merge_files' in user_data:
        for file_path in user_data['merge_files']:
            try:
                if Path(file_path).exists():
                    Path(file_path).unlink()
            except:
                pass
    
    # تنظيف الصور
    if 'merge_images' in user_data:
        for img_path in user_data['merge_images']:
            try:
                if Path(img_path).exists():
                    Path(img_path).unlink()
            except:
                pass
    
    # تنظيف الملفات الأخرى
    for key in ['pdf_for_merge', 'pending_encrypt', 'reorder_file', 'temp_pdf']:
        if key in user_data:
            try:
                if Path(user_data[key]).exists():
                    Path(user_data[key]).unlink()
            except:
                pass
    
    user_data.clear()

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على الأزرار"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    context.user_data['action'] = action
    
    messages = {
        'img2pdf': f"📤 أرسل الصور الآن (واحدة تلو الأخرى، كحد أقصى {MAX_IMAGES_MERGE} صورة، ثم اكتب /done)",
        'text2pdf': "📤 أرسل النص الذي تود تحويله إلى ملف PDF",
        'merge': "📤 أرسل ملفات PDF المراد دمجها (ملفاً تلو الآخر، ثم اكتب /done)",
        'merge_img_pdf': "📤 أرسل ملف PDF أولاً، ثم سأطلب منك إرسال الصور",
        'split': "📤 أرسل ملف PDF لتقسيمه إلى صفحات منفصلة",
        'reorder': "📤 أرسل ملف PDF لإعادة ترتيبه أولاً",
        'compress': "📤 أرسل ملف PDF لضغطه وتقليل حجمه",
        'extract': "📤 أرسل ملف PDF لاستخراج النصوص منه",
        'encrypt': "📤 أرسل ملف PDF المراد حمايته بكلمة مرور",
        'info': "📤 أرسل ملف PDF لعرض معلومات عنه",
    }
    
    await query.edit_message_text(
        messages.get(action, "أرسل الملف المطلوب"),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='back')]])
    )

async def handle_documents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الملفات المرسلة"""
    if not await spam_protection.check(update, context):
        return
    
    action = context.user_data.get('action')
    if not action or action == 'back':
        await update.message.reply_text("⚠️ الرجاء اختيار خدمة أولاً من القائمة /start")
        return
    
    document = update.message.document
    if not document:
        await update.message.reply_text("❌ يرجى إرسال ملف صالح")
        return
    
    # التحقق من حجم الملف
    if document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(f"❌ حجم الملف كبير جداً (الحد الأقصى {MAX_FILE_SIZE // (1024*1024)} ميجابايت)")
        return
    
    # التحقق من نوع الملف
    file_name = document.file_name or "unknown.pdf"
    file_ext = Path(file_name).suffix.lower()
    
    if action not in ['info'] and file_ext not in ['.pdf', '.jpg', '.jpeg', '.png', '.webp']:
        await update.message.reply_text("❌ نوع الملف غير مدعوم لهذه الخدمة")
        return
    
    # تحميل الملف
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext, dir=TEMP_DIR)
    file_path = temp_file.name
    temp_file.close()
    
    try:
        file_obj = await document.get_file()
        await file_obj.download_to_drive(file_path)
        
        # معالجة حسب نوع الخدمة
        if action == 'merge':
            if 'merge_files' not in context.user_data:
                context.user_data['merge_files'] = []
            context.user_data['merge_files'].append(file_path)
            count = len(context.user_data['merge_files'])
            await update.message.reply_text(
                f"✅ تم استلام ملف PDF رقم {count}\n"
                f"📊 اسم الملف: {file_name}\n"
                f"📦 حجم الملف: {document.file_size // 1024} كيلوبايت\n\n"
                f"أرسل ملفاً آخر أو اكتب /done للدمج"
            )
            return
        
        elif action == 'merge_img_pdf':
            context.user_data['pdf_for_merge'] = file_path
            context.user_data['merge_images'] = []
            await update.message.reply_text(
                "✅ تم استلام ملف PDF\n"
                f"📄 اسم الملف: {file_name}\n\n"
                "📸 الآن أرسل الصور التي تريد إضافتها، ثم اكتب /done"
            )
            return
        
        elif action == 'encrypt':
            context.user_data['pending_encrypt'] = file_path
            await update.message.reply_text("🔑 أرسل كلمة المرور التي تريد قفل الملف بها الآن:")
            return
        
        elif action == 'reorder':
            context.user_data['reorder_file'] = file_path
            await update.message.reply_text(
                "📝 أرسل ترتيب الصفحات المطلوب مفصولاً بفاصلة\n"
                "مثال: `3,1,2,4`\n\n"
                "✏️ يمكنك تخطي أرقام الصفحات أو تكرارها"
            )
            return
        
        # المعالجة المباشرة
        await update.message.reply_text("⏳ جاري معالجة طلبك، يرجى الانتظار...")
        
        if action == 'split':
            with tempfile.TemporaryDirectory(dir=TEMP_DIR) as temp_dir:
                output_files = await split_pdf(file_path, temp_dir)
                
                if len(output_files) > 10:
                    await update.message.reply_text(f"⚠️ الملف مقسم إلى {len(output_files)} صفحة. سيتم إرسال أول 10 صفحات فقط.")
                    output_files = output_files[:10]
                
                for out_file in output_files:
                    with open(out_file, 'rb') as f:
                        await update.message.reply_document(
                            document=f,
                            filename=Path(out_file).name,
                            caption=f"📄 صفحة {Path(out_file).stem.split('_')[-1]}"
                        )
                
                await update.message.reply_text(f"✅ تم تقسيم الملف إلى {len(output_files)} صفحات")
        
        elif action == 'compress':
            out_compressed = str(Path(file_path).with_suffix('_compressed.pdf'))
            await compress_pdf(file_path, out_compressed)
            
            original_size = Path(file_path).stat().st_size
            compressed_size = Path(out_compressed).stat().st_size
            saved_percent = ((original_size - compressed_size) / original_size) * 100
            
            with open(out_compressed, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename="Compressed_File.pdf",
                    caption=f"✅ تم الضغط بنجاح!\n📊 تم توفير {saved_percent:.1f}% من الحجم"
                )
            
            Path(out_compressed).unlink(missing_ok=True)
        
        elif action == 'extract':
            extracted_text = await extract_text_from_pdf(file_path)
            
            if len(extracted_text) > 4000:
                # تقسيم النص الطويل
                for i in range(0, len(extracted_text), 4000):
                    await update.message.reply_text(
                        extracted_text[i:i+4000],
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(extracted_text, parse_mode='Markdown')
        
        elif action == 'info':
            info = await get_pdf_info(file_path)
            info_text = (
                f"📊 *معلومات ملف PDF*\n\n"
                f"📄 عدد الصفحات: `{info['pages']}`\n"
                f"💾 الحجم: `{info['size_mb']:.2f}` ميجابايت\n"
                f"📝 اسم الملف: `{file_name}`\n"
            )
            
            if info['metadata']:
                info_text += f"\n🏷️ البيانات الوصفية:\n"
                for key, value in info['metadata'].items():
                    if value:
                        info_text += f"• {key}: `{value[:100]}`\n"
            
            await update.message.reply_text(info_text, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in handle_documents: {e}")
        await update.message.reply_text(f"❌ حدث خطأ أثناء المعالجة: {str(e)}")
    
    finally:
        # تنظيف الملف المؤقت
        if Path(file_path).exists() and action not in ['merge', 'merge_img_pdf', 'encrypt', 'reorder']:
            Path(file_path).unlink()

async def handle_photos_for_merge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الصور لخدمات الصور"""
    action = context.user_data.get('action')
    
    if action not in ['img2pdf', 'merge_img_pdf']:
        return
    
    if 'merge_images' not in context.user_data:
        context.user_data['merge_images'] = []
    
    # التحقق من الحد الأقصى
    if len(context.user_data['merge_images']) >= MAX_IMAGES_MERGE:
        await update.message.reply_text(f"⚠️ تم الوصول للحد الأقصى ({MAX_IMAGES_MERGE} صورة). اكتب /done للتنفيذ")
        return
    
    # تحميل الصورة
    photo = update.message.photo[-1]  # أفضل جودة
    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", dir=TEMP_DIR)
    img_path = temp_img.name
    temp_img.close()
    
    await photo.get_file().download_to_drive(img_path)
    context.user_data['merge_images'].append(img_path)
    
    count = len(context.user_data['merge_images'])
    await update.message.reply_text(
        f"✅ تم استلام الصورة رقم {count}\n"
        f"📸 أرسل المزيد أو اكتب /done للتنفيذ"
    )

async def handle_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنفيذ العمليات المتعددة"""
    action = context.user_data.get('action')
    
    if not action:
        await update.message.reply_text("⚠️ لا توجد عملية نشطة. استخدم /start")
        return
    
    try:
        # دمج ملفات PDF
        if action == 'merge' and context.user_data.get('merge_files'):
            files = context.user_data['merge_files']
            if len(files) < 2:
                await update.message.reply_text("❌ يجب إرسال ملفين PDF على الأقل للدمج")
                return
            
            await update.message.reply_text(f"⏳ جاري دمج {len(files)} ملف PDF...")
            out_merged = TEMP_DIR / "merged_final.pdf"
            
            try:
                await merge_pdfs(files, str(out_merged))
                
                # الحصول على معلومات الملف الناتج
                info = await get_pdf_info(str(out_merged))
                
                with open(out_merged, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename="Merged_Document.pdf",
                        caption=f"✅ تم دمج {len(files)} ملف بنجاح\n📄 إجمالي الصفحات: {info['pages']}"
                    )
            finally:
                # تنظيف الملفات
                for f in files:
                    Path(f).unlink(missing_ok=True)
                out_merged.unlink(missing_ok=True)
            
            return
        
        # تحويل الصور إلى PDF
        elif action == 'img2pdf' and context.user_data.get('merge_images'):
            images = context.user_data['merge_images']
            if not images:
                await update.message.reply_text("❌ لم تقم بإرسال أي صور بعد")
                return
            
            await update.message.reply_text(f"⏳ جاري تحويل {len(images)} صورة إلى PDF...")
            out_pdf = TEMP_DIR / "images_converted.pdf"
            
            try:
                success = await images_to_pdf(images, str(out_pdf))
                if success:
                    with open(out_pdf, 'rb') as f:
                        await update.message.reply_document(
                            document=f,
                            filename="Images_To_PDF.pdf",
                            caption=f"✅ تم تحويل {len(images)} صورة إلى PDF"
                        )
                else:
                    await update.message.reply_text("❌ فشل تحويل الصور إلى PDF")
            finally:
                for img in images:
                    Path(img).unlink(missing_ok=True)
                out_pdf.unlink(missing_ok=True)
            
            return
        
        # دمج الصور مع PDF
        elif action == 'merge_img_pdf' and context.user_data.get('pdf_for_merge'):
            pdf_path = context.user_data.pop('pdf_for_merge')
            images = context.user_data.get('merge_images', [])
            
            if not images:
                await update.message.reply_text("❌ لم يتم إرسال أي صور لدمجها")
                if Path(pdf_path).exists():
                    Path(pdf_path).unlink()
                return
            
            await update.message.reply_text(f"⏳ جاري دمج {len(images)} صورة مع ملف PDF...")
            out_mixed = TEMP_DIR / "mixed_output.pdf"
            
            try:
                await merge_images_with_pdf(pdf_path, images, str(out_mixed), 'after')
                
                info = await get_pdf_info(str(out_mixed))
                with open(out_mixed, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename="PDF_With_Images.pdf",
                        caption=f"✅ تم دمج {len(images)} صورة مع PDF\n📄 إجمالي الصفحات: {info['pages']}"
                    )
            finally:
                for img in images:
                    Path(img).unlink(missing_ok=True)
                Path(pdf_path).unlink(missing_ok=True)
                out_mixed.unlink(missing_ok=True)
            
            return
        
        else:
            await update.message.reply_text("⚠️ لا توجد ملفات للتنفيذ. ابدأ عملية جديدة بـ /start")
    
    except Exception as e:
        logger.error(f"Error in handle_done: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")
    
    finally:
        await cleanup_user_data(context)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة النصوص (كلمة المرور، ترتيب الصفحات، تحويل النص)"""
    text = update.message.text
    
    # معالجة العودة للقائمة الرئيسية
    if text == '/start':
        await start(update, context)
        return
    
    # تشفير PDF
    if context.user_data.get('pending_encrypt'):
        pdf_path = context.user_data.pop('pending_encrypt')
        password = text
        
        if len(password) < 4:
            await update.message.reply_text("⚠️ كلمة المرور يجب أن تكون 4 أحرف على الأقل")
            context.user_data['pending_encrypt'] = pdf_path  # إعادة الملف
            return
        
        await update.message.reply_text("🔒 جاري تشفير الملف...")
        out_encrypted = str(Path(pdf_path).with_suffix('.encrypted.pdf'))
        
        try:
            await encrypt_pdf(pdf_path, out_encrypted, password)
            
            with open(out_encrypted, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename="Protected_File.pdf",
                    caption="✅ تم تشفير الملف بنجاح!\n🔑 تذكر كلمة المرور جيداً"
                )
        except Exception as e:
            await update.message.reply_text(f"❌ فشل التشفير: {str(e)}")
        finally:
            Path(pdf_path).unlink(missing_ok=True)
            Path(out_encrypted).unlink(missing_ok=True)
        
        await cleanup_user_data(context)
        return
    
    # إعادة ترتيب PDF
    if context.user_data.get('reorder_file'):
        pdf_path = context.user_data.pop('reorder_file')
        order_text = text
        
        try:
            # تحويل النص إلى قائمة أرقام
            order = [int(x.strip()) for x in order_text.split(',') if x.strip().isdigit()]
            
            if not order:
                raise ValueError("لم يتم إدخال أرقام صحيحة")
            
            await update.message.reply_text("⏳ جاري إعادة ترتيب الصفحات...")
            out_reordered = str(Path(pdf_path).with_suffix('.reordered.pdf'))
            
            pages_count = await reorder_pdf(pdf_path, out_reordered, order)
            
            with open(out_reordered, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename="Reordered_File.pdf",
                    caption=f"✅ تم إعادة ترتيب {pages_count} صفحة بنجاح"
                )
            
            Path(out_reordered).unlink(missing_ok=True)
        except ValueError as e:
            await update.message.reply_text("❌ خطأ في الصيغة. مثال صحيح: `3,1,2,4`")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ في المعالجة: {str(e)}")
        finally:
            Path(pdf_path).unlink(missing_ok=True)
        
        await cleanup_user_data(context)
        return
    
    # تحويل النص المباشر إلى PDF
    if context.user_data.get('action') == 'text2pdf':
        if len(text) > 5000:
            await update.message.reply_text("⚠️ النص طويل جداً (الحد الأقصى 5000 حرف). قم بتقصيره وحاول مرة أخرى")
            return
        
        await update.message.reply_text("⏳ جاري تحويل النص إلى PDF...")
        out_txt_pdf = TEMP_DIR / "text_document.pdf"
        
        try:
            await text_to_pdf(text, str(out_txt_pdf))
            
            with open(out_txt_pdf, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename="Text_Document.pdf",
                    caption="✅ تم تحويل النص إلى PDF"
                )
        except Exception as e:
            await update.message.reply_text(f"❌ فشل التحويل: {str(e)}")
        finally:
            out_txt_pdf.unlink(missing_ok=True)
        
        await cleanup_user_data(context)
