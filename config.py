# إعدادات البوت
import os

# ⚠️ لا تضع التوكن هنا! استخدم متغيرات البيئة
TOKEN = os.environ.get('BOT_TOKEN', '')

# إعدادات الحماية من السبام
SPAM_LIMIT_SECONDS = 2

# إعدادات الملفات
MAX_FILE_SIZE = 20 * 1024 * 1024
TEMP_DIR = "/tmp/pdf_bot"

# إعدادات Railway
PORT = 8080
