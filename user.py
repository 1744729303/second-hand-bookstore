from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Book, Transaction, User
from recommendation import get_user_recommendations
from sqlalchemy import func

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/buyer-center')
@login_required
def buyer_center():
    """买家个人中心"""
    # 获取我的购买记录
    transactions = Transaction.query.filter_by(buyer_id=current_user.id)\
        .order_by(Transaction.created_at.desc()).all()
    
    # 获取个性化推荐书籍
    recommendations = get_user_recommendations(current_user.id, limit=6)
    
    return render_template('user/buyer_center.html', transactions=transactions, recommendations=recommendations)


@user_bp.route('/apply-seller', methods=['GET', 'POST'])
@login_required
def apply_seller():
    """申请成为卖家"""
    if current_user.is_verified_seller:
        flash('您已经是认证卖家', 'info')
        return redirect(url_for('user.seller_center'))
    
    if request.method == 'POST':
        real_name = request.form.get('real_name', '').strip()
        id_number = request.form.get('id_number', '').strip()
        phone = request.form.get('phone', '').strip()
        
        if not real_name or not id_number or not phone:
            flash('请填写完整的认证信息', 'danger')
            return render_template('user/apply_seller.html')
        
        # 更新用户信息
        current_user.real_name = real_name
        current_user.id_number = id_number
        current_user.phone = phone
        # 设置为卖家类型，但未认证（等待管理员审核）
        current_user.user_type = 'seller'
        
        try:
            db.session.commit()
            flash('申请已提交，请等待管理员审核', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            db.session.rollback()
            flash('申请失败，请重试', 'danger')
    
    return render_template('user/apply_seller.html')

@user_bp.route('/inventory')
@login_required
def inventory():
    """库存管理"""
    if not current_user.is_verified_seller:
        flash('只有认证卖家才能访问库存管理', 'warning')
        return redirect(url_for('main.index'))
    
    books = Book.query.filter_by(seller_id=current_user.id).all()
    
    return render_template('user/inventory.html', books=books)

@user_bp.route('/seller-center')
@login_required
def seller_center():
    """卖家个人中心"""
    if not current_user.is_verified_seller:
        flash('只有认证卖家才能访问卖家中心', 'warning')
        return redirect(url_for('main.index'))
    
    # 获取我发布的书籍
    books = Book.query.filter_by(seller_id=current_user.id)\
        .order_by(Book.created_at.desc()).all()
    
    # 获取收到的购买请求（待处理）
    pending_transactions = db.session.query(Transaction).join(Book)\
        .filter(Book.seller_id == current_user.id)\
        .filter(Transaction.status == 'pending')\
        .order_by(Transaction.created_at.desc()).all()
    
    # 获取已处理的购买请求
    processed_transactions = db.session.query(Transaction).join(Book)\
        .filter(Book.seller_id == current_user.id)\
        .filter(Transaction.status.in_(['accepted', 'rejected']))\
        .order_by(Transaction.updated_at.desc()).all()
    
    # 统计数据
    total_sales = db.session.query(func.sum(Transaction.payment_amount)).filter(
        Transaction.book_id.in_(db.session.query(Book.id).filter_by(seller_id=current_user.id)),
        Transaction.status.in_(['paid', 'completed'])
    ).scalar() or 0
    
    total_books_sold = db.session.query(func.count(Transaction.id)).filter(
        Transaction.book_id.in_(db.session.query(Book.id).filter_by(seller_id=current_user.id)),
        Transaction.status.in_(['paid', 'completed'])
    ).scalar()
    
    return render_template('user/seller_center.html', 
                         books=books,
                         pending_transactions=pending_transactions,
                         processed_transactions=processed_transactions,
                         total_sales=total_sales,
                         total_books_sold=total_books_sold)
