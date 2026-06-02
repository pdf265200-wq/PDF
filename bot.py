#!/usr/bin/env python3
import os
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TOKEN, PORT
from handlers import start, handle_documents, handle_text, handle_callback

def main():
    """تشغيل البوت"""
    if not TOKEN or TOKEN == "ضع_توكن_البوت_هنا":
        print("❌ خطأ: الرجاء وضع توكن البوت في ملف config.py")
        return
    
    # إنشاء التطبيق
    app = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_documents))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # تشغيل البوت
    print("✅ البوت يعمل...")
    
    # للتشغيل على Termux
    app.run_polling()
    
    # للتشغيل على Railway (استخدم هذا لاحقاً)
    # app.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=f"https://your-app.railway.app/webhook")

if __name__ == "__main__":
    main()
