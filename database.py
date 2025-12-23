import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import jdatetime

class Database:
    def __init__(self, db_name='food_reservation.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        """ایجاد اتصال به دیتابیس"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # برای بازگشت دیکشنری
        return conn
    
    def init_db(self):
        """ایجاد جداول دیتابیس"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. جدول کاربران
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            department TEXT,
            is_active BOOLEAN DEFAULT 1,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 2. جدول منوهای هفتگی
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS weekly_menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start DATE NOT NULL,
            week_end DATE NOT NULL,
            reservation_deadline DATETIME NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 3. جدول آیتم‌های منو
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weekly_menu_id INTEGER NOT NULL,
            day_of_week TEXT NOT NULL,
            food_name TEXT NOT NULL,
            description TEXT,
            full_price REAL NOT NULL,
            user_price REAL NOT NULL,
            company_share REAL NOT NULL,
            capacity INTEGER NOT NULL,
            reserved_count INTEGER DEFAULT 0,
            extra_food BOOLEAN DEFAULT 0,
            extra_food_price REAL,
            FOREIGN KEY (weekly_menu_id) REFERENCES weekly_menus(id) ON DELETE CASCADE
        )
        ''')
        
        # 4. جدول رزروها
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            reservation_date DATE NOT NULL,
            quantity INTEGER DEFAULT 1,
            is_extra BOOLEAN DEFAULT 0,
            paid_amount REAL NOT NULL,
            status TEXT DEFAULT 'PENDING',
            reserved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id) ON DELETE CASCADE
        )
        ''')
        
        # ایجاد داده‌های اولیه
        self.create_initial_data(cursor)
        
        conn.commit()
        conn.close()
        print("✅ پایگاه داده ایجاد شد")
    
    def create_initial_data(self, cursor):
        """ایجاد داده‌های اولیه"""
        # بررسی وجود کاربران
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            self._create_users(cursor)
        
        # بررسی وجود منو
        cursor.execute("SELECT COUNT(*) FROM weekly_menus")
        if cursor.fetchone()[0] == 0:
            self._create_sample_menu(cursor)
    
    def _create_users(self, cursor):
        """ایجاد کاربران اولیه"""
        users = [
            ('ADMIN001', 'مدیر سیستم', 'admin@company.com', 'Admin@123!', 'IT', 1),
            ('EMP001', 'رضا محمدی', 'reza@company.com', 'User@123!', 'فروش', 0),
            ('EMP002', 'سارا احمدی', 'sara@company.com', 'User@123!', 'مالی', 0),
            ('EMP003', 'علی کریمی', 'ali@company.com', 'User@123!', 'پشتیبانی', 0)
        ]
        
        for user in users:
            cursor.execute('''
            INSERT INTO users (employee_id, full_name, email, password, department, is_admin)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', user)
        
        print("✅ کاربران اولیه ایجاد شدند")
    
    def _create_sample_menu(self, cursor):
        """ایجاد منوی نمونه با تاریخ شمسی"""
        # تاریخ امروز به شمسی
        today_jalali = jdatetime.datetime.now()
        
        # پیدا کردن شنبه این هفته
        current_weekday = today_jalali.weekday()  # 0=شنبه, 1=یکشنبه, ...
        
        if current_weekday == 0:  # اگر امروز شنبه است
            week_start = today_jalali
        else:
            # رفتن به شنبه گذشته
            week_start = today_jalali - timedelta(days=current_weekday)
        
        # هفته کاری از شنبه تا چهارشنبه (5 روز)
        week_end = week_start + timedelta(days=4)
        
        # مهلت رزرو: چهارشنبه ساعت ۱۸:۰۰
        deadline = week_start + timedelta(days=3, hours=18)  # سه روز بعد از شنبه = چهارشنبه
        
        # تبدیل به رشته برای ذخیره در دیتابیس
        week_start_str = week_start.strftime('%Y-%m-%d')
        week_end_str = week_end.strftime('%Y-%m-%d')
        deadline_str = deadline.togregorian().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"📅 ایجاد منوی هفته شمسی:")
        print(f"   شروع: {week_start_str} ({week_start.strftime('%Y/%m/%d')} شمسی)")
        print(f"   پایان: {week_end_str} ({week_end.strftime('%Y/%m/%d')} شمسی)")
        print(f"   مهلت: {deadline_str}")
        
        # ایجاد منوی هفتگی
        cursor.execute('''
        INSERT INTO weekly_menus (week_start, week_end, reservation_deadline, is_active)
        VALUES (?, ?, ?, ?)
        ''', (week_start_str, week_end_str, deadline_str, 1))
        
        weekly_menu_id = cursor.lastrowid
        
        # روزهای هفته به فارسی
        days_fa = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه']
        
        # غذاهای نمونه برای هر روز (2 غذا برای هر روز)
        foods = []
        for i, day in enumerate(days_fa):
            # غذا اول برای هر روز
            foods.append((
                weekly_menu_id, day, 'قیمه بادمجان', 'با گوشت گوساله و لپه', 50000, 30000, 20000, 50
            ))
            # غذا دوم برای هر روز (گزینه دوم)
            foods.append((
                weekly_menu_id, day, 'مرغ گریل شده', 'با سس مخصوص', 45000, 27000, 18000, 40
            ))
        
        for food in foods:
            cursor.execute('''
            INSERT INTO menu_items 
            (weekly_menu_id, day_of_week, food_name, description, full_price, user_price, company_share, capacity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', food)
        
        print("✅ منوی نمونه (شمسی) ایجاد شد")
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """احراز هویت کاربر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM users 
        WHERE email = ? AND password = ? AND is_active = 1
        ''', (email, password))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_weekly_menu(self) -> Optional[Dict]:
        """دریافت منوی هفته جاری"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # دریافت آخرین منوی فعال
        cursor.execute('''
        SELECT * FROM weekly_menus 
        WHERE is_active = 1 
        ORDER BY week_start DESC 
        LIMIT 1
        ''')
        
        menu_row = cursor.fetchone()
        
        if not menu_row:
            conn.close()
            return None
        
        # تبدیل به دیکشنری
        menu = dict(menu_row)
        
        # دریافت آیتم‌های منو
        cursor.execute('''
        SELECT * FROM menu_items 
        WHERE weekly_menu_id = ? 
        ORDER BY 
            CASE day_of_week
                WHEN 'شنبه' THEN 1
                WHEN 'یکشنبه' THEN 2
                WHEN 'دوشنبه' THEN 3
                WHEN 'سه‌شنبه' THEN 4
                WHEN 'چهارشنبه' THEN 5
                ELSE 6
            END
        ''', (menu['id'],))
        
        items = []
        for row in cursor.fetchall():
            items.append(dict(row))
        
        menu['items'] = items
        conn.close()
        
        return menu
    
    def get_all_users(self) -> List[Dict]:
        """دریافت همه کاربران"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        
        users = []
        for row in cursor.fetchall():
            users.append(dict(row))
        
        conn.close()
        return users
    
    def get_user_reservations(self, user_id: int) -> List[Dict]:
        """دریافت رزروهای یک کاربر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT r.*, m.food_name, m.day_of_week
        FROM reservations r
        JOIN menu_items m ON r.menu_item_id = m.id
        WHERE r.user_id = ? AND r.status = 'CONFIRMED'
        ORDER BY r.reserved_at DESC
        ''', (user_id,))
        
        reservations = []
        for row in cursor.fetchall():
            reservations.append(dict(row))
        
        conn.close()
        return reservations
    
    def create_reservation(self, user_id: int, menu_item_id: int, quantity: int = 1, is_extra: bool = False):
        """ایجاد رزرو جدید"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # دریافت اطلاعات غذا
            cursor.execute('SELECT * FROM menu_items WHERE id = ?', (menu_item_id,))
            menu_item = cursor.fetchone()
            
            if not menu_item:
                conn.close()
                return False, "غذا پیدا نشد"
            
            menu_item = dict(menu_item)
            
            # بررسی ظرفیت
            if menu_item['reserved_count'] + quantity > menu_item['capacity']:
                conn.close()
                return False, "ظرفیت کامل است"
            
            # محاسبه مبلغ
            if is_extra and menu_item['extra_food']:
                paid_amount = menu_item['extra_food_price'] * quantity
            else:
                paid_amount = menu_item['user_price'] * quantity
            
            # ایجاد رزرو
            cursor.execute('''
            INSERT INTO reservations (user_id, menu_item_id, reservation_date, quantity, is_extra, paid_amount, status)
            VALUES (?, ?, DATE('now'), ?, ?, ?, 'CONFIRMED')
            ''', (user_id, menu_item_id, quantity, 1 if is_extra else 0, paid_amount))
            
            # به‌روزرسانی تعداد رزرو شده
            cursor.execute('''
            UPDATE menu_items 
            SET reserved_count = reserved_count + ? 
            WHERE id = ?
            ''', (quantity, menu_item_id))
            
            conn.commit()
            conn.close()
            
            return True, "رزرو با موفقیت ثبت شد"
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"خطا در ثبت رزرو: {str(e)}"
    
    def create_user(self, employee_id: str, full_name: str, email: str, password: str, 
                   department: str, is_admin: bool = False):
        """ایجاد کاربر جدید"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO users (employee_id, full_name, email, password, department, is_admin)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (employee_id, full_name, email, password, department, 1 if is_admin else 0))
            
            conn.commit()
            conn.close()
            return True, "کاربر با موفقیت ایجاد شد"
            
        except sqlite3.IntegrityError as e:
            conn.close()
            if "UNIQUE constraint failed: users.email" in str(e):
                return False, "این ایمیل قبلاً ثبت شده است"
            elif "UNIQUE constraint failed: users.employee_id" in str(e):
                return False, "این شماره پرسنلی قبلاً ثبت شده است"
            else:
                return False, f"خطا در ایجاد کاربر: {str(e)}"
        except Exception as e:
            conn.close()
            return False, f"خطای ناشناخته: {str(e)}"
    
    def calculate_stats(self) -> Dict:
        """محاسبه آمار سیستم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {
            'total_users': 0,
            'total_reservations': 0,
            'total_company_share': 0,
            'total_user_share': 0
        }
        
        # تعداد کاربران
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        result = cursor.fetchone()
        stats['total_users'] = result[0] if result else 0
        
        # تعداد رزروهای این هفته
        cursor.execute('''
        SELECT SUM(r.quantity) as total
        FROM reservations r
        JOIN menu_items m ON r.menu_item_id = m.id
        JOIN weekly_menus w ON m.weekly_menu_id = w.id
        WHERE w.is_active = 1 AND r.status = 'CONFIRMED'
        ''')
        result = cursor.fetchone()
        stats['total_reservations'] = result[0] if result and result[0] else 0
        
        # سهم شرکت و کاربران
        cursor.execute('''
        SELECT 
            SUM(m.company_share * r.quantity) as company_total,
            SUM(m.user_price * r.quantity) as user_total
        FROM reservations r
        JOIN menu_items m ON r.menu_item_id = m.id
        JOIN weekly_menus w ON m.weekly_menu_id = w.id
        WHERE w.is_active = 1 AND r.status = 'CONFIRMED'
        ''')
        result = cursor.fetchone()
        stats['total_company_share'] = result[0] if result and result[0] else 0
        stats['total_user_share'] = result[1] if result and result[1] else 0
        
        conn.close()
        return stats
    
    # توابع جدید برای ایجاد منو و غذا
    def create_weekly_menu(self, week_start: str, week_end: str, reservation_deadline: str):
        """ایجاد منوی هفتگی جدید"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # غیرفعال کردن منوهای قبلی
            cursor.execute("UPDATE weekly_menus SET is_active = 0")
            
            # ایجاد منوی جدید
            cursor.execute('''
            INSERT INTO weekly_menus (week_start, week_end, reservation_deadline, is_active)
            VALUES (?, ?, ?, ?)
            ''', (week_start, week_end, reservation_deadline, 1))
            
            weekly_menu_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            return True, weekly_menu_id, "منوی هفته جدید ایجاد شد"
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, None, f"خطا در ایجاد منو: {str(e)}"
    
    def add_menu_item(self, weekly_menu_id: int, day_of_week: str, food_name: str, description: str, 
                      full_price: float, capacity: int, extra_food: bool = False, extra_food_price: float = None):
        """اضافه کردن غذا به منو"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # محاسبه ۶۰/۴۰
            user_price = full_price * 0.6
            company_share = full_price * 0.4
            
            cursor.execute('''
            INSERT INTO menu_items 
            (weekly_menu_id, day_of_week, food_name, description, full_price, 
             user_price, company_share, capacity, extra_food, extra_food_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (weekly_menu_id, day_of_week, food_name, description, full_price,
                  user_price, company_share, capacity, 1 if extra_food else 0, extra_food_price))
            
            conn.commit()
            conn.close()
            return True, "غذا با موفقیت اضافه شد"
            
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"خطا در اضافه کردن غذا: {str(e)}"
    
    def get_foods_for_day(self, weekly_menu_id: int, day_of_week: str):
        """دریافت غذاهای یک روز خاص"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM menu_items 
        WHERE weekly_menu_id = ? AND day_of_week = ?
        ORDER BY id
        ''', (weekly_menu_id, day_of_week))
        
        foods = []
        for row in cursor.fetchall():
            foods.append(dict(row))
        
        conn.close()
        return foods

# ایجاد نمونه دیتابیس
db = Database()