import sqlite3
import os

def migrate():
    # 指向应用同目录下的 bookstore.db，避免硬编码本机绝对路径
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bookstore.db')
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    columns_to_add = [
        ('cover_image_path', 'TEXT'),
        ('title_page_image_path', 'TEXT'),
        ('inside_page_image_path', 'TEXT'),
        ('back_cover_image_path', 'TEXT'),
        ('ai_assessment_result', 'TEXT')
    ]

    for column, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE books ADD COLUMN {column} {col_type}")
            print(f"Added column {column}.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {column} already exists.")
            else:
                print(f"Error adding column {column}: {e}")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate()
