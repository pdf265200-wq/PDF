#!/usr/bin/env python
import sys
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TOKEN
from handlers import start, handle_callback, handle_documents, handle_photos_for_merge, handle_text, handle_done

def main():
    """تشغيل وإقلاع بوت تلجرام"""
    if not TOKEN:
        print("❌ خطأ فادح: توكن البوت غير معرّف بمتغيرات البيئة (BOT_TOKEN)!")
        sys.exit(1)
    
    print("🚀 جاري تهيئة خوادم معالجة مستندات الـ PDF الشاملة لعام 2026...")
    
    # بناء التطبيق بالتوكن المرفق
    app = Application.builder().token(TOKEN).build()
    
    # ربط وتوجيه المعالجات والأحداث
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", handle_done))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photos_for_merge))
    app.add_handler(MessageHandler(filters.Document.PDF | filters.Document.ALL, handle_documents))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 البوت يعمل بنشاح تام وفي وضع جاهزية الاستقبال الآن.")
    
    # تشغيل البوت (Polling)
    app.run_polling()

if __name__ == "__main__":
    main()
