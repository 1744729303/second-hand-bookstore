from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Book, User, Transaction
from sqlalchemy import func
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """管理员权限装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('只有管理员才能访问该页面', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """管理员数据面板 - 优化版本"""
    # 【性能优化】使用单次查询获取所有图书统计，减少数据库查询次数
    book_stats = db.session.query(
        func.count(Book.id),
        func.sum(func.cast(Book.status == 'available', db.Integer)),
        func.sum(func.cast(Book.status == 'sold', db.Integer)),
        func.sum(func.cast(Book.status == 'offline', db.Integer))
    ).first()

    total_books = book_stats[0] or 0
    available_books = book_stats[1] or 0
    sold_books = book_stats[2] or 0
    offline_books = book_stats[3] or 0

    # 【性能优化】使用单次查询获取所有用户统计
    user_stats = db.session.query(
        func.count(User.id),
        func.sum(func.cast(User.user_type == 'buyer', db.Integer)),
        func.sum(func.cast(User.user_type == 'seller', db.Integer)),
        func.sum(func.cast((User.user_type == 'seller') & (User.is_verified_seller == True), db.Integer))
    ).first()

    total_users = user_stats[0] or 0
    total_buyers = user_stats[1] or 0
    total_sellers = user_stats[2] or 0
    verified_sellers = user_stats[3] or 0

    # 【性能优化】使用单次查询获取所有交易统计（包括总金额）
    transaction_stats = db.session.query(
        func.count(Transaction.id),
        func.sum(func.cast(Transaction.status == 'pending', db.Integer)),
        func.sum(func.cast(Transaction.status == 'completed', db.Integer)),
        func.sum(func.cast(Transaction.status == 'completed', db.Integer) * Transaction.payment_amount)
    ).first()

    total_transactions = transaction_stats[0] or 0
    pending_transactions = transaction_stats[1] or 0
    completed_transactions = transaction_stats[2] or 0
    total_amount = transaction_stats[3] or 0

    # 平均书籍价格 - 保留单独查询
    avg_price = db.session.query(func.avg(Book.price)).scalar() or 0

    # 【性能优化】书籍条件分布 - 单次分组查询
    condition_stats = db.session.query(
        Book.condition,
        func.count(Book.id).label('count')
    ).group_by(Book.condition).all()

    condition_dict = {item[0]: item[1] for item in condition_stats}

    # 【性能优化】最受欢迎的书籍 - 使用 LEFT JOIN 和 GROUP BY
    top_books = db.session.query(
        Book.id,
        Book.title,
        func.count(Transaction.id).label('transaction_count')
    ).join(Transaction, isouter=True).group_by(Book.id).order_by(
        func.count(Transaction.id).desc()
    ).limit(5).all()

    # 【性能优化】最活跃的卖家 - 使用 LEFT JOIN
    top_sellers = db.session.query(
        User.id,
        User.username,
        func.count(Book.id).label('book_count')
    ).join(Book, isouter=True).filter(User.user_type == 'seller').group_by(User.id).order_by(
        func.count(Book.id).desc()
    ).limit(5).all()

    # 【性能优化】最活跃的买家 - 使用 LEFT JOIN
    top_buyers = db.session.query(
        User.id,
        User.username,
        func.count(Transaction.id).label('purchase_count')
    ).join(Transaction, User.id == Transaction.buyer_id, isouter=True).group_by(User.id).order_by(
        func.count(Transaction.id).desc()
    ).limit(5).all()

    # 【性能优化】最近的交易 - 使用 joinedload 预加载关联对象，避免 N+1 查询
    recent_transactions = db.session.query(Transaction).options(
        db.joinedload(Transaction.book),
        db.joinedload(Transaction.buyer)
    ).order_by(Transaction.created_at.desc()).limit(10).all()

    # ========== 新增统计数据 ==========

    # 最近7天新增用户
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    new_users_this_week = db.session.query(func.count(User.id)).filter(
        User.created_at >= seven_days_ago
    ).scalar() or 0

    # 最近7天新增书籍
    new_books_this_week = db.session.query(func.count(Book.id)).filter(
        Book.created_at >= seven_days_ago
    ).scalar() or 0

    # 最近7天交易数量
    transactions_this_week = db.session.query(func.count(Transaction.id)).filter(
        Transaction.created_at >= seven_days_ago
    ).scalar() or 0

    # 最近7天交易金额
    amount_this_week = db.session.query(func.sum(Transaction.payment_amount)).filter(
        Transaction.status == 'completed',
        Transaction.created_at >= seven_days_ago
    ).scalar() or 0

    # 交易状态分布
    transaction_status_stats = db.session.query(
        Transaction.status,
        func.count(Transaction.id).label('count')
    ).group_by(Transaction.status).all()

    transaction_status_dict = {item[0]: item[1] for item in transaction_status_stats}

    # 价格区间分布
    price_ranges = [
        (0, 10, '0-10元'),
        (10, 30, '10-30元'),
        (30, 50, '30-50元'),
        (50, 100, '50-100元'),
        (100, float('inf'), '100元以上')
    ]

    price_distribution = []
    for low, high, label in price_ranges:
        if high == float('inf'):
            count = db.session.query(func.count(Book.id)).filter(Book.price >= low).scalar() or 0
        else:
            count = db.session.query(func.count(Book.id)).filter(
                Book.price >= low, Book.price < high
            ).scalar() or 0
        price_distribution.append({'label': label, 'count': count})

    # 按月份统计交易趋势（最近6个月）
    monthly_transactions = []
    for i in range(5, -1, -1):
        month_start = datetime.utcnow().replace(day=1) - timedelta(days=i * 30)
        month_end = month_start + timedelta(days=30)

        count = db.session.query(func.count(Transaction.id)).filter(
            Transaction.created_at >= month_start,
            Transaction.created_at < month_end
        ).scalar() or 0

        amount = db.session.query(func.sum(Transaction.payment_amount)).filter(
            Transaction.status == 'completed',
            Transaction.created_at >= month_start,
            Transaction.created_at < month_end
        ).scalar() or 0

        monthly_transactions.append({
            'month': month_start.strftime('%m月'),
            'count': count,
            'amount': amount or 0
        })

    # 活跃用户（最近30天有交易的用户）
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = db.session.query(func.count(func.distinct(Transaction.buyer_id))).filter(
        Transaction.created_at >= thirty_days_ago
    ).scalar() or 0

    # 热门分类（按书籍数量）
    # 由于没有分类字段，这里按作者数量作为参考
    author_stats = db.session.query(
        Book.author,
        func.count(Book.id).label('count')
    ).group_by(Book.author).order_by(func.count(Book.id).desc()).limit(8).all()

    author_distribution = [{'author': item[0], 'count': item[1]} for item in author_stats]

    # 用户注册趋势（最近6个月）
    monthly_users = []
    for i in range(5, -1, -1):
        month_start = datetime.utcnow().replace(day=1) - timedelta(days=i * 30)
        month_end = month_start + timedelta(days=30)

        count = db.session.query(func.count(User.id)).filter(
            User.created_at >= month_start,
            User.created_at < month_end
        ).scalar() or 0

        monthly_users.append({
            'month': month_start.strftime('%m月'),
            'count': count
        })

    # 书籍发布趋势（最近6个月）
    monthly_books = []
    for i in range(5, -1, -1):
        month_start = datetime.utcnow().replace(day=1) - timedelta(days=i * 30)
        month_end = month_start + timedelta(days=30)

        count = db.session.query(func.count(Book.id)).filter(
            Book.created_at >= month_start,
            Book.created_at < month_end
        ).scalar() or 0

        monthly_books.append({
            'month': month_start.strftime('%m月'),
            'count': count
        })

    return render_template('admin/dashboard.html',
                         total_books=total_books,
                         available_books=available_books,
                         sold_books=sold_books,
                         offline_books=offline_books,
                         total_users=total_users,
                         total_buyers=total_buyers,
                         total_sellers=total_sellers,
                         verified_sellers=verified_sellers,
                         total_transactions=total_transactions,
                         pending_transactions=pending_transactions,
                         completed_transactions=completed_transactions,
                         total_amount=total_amount,
                         avg_price=avg_price,
                         condition_dict=condition_dict,
                         top_books=top_books,
                         top_sellers=top_sellers,
                         top_buyers=top_buyers,
                         recent_transactions=recent_transactions,
                         new_users_this_week=new_users_this_week,
                         new_books_this_week=new_books_this_week,
                         transactions_this_week=transactions_this_week,
                         amount_this_week=amount_this_week,
                         transaction_status_dict=transaction_status_dict,
                         price_distribution=price_distribution,
                         monthly_transactions=monthly_transactions,
                         active_users=active_users,
                         author_distribution=author_distribution,
                         monthly_users=monthly_users,
                         monthly_books=monthly_books)

@admin_bp.route('/books')
@login_required
@admin_required
def books_management():
    """书籍管理页面"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '').strip()
    
    query = Book.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if search_query:
        query = query.filter(Book.title.contains(search_query) | Book.author.contains(search_query))
    
    books_pagination = query.order_by(Book.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('admin/books_management.html', 
                         books=books_pagination.items,
                         pagination=books_pagination,
                         current_status=status_filter,
                         search_query=search_query)

@admin_bp.route('/books/<int:book_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_book_status(book_id):
    """切换书籍状态"""
    book = Book.query.get_or_404(book_id)
    new_status = request.form.get('status')
    
    if new_status in ['available', 'sold', 'offline']:
        book.status = new_status
        try:
            db.session.commit()
            flash(f'书籍《{book.title}》状态已更新为{get_status_display(new_status)}', 'success')
        except Exception as e:
            db.session.rollback()
            flash('更新失败，请重试', 'danger')
    else:
        flash('无效的状态值', 'danger')
    
    return redirect(url_for('admin.books_management'))

def get_status_display(status):
    """获取状态显示文本"""
    status_map = {
        'available': '在售',
        'sold': '已售出',
        'offline': '已下架'
    }
    return status_map.get(status, status)

@admin_bp.route('/users')
@login_required
@admin_required
def users_management():
    """用户管理页面"""
    page = request.args.get('page', 1, type=int)
    user_type_filter = request.args.get('user_type', 'all')
    search_query = request.args.get('search', '').strip()
    
    query = User.query
    
    if user_type_filter != 'all':
        query = query.filter_by(user_type=user_type_filter)
    
    if search_query:
        query = query.filter(User.username.contains(search_query) | User.email.contains(search_query))
    
    users_pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('admin/users_management.html',
                         users=users_pagination.items,
                         pagination=users_pagination,
                         current_user_type=user_type_filter,
                         search_query=search_query)

@admin_bp.route('/orders')
@login_required
@admin_required
def orders_management():
    """订单管理页面"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '').strip()

    query = db.session.query(Transaction).options(
        db.joinedload(Transaction.book),
        db.joinedload(Transaction.buyer)
    )

    if status_filter != 'all':
        query = query.filter(Transaction.status == status_filter)

    if search_query:
        query = query.join(Book, Transaction.book_id == Book.id, isouter=True)\
            .join(User, Transaction.buyer_id == User.id, isouter=True)\
            .filter(
                Book.title.contains(search_query) |
                User.username.contains(search_query)
            )

    orders_pagination = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False
    )

    # 统计各状态数量
    status_counts = {}
    for s in ['pending', 'accepted', 'paid', 'completed', 'rejected']:
        status_counts[s] = db.session.query(func.count(Transaction.id)).filter(
            Transaction.status == s
        ).scalar() or 0
    status_counts['all'] = db.session.query(func.count(Transaction.id)).scalar() or 0

    return render_template('admin/orders_management.html',
                           orders=orders_pagination.items,
                           pagination=orders_pagination,
                           current_status=status_filter,
                           search_query=search_query,
                           status_counts=status_counts)


@admin_bp.route('/users/<int:user_id>/toggle-verification', methods=['POST'])
@login_required
@admin_required
def toggle_seller_verification(user_id):
    """切换卖家认证状态"""
    user = User.query.get_or_404(user_id)
    
    if user.user_type != 'seller':
        flash('只能审核卖家用户', 'danger')
        return redirect(url_for('admin.users_management'))
    
    new_verification = request.form.get('verification') == 'true'
    user.is_verified_seller = new_verification
    
    try:
        db.session.commit()
        status_text = '已认证' if new_verification else '未认证'
        flash(f'用户 {user.username} 的卖家认证状态已更新为{status_text}', 'success')
    except Exception as e:
        db.session.rollback()
        flash('更新失败，请重试', 'danger')
    
    return redirect(url_for('admin.users_management'))
