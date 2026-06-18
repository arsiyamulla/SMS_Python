from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from datetime import datetime
import re
from functools import wraps
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_12345'

# Excel file names
EXCEL_FILE = 'students.xlsx'

# User authentication data
users = [{'id': 1, 'username': 'admin', 'password': 'admin123'}]
user_id_counter = 2

# Valid departments
DEPARTMENTS = ['Computer Science', 'Information Technology', 'Electronics', 'Mechanical', 'Civil', 'Electrical']

# ========== STUDENT FUNCTIONS ==========
def load_students():
    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
            return df.to_dict('records')
        except:
            return []
    else:
        sample = [
            {'id': 1, 'rollno': 'CS101', 'name': 'John Doe', 'dept': 'Computer Science', 
             'email': 'john@example.com', 'phone': '9876543210', 'year': 3, 'cgpa': 8.5, 
             'attendance': 92, 'enrolled_date': '2023-06-15'},
            {'id': 2, 'rollno': 'IT202', 'name': 'Jane Smith', 'dept': 'Information Technology', 
             'email': 'jane@example.com', 'phone': '9876543211', 'year': 2, 'cgpa': 8.9, 
             'attendance': 88, 'enrolled_date': '2023-08-20'},
            {'id': 3, 'rollno': 'CS103', 'name': 'Mike Johnson', 'dept': 'Computer Science', 
             'email': 'mike@example.com', 'phone': '9876543212', 'year': 4, 'cgpa': 7.8, 
             'attendance': 75, 'enrolled_date': '2022-01-10'},
        ]
        save_students(sample)
        return sample

def save_students(data):
    df = pd.DataFrame(data)
    df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')

def get_next_id(data):
    return max([s['id'] for s in data], default=0) + 1

# ========== VALIDATION ==========
def is_valid_rollno(rollno):
    return bool(re.match(r'^[A-Za-z0-9]{4,10}$', rollno))

def is_valid_email(email):
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

def is_valid_phone(phone):
    return bool(re.match(r'^[0-9]{10}$', phone)) if phone else True

# ========== LOGIN REQUIRED ==========
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ========== ROUTES ==========
@app.route('/')
@login_required
def home():
    students = load_students()
    total_students = len(students)
    avg_cgpa = round(sum(s['cgpa'] for s in students)/len(students), 2) if students else 0
    return render_template('index.html', 
                         total_students=total_students,
                         avg_cgpa=avg_cgpa,
                         DEPARTMENTS=DEPARTMENTS)

@app.route('/add', methods=['POST'])
@login_required
def add():
    students = load_students()
    
    rollno = request.form['rollno'].strip()
    name = request.form['name'].strip()
    dept = request.form['dept']
    email = request.form['email'].strip()
    phone = request.form['phone'].strip()
    year = int(request.form['year'])
    cgpa = float(request.form['cgpa'])
    
    if not rollno or not name:
        flash('Roll Number and Name required!', 'error')
        return redirect('/')
    
    if any(s['rollno'] == rollno for s in students):
        flash(f'Roll number {rollno} already exists!', 'error')
        return redirect('/')
    
    if not is_valid_email(email):
        flash('Invalid email!', 'error')
        return redirect('/')
    
    new_student = {
        'id': get_next_id(students),
        'rollno': rollno, 'name': name, 'dept': dept,
        'email': email, 'phone': phone, 'year': year,
        'cgpa': cgpa, 'attendance': 100,
        'enrolled_date': datetime.now().strftime('%Y-%m-%d')
    }
    students.append(new_student)
    save_students(students)
    
    flash(f'Student {name} added!', 'success')
    return redirect('/display')

@app.route('/display')
@login_required
def display():
    students = load_students()
    sort_by = request.args.get('sort', 'rollno')
    
    if sort_by == 'name':
        students = sorted(students, key=lambda x: x['name'])
    elif sort_by == 'cgpa':
        students = sorted(students, key=lambda x: x['cgpa'], reverse=True)
    elif sort_by == 'year':
        students = sorted(students, key=lambda x: x['year'])
    else:
        students = sorted(students, key=lambda x: x['rollno'])
    
    return render_template('display.html', students=students, current_sort=sort_by)

