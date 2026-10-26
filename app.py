from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
import hashlib
import json
import random
import string
import os
from datetime import datetime
from functools import wraps
from werkzeug.security import check_password_hash

# Import our local logic
import database
from blockchain import Blockchain

app = Flask(__name__)
# Use environment variable for secret key, fallback to dev key for local development
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-certchain-2026')
app.permanent_session_lifetime = 1200 # 20 minutes

# Initialize database and blockchain
database.init_db()
bc = Blockchain()

# --- Authorization Decorators ---

def login_required(f):
    """Ensures the user is authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Store the requested URL to redirect back after login
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Ensures the user is an administrator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        if session.get('role') != 'admin':
            # Access denied for regular users
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

def generate_cert_id():
    """Generates a unique certificate ID (e.g., CERT-A1B2C3)."""
    chars = string.ascii_uppercase + string.digits
    random_id = ''.join(random.choices(chars, k=6))
    return f"CERT-{random_id}"

def calculate_certificate_hash(name, course, org, date):
    """
    Creates a SHA-256 hash of the certificate details.
    The data is sorted and combined into a single string to ensure
    the hash is always the same for the same input.
    """
    cert_string = f"Name:{name}|Course:{course}|Org:{org}|Date:{date}"
    return hashlib.sha256(cert_string.encode()).hexdigest()

@app.route('/')
def index():
    return redirect(url_for('landing'))

@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/architecture')
def architecture():
    return render_template('architecture.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = database.get_user_by_username(username)

        if user and check_password_hash(user['password_hash'], password):
            if not user['is_active']:
                return render_template('login.html', error="Your account is disabled. Please contact an administrator.")

            # Establish Session
            session.clear() # Rotate session to prevent fixation
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard'))

        return render_template('login.html', error="Invalid login credentials. Please try again.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # 1. Fetch Total Certificates
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM certificates')
    total_certs = cursor.fetchone()['count']

    # 2. Recent Activity (Last 10)
    cursor.execute('SELECT * FROM certificates ORDER BY id DESC LIMIT 10')
    recent_certs = cursor.fetchall()

    # 3. Course Distribution (for charts)
    cursor.execute('SELECT course_name, COUNT(*) as count FROM certificates GROUP BY course_name')
    course_dist = [{"label": row['course_name'], "value": row['count']} for row in cursor.fetchall()]

    # 4. Issuance Trends (last 30 days)
    cursor.execute('SELECT issue_date, COUNT(*) as count FROM certificates GROUP BY issue_date ORDER BY issue_date ASC')
    trends = [{"date": row['issue_date'], "count": row['count']} for row in cursor.fetchall()]

    # Avoid closing shared in-memory connection
    if database._db_path != ':memory:':
        conn.close()

    # 5. Blockchain Metrics
    chain_length = len(bc.chain)
    is_valid, validation_msg = bc.is_chain_valid()

    # 6. Consistency Check: Are all DB records anchored in BC?
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM certificates')
    all_ids = [row['id'] for row in cursor.fetchall()]

    if database._db_path != ':memory:':
        conn.close()

    anchored_count = 0
    unanchored_ids = []
    for cid in all_ids:
        if any(cid in block.data for block in bc.chain):
            anchored_count += 1
        else:
            unanchored_ids.append(cid)

    all_anchored = (len(all_ids) == anchored_count)
    unanchored_count = len(unanchored_ids)

    return render_template('index.html',
                           total_certs=total_certs,
                           chain_length=chain_length,
                           is_valid=is_valid,
                           validation_msg=validation_msg,
                           all_anchored=all_anchored,
                           unanchored_count=unanchored_count,
                           unanchored_ids=unanchored_ids,
                           recent_certs=recent_certs,
                           course_dist=json.dumps(course_dist),
                           trends=json.dumps(trends))

@app.route('/issue', methods=['GET', 'POST'])
@login_required
def issue():
    if request.method == 'POST':
        name = request.form.get('student_name')
        course = request.form.get('course_name')
        org = request.form.get('organization')
        date = request.form.get('issue_date')

        # 1. Generate Unique ID
        cert_id = generate_cert_id()

        # 2. Calculate Certificate Hash
        cert_hash = calculate_certificate_hash(name, course, org, date)

        # 3. Save to SQLite Database
        success = database.save_certificate(cert_id, name, course, org, date, cert_hash)

        if success:
            # 4. Add to Blockchain
            # We store the cert_id and the hash in the block for transparency
            block_data = f"ID:{cert_id} | Hash:{cert_hash}"
            bc.add_block(block_data)

            return render_template('issue.html', message=f"Success! Certificate issued. ID: {cert_id}")
        else:
            return render_template('issue.html', message="Error: Could not save certificate.")

    return render_template('issue.html')

@app.route('/verify', methods=['GET', 'POST'])
@login_required
def verify():
    result = None
    cert = None

    if request.method == 'POST':
        cert_id = request.form.get('cert_id')

        # 1. Fetch from Database
        cert = database.get_certificate(cert_id)

        if cert:
            # 2. Re-calculate Hash of current data in DB
            current_hash = calculate_certificate_hash(
                cert['student_name'],
                cert['course_name'],
                cert['organization'],
                cert['issue_date']
            )

            # 3. Compare with the hash recorded during issuance
            if current_hash != cert['certificate_hash']:
                result = {
                    'status': 'Tampered',
                    'message': 'DATABASE TAMPERING DETECTED! The certificate data has been modified after issuance. The current data hash does not match the original locked hash.',
                    'detail': 'The "fingerprint" has changed.'
                }
            else:
                # 4. Check if Blockchain is valid
                is_valid, msg = bc.is_chain_valid()
                if not is_valid:
                    result = {
                        'status': 'Invalid',
                        'message': f'BLOCKCHAIN INTEGRITY COMPROMISED: {msg}',
                        'detail': 'The chain of trust is broken.'
                    }
                else:
                    # 5. Finally, ensure the record actually exists in the blockchain
                    found_in_chain = any(cert_id in block.data for block in bc.chain)
                    if found_in_chain:
                        result = {
                            'status': 'Verified',
                            'message': 'Certificate is authentic and verified against the blockchain ledger.',
                            'detail': 'All integrity checks passed.'
                        }
                    else:
                        result = {
                            'status': 'Invalid',
                            'message': 'Blockchain Record Missing: The certificate exists in the database but no corresponding entry exists in the blockchain.',
                            'detail': 'The record is not anchored to the chain.'
                        }
        else:
            result = {
                'status': 'Not Found',
                'message': 'Invalid Certificate ID. No such record exists in our systems.',
                'detail': 'Check the ID and try again.'
            }

    return render_template('verify.html', result=result, cert=cert)

@app.route('/explorer')
@admin_required
def explorer():
    is_valid, msg = bc.is_chain_valid()
    # Convert block objects to dicts for the template
    chain_data = [block.to_dict() for block in bc.chain]
    return render_template('explorer.html', chain=chain_data, chain_valid=is_valid, validation_message=msg)

@app.route('/tamper', methods=['POST'])
@admin_required
def tamper():
    cert_id = request.form.get('cert_id')
    fake_name = request.form.get('fake_name')

    # Directly modify the database to simulate an attack
    database.update_certificate_data(cert_id, fake_name)

    return redirect(url_for('explorer'))

@app.route('/reset', methods=['GET', 'POST'])
@admin_required
def reset():
    if request.method == 'POST':
        # Clear Database
        database.delete_all_certificates()
        # Reset Blockchain
        bc.initialize_new_chain()
        return redirect(url_for('explorer'))

    # GET request shows confirmation page
    return render_template('reset_confirm.html')

@app.route('/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    if request.method == 'POST':
        username = request.form.get('username')
        action = request.form.get('action')

        if action == 'toggle_status':
            current_user = database.get_user_by_username(username)
            if current_user:
                new_status = 0 if current_user['is_active'] else 1
                database.update_user_status(username, new_status)

        elif action == 'change_role':
            new_role = request.form.get('role')
            if new_role in ['user', 'admin']:
                database.update_user_role(username, new_role)

        return redirect(url_for('manage_users'))

    users = database.list_users()
    return render_template('users.html', users=users)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
