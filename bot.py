#!/usr/bin/env python
import sys
import logging
from pathlib import Path
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TOKEN, LOG_DIR
from handlers import start, handle_callback, handle_documents, handle_done, handle_text

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_DIR / 'bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """تشغيل البوت"""
    if not TOKEN:
        logger.error("❌ توكن البوت غير موجود في متغيرات البيئة!")
        sys.exit(1)
    
    logger.info("🚀 جاري تشغيل بوت PDF...")
    logger.info("🔒 ميزة الاشتراك الإجباري مفعلة - القناة: @BEXO50")
    
    try:
        app = Application.builder().token(TOKEN).build()
        
        # إضافة المعالجات
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("done", handle_done))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(filters.Document.ALL, handle_documents))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        logger.info("✅ البوت جاهز للعمل!")
        
        # تشغيل البوت
        app.run_polling(drop_pending_updates=True)
    
    except Exception as e:
        logger.error(f"❌ فشل تشغيل البوت: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
