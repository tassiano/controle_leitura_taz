import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "taz_reading.db"

def connect_db():
    """Cria uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Retorna linhas como dicionários
    return conn

def create_tables():
    """Cria as tabelas necessárias se não existirem."""
    conn = connect_db()
    cursor = conn.cursor()

    # Tabela de Livros
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT,
            total_pages INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('lendo', 'concluído', 'abandonado', 'desejado')),
            start_date TEXT, -- Formato YYYY-MM-DD
            end_date TEXT     -- Formato YYYY-MM-DD
        )
    ''')

    # Tabela de Log de Leitura
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            log_date TEXT NOT NULL, -- Formato YYYY-MM-DD
            pages_read INTEGER NOT NULL,
            notes TEXT,
            FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()

# --- Funções CRUD para Livros ---

def add_book(title, author, genre, total_pages, status, start_date=None, end_date=None):
    conn = connect_db()
    cursor = conn.cursor()
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    cursor.execute('''
        INSERT INTO books (title, author, genre, total_pages, status, start_date, end_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (title, author, genre, total_pages, status, start_date_str, end_date_str))
    conn.commit()
    conn.close()

def get_all_books():
    conn = connect_db()
    # Usando Pandas para ler diretamente do SQL para um DataFrame
    try:
        df = pd.read_sql_query("SELECT * FROM books ORDER BY title", conn)
        # Converter datas de string para datetime objects (se existirem)
        if 'start_date' in df.columns:
            df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce').dt.date
        if 'end_date' in df.columns:
            df['end_date'] = pd.to_datetime(df['end_date'], errors='coerce').dt.date
        return df
    except Exception as e:
        print(f"Erro ao buscar livros: {e}")
        # Retorna DataFrame vazio se a tabela não existir ou ocorrer erro
        return pd.DataFrame(columns=['id', 'title', 'author', 'genre', 'total_pages', 'status', 'start_date', 'end_date'])
    finally:
        conn.close()


def get_book_by_id(book_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()
    conn.close()
    return dict(book) if book else None

def update_book(book_id, title, author, genre, total_pages, status, start_date=None, end_date=None):
    conn = connect_db()
    cursor = conn.cursor()
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    cursor.execute('''
        UPDATE books
        SET title = ?, author = ?, genre = ?, total_pages = ?, status = ?, start_date = ?, end_date = ?
        WHERE id = ?
    ''', (title, author, genre, total_pages, status, start_date_str, end_date_str, book_id))
    conn.commit()
    conn.close()

def delete_book(book_id):
    conn = connect_db()
    cursor = conn.cursor()
    # Deletar logs associados primeiro (CASCADE deve cuidar disso, mas é bom garantir)
    # cursor.execute("DELETE FROM reading_log WHERE book_id = ?", (book_id,))
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()

def get_books_by_status(status):
     conn = connect_db()
     df = pd.read_sql_query("SELECT id, title FROM books WHERE status = ? ORDER BY title", conn, params=(status,))
     conn.close()
     return df

# --- Funções para Log de Leitura ---

def add_log_entry(book_id, log_date, pages_read, notes=None):
    conn = connect_db()
    cursor = conn.cursor()
    log_date_str = log_date.strftime('%Y-%m-%d')
    cursor.execute('''
        INSERT INTO reading_log (book_id, log_date, pages_read, notes)
        VALUES (?, ?, ?, ?)
    ''', (book_id, log_date_str, pages_read, notes))
    conn.commit()
    conn.close()

def get_reading_log(book_id=None, start_date=None, end_date=None):
    conn = connect_db()
    query = """
        SELECT rl.id, rl.log_date, rl.pages_read, rl.notes, b.title as book_title, rl.book_id
        FROM reading_log rl
        JOIN books b ON rl.book_id = b.id
    """
    params = []
    conditions = []

    if book_id:
        conditions.append("rl.book_id = ?")
        params.append(book_id)
    if start_date:
        conditions.append("rl.log_date >= ?")
        params.append(start_date.strftime('%Y-%m-%d'))
    if end_date:
        conditions.append("rl.log_date <= ?")
        params.append(end_date.strftime('%Y-%m-%d'))

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY rl.log_date DESC, rl.id DESC" # Ordena por data e depois ID

    try:
        df = pd.read_sql_query(query, conn, params=params)
        if not df.empty:
             df['log_date'] = pd.to_datetime(df['log_date']) # Converte para datetime
        return df
    except Exception as e:
        print(f"Erro ao buscar log de leitura: {e}")
        return pd.DataFrame(columns=['id', 'log_date', 'pages_read', 'notes', 'book_title', 'book_id'])
    finally:
        conn.close()


def get_pages_read_for_book(book_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(pages_read) FROM reading_log WHERE book_id = ?", (book_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] is not None else 0

# --- Inicialização ---
# Cria as tabelas na primeira vez que o módulo é importado
create_tables()