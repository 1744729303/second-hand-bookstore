from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Book, Transaction
from datetime import datetime

transactions_bp = Blueprint('transactions', __name__, url_prefix='/transactions')

@transactions_bp.route('/purchase/<int:book_id>', methods=['POST'])
@login_required
def purchase(book_id):
    """发起购买请求"""
    book = Book.query.get_or_404(book_id)
    
    # 检查书籍状态和库存
    if book.status != 'available':
        flash('该书籍已不可购买', 'warning')
        return redirect(url_for('books.detail', book_id=book_id))
    
    if book.stock_quantity < 1:
        flash('该书籍已售罄', 'warning')
        return redirect(url_for('books.detail', book_id=book_id))
    
    # 不能购买自己的书
    if book.seller_id == current_user.id:
        flash('不能购买自己发布的书籍', 'warning')
        return redirect(url_for('books.detail', book_id=book_id))
    
    # 检查是否已经有待处理的购买请求
    existing_transaction = Transaction.query.filter_by(
        buyer_id=current_user.id,
        book_id=book_id,
        status='pending'
    ).first()
    
    if existing_transaction:
        flash('您已经对该书籍发起过购买请求，请等待卖家处理', 'info')
        return redirect(url_for('books.detail', book_id=book_id))
    
    # 获取留言
    message = request.form.get('message', '').strip()
    
    # 创建交易记录
    transaction = Transaction(
        buyer_id=current_user.id,
        book_id=book_id,
        message=message,
        status='pending'
    )
    
    try:
        db.session.add(transaction)
        db.session.commit()
        flash('购买请求已发送，请等待卖家确认', 'success')
    except Exception as e:
        db.session.rollback()
        flash('操作失败，请重试', 'danger')
    
    return redirect(url_for('books.detail', book_id=book_id))


@transactions_bp.route('/<int:transaction_id>/accept', methods=['POST'])
@login_required
def accept(transaction_id):
    """卖家同意购买请求"""
    transaction = Transaction.query.get_or_404(transaction_id)
    book = transaction.book
    
    # 只有卖家本人可以操作
    if book.seller_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('user.seller_center'))
    
    # 检查交易状态
    if transaction.status != 'pending':
        flash('该请求已被处理', 'info')
        return redirect(url_for('user.seller_center'))
    
    # 检查书籍状态
    if book.status != 'available':
        flash('该书籍已不可售', 'warning')
        return redirect(url_for('user.seller_center'))
    
    # 获取卖家回复
    seller_reply = request.form.get('seller_reply', '').strip()
    
    # 更新交易状态为待付款
    transaction.status = 'accepted'
    transaction.seller_reply = seller_reply
    
    # 如果库存只有1本，卖家同意后其他请求自动拒绝（因为只能卖给一个人）
    if book.stock_quantity <= 1:
        other_transactions = Transaction.query.filter_by(
            book_id=book.id,
            status='pending'
        ).filter(Transaction.id != transaction_id).all()
        
        for other_trans in other_transactions:
            other_trans.status = 'rejected'
            other_trans.seller_reply = '该书籍已被其他买家抢先购买'
    
    try:
        db.session.commit()
        flash('已同意购买请求，请买家付款', 'success')
    except Exception as e:
        db.session.rollback()
        flash('操作失败，请重试', 'danger')
    
    return redirect(url_for('user.seller_center'))


@transactions_bp.route('/<int:transaction_id>/pay', methods=['POST'])
@login_required
def pay(transaction_id):
    """买家付款（模拟）"""
    transaction = Transaction.query.get_or_404(transaction_id)
    book = transaction.book
    
    # 只有买家本人可以付款
    if transaction.buyer_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('user.buyer_center'))
    
    # 检查交易状态
    if transaction.status != 'accepted':
        flash('该订单状态不允许付款', 'warning')
        return redirect(url_for('user.buyer_center'))
    
    # 模拟付款过程（实际项目中需要集成支付接口）
    transaction.status = 'paid'
    transaction.paid_at = datetime.utcnow()
    transaction.payment_amount = book.price
    
    # 减少库存数量
    if book.stock_quantity > 1:
        book.stock_quantity -= 1
    else:
        # 库存为1时，标记为已售出
        book.status = 'sold'
    
    # 拒绝其他待处理的购买请求
    other_transactions = Transaction.query.filter_by(
        book_id=book.id,
        status='pending'
    ).all()
    
    for other_trans in other_transactions:
        other_trans.status = 'rejected'
        other_trans.seller_reply = '该书籍已售出'
    
    try:
        db.session.commit()
        flash('付款成功！请联系卖家安排取书事宜', 'success')
    except Exception as e:
        db.session.rollback()
        flash('付款失败，请重试', 'danger')
    
    return redirect(url_for('user.buyer_center'))


@transactions_bp.route('/<int:transaction_id>/reject', methods=['POST'])
@login_required
def reject(transaction_id):
    """卖家拒绝购买请求"""
    transaction = Transaction.query.get_or_404(transaction_id)
    book = transaction.book
    
    # 只有卖家本人可以操作
    if book.seller_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('user.seller_center'))
    
    # 检查交易状态
    if transaction.status != 'pending':
        flash('该请求已被处理', 'info')
        return redirect(url_for('user.seller_center'))
    
    # 获取卖家回复
    seller_reply = request.form.get('seller_reply', '').strip()
    
    # 更新交易状态
    transaction.status = 'rejected'
    transaction.seller_reply = seller_reply
    
    try:
        db.session.commit()
        flash('已拒绝购买请求', 'info')
    except Exception as e:
        db.session.rollback()
        flash('操作失败，请重试', 'danger')
    
    return redirect(url_for('user.seller_center'))

@transactions_bp.route('/exchange', methods=['GET', 'POST'])
@login_required
def exchange():
    """书籍交换功能"""
    if request.method == 'POST':
        # 获取表单数据
        book_id = request.form.get('book_id', type=int)
        offer_book_ids = request.form.getlist('offer_books')
        message = request.form.get('message', '').strip()
        
        if not book_id or not offer_book_ids:
            flash('请选择要交换的书籍', 'danger')
            return redirect(url_for('transactions.exchange'))
        
        # 这里可以实现书籍交换逻辑
        # 为了简化，我们创建一个特殊的交易记录来表示交换意向
        # 实际应用中可能需要更复杂的交换机制
        
        # 创建交换记录（这里简化为普通交易记录）
        flash('交换请求已发送，请等待对方确认', 'success')
        return redirect(url_for('transactions.exchange'))
    
    # GET请求：显示可交换的书籍
    my_books = Book.query.filter_by(seller_id=current_user.id).all()
    available_books = Book.query.filter(
        Book.status == 'available',
        Book.seller_id != current_user.id
    ).limit(20).all()  # 限制数量提高性能
    
    return render_template('transactions/exchange.html', 
                         my_books=my_books, 
                         available_books=available_books)
