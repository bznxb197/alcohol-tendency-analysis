import socket
import os
import joblib
import urllib.parse
import numpy as np
import mimetypes
import threading
import html
import re

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 10000))
BASE_DIR = os.path.abspath('.')   # корень для статики

# ----------------------------
# Загрузка модели
# ----------------------------
def load_model():
    if os.path.exists('model.joblib'):
        print("Модель загружена успешно", flush=True)
        return joblib.load('model.joblib')
    else:
        print("Модель не найдена. Используется заглушка", flush=True)
        return None

model = load_model()

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
    # Защита от Path Traversal
    safe_path = os.path.normpath(path.lstrip('/'))
    full_path = os.path.abspath(safe_path)
    if not full_path.startswith(BASE_DIR):
        return build_response(b"Forbidden", 403)
    if not os.path.isfile(full_path):
        return build_response(b"<h1>404 Not Found</h1>", 404)
    mime_type, _ = mimetypes.guess_type(full_path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    with open(full_path, 'rb') as f:
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
    html_template = load_template("result.html")
    if query:
        params = dict(urllib.parse.parse_qsl(query))
        for k, v in params.items():
            # Защита от XSS: экранируем HTML-символы
            safe_value = html.escape(urllib.parse.unquote(v))
            html_template = html_template.replace(f"{{{{{k}}}}}", safe_value)
    return build_response(html_template.encode('utf-8'))

def handle_submit_test(post_body):
    try:
        # Парсим POST данные (x-www-form-urlencoded)
        params = urllib.parse.parse_qs(post_body.decode('utf-8'))

        # Извлекаем «сырые» значения (числа, но могут быть пустыми)
        def get_int(key, default=0):
            val = params.get(key, [str(default)])[0]
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        # ---------- Демография ----------
        age = get_int('age', 30)
        gender = get_int('gender', 0)          # 1=М, 0=Ж
        education = get_int('education_level', 3)

        # ---------- Личностные черты (1-4) ----------
        talkativeness = get_int('talkativeness', 3)
        work_accuracy = get_int('work_accuracy', 3)
        creativity = get_int('creativity', 3)

        stress_tolerance_raw = get_int('stress_tolerance', 3)
        task_completion_raw = get_int('task_completion', 3)
        work_ethic_raw = get_int('work_ethic', 3)
        forgiveness = get_int('forgiveness', 3)
        curiosity = get_int('curiosity', 3)

        long_term_focus_raw = get_int('long_term_focus', 3)
        aesthetic_appreciation = get_int('aesthetic_appreciation', 3)
        future_orientation_raw = get_int('future_orientation', 3)
        politeness = get_int('politeness', 3)

        work_efficiency_raw = get_int('work_efficiency', 3)
        generosity = get_int('generosity', 3)
        sociability = get_int('sociability', 3)

        decision_carefulness_raw = get_int('decision_carefulness', 3)
        reserved_opinions = get_int('reserved_opinions', 3)

        # Риск-усиливающие (без инверсии)
        exploitability = get_int('exploitability', 3)
        anxiety = get_int('anxiety', 3)
        preference_leisure = get_int('preference_leisure', 3)
        nervousness = get_int('nervousness', 3)
        perceived_hostility = get_int('perceived_hostility', 3)

        # ---------- Рисковое поведение (0-10) ----------
        general_risk = get_int('general_risk', 0)
        driving_risk = get_int('driving_risk', 0)
        financial_risk = get_int('financial_risk', 0)
        health_risk = get_int('health_risk', 0)

        # ---------- Новый признак ----------
        future_sacrifice = get_int('future_sacrifice', 5)   # 0-10

        # ---------- Здоровье ----------
        self_rated_health = get_int('self_rated_health', 3)  # 1-5
        is_smoker = get_int('is_smoker', 0)                  # 1=Да, 0=Нет

        # ---------- ИНВЕРСИЯ ЗАЩИТНЫХ ЧЕРТ (1↔4, 2↔3) ----------
        invert = {1:4, 2:3, 3:2, 4:1}
        stress_tolerance = invert.get(stress_tolerance_raw, stress_tolerance_raw)
        task_completion = invert.get(task_completion_raw, task_completion_raw)
        work_ethic = invert.get(work_ethic_raw, work_ethic_raw)
        long_term_focus = invert.get(long_term_focus_raw, long_term_focus_raw)
        future_orientation = invert.get(future_orientation_raw, future_orientation_raw)
        work_efficiency = invert.get(work_efficiency_raw, work_efficiency_raw)
        decision_carefulness = invert.get(decision_carefulness_raw, decision_carefulness_raw)

        # ---------- Формируем массив признаков в СТРОГОМ ПОРЯДКЕ ----------
        features = [
            age,
            gender,
            education,
            talkativeness,
            work_accuracy,
            creativity,
            stress_tolerance,       # уже инвертирован
            task_completion,
            work_ethic,
            forgiveness,
            curiosity,
            long_term_focus,
            aesthetic_appreciation,
            future_orientation,
            politeness,
            work_efficiency,
            generosity,
            sociability,
            decision_carefulness,
            reserved_opinions,
            exploitability,
            anxiety,
            preference_leisure,
            nervousness,
            perceived_hostility,
            general_risk,
            driving_risk,
            financial_risk,
            health_risk,
            future_sacrifice,       # новый признак
            self_rated_health,
            is_smoker
        ]

        features_2d = np.array(features).reshape(1, -1)

        # ---------- Предсказание ----------
        if model:
            prediction = int(model.predict(features_2d)[0])
            probability = model.predict_proba(features_2d)[0][1]
        else:
            prediction = 1
            probability = 0.7

        # ---------- Категории риска (пороги можно настроить) ----------
        if probability >= 0.7:
            risk = 'high'
            result_text = 'ВЫЯВЛЕНА СКЛОННОСТЬ'
            rec = 'Рекомендуется консультация специалиста'
            icon = '🚨'
            color = 'red'
        elif probability >= 0.4:
            risk = 'medium'
            result_text = 'ВЫЯВЛЕНА СРЕДНЯЯ СКЛОННОСТЬ'
            rec = 'Следует быть внимательным, возможно наблюдение специалиста'
            icon = '⚠️'
            color = 'orange'
        else:
            risk = 'low'
            result_text = 'СКЛОННОСТЬ НЕ ВЫЯВЛЕНА'
            rec = 'Рутинное наблюдение'
            icon = '✅'
            color = 'green'

        # Формируем редирект
        gender_str = 'Мужской' if gender == 1 else 'Женский'
        smoker_str = 'Да' if is_smoker == 1 else 'Нет'

        redirect_url = (
            f"/result.html?"
            f"risk={risk}&"
            f"result={urllib.parse.quote(result_text)}&"
            f"rec={urllib.parse.quote(rec)}&"
            f"age={age}&"
            f"gender={urllib.parse.quote(gender_str)}&"
            f"smoking={urllib.parse.quote(smoker_str)}&"
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
        client_socket.settimeout(5)
        request = b""
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            request += chunk
            if len(chunk) < 4096:
                break

        if not request:
            client_socket.close()
            return

        request_text = request.decode('utf-8', errors='ignore')
        lines = request_text.splitlines()
        if not lines:
            client_socket.close()
            return
        first_line = lines[0]
        method, full_url = first_line.split()[:2]
        path, _, query = full_url.partition('?')
        print(f"{method} {path}?{query}", flush=True)

        # Статика
        if path.startswith("/static/") or os.path.splitext(path)[1].lower() in ('.css','.js','.png','.jpg','.jpeg','.svg','.ico','.woff2','.woff','.ttf'):
            response = serve_static(path)
        elif path == '/':
            response = handle_index()
        elif path == '/test':
            response = handle_test()
        elif path.startswith('/result'):
            response = handle_result(query)
        elif path == '/submit-test' and method == 'POST':
            # Извлекаем Content-Length и читаем тело целиком
            content_length = 0
            for line in lines:
                if line.lower().startswith('content-length:'):
                    content_length = int(line.split(':')[1].strip())
                    break
            header_end = request.find(b"\r\n\r\n") + 4
            body = request[header_end:header_end + content_length]
            response = handle_submit_test(body)
        else:
            response = build_response(b"<h1>404 Not Found</h1>", 404)

        client_socket.sendall(response)

    except Exception as e:
        print(f"Ошибка клиента: {e}", flush=True)
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
    print(f"Сервер запущен на http://{HOST}:{PORT}", flush=True)

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Подключение: {addr}", flush=True)
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == "__main__":
    main()