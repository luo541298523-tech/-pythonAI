from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# 配置你的智谱 API Key
ZHIPU_API_KEY = "0d41a57ecc7d4673885f1ca28ed3cc62.A5mwHgJKMN5Uijyk"

@app.route('/')
def index():
    # 渲染前端页面
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """接收前端请求，代理调用大模型API"""
    data = request.json
    prompt = data.get('prompt')
    mode = data.get('mode', 'chat')

    # 系统提示词拦截机制
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
        # 向智谱发送请求
        response = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        reply = result['choices'][0]['message']['content']
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": f"服务器代理请求失败，请检查后端报错: {str(e)}"}), 500

if __name__ == '__main__':
    # 监听 0.0.0.0 允许局域网内其他机器（如学生机）通过 IP 访问
    app.run(host='0.0.0.0', port=5000, debug=True)