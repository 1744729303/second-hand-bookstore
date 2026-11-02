"""清空测试数据：删除所有书籍和交易记录，保留用户账号"""
import os
import sys

# 确保能导入 app 和 models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Book, Transaction

def main():
    app = create_app()
    with app.app_context():
        # 先删除交易记录（依赖书籍）
        tx_count = Transaction.query.delete()
        # 再删除所有书籍
        book_count = Book.query.delete()
        db.session.commit()
        print(f'已删除 {tx_count} 条交易记录，{book_count} 本书籍。')
        print('测试数据已清空，可以登录卖家账号上传商品。')

if __name__ == '__main__':
    main()
