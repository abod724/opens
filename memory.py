# memory.py
# مسؤول عن إدارة سياق المحادثة الحالية (الذاكرة المؤقتة في RAM)

class ConversationMemory:
    def __init__(self, max_history=20):
        """
        تهيئة الذاكرة المؤقتة.
        max_history: أقصى عدد من الرسائل نحتفظ بها في السياق 
                     (لتجنب تجاوز حد الرموز للنموذج).
        """
        self.max_history = max_history
        self.messages = []  # القائمة التي تحتفظ بالرسائل مؤقتاً

    def add_message(self, role, content):
        """
        إضافة رسالة جديدة إلى سياق المحادثة.
        - role: نوع المرسل (user / assistant / system)
        - content: محتوى النص
        """
        self.messages.append({"role": role, "content": content})
        self._trim_history()  # التأكد من عدم تجاوز الحد الأقصى

    def _trim_history(self):
        """تقليم التاريخ القديم إذا تجاوز العدد المسموح (نافذة منزلقة)."""
        if len(self.messages) > self.max_history:
            # نحذف أقدم الرسائل ونبقي فقط آخر max_history رسالة
            self.messages = self.messages[-self.max_history:]

    def get_context(self):
        """
        استرجاع سياق المحادثة الحالي (القائمة الكاملة).
        يتم إرسال هذه القائمة مباشرة إلى نموذج الذكاء الاصطناعي.
        """
        return self.messages

    def get_last_n_messages(self, n):
        """استرجاع آخر n من الرسائل فقط (للحصول على جزء معين من السياق)."""
        return self.messages[-n:] if n > 0 else []

    def load_from_db(self, db_connection, session_id):
        """
        تحميل المحادثات السابقة من قاعدة البيانات (الذاكرة الدائمة).
        هنا نقوم باستدعاء دالة من database.py لجلب التاريخ القديم.
        """
        try:
            # نفترض أن database.py يحتوي على دالة fetch_history(session_id)
            history = db_connection.fetch_history(session_id)  
            if history:
                # نحتفظ فقط بأحدث الرسائل حسب max_history
                self.messages = history[-self.max_history:]
            else:
                self.messages = []
        except Exception as e:
            print(f"خطأ في تحميل التاريخ من قاعدة البيانات: {e}")
            self.messages = []

    def save_to_db(self, db_connection, session_id):
        """
        حفظ المحادثة الحالية إلى قاعدة البيانات (اختياري، يمكن استدعاؤها عند إنهاء الجلسة).
        """
        try:
            # نفترض أن database.py يحتوي على دالة save_messages(session_id, messages)
            db_connection.save_messages(session_id, self.messages)
        except Exception as e:
            print(f"خطأ في حفظ التاريخ إلى قاعدة البيانات: {e}")

    def clear(self):
        """مسح الذاكرة المؤقتة بالكامل (بدء محادثة جديدة)."""
        self.messages = []

    def __len__(self):
        """إرجاع عدد الرسائل في الذاكرة المؤقتة."""
        return len(self.messages)

    def __str__(self):
        """عرض مقتطف من المحادثة للتصحيح (Debugging)."""
        return f"ConversationMemory(messages={len(self.messages)}, max={self.max_history})"
