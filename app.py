from flask import Flask, render_template, request, redirect, session, jsonify
from database import db
import os
import jdatetime
from datetime import datetime as dt

app = Flask(__name__)
app.secret_key = 'your-secret-key-123'
app.config['SESSION_TYPE'] = 'filesystem'

# توابع کمکی تاریخ شمسی
def get_jalali_info():
    """دریافت اطلاعات تاریخ شمسی"""
    now_jalali = jdatetime.datetime.now()
    
    return {
        'today': now_jalali.strftime('%Y/%m/%d'),
        'today_full': now_jalali.strftime('%A %d %B %Y'),
        'current_year': now_jalali.year,
        'current_month': now_jalali.month,
        'current_day': now_jalali.day,
        'weekday': now_jalali.weekday()  # 0=شنبه, 1=یکشنبه, ...
    }

def convert_to_jalali(gregorian_date_str):
    """تبدیل تاریخ میلادی به شمسی"""
    try:
        if not gregorian_date_str:
            return ""
        
        # اگر تاریخ شامل زمان است
        if ' ' in gregorian_date_str:
            date_part = gregorian_date_str.split(' ')[0]
        else:
            date_part = gregorian_date_str
            
        # تبدیل رشته به datetime
        gregorian_date = dt.strptime(date_part, '%Y-%m-%d')
        
        # تبدیل به شمسی
        jalali_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
        
        return jalali_date.strftime('%Y/%m/%d')
    except:
        return gregorian_date_str

# صفحه اصلی
@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect('/admin')
        else:
            return redirect('/user')
    return redirect('/login')

# صفحه ورود
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = db.authenticate_user(email, password)
        
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['is_admin'] = bool(user['is_admin'])
            
            if user['is_admin']:
                return redirect('/admin')
            else:
                return redirect('/user')
        else:
            return render_template('login.html', error='ایمیل یا رمز عبور اشتباه است')
    
    return render_template('login.html')

# خروج
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# پنل مدیریت
@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect('/login')
    
    # دریافت داده‌ها
    users = db.get_all_users()
    weekly_menu = db.get_weekly_menu()
    stats = db.calculate_stats()
    
    # اطمینان از ساختار داده‌ها
    menu_items = []
    if weekly_menu and isinstance(weekly_menu, dict):
        menu_items = weekly_menu.get('items', [])
    
    # اطلاعات تاریخ شمسی
    jalali_info = get_jalali_info()
    
    return render_template('admin_simple.html',
                         user={'name': session.get('user_name', 'مدیر')},
                         users=users,
                         weekly_menu=weekly_menu,
                         menu_items=menu_items,
                         stats=stats,
                         jalali_info=jalali_info,
                         convert_to_jalali=convert_to_jalali)

# پنل کاربر
@app.route('/user')
def user():
    if 'user_id' not in session:
        return redirect('/login')
    
    weekly_menu = db.get_weekly_menu()
    reservations = db.get_user_reservations(session['user_id'])
    
    # اطمینان از ساختار داده‌ها
    menu_items = []
    if weekly_menu and isinstance(weekly_menu, dict):
        menu_items = weekly_menu.get('items', [])
    
    # اطلاعات تاریخ شمسی
    jalali_info = get_jalali_info()
    
    return render_template('user_simple.html',
                         user={'name': session.get('user_name', 'کاربر')},
                         weekly_menu=weekly_menu,
                         menu_items=menu_items,
                         reservations=reservations,
                         jalali_info=jalali_info,
                         convert_to_jalali=convert_to_jalali)

# API رزرو
@app.route('/api/reserve', methods=['POST'])
def reserve():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'لطفاً ابتدا وارد شوید'})
    
    try:
        data = request.get_json()
        menu_item_id = data.get('menu_item_id')
        quantity = data.get('quantity', 1)
        is_extra = data.get('is_extra', False)
        
        success, message = db.create_reservation(
            session['user_id'],
            menu_item_id,
            quantity,
            is_extra
        )
        
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# API ایجاد کاربر
@app.route('/api/create_user', methods=['POST'])
def api_create_user():
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'دسترسی غیرمجاز'})
    
    try:
        data = request.get_json()
        success, message = db.create_user(
            data.get('employee_id'),
            data.get('full_name'),
            data.get('email'),
            data.get('password'),
            data.get('department'),
            data.get('is_admin', False)
        )
        
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# API ایجاد منوی هفتگی
@app.route('/api/create_weekly_menu', methods=['POST'])
def api_create_weekly_menu():
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'دسترسی غیرمجاز'})
    
    try:
        data = request.get_json()
        
        # بررسی داده‌ها
        week_start = data.get('week_start')
        week_end = data.get('week_end')
        reservation_deadline = data.get('reservation_deadline')
        
        if not all([week_start, week_end, reservation_deadline]):
            return jsonify({'success': False, 'message': 'لطفاً تمام فیلدها را پر کنید'})
        
        success, menu_id, message = db.create_weekly_menu(
            week_start, week_end, reservation_deadline
        )
        
        return jsonify({'success': success, 'menu_id': menu_id, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# API اضافه کردن غذا
@app.route('/api/add_menu_item', methods=['POST'])
def api_add_menu_item():
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'دسترسی غیرمجاز'})
    
    try:
        data = request.get_json()
        
        # بررسی داده‌ها
        weekly_menu_id = data.get('weekly_menu_id')
        day_of_week = data.get('day_of_week')
        food_name = data.get('food_name')
        full_price = float(data.get('full_price', 0))
        capacity = int(data.get('capacity', 0))
        
        if not all([weekly_menu_id, day_of_week, food_name]):
            return jsonify({'success': False, 'message': 'لطفاً فیلدهای ضروری را پر کنید'})
        
        success, message = db.add_menu_item(
            weekly_menu_id=weekly_menu_id,
            day_of_week=day_of_week,
            food_name=food_name,
            description=data.get('description', ''),
            full_price=full_price,
            capacity=capacity,
            extra_food=data.get('extra_food', False),
            extra_food_price=data.get('extra_food_price')
        )
        
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# API دریافت غذاهای یک روز
@app.route('/api/get_foods_for_day')
def api_get_foods_for_day():
    weekly_menu_id = request.args.get('weekly_menu_id')
    day_of_week = request.args.get('day_of_week')
    
    if not weekly_menu_id or not day_of_week:
        return jsonify([])
    
    foods = db.get_foods_for_day(weekly_menu_id, day_of_week)
    return jsonify(foods)

if __name__ == '__main__':
    # ایجاد پوشه‌ها اگر وجود ندارند
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("🚀 سیستم رزرواسیون غذای شرکت")
    print("📅 تقویم شمسی فعال")
    print("🌐 آدرس: http://localhost:5000")
    print("🔐 اطلاعات ورود:")
    print("   مدیر سیستم: admin@company.com / Admin@123!")
    print("   کاربران: reza@company.com / User@123!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)