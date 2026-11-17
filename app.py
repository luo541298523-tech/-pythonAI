import sqlite3
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests

app = Flask(__name__)
# 设置 session 密钥，用于加密浏览器 cookie
app.secret_key = 'python_class_secret_key' 

ZHIPU_API_KEY = "ad1000068d12423484cc1a3d50b945d5.TVtbgiQpHK3Y8NY4"

# 初始化本地 SQLite 数据库
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 班级表
    c.execute('CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)')
    # 学生表
    c.execute('CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, class_id INTEGER, FOREIGN KEY(class_id) REFERENCES classes(id), UNIQUE(name, class_id))')
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ================= 登录与注销路由 =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        login_type = request.form.get('type')
        
        # 管理员登录逻辑
        if login_type == 'admin':
            if request.form.get('username') == 'admin' and request.form.get('password') == 'admin':
                session['user_type'] = 'admin'
                return redirect(url_for('admin'))
            else:
                error = '管理员账号或密码错误'
                
        # 学生登录逻辑
        elif login_type == 'student':
            student_name = request.form.get('student_name').strip()
            conn = get_db()
            student = conn.execute('SELECT * FROM students WHERE name = ?', (student_name,)).fetchone()
            conn.close()
            
            if student:
                session['user_type'] = 'student'
                session['student_name'] = student['name']
                return redirect(url_for('index'))
            else:
                error = '系统中未找到该姓名，请联系老师添加。'
                
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ================= 核心编辑器路由 (鉴权) =================
@app.route('/')
def index():
    # 必须是学生才能进入编程界面
    if session.get('user_type') != 'student':
        return redirect(url_for('login'))
    return render_template('index.html')

# ================= 管理员后台路由 (鉴权) =================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # 必须是管理员才能进入后台
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        # 增加班级
        if action == 'add_class':
            class_name = request.form.get('class_name').strip()
            if class_name:
                try:
                    conn.execute('INSERT INTO classes (name) VALUES (?)', (class_name,))
                    conn.commit()
                except sqlite3.IntegrityError:
                    pass # 忽略重复添加
                    
        # 增加学生
        elif action == 'add_student':
            student_name = request.form.get('student_name').strip()
            class_id = request.form.get('class_id')
            if student_name and class_id:
                try:
                    conn.execute('INSERT INTO students (name, class_id) VALUES (?, ?)', (student_name, class_id))
                    conn.commit()
                except sqlite3.IntegrityError:
                    pass # 忽略同班级重名
                    
        # 删除学生
        elif action == 'delete_student':
            student_id = request.form.get('student_id')
            conn.execute('DELETE FROM students WHERE id = ?', (student_id,))
            conn.commit()

    # 获取用于渲染列表的数据
    classes = conn.execute('SELECT * FROM classes').fetchall()
    students = conn.execute('''
        SELECT students.id, students.name as s_name, classes.name as c_name 
        FROM students 
        JOIN classes ON students.class_id = classes.id
        ORDER BY classes.name, students.name
    ''').fetchall()
    conn.close()
    
    return render_template('admin.html', classes=classes, students=students)

# ================= AI 代理接口 (保持不变) =================
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    prompt = data.get('prompt')
    mode = data.get('mode', 'chat')

    sys_prompts = {
        'diagnostics': "你是一个代码诊断助手。请指出学生代码中的语法或逻辑错误，并给出修改建议。如果学生发来的不是代码，请回复：‘请发送需要诊断的代码。’",
        'chat': "你是一个中学生编程辅导AI。你必须先判断学生的问题是否与编程、算法、信息技术相关。如果完全无关，你必须仅回复：‘提问仅限与编程相关的内容。’，绝不能有其他废话。如果相关，再进行专业解答。"
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ZHIPU_API_KEY}"
    }
    
    payload = {
        "model": "glm-4-flash",
        "messages": [
            {"role": "system", "content": sys_prompts.get(mode, sys_prompts['chat'])},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        reply = result['choices'][0]['message']['content']
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": f"服务器代理请求失败，请检查后端报错: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
