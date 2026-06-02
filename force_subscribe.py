import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import FORCE_SUBSCRIBE_CHANNEL, FORCE_SUBSCRIBE_CHANNEL_ID

logger = logging.getLogger(__name__)

# معرف القناة @BEXO50
# يمكنك الحصول عليه من خلال @userinfobot أو عن طريق إرسال رسالة للقناة وجلب التحديثات
# مثال: -1001234567890
CHANNEL_USERNAME = "@BEXO50"
CHANNEL_ID = None  # سيتم ملؤه تلقائياً أو من config

async def get_channel_id(context: ContextTypes.DEFAULT_TYPE, username: str = "BEXO50"):
    """الحصول على معرف القناة الرقمي"""
    try:
        chat = await context.bot.get_chat(f"@{username}")
        return chat.id
    except Exception as e:
        logger.error(f"لا يمكن الحصول على معرف القناة: {e}")
        return None

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من اشتراك المستخدم في القناة"""
    user_id = update.effective_user.id
    
    # التحقق من التهيئة
    if 'force_subscribe' not in context.bot_data:
        context.bot_data['force_subscribe'] = {
            'channel_username': CHANNEL_USERNAME,
            'channel_id': None,
            'enabled': True
        }
    
    # جلب معرف القناة إذا لم يكن موجوداً
    if context.bot_data['force_subscribe']['channel_id'] is None:
        context.bot_data['force_subscribe']['channel_id'] = await get_channel_id(context, "BEXO50")
        if context.bot_data['force_subscribe']['channel_id'] is None:
            # إذا فشل جلب المعرف، نسمح بالاستخدام (تفادي تعطل البوت)
            logger.warning("⚠️ لم يتم العثور على القناة، تعطيل الاشتراك الإجباري مؤقتاً")
            return True
    
    # إذا كانت الميزة معطلة
    if not context.bot_data['force_subscribe']['enabled']:
        return True
    
    try:
        # التحقق من عضوية المستخدم
        chat_member = await context.bot.get_chat_member(
            chat_id=context.bot_data['force_subscribe']['channel_id'],
            user_id=user_id
        )
        
        # الحالات المسموح بها: عضو، مدير، منشئ
        allowed_statuses = ['member', 'administrator', 'creator']
        
        if chat_member.status in allowed_statuses:
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"خطأ في التحقق من الاشتراك: {e}")
        # في حالة الخطأ، نسمح بالاستخدام (تفادي تعطل البوت)
        return True

async def send_subscription_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة تطلب الاشتراك في القناة"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/BEXO50")],
        [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data='check_subscription')]
    ])
    
    message_text = (
        "🔒 *اشتراك إجباري*\n\n"
        "عذراً، يجب عليك الاشتراك في قناتنا أولاً لاستخدام البوت.\n\n"
        "📢 *قناة البوت:* @BEXO50\n\n"
        "👇 اضغط على الزر أدناه للاشتراك، ثم اضغط *تحقق من الاشتراك*"
    )
    
    await update.message.reply_text(
        message_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def handle_subscription_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة طلب التحقق من الاشتراك"""
    query = update.callback_query
    await query.answer()
    
    if await check_subscription(update, context):
        await query.edit_message_text(
            "✅ *تم التحقق بنجاح!*\n\n"
            "شكراً لاشتراكك في قناتنا. يمكنك الآن استخدام البوت.\n"
            "اكتب /start لبدء الاستخدام.",
            parse_mode='Markdown'
        )
        # تنظيف البيانات المؤقتة
        context.user_data.clear()
    else:
        await query.answer("❌ لم تشترك بعد! يرجى الاشتراك ثم حاول مرة أخرى.", show_alert=True)

# ديكوراتور للتحقق من الاشتراك قبل تنفيذ أي أمر
def require_subscription(func):
    """ديكوراتور للتحقق من الاشتراك قبل تنفيذ الدالة"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # تخطي التحقق للأوامر الداخلية
        if update.callback_query and update.callback_query.data == 'check_subscription':
            return await func(update, context, *args, **kwargs)
        
        # التحقق من الاشتراك
        if not await check_subscription(update, context):
            await send_subscription_message(update, context)
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper
