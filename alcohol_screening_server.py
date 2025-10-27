import socket
import multiprocessing
import os
import joblib
import urllib.parse
import numpy as np
import traceback 

# Конфигурация для продакшена
HOST = os.environ.get('HOST', '0.0.0.0')  # Важно для деплоя!
PORT = int(os.environ.get('PORT', 8080))

# Загрузка модели
try:
    model = joblib.load('model.joblib')
    print("✅ Модель загружена успешно")
except Exception as e:
    print(f"❌ Ошибка загрузки модели: {e}. Используется заглушка.")
    model = None

def load_template(template_name):
    """Загрузка HTML шаблона"""
    try:
        with open(f'templates/{template_name}', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"<h1>Error: Template {template_name} not found</h1>"

def handle_index():
    """Главная страница"""
    html = load_template('index.html')
    response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Server: AlcoholScreening
Connection: close

{html}"""
    return response.encode('utf-8')

def handle_test():
    """Страница теста"""
    html = load_template('test.html')
    response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Server: AlcoholScreening
Connection: close

{html}"""
    return response.encode('utf-8')

def handle_result():
    """Страница результата"""
    html = load_template('result.html')
    response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Server: AlcoholScreening
Connection: close

{html}"""
    return response.encode('utf-8')

def handle_submit_test(post_data):
    """Обработка результатов теста"""
    try:
        # Ваша существующая логика обработки...
        # ... (оставьте ваш текущий код без изменений)
        
        # Редирект на страницу результата
        redirect_url = (
            f"/result.html?"
            f"risk={risk_level}&"
            f"result={urllib.parse.quote(result_text)}&"
            f"rec={urllib.parse.quote(recommendation)}&"
            f"icon={urllib.parse.quote(icon)}&"
            f"color={color}"
        )
        
        response = f"""HTTP/1.1 303 See Other
Location: {redirect_url}
Connection: close

"""
        return response.encode('utf-8')
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        error_html = f"""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>❌ Ошибка</h1><p>{str(e)}</p>
            <a href="/test">Вернуться к тесту</a>
        </body></html>
        """
        return error_html.encode('utf-8')
    
def handle_client(client_socket, id):
    """Обработка клиентского соединения"""
    try:
        request_data = client_socket.recv(1024).decode('utf-8', errors='ignore')
        if not request_data:
            return
            
        lines = request_data.split('\n')
        if not lines:
            return
            
        first_line = lines[0].split()
        if len(first_line) < 2:
            return
            
        method, url = first_line[0], first_line[1]
        
        print(f"📨 Запрос: {method} {url}")
        
        # Обработка разных URL
        if url == '/':
            response = handle_index()
        elif url == '/test':
            response = handle_test()
        elif url.startswith('/result.html'):
            response = handle_result()
        elif url == '/submit-test' and method == 'POST':
            content_length = 0
            for line in lines:
                if line.startswith('Content-Length:'):
                    content_length = int(line.split(':')[1].strip())
                    break
            
            body = request_data.split('\r\n\r\n')[-1]
            if len(body) < content_length:
                remaining = content_length - len(body)
                body += client_socket.recv(remaining).decode('utf-8', errors='ignore')
            
            response = handle_submit_test(body)
        else:
            # 404 для всех остальных URL
            response = """HTTP/1.1 404 Not Found
Content-Type: text/html
Connection: close

<h1>404 Not Found</h1>
<p>Страница не найдена</p>
<a href="/">На главную</a>""".encode('utf-8')
        
        client_socket.sendall(response)
        client_socket.close()
        
    except Exception as e:
        print(f"❌ Ошибка обработки клиента: {e}")
        try:
            client_socket.close()
        except:
            pass

def main():
    """Запуск сервера"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    print(f"🚀 Alcohol Screening Server запущен на http://{HOST}:{PORT}")
    print("📊 Модель:", "загружена" if model else "не загружена (используется заглушка)")
    
    # Создаем папку templates если её нет
    if not os.path.exists('templates'):
        os.makedirs('templates')
        print("📁 Создана папка templates")
    
    id = multiprocessing.Value("i", 0)
    
    try:
        while True:
            client_socket, addr = server_socket.accept()
            print(f"📨 Новое соединение от {addr[0]}:{addr[1]}")
            
            client_process = multiprocessing.Process(
                target=handle_client, 
                args=(client_socket, id)
            )
            client_process.start()
            
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
