import socket
import multiprocessing
import os
import datetime
import joblib
import urllib.parse
import numpy as np
import traceback 

# Загрузка модели
try:
    model = joblib.load('model.joblib')
    print("✅ Модель загружена успешно")
except:
    print("❌ Ошибка загрузки модели. Используется заглушка.")
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
    """Обработка результатов теста с бинарной классификацией"""
    try:
        # Парсим POST данные
        params = urllib.parse.parse_qs(post_data)
        
        print(f"📊 Получены параметры: {list(params.keys())}")
        
        # Извлекаем признаки (порядок как в модели)
        features = [
            # Демография (3)
            int(params.get('age', [0])[0]),
            int(params.get('gender', [0])[0]),
            int(params.get('education_level', [3])[0]),
            
            # Личностные характеристики (22)
            int(params.get('talkativeness', [3])[0]),
            int(params.get('work_accuracy', [3])[0]),
            int(params.get('creativity', [3])[0]),
            int(params.get('stress_tolerance', [3])[0]),
            int(params.get('task_completion', [3])[0]),
            int(params.get('work_ethic', [3])[0]),
            int(params.get('forgiveness', [3])[0]),
            int(params.get('curiosity', [3])[0]),
            int(params.get('long_term_focus', [3])[0]),
            int(params.get('aesthetic_appreciation', [3])[0]),
            int(params.get('future_orientation', [3])[0]),
            int(params.get('politeness', [3])[0]),
            int(params.get('work_efficiency', [3])[0]),
            int(params.get('generosity', [3])[0]),
            int(params.get('sociability', [3])[0]),
            int(params.get('decision_carefulness', [3])[0]),
            int(params.get('reserved_opinions', [3])[0]),
            int(params.get('exploitability', [3])[0]),
            int(params.get('anxiety', [3])[0]),
            int(params.get('preference_leisure', [3])[0]),
            int(params.get('nervousness', [3])[0]),
            int(params.get('perceived_hostility', [3])[0]),
            
            # Рисковое поведение (4)
            int(params.get('general_risk', [0])[0]),
            int(params.get('driving_risk', [0])[0]),
            int(params.get('financial_risk', [0])[0]),
            int(params.get('health_risk', [0])[0]),
            
            # Здоровье и курение (2)
            int(params.get('self_rated_health', [3])[0]),
            int(params.get('is_smoker', [0])[0]),
        ]
        
        print(f"🔢 Признаков: {len(features)}")
        
        # Преобразуем в 2D массив
        features_2d = np.array(features).reshape(1, -1)
        
        # БИНАРНОЕ ПРЕДСКАЗАНИЕ (склонен/не склонен)
        if model is not None:
            prediction = model.predict(features_2d)[0]  # 0 или 1
            probability = model.predict_proba(features_2d)[0][1]  # для информации
        else:
            prediction = 1  # заглушка - склонен
            probability = 0.7
        
        # БИНАРНЫЕ РЕЗУЛЬТАТЫ
        if prediction == 1:
            risk_level = "high"
            result_text = "ВЫЯВЛЕНА СКЛОННОСТЬ"
            recommendation = "Рекомендуется консультация специалиста"
            icon = "🚨"
            color = "red"
        else:
            risk_level = "low" 
            result_text = "СКЛОННОСТЬ НЕ ВЫЯВЛЕНА"
            recommendation = "Рутинное медицинское наблюдение"
            icon = "✅"
            color = "green"
        
        print(f"🎯 Результат: {'СКЛОНЕН' if prediction == 1 else 'НЕ СКЛОНЕН'} (вероятность: {probability:.1%})")
        
        # Редирект на страницу результата
        redirect_url = (
            f"/result.html?"
            f"risk={risk_level}&"
            f"result={urllib.parse.quote(result_text)}&"
            f"rec={urllib.parse.quote(recommendation)}&"
            f"age={features[0]}&"
            f"gender={'Мужской' if features[1] == 1 else 'Женский'}&"
            f"smoking={'Да' if features[30] == 1 else 'Нет'}&"
            f"icon={urllib.parse.quote(icon)}&"
            f"color={color}&"
            f"prob={probability:.1%}"  # оставляем для отладки
        )
        
        response = f"""HTTP/1.1 303 See Other
Location: {redirect_url}
Connection: close

"""
        return response.encode('utf-8')
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        
        error_html = f"""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>❌ Ошибка</h1><p>{str(e)}</p>
            <a href="/test" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px;">Вернуться к тесту</a>
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
        elif url.startswith('/result.html'):  # ← ВАЖНО: добавили эту строку
            response = handle_result()         # ← И эту
        elif url == '/submit-test' and method == 'POST':
            # Извлекаем POST данные
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
    server_socket.bind(('127.0.0.1', 8080))
    server_socket.listen(5)
    
    print("🚀 Alcohol Screening Server запущен на http://127.0.0.1:8080")
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