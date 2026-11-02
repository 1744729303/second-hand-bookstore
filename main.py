from flask import Blueprint, render_template
from models import Book

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """首页"""
    # 获取最新发布的书籍
    latest_books = Book.query.filter_by(status='available')\
        .order_by(Book.created_at.desc()).limit(8).all()
    
    return render_template('index.html', latest_books=latest_books)
