import os
import logging
import tempfile
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import TEMP_DIR, MAX_FILE_SIZE, MAX_IMAGES_MERGE
from utils import *
from spam_protection import spam_protection
from force_subscribe import require_subscription, handle_subscription_check

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TEMP_DIR.mkdir(parents=True, exist_ok=True)

# القائمة الرئيسية (الخدمات المتاحة فقط)
MAIN_MENU = [
    [InlineKeyboardButton("🔗 دمج PDF", callback_data='merge')],
    [InlineKeyboardButton("✂️ تقسيم PDF", callback_data='split')],
    [InlineKeyboardButton("🔒 تشفير PDF", callback_data='encrypt')],
    [InlineKeyboardButton("ℹ️ معلومات PDF", callback_data='info')],
   # [InlineKeyboardButton("📢 قناة البوت", url="https://t.me/BEXO50")],
]

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

@require_subscription
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة الأوامر الرئيسية"""
    if not await spam_protection.check(update, context):
        return
    
    # تنظيف البيانات القديمة
    await cleanup_user_data(context)
    
    await update.message.reply_text(
        "🤖 *مرحباً بك في بوت PDF*\n\n"
        "✨ *المميزات:*\n"
        "• دمج ملفات PDF\n"
        "• تقسيم ملفات PDF\n"
        "• تشفير PDF\n"
        "• معلومات عن PDF\n\n"
        "👇 *اختر الخدمة:*",
        reply_markup=InlineKeyboardMarkup(MAIN_MENU),
        parse_mode='Markdown'
    )

@require_subscription
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على الأزرار"""
    query = update.callback_query
    
    # معالجة التحقق من الاشتراك
    if query.data == 'check_subscription':
        await handle_subscription_check(update, context)
        return
    
    await query.answer()
    
    action = query.data
    
    # معالجة زر الرجوع
    if action == 'back':
        await query.edit_message_text(
            "🤖 *مرحباً بك في بوت PDF*\n\n"
            "👇 *اختر الخدمة:*",
            reply_markup=InlineKeyboardMarkup(MAIN_MENU),
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return
    
    context.user_data['action'] = action
    
    messages = {
        'merge': "📤 أرسل ملفات PDF المراد دمجها (ملفاً تلو الآخر، ثم اكتب /done)",
        'split': "📤 أرسل ملف PDF لتقسيمه إلى صفحات منفصلة",
        'encrypt': "📤 أرسل ملف PDF المراد حمايته بكلمة مرور",
        'info': "📤 أرسل ملف PDF لعرض معلومات عنه",
    }
    
    back_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع", callback_data='back')],
        [InlineKeyboardButton("📢 قناة البوت", url="https://t.me/BEXO50")]
    ])
    
    await query.edit_message_text(
        messages.get(action, "أرسل الملف المطلوب"),
        reply_markup=back_button
    )

@require_subscription
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
    
    if file_ext != '.pdf':
        await update.message.reply_text("❌ هذا البوت يدعم ملفات PDF فقط")
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
        
        elif action == 'encrypt':
            context.user_data['pending_encrypt'] = file_path
            await update.message.reply_text("🔑 أرسل كلمة المرور التي تريد قفل الملف بها الآن:")
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
        
        elif action == 'info':
            info = await get_pdf_info(file_path)
            info_text = (
                f"📊 *معلومات ملف PDF*\n\n"
                f"📄 عدد الصفحات: `{info['pages']}`\n"
                f"💾 الحجم: `{info['size_mb']:.2f}` ميجابايت\n"
                f"📝 اسم الملف: `{file_name}`\n"
            )
            
            if info.get('metadata'):
                info_text += f"\n🏷️ البيانات الوصفية:\n"
                for key, value in info['metadata'].items():
                    if value:
                        info_text += f"• {key}: `{str(value)[:100]}`\n"
            
            await update.message.reply_text(info_text, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Error in handle_documents: {e}")
        await update.message.reply_text(f"❌ حدث خطأ أثناء المعالجة: {str(e)}")
    
    finally:
        # تنظيف الملف المؤقت
        if Path(file_path).exists() and action not in ['merge', 'encrypt']:
            Path(file_path).unlink()

@require_subscription
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
        
        else:
            await update.message.reply_text("⚠️ لا توجد ملفات للتنفيذ. ابدأ عملية جديدة بـ /start")
    
    except Exception as e:
        logger.error(f"Error in handle_done: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")
    
    finally:
        await cleanup_user_data(context)

@require_subscription
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة النصوص (كلمة المرور)"""
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
            context.user_data['pending_encrypt'] = pdf_path
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
    
    # إذا كان النص لا يخص أي عملية
    if context.user_data.get('action'):
        await update.message.reply_text("❌ أمر غير معروف. استخدم /start للقائمة الرئيسية")
