import socket
import os
import joblib
import urllib.parse
import numpy as np
import mimetypes

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 8080))

# ----------------------------
# Загрузка модели
# ----------------------------
try:
    model = joblib.load('model.joblib')
    print("✅ Модель загружена успешно", flush=True)
except:
    print("⚠ Модель не найдена. Используется заглушка", flush=True)
    model = None

# ----------------------------
# MIME types
# ----------------------------
mimetypes.init()
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('image/svg+xml', '.svg')
mimetypes.add_type('font/woff2', '.woff2')

# ----------------------------
# Вспомогательные функции
# ----------------------------
def load_template(name):
    path = os.path.join('templates', name)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return f"<h1>Template {name} missing</h1>"

def build_response(body_bytes, status=200, content_type='text/html; charset=utf-8', extra_headers=None):
    status_text = {200:'OK', 303:'See Other', 404:'Not Found', 500:'Internal Server Error'}.get(status, 'OK')
    headers = [
        f"HTTP/1.1 {status} {status_text}",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close"
    ]
    if extra_headers:
        headers.extend(extra_headers)
    header_bytes = "\r\n".join(headers).encode('utf-8') + b"\r\n\r\n"
    return header_bytes + body_bytes

def serve_static(path):
    path = path.lstrip('/')
    if not os.path.exists(path) or not os.path.isfile(path):
        return build_response(b"<h1>404 Not Found</h1>", 404)
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    with open(path, 'rb') as f:
        data = f.read()
    return build_response(data, 200, mime_type)

# ----------------------------
# Роуты
# ----------------------------
def handle_index():
    return build_response(load_template("index.html").encode('utf-8'))

def handle_test():
    return build_response(load_template("test.html").encode('utf-8'))

def handle_result(query=""):
    html = load_template("result.html")
    if query:
        params = dict(urllib.parse.parse_qsl(query))
        for k,v in params.items():
            html = html.replace(f"{{{{{k}}}}}", urllib.parse.unquote(v))
    return build_response(html.encode('utf-8'))

def handle_submit_test(post_body):
    try:
        # -----------------------------
        # Парсим POST данные
        # -----------------------------
        params = urllib.parse.parse_qs(post_body)
        
        # -----------------------------
        # Собираем все 31 признаков в том же порядке, что при обучении
        # -----------------------------
        features = [
            int(params.get('age', ['0'])[0]),
            int(params.get('gender', ['0'])[0]),
            int(params.get('education_level', ['3'])[0]),
            int(params.get('talkativeness', ['3'])[0]),
            int(params.get('work_accuracy', ['3'])[0]),
            int(params.get('creativity', ['3'])[0]),
            int(params.get('stress_tolerance', ['3'])[0]),
            int(params.get('task_completion', ['3'])[0]),
            int(params.get('work_ethic', ['3'])[0]),
            int(params.get('forgiveness', ['3'])[0]),
            int(params.get('curiosity', ['3'])[0]),
            int(params.get('long_term_focus', ['3'])[0]),
            int(params.get('aesthetic_appreciation', ['3'])[0]),
            int(params.get('future_orientation', ['3'])[0]),
            int(params.get('politeness', ['3'])[0]),
            int(params.get('work_efficiency', ['3'])[0]),
            int(params.get('generosity', ['3'])[0]),
            int(params.get('sociability', ['3'])[0]),
            int(params.get('decision_carefulness', ['3'])[0]),
            int(params.get('reserved_opinions', ['3'])[0]),
            int(params.get('exploitability', ['3'])[0]),
            int(params.get('anxiety', ['3'])[0]),
            int(params.get('preference_leisure', ['3'])[0]),
            int(params.get('nervousness', ['3'])[0]),
            int(params.get('perceived_hostility', ['3'])[0]),
            int(params.get('general_risk', ['0'])[0]),
            int(params.get('driving_risk', ['0'])[0]),
            int(params.get('financial_risk', ['0'])[0]),
            int(params.get('health_risk', ['0'])[0]),
            int(params.get('self_rated_health', ['3'])[0]),
            int(params.get('is_smoker', ['0'])[0]),
        ]
        
        features_2d = np.array(features).reshape(1, -1)
        
        if model:
            prediction = int(model.predict(features_2d)[0])
            probability = model.predict_proba(features_2d)[0][1]
        else:
            prediction = 1
            probability = 0.7
        
        if prediction==1:
            risk='high'
            result_text='ВЫЯВЛЕНА СКЛОННОСТЬ'
            rec='Рекомендуется консультация специалиста'
            icon='🚨'
            color='red'
        else:
            risk='low'
            result_text='СКЛОННОСТЬ НЕ ВЫЯВЛЕНА'
            rec='Рутинное наблюдение'
            icon='✅'
            color='green'
        
        # -----------------------------
        # Редирект на результат
        # -----------------------------
        redirect_url = (
            f"/result.html?"
            f"risk={risk}&"
            f"result={urllib.parse.quote(result_text)}&"
            f"rec={urllib.parse.quote(rec)}&"
            f"age={features[0]}&"
            f"gender={'Мужской' if features[1]==1 else 'Женский'}&"
            f"smoking={'Да' if features[30]==1 else 'Нет'}&"
            f"icon={urllib.parse.quote(icon)}&"
            f"color={color}&"
            f"prob={probability:.1%}"
        )
        return build_response(b"", 303, extra_headers=[f"Location: {redirect_url}"])
    
    except Exception as e:
        error_html = f"<h1>Ошибка: {e}</h1>"
        return build_response(error_html.encode('utf-8'), 500)

# ----------------------------
# Обработка клиента
# ----------------------------
def handle_client(client_socket):
    try:
        request = b""
        while True:
            chunk = client_socket.recv(4096)
            request += chunk
            if len(chunk) < 4096:
                break
        if not request:
            client_socket.close()
            return
        request_text = request.decode('utf-8', errors='ignore')
        first_line = request_text.splitlines()[0]
        method, full_url = first_line.split()[:2]
        path, _, query = full_url.partition('?')
        print(f"📨 {method} {path}?{query}", flush=True)
        
        # -----------------------------
        # Статика
        # -----------------------------
        if path.startswith("/static/") or os.path.splitext(path)[1].lower() in ('.css','.js','.png','.jpg','.jpeg','.svg','.ico','.woff2','.woff','.ttf'):
            response = serve_static(path)
        # -----------------------------
        # Маршруты
        # -----------------------------
        elif path == '/':
            response = handle_index()
        elif path == '/test':
            response = handle_test()
        elif path.startswith('/result'):
            response = handle_result(query)
        elif path=='/submit-test' and method=='POST':
            body = request_text.split("\r\n\r\n",1)[1] if "\r\n\r\n" in request_text else ""
            response = handle_submit_test(body)
        else:
            response = build_response(b"<h1>404 Not Found</h1>",404)
        
        client_socket.sendall(response)
    
    except Exception as e:
        print(f"❌ Ошибка клиента: {e}", flush=True)
    
    finally:
        client_socket.close()

# ----------------------------
# Сервер
# ----------------------------
def main():
    if not os.path.exists('templates'):
        os.makedirs('templates')
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(20)
    print(f"🚀 Сервер запущен на http://{HOST}:{PORT}", flush=True)
    
    while True:
        client_socket, addr = server_socket.accept()
        print(f"👤 Подключение: {addr}", flush=True)
        handle_client(client_socket)

if __name__=="__main__":
    main()