@app.route('/delete/<int:student_id>')
@login_required
def delete(student_id):
    students = load_students()
    students = [s for s in students if s['id'] != student_id]
    save_students(students)
    flash('Student deleted!', 'warning')
    return redirect('/display')

@app.route('/student/<int:student_id>')
@login_required
def view_student(student_id):
    students = load_students()
    student = next((s for s in students if s['id'] == student_id), None)
    if not student:
        flash('Student not found!', 'error')
        return redirect('/display')
    return render_template('student_detail.html', student=student)

# ========== SEARCH FUNCTION ==========
@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    students = load_students()
    results = []
    query = ''
    search_type = 'rollno'
    
    if request.method == 'POST':
        search_type = request.form.get('search_type', 'rollno')
        query = request.form.get('query', '').strip().lower()
        
        if query:
            if search_type == 'rollno':
                results = [s for s in students if query in s['rollno'].lower()]
            elif search_type == 'name':
                results = [s for s in students if query in s['name'].lower()]
            elif search_type == 'dept':
                results = [s for s in students if query in s['dept'].lower()]
            elif search_type == 'cgpa':
                try:
                    cgpa_val = float(query)
                    results = [s for s in students if s['cgpa'] >= cgpa_val]
                except:
                    results = []
        else:
            flash('Please enter a search query!', 'error')
    
    return render_template('search.html', students=results, query=query, search_type=search_type)

# ========== STATISTICS FUNCTION (FIXED) ==========
@app.route('/stats')
@login_required
def stats():
    students = load_students()
    
    if not students:
        flash('No students to display statistics!', 'error')
        return redirect('/')
    
    total = len(students)
    
    # Department distribution
    dept_dist = {}
    for s in students:
        dept_dist[s['dept']] = dept_dist.get(s['dept'], 0) + 1
    
    # Year-wise distribution
    year_dist = {}
    for s in students:
        year_dist[s['year']] = year_dist.get(s['year'], 0) + 1
    
    # CGPA distribution
    cgpa_ranges = {
        'Excellent (9-10)': 0, 
        'Good (8-9)': 0, 
        'Average (7-8)': 0, 
        'Below Average (6-7)': 0, 
        'Poor (<6)': 0
    }
    
    for s in students:
        if s['cgpa'] >= 9:
            cgpa_ranges['Excellent (9-10)'] += 1
        elif s['cgpa'] >= 8:
            cgpa_ranges['Good (8-9)'] += 1
        elif s['cgpa'] >= 7:
            cgpa_ranges['Average (7-8)'] += 1
        elif s['cgpa'] >= 6:
            cgpa_ranges['Below Average (6-7)'] += 1
        else:
            cgpa_ranges['Poor (<6)'] += 1
    
    # Average CGPA by department
    dept_avg_cgpa = {}
    for dept in set(s['dept'] for s in students):
        dept_students = [s['cgpa'] for s in students if s['dept'] == dept]
        dept_avg_cgpa[dept] = round(sum(dept_students) / len(dept_students), 2)
    
    # Best and worst student
    best_student = max(students, key=lambda x: x['cgpa'])
    worst_student = min(students, key=lambda x: x['cgpa'])
    
    return render_template('stats.html', 
                         total=total,
                         dept_dist=dept_dist,
                         year_dist=year_dist,
                         cgpa_ranges=cgpa_ranges,
                         dept_avg_cgpa=dept_avg_cgpa,
                         best_student=best_student,
                         worst_student=worst_student)

@app.route('/export_excel')
@login_required
def export_excel():
    students = load_students()
    df = pd.DataFrame(students)
    if 'id' in df.columns:
        df = df.drop('id', axis=1)
    df.to_excel('export.xlsx', index=False, engine='openpyxl')
    return send_file('export.xlsx', as_attachment=True, download_name='students_data.xlsx')

# ========== LOGIN ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = next((u for u in users if u['username'] == username and u['password'] == password), None)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Welcome {username}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials!', 'error')
    return render_template('login_page.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    global user_id_counter
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm_password']
        
        if any(u['username'] == username for u in users):
            flash('Username exists!', 'error')
        elif password != confirm:
            flash('Passwords do not match!', 'error')
        elif len(password) < 4:
            flash('Password too short!', 'error')
        else:
            users.append({'id': user_id_counter, 'username': username, 'password': password})
            user_id_counter += 1
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out!', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)