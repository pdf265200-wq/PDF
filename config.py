import os
from pathlib import Path

# ⚠️ يتم جلب التوكن من متغيرات البيئة
TOKEN = os.environ.get('BOT_TOKEN', '')

# إعدادات الحماية المتقدمة
SPAM_LIMIT_SECONDS = 2
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 ميجابايت
MAX_PAGES_EXTRACT = 50  # الحد الأقصى للصفحات المستخرجة
MAX_IMAGES_MERGE = 100  # الحد الأقصى للصور المدمجة

# المسارات
BASE_DIR = Path(__file__).parent
TEMP_DIR = Path(os.environ.get('TEMP_DIR', '/tmp/pdf_bot'))
LOG_DIR = BASE_DIR / 'logs'

# إنشاء المجلدات
TEMP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# إعدادات الاستضافة
PORT = int(os.environ.get('PORT', 8080))
