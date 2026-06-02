import time
from typing import Dict
from telegram import Update
from telegram.ext import ContextTypes

class SpamProtection:
    def __init__(self, limit_seconds: int = 2):
        self.user_last_command: Dict[int, float] = {}
        self.limit_seconds = limit_seconds
    
    async def check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """التحقق من السبام"""
        if not update.message or not update.message.text:
            return True
        
        # السماح بكلمات المرور وترتيب الصفحات
        action = context.user_data.get('action')
        if action in ['encrypt', 'reorder']:
            return True
        
        user_id = update.effective_user.id
        now = time.time()
        last = self.user_last_command.get(user_id, 0)
        
        if now - last < self.limit_seconds:
            await update.message.reply_text(
                "⏳ *توقف قليلاً!*\n"
                f"انتظر {self.limit_seconds} ثانية قبل إرسال أمر جديد.",
                parse_mode='Markdown'
            )
            return False
        
        self.user_last_command[user_id] = now
        return True

# إنشاء نسخة عامة
spam_protection = SpamProtection()
