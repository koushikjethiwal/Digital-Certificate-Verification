import os
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "certificates.db")
_db_path = DEFAULT_DB_PATH
_shared_conn = None

def set_db_path(path):
    """Allows tests to override the database path (e.g., to :memory:)."""
    global _db_path, _shared_conn
    _db_path = path
    _shared_conn = None # Reset shared connection if path changes

def get_db_connection():
    """Connects to the SQLite database. If using :memory:, returns a shared connection."""
    global _shared_conn
    if _db_path == ':memory:':
        if _shared_conn is None:
            _shared_conn = sqlite3.connect(':memory:', check_same_thread=False)
            _shared_conn.row_factory = sqlite3.Row
        return _shared_conn

    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the necessary tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Certificates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS certificates (
            id TEXT PRIMARY KEY,
            student_name TEXT NOT NULL,
            course_name TEXT NOT NULL,
            organization TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            certificate_hash TEXT NOT NULL
        )
    ''')
    # Users table for RBAC
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    if _db_path != ':memory:':
        conn.close()

def create_user(username, password_hash, role='user'):
    """Adds a new user to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
        ''', (username, password_hash, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        if _db_path != ':memory:':
            conn.close()

def get_user_by_username(username):
    """Fetches a user record by username."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    if _db_path != ':memory:':
        conn.close()
    return user

def update_user_status(username, is_active):
    """Enables or disables a user account."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_active = ? WHERE username = ?', (is_active, username))
    conn.commit()
    if _db_path != ':memory:':
        conn.close()

def update_user_role(username, new_role):
    """Changes the role of a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET role = ? WHERE username = ?', (new_role, username))
    conn.commit()
    if _db_path != ':memory:':
        conn.close()

def list_users():
    """Returns all users for the admin management page."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, role, is_active FROM users')
    users = cursor.fetchall()
    if _db_path != ':memory:':
        conn.close()
    return users


def save_certificate(cert_id, name, course, org, date, cert_hash):
    """Saves certificate details into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO certificates (id, student_name, course_name, organization, issue_date, certificate_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cert_id, name, course, org, date, cert_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # ID already exists
    finally:
        if _db_path != ':memory:':
            conn.close()

def get_certificate(cert_id):
    """Fetches a certificate record by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM certificates WHERE id = ?', (cert_id,))
    cert = cursor.fetchone()
    if _db_path != ':memory:':
        conn.close()
    return cert

def update_certificate_data(cert_id, new_name):
    """
    DANGEROUS: Updates the student name.
    Used ONLY for the Tampering Demonstration to show that
    the blockchain will detect the mismatch.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE certificates SET student_name = ? WHERE id = ?', (new_name, cert_id))
    conn.commit()
    if _db_path != ':memory:':
        conn.close()

def delete_all_certificates():
    """Clears all data from the database for the reset workflow."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM certificates')
    conn.commit()
    if _db_path != ':memory:':
        conn.close()
