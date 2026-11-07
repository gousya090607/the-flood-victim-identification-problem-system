import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

# Configuration
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Database helper
DB_PATH = 'flood_victim_system.db'


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# User class for Flask-Login
class Admin(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    admin = conn.execute('SELECT * FROM admin WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if admin:
        return Admin(id_=admin['id'], username=admin['username'])
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        admin = conn.execute('SELECT * FROM admin WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        if admin:
            user = Admin(id_=admin['id'], username=admin['username'])
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        existing = conn.execute('SELECT * FROM admin WHERE username = ?', (username,)).fetchone()
        if existing:
            flash('Username already exists.', 'danger')
        else:
            conn.execute('INSERT INTO admin (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        conn.close()
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    total_victims = conn.execute('SELECT COUNT(*) FROM victims').fetchone()[0]
    total_missing = conn.execute('SELECT COUNT(*) FROM missing_persons').fetchone()[0]
    identified = conn.execute('SELECT COUNT(*) FROM identification_results WHERE confidence > 0').fetchone()[0]
    pending = conn.execute('SELECT COUNT(*) FROM victims WHERE rescue_status = "Pending"').fetchone()[0]
    rescued = conn.execute('SELECT COUNT(*) FROM victims WHERE rescue_status = "Rescued"').fetchone()[0]
    recent = conn.execute('SELECT * FROM victims ORDER BY id DESC LIMIT 5').fetchall()
    conn.close()
    return render_template('dashboard.html', total_victims=total_victims, total_missing=total_missing,
                           identified=identified, pending=pending, rescued=rescued, recent=recent)

# Victim Registration
@app.route('/victim_registration', methods=['GET', 'POST'])
@login_required
def victim_registration():
    if request.method == 'POST':
        data = (
            request.form['full_name'],
            request.form['age'],
            request.form['gender'],
            request.form['contact_number'],
            request.form['address'],
            request.form['district'],
            request.form['last_location'],
            request.form['medical_conditions'],
            request.form['emergency_status'],
            request.form.get('photo')  # placeholder, will be replaced below
        )
        photo = request.files.get('photo')
        photo_filename = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_filename = filename
        conn = get_db_connection()
        conn.execute('''INSERT INTO victims (full_name, age, gender, contact_number, address, district, last_known_location,
                        medical_conditions, emergency_status, photo_path)
                        VALUES (?,?,?,?,?,?,?,?,?,?)''',
                     (data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], photo_filename))
        conn.commit()
        conn.close()
        flash('Victim registered successfully.', 'success')
        return redirect(url_for('victim_registration'))
    return render_template('victim_registration.html')

# Missing Person Registration
@app.route('/missing_person', methods=['GET', 'POST'])
@login_required
def missing_person():
    if request.method == 'POST':
        photo = request.files.get('photo')
        photo_filename = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_filename = filename
        conn = get_db_connection()
        conn.execute('''INSERT INTO missing_persons (full_name, age, gender, photo_path, last_seen_location, date_reported, contact_details)
                        VALUES (?,?,?,?,?,?,?)''',
                     (request.form['full_name'], request.form['age'], request.form['gender'],
                      photo_filename, request.form['last_seen_location'], request.form['date_reported'],
                      request.form['contact_details']))
        conn.commit()
        conn.close()
        flash('Missing person reported.', 'success')
        return redirect(url_for('missing_person'))
    return render_template('missing_person.html')

# AI Identification
from ai_matching import find_similar_missing

@app.route('/identification', methods=['GET', 'POST'])
@login_required
def identification():
    matches = []
    if request.method == 'POST':
        photo = request.files.get('photo')
        if not photo or not allowed_file(photo.filename):
            flash('Invalid or missing photo.', 'danger')
        else:
            filename = secure_filename(photo.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(path)
            matches = find_similar_missing(path)
            # Store results (optional)
            conn = get_db_connection()
            for match in matches:
                conn.execute('''INSERT INTO identification_results (victim_photo_path, missing_person_id, confidence)
                                VALUES (?,?,?)''', (path, match['id'], match['confidence']))
            conn.commit()
            conn.close()
    return render_template('identification.html', matches=matches)

# Rescue Management
@app.route('/rescue_management', methods=['GET', 'POST'])
@login_required
def rescue_management():
    conn = get_db_connection()
    victims = conn.execute('SELECT * FROM victims').fetchall()
    if request.method == 'POST':
        victim_id = request.form['victim_id']
        new_status = request.form['rescue_status']
        conn.execute('UPDATE victims SET rescue_status = ? WHERE id = ?', (new_status, victim_id))
        conn.commit()
        flash('Rescue status updated.', 'success')
        return redirect(url_for('rescue_management'))
    conn.close()
    return render_template('rescue_management.html', victims=victims)

# Search Victims
@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('q', '')
    filter_status = request.args.get('status', '')
    sql = 'SELECT * FROM victims WHERE 1=1'
    params = []
    if query:
        sql += ' AND (full_name LIKE ? OR district LIKE ? OR id = ? )'
        like_q = f"%{query}%"
        params.extend([like_q, like_q, query])
    if filter_status:
        sql += ' AND rescue_status = ?'
        params.append(filter_status)
    conn = get_db_connection()
    results = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template('search.html', victims=results, query=query, filter_status=filter_status)

# Reports
@app.route('/reports')
@login_required
def reports():
    conn = get_db_connection()
    stats = {
        'total_victims': conn.execute('SELECT COUNT(*) FROM victims').fetchone()[0],
        'total_missing': conn.execute('SELECT COUNT(*) FROM missing_persons').fetchone()[0],
        'identified': conn.execute('SELECT COUNT(*) FROM identification_results WHERE confidence > 0').fetchone()[0],
        'rescued': conn.execute('SELECT COUNT(*) FROM victims WHERE rescue_status = "Rescued"').fetchone()[0],
        'pending': conn.execute('SELECT COUNT(*) FROM victims WHERE rescue_status = "Pending"').fetchone()[0],
    }
    conn.close()
    return render_template('reports.html', stats=stats)

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # Initialize DB if not exists
    if not os.path.exists(DB_PATH):
        from database import init_db
        init_db()
    # Enable Flask reloader for development
    app.run(debug=True, use_reloader=True)

