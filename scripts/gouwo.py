#!/usr/bin/env python3
"""
狗窝 - 本地SQLite知识库
"""

import sqlite3
import sys
import os
import re
from datetime import datetime
from pathlib import Path

# 数据库路径
DB_PATH = os.path.join(os.getcwd(), "data", "gouwo.db")

# 中文停用词，提高关键词提取质量
STOP_WORDS = {
    '的', '是', '在', '我', '有', '和', '就', '不', '也', '都', '要', '这', '那',
    '一个', '可以', '我们', '你', '他', '她', '它', '了', '着', '给', '对', '到',
    '能', '会', '去', '说', '看', '让', '好', '很', '等', '把', '被', '比', '但',
    '如果', '因为', '所以', '而且', '但是', '就是', '还是', '只是', '这个', '那个',
    '一些', '已经', '正在', '没有', '什么', '这样', '那样', '如何', '为什么',
}

def init_db():
    """初始化数据库表，启用FTS全文检索"""
    Path(os.path.dirname(DB_PATH)).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 主表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            keywords TEXT,
            category TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    ''')
    
    # 创建FTS全文检索虚拟表用于高效检索
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts 
        USING fts5(id, content, keywords, content=knowledge, content_rowid=id)
    ''')
    
    # 触发器自动维护FTS索引
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
            INSERT INTO knowledge_fts(rowid, id, content, keywords) 
            VALUES (new.id, new.id, new.content, new.keywords);
        END;
    ''')
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, id, content, keywords) 
            VALUES('delete', old.id, old.id, old.content, old.keywords);
        END;
    ''')
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, id, content, keywords) 
            VALUES('delete', old.id, old.id, old.content, old.keywords);
            INSERT INTO knowledge_fts(rowid, id, content, keywords) 
            VALUES (new.id, new.id, new.content, new.keywords);
        END;
    ''')
    
    conn.commit()
    conn.close()

def extract_keywords(content, num_keywords=10):
    """提取关键词：基于词频，过滤停用词，提高质量"""
    # 去除标点符号，分词
    words = re.findall(r'[\w\u4e00-\u9fa5]+', content)
    
    # 过滤短词和停用词
    words = [w for w in words if len(w) >= 2 and w not in STOP_WORDS]
    
    # 词频统计
    word_count = {}
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1
    
    # 按词频排序，取前N个
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    keywords = [w[0] for w in sorted_words[:num_keywords]]
    
    return ','.join(keywords)

def clean_content(content):
    """清洗内容：去除多余空行、空格，压缩空白，保持整洁"""
    # 将多个换行替换为一个
    content = re.sub(r'\n+', ' ', content)
    # 将多个空格替换为一个
    content = re.sub(r'\s+', ' ', content)
    # 修剪首尾
    content = content.strip()
    return content

def add_content(content, keywords=None, category=None):
    """添加新内容到知识库，先清洗数据，支持分类"""
    # 数据清洗压缩
    content = clean_content(content)
    if not keywords:
        keywords = extract_keywords(content)
    
    init_db()
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        '''INSERT INTO knowledge (content, keywords, category, created_at, updated_at) 
           VALUES (?, ?, ?, ?, ?)''',
        (content, keywords, category, now, now)
    )
    
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    
    print(f"✅ 内容已存入狗窝，ID: {last_id}")
    if category:
        print(f"📁 分类: {category}")
    print(f"🔑 关键词: {keywords}")
    print(f"📊 清洗后大小: {len(content)} 字符")
    return last_id

def update_content(item_id, new_content, keywords=None, category=None):
    """更新已有内容"""
    new_content = clean_content(new_content)
    if not keywords:
        keywords = extract_keywords(new_content)
    
    init_db()
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if category is not None:
        cursor.execute(
            '''UPDATE knowledge 
               SET content=?, keywords=?, category=?, updated_at=? 
               WHERE id=?''',
            (new_content, keywords, category, now, item_id)
        )
    else:
        cursor.execute(
            '''UPDATE knowledge 
               SET content=?, keywords=?, updated_at=? 
               WHERE id=?''',
            (new_content, keywords, now, item_id)
        )
    
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    
    if changed:
        print(f"✏️ 已更新 ID {item_id}")
    else:
        print(f"❌ 未找到 ID {item_id}")
    return changed

def search_content(keyword):
    """按关键词搜索，使用FTS全文检索，更快速更准确"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 使用FTS全文检索，支持多关键词
    query = keyword.replace(',', ' ').replace('，', ' ')
    # 使用FTS匹配
    cursor.execute('''
        SELECT k.id, k.content, k.keywords, k.category, k.created_at
        FROM knowledge k
        JOIN knowledge_fts fts ON k.id = fts.rowid
        WHERE knowledge_fts MATCH ?
        ORDER BY k.created_at DESC
    ''', (query,))
    
    results = cursor.fetchall()
    
    # 如果FTS没找到，降级到模糊搜索
    if not results:
        cursor.execute('''
            SELECT id, content, keywords, category, created_at 
            FROM knowledge 
            WHERE keywords LIKE ? OR content LIKE ?
            ORDER BY created_at DESC
        ''', (f'%{keyword}%', f'%{keyword}%'))
        results = cursor.fetchall()
    
    conn.close()
    
    if not results:
        print("🔍 未找到相关内容")
        return []
    
    print(f"🔍 找到 {len(results)} 条相关内容:\n")
    for i, row in enumerate(results, 1):
        rid, content, keywords, category, created_at = row
        print(f"[{i}] ID: {rid}")
        if category:
            print(f"📁 分类: {category}")
        print(f"📅 创建时间: {created_at[:10]}")
        print(f"🔑 关键词: {keywords}")
        # 如果内容较短，显示全文；较长显示摘要
        if len(content) <= 300:
            print(f"📝 内容: {content}")
        else:
            print(f"📝 内容: {content[:300]}...")
        print("-" * 60)
    
    return results

def get_full(item_id):
    """获取条目的完整内容"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, content, keywords, category, created_at 
        FROM knowledge WHERE id = ?
    ''', (item_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print(f"❌ 未找到 ID {item_id}")
        return None
    
    rid, content, keywords, category, created_at = row
    print(f"\n📖 ID {rid} - 完整内容:\n")
    print(content)
    print(f"\n----------------------------------------")
    print(f"🔑 关键词: {keywords}")
    if category:
        print(f"📁 分类: {category}")
    print(f"📅 创建时间: {created_at}")
    
    return row

def list_all(category=None):
    """列出所有内容，可按分类筛选"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if category:
        cursor.execute('''
            SELECT id, content, keywords, category, created_at 
            FROM knowledge 
            WHERE category = ?
            ORDER BY created_at DESC
        ''', (category,))
    else:
        cursor.execute('''
            SELECT id, content, keywords, category, created_at 
            FROM knowledge 
            ORDER BY created_at DESC
        ''')
    
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        if category:
            print(f"📚 分类 [{category}] 没有内容")
        else:
            print("📚 狗窝还是空的")
        return []
    
    if category:
        print(f"📚 分类 [{category}] 共 {len(results)} 条内容:\n")
    else:
        print(f"📚 狗窝共 {len(results)} 条内容:\n")
    
    for row in results:
        rid, content, keywords, cat, created_at = row
        cat_str = f" | {cat}" if cat else ""
        print(f"ID: {rid} | {created_at[:10]}{cat_str} | {keywords}")
        print(f"  {content[:60]}...")
    
    return results

def delete_item(item_id):
    """删除指定条目"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM knowledge WHERE id = ?', (item_id,))
    conn.commit()
    
    if cursor.rowcount > 0:
        print(f"🗑️ 已删除 ID {item_id}")
    else:
        print(f"❌ 未找到 ID {item_id}")
    
    conn.close()

def show_help():
    """显示帮助"""
    help_text = """
🐶 狗窝 - 本地SQLite知识库使用方法

命令:
  add <内容> [关键词] [分类]    - 添加内容，关键词自动提取，分类可选
  search <关键词>              - 全文搜索相关内容（FTS加速）
  get <id>                    - 获取条目的完整内容
  update <id> <内容> [关键词] - 更新已有内容
  list [分类]                 - 列出所有内容，可按分类筛选
  delete <id>                 - 删除指定ID条目
  stats                       - 统计数据库信息
  help                        - 显示帮助

示例:
  python gouwo.py add "麟德智造3匹机组价格3300元" "麟德智造,价格,3匹" "产品"
  python gouwo.py search "价格"
  python gouwo.py get 1
  python gouwo.py list 产品
"""
    print(help_text)

def stats():
    """统计数据库信息"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM knowledge')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(length(content)) FROM knowledge')
    total_chars = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT DISTINCT category FROM knowledge WHERE category IS NOT NULL')
    categories = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    print(f"📊 狗窝统计:")
    print(f"  总条目数: {total}")
    print(f"  总字符数: {total_chars}")
    print(f"  分类列表: {', '.join(categories) if categories else '无'}")
    print(f"  数据库文件: {DB_PATH}")
    return total, total_chars, categories

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'add':
        if len(sys.argv) < 3:
            print("❌ 请提供要存储的内容")
            return
        content = sys.argv[2]
        keywords = sys.argv[3] if len(sys.argv) > 3 else None
        category = sys.argv[4] if len(sys.argv) > 4 else None
        add_content(content, keywords, category)
    
    elif command == 'search':
        if len(sys.argv) < 3:
            print("❌ 请提供搜索关键词")
            return
        keyword = sys.argv[2]
        search_content(keyword)
    
    elif command == 'get':
        if len(sys.argv) < 3:
            print("❌ 请提供ID")
            return
        item_id = int(sys.argv[2])
        get_full(item_id)
    
    elif command == 'update':
        if len(sys.argv) < 4:
            print("❌ 请提供ID和新内容")
            return
        item_id = int(sys.argv[2])
        new_content = sys.argv[3]
        keywords = sys.argv[4] if len(sys.argv) > 4 else None
        category = sys.argv[5] if len(sys.argv) > 5 else None
        update_content(item_id, new_content, keywords, category)
    
    elif command == 'list':
        category = sys.argv[2] if len(sys.argv) > 2 else None
        list_all(category)
    
    elif command == 'delete':
        if len(sys.argv) < 3:
            print("❌ 请提供要删除的ID")
            return
        item_id = int(sys.argv[2])
        delete_item(item_id)
    
    elif command == 'stats':
        stats()
    
    elif command == 'help':
        show_help()
    
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == '__main__':
    main()
