
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.secret_key = 'kiapars_gym_secure_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # جدول محصولات
    conn.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  description TEXT,
                  price TEXT,
                  image TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL)''')
    
    admin_user = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin_user:
        hashed_password = generate_password_hash('123456') 
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', hashed_password))
    
    conn.commit()
    conn.close()

def crop_to_square(image_path):
    """کراپ هوشمند تصویر به صورت مربعی از مرکز"""
    img = Image.open(image_path)
    width, height = img.size
    min_dim = min(width, height)
    
    left = (width - min_dim) / 2
    top = (height - min_dim) / 2
    right = (width + min_dim) / 2
    bottom = (height + min_dim) / 2
    
    img = img.crop((left, top, right, bottom))
    img = img.resize((600, 600), Image.Resampling.LANCZOS)
    img.save(image_path)

@app.route('/')
def index():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('index.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('نام کاربری یا رمز عبور اشتباه است')
            
    return render_template('login.html')

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('admin.html', products=products)

@app.route('/admin/add', methods=['POST'])
def add_product():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    file = request.files['image']
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        crop_to_square(filepath) # کراپ خودکار به مربع
        
        conn = get_db_connection()
        conn.execute('INSERT INTO products (name, description, price, image) VALUES (?, ?, ?, ?)',
                     (name, description, price, filename))
        conn.commit()
        conn.close()
        
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:id>')
def delete_product(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db_connection()
    # حذف فایل تصویر از هاست
    product = conn.execute('SELECT image FROM products WHERE id = ?', (id,)).fetchone()
    if product:
        try: os.remove(os.path.join(app.config['UPLOAD_FOLDER'], product['image']))
        except: pass
        
    conn.execute('DELETE FROM products WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
