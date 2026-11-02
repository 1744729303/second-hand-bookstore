from flask import Flask
from flask_login import LoginManager
from models import db, User
from config import Config
import os

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 初始化数据库
    db.init_app(app)
    
    # 初始化登录管理器
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # 注册蓝图
    from main import main_bp
    from auth import auth_bp
    from books import books_bp
    from transactions import transactions_bp
    from user import user_bp
    from admin import admin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    
    # 创建上传目录
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()

    @app.after_request
    def add_no_cache_headers(response):
        """Avoid stale HTML pages that may show outdated seeded data."""
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
