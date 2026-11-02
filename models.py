from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    
    # 用户类型：buyer（买家）或 seller（卖家）
    user_type = db.Column(db.String(20), default='buyer', nullable=False)
    
    # 是否为管理员
    is_admin = db.Column(db.Boolean, default=False)
    
    # 卖家认证信息
    is_verified_seller = db.Column(db.Boolean, default=False)
    real_name = db.Column(db.String(100))  # 真实姓名
    id_number = db.Column(db.String(50))   # 身份证号
    phone = db.Column(db.String(20))       # 联系电话
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    books = db.relationship('Book', backref='seller', lazy='dynamic', cascade='all, delete-orphan')
    purchase_orders = db.relationship('Transaction', foreign_keys='Transaction.buyer_id', 
                                     backref='buyer', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Book(db.Model):
    """书籍表"""
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    author = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(50))
    publisher = db.Column(db.String(100))
    
    # 书籍状态：available（在售）、sold（已售出）、offline（已下架）
    status = db.Column(db.String(20), default='available', nullable=False, index=True)
    
    # 新旧程度：new（全新）、like_new（几乎全新）、good（良好）、acceptable（可接受）
    condition = db.Column(db.String(20), nullable=False)
    
    # 库存数量
    stock_quantity = db.Column(db.Integer, default=1, nullable=False)
    
    # 页数
    pages = db.Column(db.Integer)
    
    # 书籍照片（多个照片路径，逗号分隔）
    photo_paths = db.Column(db.String(1000))  # 存储多个照片路径
    
    # 强制特定页面照片路径
    cover_image_path = db.Column(db.String(200))      # 封面
    title_page_image_path = db.Column(db.String(200)) # 扉页
    inside_page_image_path = db.Column(db.String(500))# 内页（可能多张，逗号分隔）
    back_cover_image_path = db.Column(db.String(200)) # 封底
    
    # AI成色评估结果
    ai_assessment_result = db.Column(db.Text)         # 存储AI评估的详细结果
    
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(200))  # 图片路径
    
    # 卖家ID
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    transactions = db.relationship('Transaction', backref='book', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Book {self.title}>'


class Transaction(db.Model):
    """交易记录表"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 买家ID
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 书籍ID
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    
    # 交易状态：pending（待处理）、accepted（已同意-待付款）、paid（已付款）、rejected（已拒绝）、completed（已完成）
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    
    # 留言
    message = db.Column(db.Text)
    
    # 卖家回复
    seller_reply = db.Column(db.Text)
    
    # 支付相关
    paid_at = db.Column(db.DateTime)  # 付款时间
    payment_amount = db.Column(db.Float)  # 实际支付金额
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Transaction {self.id}>'
