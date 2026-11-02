"""
二手图书交易平台数据库初始化脚本

功能：
1. 创建数据库表
2. 创建测试用户（买家和卖家）
3. 创建示例书籍数据
"""

from app import create_app
from models import db, User, Book

def init_database():
    """初始化数据库"""
    app = create_app()
    
    with app.app_context():
        # 删除所有表（谨慎使用）
        print("删除现有数据库表...")
        db.drop_all()
        
        # 创建所有表
        print("创建数据库表...")
        db.create_all()
        
        # 创建测试用户
        print("创建测试用户...")
        
        # 管理员
        admin = User(
            username='admin',
            email='admin@example.com',
            user_type='admin',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # 买家
        buyer = User(
            username='buyer1',
            email='buyer1@example.com',
            user_type='buyer'
        )
        buyer.set_password('123456')
        db.session.add(buyer)
        
        # 卖家
        seller = User(
            username='seller1',
            email='seller1@example.com',
            user_type='seller',
            is_verified_seller=True,
            real_name='张三',
            id_number='110101199001011234',
            phone='13800138000'
        )
        seller.set_password('123456')
        db.session.add(seller)
        
        seller2 = User(
            username='seller2',
            email='seller2@example.com',
            user_type='seller',
            is_verified_seller=True,
            real_name='李四',
            id_number='110101199002021234',
            phone='13800138001'
        )
        seller2.set_password('123456')
        db.session.add(seller2)
        
        db.session.commit()
        
        # 创建示例书籍
        print("创建示例书籍...")
        
        books_data = [
            {
                'title': 'Python编程：从入门到实践',
                'author': 'Eric Matthes',
                'isbn': '9787115428028',
                'publisher': '人民邮电出版社',
                'condition': 'like_new',
                'price': 45.00,
                'description': '这是一本针对所有层次Python读者的书，非常适合初学者。书籍九成新，无笔记无划痕。',
                'seller_id': seller.id
            },
            {
                'title': '深入理解计算机系统',
                'author': 'Randal E. Bryant',
                'isbn': '9787111544937',
                'publisher': '机械工业出版社',
                'condition': 'good',
                'price': 80.00,
                'description': '经典的计算机系统教材，有少量笔记，不影响阅读。',
                'seller_id': seller.id
            },
            {
                'title': '算法导论',
                'author': 'Thomas H. Cormen',
                'isbn': '9787111407010',
                'publisher': '机械工业出版社',
                'condition': 'new',
                'price': 95.00,
                'description': '全新未拆封，因重复购买转让。',
                'seller_id': seller2.id
            },
            {
                'title': '机器学习实战',
                'author': 'Peter Harrington',
                'isbn': '9787115290632',
                'publisher': '人民邮电出版社',
                'condition': 'good',
                'price': 38.00,
                'description': '适合机器学习入门，书角有轻微磨损。',
                'seller_id': seller2.id
            },
            {
                'title': 'Flask Web开发实战',
                'author': '李辉',
                'isbn': '9787115501707',
                'publisher': '人民邮电出版社',
                'condition': 'like_new',
                'price': 55.00,
                'description': 'Flask框架实战教程，几乎全新。',
                'seller_id': seller.id
            },
            {
                'title': 'SQL必知必会',
                'author': 'Ben Forta',
                'isbn': '9787115426727',
                'publisher': '人民邮电出版社',
                'condition': 'acceptable',
                'price': 20.00,
                'description': '内容完整，封面有磨损，适合学习使用。',
                'seller_id': seller2.id
            }
        ]
        
        for book_data in books_data:
            book = Book(**book_data)
            db.session.add(book)
        
        db.session.commit()
        
        print("数据库初始化完成！")
        print("\n测试账号：")
        print("管理员 - 用户名: admin, 密码: admin123")
        print("买家 - 用户名: buyer1, 密码: 123456")
        print("卖家 - 用户名: seller1, 密码: 123456")
        print("卖家 - 用户名: seller2, 密码: 123456")

if __name__ == '__main__':
    init_database()
