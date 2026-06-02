import os

# ⚠️ يتم جلب التوكن من متغيرات البيئة لمنع التسريب
TOKEN = os.environ.get('BOT_TOKEN', '')

# إعدادات الحماية
SPAM_LIMIT_SECONDS = 2
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 ميجابايت

# المجلد المؤقت للملفات
TEMP_DIR = os.environ.get('TEMP_DIR', '/tmp/pdf_bot')

# إعدادات الاستضافة لـ Railway
PORT = int(os.environ.get('PORT', 8080))
