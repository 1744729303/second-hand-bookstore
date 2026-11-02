from models import db, Book, Transaction, User
from sqlalchemy import func
import math
from collections import defaultdict
from flask_login import current_user


def calculate_book_similarity(book1, book2):
    """
    计算两本书之间的相似度
    使用基于作者、标题关键词、出版社等的相似度计算
    """
    similarity_score = 0.0
    
    # 作者相同
    if book1.author.lower() == book2.author.lower():
        similarity_score += 0.4
    
    # 出版社相同
    if book1.publisher and book2.publisher and book1.publisher.lower() == book2.publisher.lower():
        similarity_score += 0.2
    
    # 标题相似度（基于词汇重叠）
    title1_words = set(book1.title.lower().split())
    title2_words = set(book2.title.lower().split())
    if title1_words and title2_words:
        common_words = title1_words.intersection(title2_words)
        jaccard_similarity = len(common_words) / len(title1_words.union(title2_words))
        similarity_score += jaccard_similarity * 0.3
    
    # 价格相似度（归一化到0-1）
    if book1.price > 0 and book2.price > 0:
        price_diff = abs(book1.price - book2.price) / max(book1.price, book2.price)
        price_similarity = 1 - min(price_diff, 1.0)
        similarity_score += price_similarity * 0.1
    
    return min(similarity_score, 1.0)


def get_user_book_preferences(user_id):
    """
    获取用户对书籍的偏好，基于购买历史和浏览行为
    """
    # 获取用户购买过的书籍
    purchased_books = db.session.query(Transaction.book_id).filter(
        Transaction.buyer_id == user_id,
        Transaction.status.in_(['paid', 'completed'])
    ).all()
    
    purchased_book_ids = [tb[0] for tb in purchased_books]
    
    # 获取用户发起购买但未完成的书籍（表示兴趣）
    interested_books = db.session.query(Transaction.book_id).filter(
        Transaction.buyer_id == user_id,
        Transaction.status.in_(['pending', 'accepted'])
    ).all()
    
    interested_book_ids = [tb[0] for tb in interested_books]
    
    return {
        'purchased': purchased_book_ids,
        'interested': interested_book_ids
    }


def get_content_based_recommendations(book_id, limit=5):
    """
    基于内容的推荐：根据书籍的相似性推荐
    """
    target_book = Book.query.get(book_id)
    if not target_book:
        return []
    
    all_books = Book.query.filter(Book.id != book_id, Book.status == 'available').all()
    
    # 计算与目标书籍的相似度
    similarities = []
    for book in all_books:
        similarity = calculate_book_similarity(target_book, book)
        if similarity > 0:  # 只保留有相似度的书籍
            similarities.append((book, similarity))
    
    # 按相似度排序
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # 返回最相似的书籍
    return [book for book, score in similarities[:limit]]


def get_collaborative_filtering_recommendations(user_id, limit=5):
    """
    协同过滤推荐：基于其他相似用户的行为推荐
    """
    # 获取用户偏好
    user_prefs = get_user_book_preferences(user_id)
    user_books = user_prefs['purchased'] + user_prefs['interested']
    
    if not user_books:
        # 如果用户没有购买或感兴趣的历史，返回热门书籍
        return get_popular_books(limit)
    
    # 找到购买过相同书籍的其他用户
    similar_users = set()
    for book_id in user_books:
        transactions = Transaction.query.filter(
            Transaction.book_id == book_id,
            Transaction.status.in_(['paid', 'completed'])
        ).all()
        
        for transaction in transactions:
            if transaction.buyer_id != user_id:
                similar_users.add(transaction.buyer_id)
    
    # 获取相似用户购买的书籍
    recommended_books = {}
    for similar_user_id in similar_users:
        user_transactions = Transaction.query.filter(
            Transaction.buyer_id == similar_user_id,
            Transaction.status.in_(['paid', 'completed'])
        ).all()
        
        for transaction in user_transactions:
            book = transaction.book
            if book.id not in user_books and book.status == 'available':
                if book.id not in recommended_books:
                    recommended_books[book.id] = {
                        'book': book,
                        'score': 0
                    }
                recommended_books[book.id]['score'] += 1  # 根据被多少个相似用户购买来评分
    
    # 按评分排序并返回
    sorted_recommendations = sorted(
        recommended_books.values(),
        key=lambda x: x['score'],
        reverse=True
    )
    
    return [item['book'] for item in sorted_recommendations[:limit]]


def get_popular_books(limit=5):
    """
    获取热门书籍推荐（基于购买次数）
    """
    popular_books = db.session.query(
        Book,
        func.count(Transaction.id).label('purchase_count')
    ).join(Transaction).filter(
        Transaction.status.in_(['paid', 'completed']),
        Book.status == 'available'
    ).group_by(Book.id).order_by(
        func.count(Transaction.id).desc()
    ).limit(limit).all()
    
    return [book for book, count in popular_books]


def get_hybrid_recommendations(user_id=None, book_id=None, limit=5):
    """
    混合推荐算法：结合内容推荐、协同过滤和热门推荐
    """
    recommendations = []
    
    # 如果指定了书籍ID，使用基于内容的推荐
    if book_id:
        content_recs = get_content_based_recommendations(book_id, limit=limit//2)
        recommendations.extend(content_recs)
    
    # 使用协同过滤推荐
    if user_id:
        collab_recs = get_collaborative_filtering_recommendations(user_id, limit=limit//2)
        for book in collab_recs:
            if book not in recommendations:
                recommendations.append(book)
    
    # 如果推荐数量不足，补充热门书籍
    if len(recommendations) < limit:
        popular_recs = get_popular_books(limit - len(recommendations))
        for book in popular_recs:
            if book not in recommendations:
                recommendations.append(book)
    
    return recommendations[:limit]


def get_user_recommendations(user_id, limit=5):
    """
    为特定用户生成个性化推荐
    """
    return get_hybrid_recommendations(user_id=user_id, limit=limit)


def get_book_recommendations(book_id, limit=5, user_id=None):
    """
    为特定书籍生成相关推荐
    如果提供了user_id则使用，否则尝试从current_user获取
    """
    # 如果没有提供user_id，尝试从当前登录用户获取
    if user_id is None:
        try:
            # 检查用户是否已登录
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                user_id = current_user.id
        except:
            # 如果获取当前用户失败，保持user_id为None
            user_id = None
    
    return get_hybrid_recommendations(user_id=user_id, book_id=book_id, limit=limit)