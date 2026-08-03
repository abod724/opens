from datetime import date, datetime
from database import fetch_one, fetch_all, execute_query

def get_user_plan(user_id):
    """
    جلب خطة المستخدم الحالية
    إذا لم يكن لديه اشتراك، يرجع الخطة المجانية
    """
    query = """
        SELECT p.id, p.name, p.daily_limit, p.features, us.end_date
        FROM user_subscriptions us
        JOIN plans p ON us.plan_id = p.id
        WHERE us.user_id = %s AND us.status = 'active'
        AND (us.end_date IS NULL OR us.end_date > NOW())
    """
    plan = fetch_one(query, (user_id,))
    
    if not plan:
        # إذا لم يجد اشتراكاً، ارجع الخطة المجانية
        free_plan = fetch_one("SELECT id, name, daily_limit, features FROM plans WHERE name = 'free'")
        if free_plan:
            return {
                'id': free_plan[0],
                'name': free_plan[1],
                'daily_limit': free_plan[2],
                'features': free_plan[3] or {},
                'end_date': None
            }
        # خطة افتراضية (أمان)
        return {
            'id': None,
            'name': 'free',
            'daily_limit': 9999,
            'features': {},
            'end_date': None
        }
    
    return {
        'id': plan[0],
        'name': plan[1],
        'daily_limit': plan[2],
        'features': plan[3] or {},
        'end_date': plan[4]
    }

def check_daily_limit(user_id):
    """
    التحقق من عدم تجاوز الحد اليومي للمحادثات
    ترجع (boolean, message)
    """
    plan = get_user_plan(user_id)
    today = date.today()
    
    # جلب عدد المحادثات اليومية
    query = """
        SELECT message_count FROM daily_usage
        WHERE user_id = %s AND usage_date = %s
    """
    row = fetch_one(query, (user_id, today))
    count = row[0] if row else 0
    
    if count >= plan['daily_limit']:
        return False, f"⚠️ لقد تجاوزت حد المحادثات اليومي ({plan['daily_limit']}). يرجى الترقية للاستمرار."
    
    return True, None

def increment_daily_usage(user_id):
    """
    زيادة عداد المحادثات اليومية للمستخدم
    """
    today = date.today()
    query = """
        INSERT INTO daily_usage (user_id, usage_date, message_count)
        VALUES (%s, %s, 1)
        ON CONFLICT (user_id, usage_date)
        DO UPDATE SET message_count = daily_usage.message_count + 1
    """
    execute_query(query, (user_id, today))

def upgrade_user(user_id, plan_name='premium', duration_months=1):
    """
    ترقية المستخدم إلى خطة مدفوعة
    """
    # جلب معرف الخطة
    plan = fetch_one("SELECT id, price FROM plans WHERE name = %s", (plan_name,))
    if not plan:
        return False, "الخطة غير موجودة"
    
    plan_id = plan[0]
    
    # حساب تاريخ الانتهاء
    end_date = datetime.now() + timedelta(days=30 * duration_months)
    
    # تحديث أو إدراج اشتراك جديد
    query = """
        INSERT INTO user_subscriptions (user_id, plan_id, status, end_date)
        VALUES (%s, %s, 'active', %s)
        ON CONFLICT (user_id, plan_id) 
        DO UPDATE SET status = 'active', end_date = %s, updated_at = CURRENT_TIMESTAMP
    """
    execute_query(query, (user_id, plan_id, end_date, end_date))
    
    return True, "تمت الترقية بنجاح!"

def get_daily_usage(user_id):
    """
    جلب عدد المحادثات المستخدمة اليوم
    """
    today = date.today()
    query = """
        SELECT message_count FROM daily_usage
        WHERE user_id = %s AND usage_date = %s
    """
    row = fetch_one(query, (user_id, today))
    return row[0] if row else 0

def reset_daily_usage(user_id):
    """
    إعادة تعيين عداد الاستخدام اليومي (للتجربة أو التصحيح)
    """
    today = date.today()
    execute_query(
        "DELETE FROM daily_usage WHERE user_id = %s AND usage_date = %s",
        (user_id, today)
    )
