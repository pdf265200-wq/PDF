#!/usr/bin/env python
import os
import sys
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TOKEN
from handlers import start, handle_callback, handle_documents, handle_photos_for_merge, handle_text, handle_done
from spam_protection import spam_protection

def main():
    """تشغيل البوت"""
    if not TOKEN:
        print("❌ خطأ: الرجاء وضع توكن البوت في config.py أو متغيرات البيئة")
        return
    
    print("✅ جاري تشغيل بوت PDF...")
    
    # إنشاء التطبيق
    app = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", handle_done))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photos_for_merge))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_documents))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ البوت يعمل بنجاح! اذهب إلى تلجرام وجرب /start")
    
    # تشغيل البوت
    app.run_polling()

if __name__ == "__main__":
    main()
