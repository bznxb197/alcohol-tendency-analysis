import socket
import os
import joblib
import urllib.parse
import numpy as np

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 8080))

# Загрузка модели
try:
    model = joblib.load('model.joblib')
    print("✅ Модель загружена успешно", flush=True)
except Exception as e:
    print(f"⚠ Модель не найдена ({e}). Используем заглушку.", flush=True)
    model = None

def load_template(name):
    path = f'templates/{name}'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as file:
            return file.read()
    return f"<h1>Template {name} missing</h1>"

def response_ok(body, content_type="text/html"):
    return f"""HTTP/1.1 200 OK
Content-Type: {content_type}; charset=utf-8
Connection: close

{body}""".encode("utf-8")

def handle_index():
    return response_ok(load_template("index.html"))

def handle_test():
    return response_ok(load_template("test.html"))

def handle_result():
    return response_ok(load_template("result.html"))

def handle_submit_test(post_data):
    try:
        params = dict(urllib.parse.parse_qsl(post_data))
        scores = np.array([int(params.get(f"q{i}", 0)) for i in range(1, 6)])

        if model:
            prediction = model.predict([scores])[0]
            risk_level = int(prediction)
        else:
            risk_level = int(scores.mean() > 2)  # Простейшая заглушка

        result_text = ["Низкий риск", "Высокий риск"][risk_level]
        recommendation = ["Поддерживайте своё состояние", "Обратитесь за консультацией"][risk_level]
        icon = ["✅", "⚠️"][risk_level]
        color = ["green", "red"][risk_level]

        redirect_url = (
            f"/result?"
            f"risk={risk_level}&"
            f"result={urllib.parse.quote(result_text)}&"
            f"rec={urllib.parse.quote(recommendation)}&"
            f"icon={urllib.parse.quote(icon)}&"
            f"color={color}"
        )

        return f"""HTTP/1.1 303 See Other
Location: {redirect_url}
Connection: close

""".encode("utf-8")

    except Exception as e:
        print(f"❌ Ошибка обработки POST: {e}", flush=True)
        return response_ok(f"<h3>Ошибка обработки: {e}</h3>")

def handle_client(client_socket):
    try:
        request = client_socket.recv(4096).decode("utf-8", errors="ignore")
        if not request:
            client_socket.close()
            return

        first_line = request.split("\n")[0]
        method, url = first_line.split()[:2]

        print(f"📨 {method} {url}", flush=True)

        if url == "/":
            response = handle_index()
        elif url == "/test":
            response = handle_test()
        elif url.startswith("/result"):
            response = handle_result()
        elif url == "/submit-test" and method == "POST":
            body = request.split("\r\n\r\n")[-1]
            response = handle_submit_test(body)
        else:
            response = b"""HTTP/1.1 404 Not Found
Connection: close

<h1>404</h1>"""

        client_socket.sendall(response)

    except Exception as e:
        print(f"❌ Ошибка клиента: {e}", flush=True)
    finally:
        client_socket.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(20)
    
    print(f"🚀 Сервер запущен на http://{HOST}:{PORT}", flush=True)

    if not os.path.exists('templates'):
        os.makedirs('templates')
        print("📁 Папка templates создана", flush=True)

    while True:
        client_socket, addr = server.accept()
        print(f"👤 Подключение: {addr}", flush=True)
        handle_client(client_socket)

if __name__ == "__main__":
    main()
