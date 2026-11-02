from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Book
from werkzeug.utils import secure_filename
import os
import time
from config import Config
from recommendation import get_book_recommendations
from apikey import assess_book_condition

books_bp = Blueprint('books', __name__, url_prefix='/books')

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


@books_bp.route('/')
def list_books():
    """浏览所有在售书籍"""
    page = request.args.get('page', 1, type=int)
    
    # 搜索过滤
    search_query = request.args.get('q', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    condition = request.args.get('condition', '').strip()
    
    # 构建查询
    query = Book.query.filter_by(status='available')
    
    if search_query:
        query = query.filter(
            db.or_(
                Book.title.contains(search_query),
                Book.author.contains(search_query),
                Book.isbn.contains(search_query)
            )
        )
    
    if min_price is not None:
        query = query.filter(Book.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Book.price <= max_price)
    
    if condition:
        query = query.filter_by(condition=condition)
    
    # 按创建时间倒序排列
    query = query.order_by(Book.created_at.desc())
    
    # 分页
    pagination = query.paginate(
        page=page, 
        per_page=Config.BOOKS_PER_PAGE,
        error_out=False
    )
    
    books = pagination.items
    
    return render_template('books/list.html', 
                         books=books, 
                         pagination=pagination,
                         search_query=search_query,
                         min_price=min_price,
                         max_price=max_price,
                         condition=condition)


@books_bp.route('/<int:book_id>')
def detail(book_id):
    """查看书籍详情"""
    book = Book.query.get_or_404(book_id)
    
    # 获取相关推荐书籍
    user_id = current_user.id if current_user.is_authenticated else None
    recommendations = get_book_recommendations(book_id, limit=6, user_id=user_id)
    
    return render_template('books/detail.html', book=book, recommendations=recommendations)


@books_bp.route('/publish', methods=['GET', 'POST'])
@login_required
def publish():
    """发布书籍（仅卖家）"""
    if not current_user.is_verified_seller:
        flash('只有认证卖家才能发布书籍', 'warning')
        return redirect(url_for('books.list_books'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        isbn = request.form.get('isbn', '').strip()
        publisher = request.form.get('publisher', '').strip()
        condition = request.form.get('condition', '').strip()
        price = request.form.get('price', type=float)
        description = request.form.get('description', '').strip()
        pages = request.form.get('pages', type=int)
        stock_quantity = request.form.get('stock_quantity', 1, type=int)
        
        # 表单验证
        if not title or not author or not condition or price is None or pages is None:
            flash('请填写所有必填项（包括页数）', 'danger')
            return render_template('books/publish.html')
        
        if price <= 0:
            flash('价格必须大于0', 'danger')
            return render_template('books/publish.html')
            
        if pages <= 0:
            flash('页数必须大于0', 'danger')
            return render_template('books/publish.html')
        
        if stock_quantity < 1:
            flash('数量必须大于0', 'danger')
            return render_template('books/publish.html')
        
        # 获取特定页面照片
        cover = request.files.get('cover_image')
        title_page = request.files.get('title_page_image')
        inside_pages = request.files.getlist('inside_page_images')
        back_cover = request.files.get('back_cover_image')
        
        if not cover or not title_page or not back_cover or not inside_pages:
            flash('请上传所有必须的照片 (封面, 扉页, 内页, 封底)', 'danger')
            return render_template('books/publish.html')

        # 辅助函数：保存文件
        def save_uploaded_file(file):
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # 添加时间戳避免文件名冲突
                filename = f"{int(time.time())}_{filename}"
                
                # 确保上传目录存在
                os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                
                filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                file.save(filepath)
                return f"uploads/{filename}"
            return None

        # 保存各个部分的照片
        cover_path = save_uploaded_file(cover)
        title_page_path = save_uploaded_file(title_page)
        back_cover_path = save_uploaded_file(back_cover)
        
        inside_paths = []
        for f in inside_pages:
            p = save_uploaded_file(f)
            if p: inside_paths.append(p)
            
        if not cover_path or not title_page_path or not back_cover_path or not inside_paths:
            flash('部分照片上传失败，请重试', 'danger')
            return render_template('books/publish.html')

        # 构建所有照片列表 (用于兼容旧逻辑)
        all_photos = [cover_path, title_page_path, back_cover_path] + inside_paths
        
        # 调用千问API进行AI成色评估
        try:
            # 重新读取上传的文件用于API调用
            cover_file = request.files.get('cover_image')
            title_page_file = request.files.get('title_page_image')
            back_cover_file = request.files.get('back_cover_image')
            inside_files = request.files.getlist('inside_page_images')
            
            # 调用AI评估函数
            ai_result_data = assess_book_condition(
                cover_image=cover_file,
                title_page_image=title_page_file,
                inside_images=inside_files,
                back_cover_image=back_cover_file
            )
            
            if ai_result_data and ai_result_data.get('success'):
                # 使用AI评估结果
                detected_condition = ai_result_data.get('condition', condition)
                ai_result = f"【AI评估】{ai_result_data.get('condition_text', '')}：{ai_result_data.get('reason', '')}（置信度：{ai_result_data.get('confidence', 0):.0%}）"
            else:
                # AI评估失败时使用用户选择的成色
                detected_condition = condition
                error_msg = ai_result_data.get('message', '未知错误') if ai_result_data else '无法连接AI服务'
                ai_result = f"【自动评估】{error_msg}，采用用户自评：{condition}"
                print(f"AI评估失败: {error_msg}")
                
        except Exception as e:
            # API调用异常处理
            detected_condition = condition
            ai_result = f"【自动评估】AI评估服务暂时不可用，采用用户自评：{condition}（错误：{str(e)}）"
            print(f"AI评估异常: {e}")

        # 创建书籍记录
        book = Book(
            title=title,
            author=author,
            isbn=isbn,
            publisher=publisher,
            condition=detected_condition,
            price=price,
            description=description,
            pages=pages,
            stock_quantity=stock_quantity,
            seller_id=current_user.id,
            
            # 新字段
            cover_image_path=cover_path,
            title_page_image_path=title_page_path,
            inside_page_image_path=','.join(inside_paths),
            back_cover_image_path=back_cover_path,
            ai_assessment_result=ai_result,
            
            # 兼容字段 (存储所有照片的文件名)
            photo_paths=','.join(all_photos),
            # 兼容字段 (使用封面作为主图)
            image_path=cover_path
        )
        
        try:
            db.session.add(book)
            db.session.commit()
            flash('书籍发布成功！AI已完成成色评估。', 'success')
            return redirect(url_for('books.detail', book_id=book.id))
        except Exception as e:
            db.session.rollback()
            print(f"Error publishing book: {e}")
            flash('发布失败，请重试', 'danger')
            return render_template('books/publish.html')
    
    return render_template('books/publish.html')


@books_bp.route('/ai-assess', methods=['POST'])
def ai_assess():
    """
    处理AI成色评估请求
    使用阿里云千问API进行图像识别和成色评估
    """
    try:
        # 获取上传的文件
        cover = request.files.get('cover_image')
        title_page = request.files.get('title_page_image')
        inside_pages = request.files.getlist('inside_page_images')
        back_cover = request.files.get('back_cover_image')
        
        # 验证必要文件
        if not cover or not title_page:
            return jsonify({'success': False, 'message': '缺少必要照片（封面和扉页必传）'})
        
        if not cover.filename or not title_page.filename:
            return jsonify({'success': False, 'message': '请上传有效的封面和扉页图片'})
        
        # 调用千问API进行成色评估
        result = assess_book_condition(
            cover_image=cover,
            title_page_image=title_page,
            inside_images=inside_pages if inside_pages else None,
            back_cover_image=back_cover if back_cover and back_cover.filename else None
        )
        
        # 返回评估结果
        if result and result.get('success'):
            return jsonify({
                'success': True,
                'condition_value': result.get('condition'),
                'condition_text': result.get('condition_text'),
                'reason': result.get('reason'),
                'confidence': result.get('confidence')
            })
        else:
            # AI评估失败
            error_msg = result.get('message', '未知错误') if result else '无法连接AI服务'
            return jsonify({
                'success': False,
                'message': f'AI评估失败: {error_msg}'
            })
        
    except Exception as e:
        print(f"AI assessment error: {e}")
        return jsonify({'success': False, 'message': f'AI评估服务异常: {str(e)}'})


@books_bp.route('/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(book_id):
    """编辑书籍"""
    book = Book.query.get_or_404(book_id)
    
    # 只有卖家本人可以编辑
    if book.seller_id != current_user.id:
        flash('无权编辑此书籍', 'danger')
        return redirect(url_for('books.detail', book_id=book_id))
    
    if request.method == 'POST':
        book.title = request.form.get('title', '').strip()
        book.author = request.form.get('author', '').strip()
        book.isbn = request.form.get('isbn', '').strip()
        book.publisher = request.form.get('publisher', '').strip()
        book.condition = request.form.get('condition', '').strip()
        book.price = request.form.get('price', type=float)
        book.description = request.form.get('description', '').strip()
        book.pages = request.form.get('pages', type=int)
        
        # 处理多张图片上传
        uploaded_files = request.files.getlist('images')
        if uploaded_files and any([f for f in uploaded_files if f.filename]):
            # 获取现有照片路径
            existing_photos = book.photo_paths.split(',') if book.photo_paths else []
            for file in uploaded_files:
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # 添加时间戳避免文件名冲突
                    import time
                    filename = f"{int(time.time())}_{filename}"
                    
                    # 确保上传目录存在
                    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                    
                    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    existing_photos.append(f"uploads/{filename}")
            
            # 更新照片路径
            book.photo_paths = ','.join(existing_photos)
        
        # 表单验证
        if not book.title or not book.author or not book.condition or book.price is None:
            flash('请填写所有必填项', 'danger')
            return render_template('books/edit.html', book=book)
        
        if book.price <= 0:
            flash('价格必须大于0', 'danger')
            return render_template('books/edit.html', book=book)
        
        # 处理图片上传
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                import time
                filename = f"{int(time.time())}_{filename}"
                
                os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                
                filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                file.save(filepath)
                book.image_path = f"uploads/{filename}"
        
        try:
            db.session.commit()
            flash('书籍信息已更新', 'success')
            return redirect(url_for('books.detail', book_id=book.id))
        except Exception as e:
            db.session.rollback()
            flash('更新失败，请重试', 'danger')
            return render_template('books/edit.html', book=book)
    
    return render_template('books/edit.html', book=book)


@books_bp.route('/<int:book_id>/offline', methods=['POST'])
@login_required
def offline(book_id):
    """下架书籍"""
    book = Book.query.get_or_404(book_id)
    
    # 只有卖家本人可以下架
    if book.seller_id != current_user.id:
        flash('无权操作此书籍', 'danger')
        return redirect(url_for('books.detail', book_id=book_id))
    
    book.status = 'offline'
    
    try:
        db.session.commit()
        flash('书籍已下架', 'info')
    except Exception as e:
        db.session.rollback()
        flash('操作失败', 'danger')
    
    return redirect(url_for('user.seller_center'))

@books_bp.route('/<int:book_id>/update-stock', methods=['POST'])
@login_required
def update_stock(book_id):
    """更新库存数量"""
    book = Book.query.get_or_404(book_id)
    
    # 只有卖家本人可以更新库存
    if book.seller_id != current_user.id:
        flash('无权操作此书籍', 'danger')
        return redirect(url_for('books.detail', book_id=book_id))
    
    new_stock = request.form.get('stock_quantity', type=int)
    
    if new_stock is not None and new_stock >= 0:
        book.stock_quantity = new_stock
        
        try:
            db.session.commit()
            flash(f'库存数量已更新为 {new_stock}', 'success')
        except Exception as e:
            db.session.rollback()
            flash('更新库存失败', 'danger')
    else:
        flash('库存数量必须为非负整数', 'danger')
    
    return redirect(url_for('user.inventory'))

@books_bp.route('/assistant')
def ai_assistant():
    """AI课程用书助手页面"""
    return render_template('books/ai_assistant.html')

@books_bp.route('/assistant-chat', methods=['POST'])
def ai_assistant_chat():
    """处理AI助手的查询请求"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'success': False, 'message': '请输入课程名称'})
        
        # 简单模拟：搜索书籍
        # 实际项目中可以使用向量搜索或更复杂的NLP
        books = Book.query.filter(
            db.or_(
                Book.title.contains(query),
                Book.description.contains(query),
                Book.author.contains(query)
            ),
            Book.status == 'available'
        ).limit(5).all()
        
        response_data = {
            'success': True,
            'message': '',
            'books': []
        }
        
        if books:
            response_data['message'] = f"为你找到以下关于“{query}”的书籍："
            for book in books:
                # 获取图片URL
                image_url = ''
                # 优先使用 image_path
                if book.image_path:
                    # 如果已经是 uploads/ 开头，则直接使用
                    if book.image_path.startswith('uploads/'):
                         image_url = url_for('static', filename=book.image_path)
                    else:
                         image_url = url_for('static', filename='uploads/' + book.image_path)
                elif book.photo_paths:
                    # 尝试从 photo_paths 获取第一张
                    first_photo = book.photo_paths.split(',')[0]
                    if first_photo.startswith('uploads/'):
                         image_url = url_for('static', filename=first_photo)
                    else:
                         image_url = url_for('static', filename='uploads/' + first_photo)
                else:
                    # 使用默认占位图或空字符串
                    image_url = '' 
                
                response_data['books'].append({
                    'id': book.id,
                    'title': book.title,
                    'author': book.author,
                    'price': book.price,
                    'image': image_url
                })
        else:
            # 尝试一些通用建议
            response_data['message'] = f"抱歉，暂时没有找到关于“{query}”的二手书。你可以尝试搜索相关领域的通用教材，或者稍后再来查看。"
            
        return jsonify(response_data)
    except Exception as e:
        print(f"Assistant error: {e}")
        return jsonify({'success': False, 'message': '助手暂时无法回答，请稍后再试。'})
