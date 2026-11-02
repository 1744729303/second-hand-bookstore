from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # 是否申请成为卖家
        apply_seller = request.form.get('apply_seller') == 'on'
        
        # 表单验证
        if not username or not email or not password:
            flash('请填写所有必填项', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('密码长度至少为6位', 'danger')
            return render_template('register.html')
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已被使用', 'danger')
            return render_template('register.html')
        
        # 检查邮箱是否已存在
        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册', 'danger')
            return render_template('register.html')
        
        # 创建用户
        user = User(username=username, email=email)
        user.set_password(password)
        
        # 如果申请成为卖家，获取认证信息
        if apply_seller:
            real_name = request.form.get('real_name', '').strip()
            id_number = request.form.get('id_number', '').strip()
            phone = request.form.get('phone', '').strip()
            
            if not real_name or not id_number or not phone:
                flash('申请卖家需要填写完整的认证信息', 'danger')
                return render_template('register.html')
            
            user.user_type = 'seller'
            user.is_verified_seller = True  # 简化处理，直接认证通过
            user.real_name = real_name
            user.id_number = id_number
            user.phone = phone
        else:
            user.user_type = 'buyer'
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('注册成功！请登录', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('注册失败，请重试', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = request.form.get('remember') == 'on'
        
        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('用户名或密码错误', 'danger')
            return render_template('login.html')
        
        login_user(user, remember=remember)
        
        # 管理员登录处理
        if user.is_admin:
            flash(f'欢迎回来，管理员 {user.username}！', 'success')
            return redirect(url_for('admin.dashboard'))
        # 区分买家和卖家的欢迎信息
        elif user.is_verified_seller:
            flash(f'欢迎回来，卖家 {user.username}！', 'success')
        else:
            flash(f'欢迎回来，{user.username}！', 'success')
        
        # 重定向到原页面或首页
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.index'))
    
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('已成功退出登录', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile')
@login_required
def profile():
    """个人信息页面"""
    return render_template('profile.html', user=current_user)
