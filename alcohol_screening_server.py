import html
import mimetypes
import os
import socket
import threading
import traceback
import urllib.parse

import joblib
import lightgbm
import numpy as np
import pandas as pd
import sklearn

from preprocessing import FEATURE_COLUMNS, RISK_COLS, TRAIT_COLS, encode_traits

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 10000))
MODEL_PATH = os.environ.get('MODEL_PATH', 'model.joblib')
BASE_DIR = os.path.abspath('.')          # корень для статики
MAX_REQUEST_BYTES = 64 * 1024


# ----------------------------
# Загрузка модели
# ----------------------------
def load_artifact():
    """Артефакт из ноутбука: пайплайн (препроцессинг + LightGBM + калибровка),
    список признаков, пороги и доли группы риска по зонам."""
    if not os.path.exists(MODEL_PATH):
        # Без модели сервис не должен отдавать выдуманные результаты
        raise SystemExit(f"Файл модели {MODEL_PATH} не найден")

    artifact = joblib.load(MODEL_PATH)

    if list(artifact['feature_columns']) != list(FEATURE_COLUMNS):
        raise SystemExit("Признаки модели не совпадают с preprocessing.FEATURE_COLUMNS — "
                         "переобучите модель или обновите preprocessing.py")

    runtime = {'scikit-learn': sklearn.__version__, 'lightgbm': lightgbm.__version__,
               'numpy': np.__version__, 'pandas': pd.__version__}
    for lib, version in runtime.items():
        trained = artifact['versions'].get(lib)
        if trained != version:
            print(f"ВНИМАНИЕ: {lib} при обучении {trained}, на сервере {version}", flush=True)

    print(f"Модель загружена: {artifact['config']['model']}, "
          f"калибровка {artifact['config']['calibration']}", flush=True)
    return artifact


ARTIFACT = load_artifact()
PIPELINE = ARTIFACT['pipeline']
CONFIG = ARTIFACT['config']


# ----------------------------
# Валидация формы
# ----------------------------
REQUIRED_COLS = [c for c in FEATURE_COLUMNS if c not in RISK_COLS]
RANGES = {
    'age': (18, 100),
    'gender': (0, 1),               # 1 = М, 0 = Ж
    'education_level': (1, 6),      # коды bb_diplom
    'self_rated_health': (1, 5),    # коды bbm3
    'is_smoker': (0, 1),
    'drives': (0, 1),
    **{c: (1, 4) for c in TRAIT_COLS},   # коды RLMS: 1 = «почти всегда»
    **{c: (0, 10) for c in RISK_COLS},
}
NA_VALUES = {'', 'na'}              # «затрудняюсь ответить»


class FormError(ValueError):
    pass


def parse_features(params):
    row = {}
    for col in FEATURE_COLUMNS:
        raw = params.get(col, [''])[0].strip().lower()
        if raw in NA_VALUES:
            if col in RISK_COLS:
                row[col] = np.nan
                continue
            raise FormError(f"Не заполнено поле «{col}»")
        try:
            value = float(raw)
        except ValueError:
            raise FormError(f"Некорректное значение поля «{col}»")
        lo, hi = RANGES[col]
        if not lo <= value <= hi:
            raise FormError(f"Значение поля «{col}» должно быть от {lo} до {hi}")
        row[col] = value

    # Тем, кто не водит, вопрос о риске за рулём не задавался (как в RLMS)
    if row['drives'] == 0:
        row['driving_risk'] = 0.0

    return encode_traits(pd.DataFrame([row], columns=FEATURE_COLUMNS))


# ----------------------------
# Интерпретация вероятности
# ----------------------------
BAND_UI = {
    'low': {
        'result': 'РИСК НИЖЕ СРЕДНЕГО',
        'rec': 'Особых мер не требуется.',
        'icon': '✅', 'color': 'green',
    },
    'medium': {
        'result': 'РИСК НА УРОВНЕ СРЕДНЕГО',
        'rec': 'Стоит внимательнее отнестись к своим привычкам. '
               'Для более точной оценки можно пройти стандартизированный тест AUDIT.',
        'icon': '⚠️', 'color': 'orange',
    },
    'high': {
        'result': 'РИСК ВЫШЕ СРЕДНЕГО',
        'rec': 'Рекомендуется пройти тест AUDIT и при необходимости обсудить результат со специалистом.',
        'icon': '🚨', 'color': 'red',
    },
}


def risk_band(p):
    if p >= CONFIG['threshold_high']:
        return 'high'
    if p >= CONFIG['threshold_screen']:
        return 'medium'
    return 'low'


def context_text(band):
    rate = CONFIG['band_rates'][band]
    base = CONFIG['base_rate']
    return (f"Среди людей с похожими ответами к группе риска относятся около {rate:.0%} "
            f"(в среднем по выборке — {base:.0%}). Это скрининг, а не диагноз.")


# ----------------------------
# HTTP-утилиты
# ----------------------------
mimetypes.init()
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('image/svg+xml', '.svg')
mimetypes.add_type('font/woff2', '.woff2')

STATUS_TEXT = {200: 'OK', 303: 'See Other', 400: 'Bad Request', 403: 'Forbidden',
               404: 'Not Found', 413: 'Payload Too Large', 500: 'Internal Server Error'}


def load_template(name):
    path = os.path.join('templates', name)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return f"<h1>Template {html.escape(name)} missing</h1>"


def build_response(body_bytes, status=200, content_type='text/html; charset=utf-8', extra_headers=None):
    headers = [
        f"HTTP/1.1 {status} {STATUS_TEXT.get(status, 'OK')}",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close",
    ]
    if extra_headers:
        headers.extend(extra_headers)
    return "\r\n".join(headers).encode('utf-8') + b"\r\n\r\n" + body_bytes


def error_page(message, status):
    body = f"<h1>{html.escape(message)}</h1><p><a href='/test'>Вернуться к анкете</a></p>"
    return build_response(body.encode('utf-8'), status)


def serve_static(path):
    full_path = os.path.abspath(os.path.normpath(path.lstrip('/')))
    if os.path.commonpath([full_path, BASE_DIR]) != BASE_DIR:   # защита от path traversal
        return build_response(b"Forbidden", 403, 'text/plain; charset=utf-8')
    if not os.path.isfile(full_path):
        return build_response(b"<h1>404 Not Found</h1>", 404)
    mime_type = mimetypes.guess_type(full_path)[0] or 'application/octet-stream'
    with open(full_path, 'rb') as f:
        return build_response(f.read(), 200, mime_type)


def read_request(sock):
    """Читает заголовки целиком, затем тело ровно по Content-Length."""
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if len(data) > MAX_REQUEST_BYTES:
            raise OverflowError
    head, _, body = data.partition(b"\r\n\r\n")
    head_text = head.decode('latin-1')

    content_length = 0
    for line in head_text.split("\r\n")[1:]:
        key, _, value = line.partition(':')
        if key.strip().lower() == 'content-length':
            content_length = int(value.strip())
    if content_length > MAX_REQUEST_BYTES:
        raise OverflowError

    while len(body) < content_length:
        chunk = sock.recv(4096)
        if not chunk:
            break
        body += chunk
    return head_text, body[:content_length]


# ----------------------------
# Роуты
# ----------------------------
def handle_index():
    return build_response(load_template("index.html").encode('utf-8'))


def handle_test():
    return build_response(load_template("test.html").encode('utf-8'))


def handle_result(query=""):
    page = load_template("result.html")
    for key, value in urllib.parse.parse_qsl(query):
        page = page.replace(f"{{{{{key}}}}}", html.escape(value))   # защита от XSS
    return build_response(page.encode('utf-8'))


def handle_submit_test(post_body):
    try:
        params = urllib.parse.parse_qs(post_body.decode('utf-8'), keep_blank_values=True)
        X = parse_features(params)
    except FormError as e:
        return error_page(str(e), 400)
    except UnicodeDecodeError:
        return error_page("Некорректная кодировка запроса", 400)

    try:
        probability = float(PIPELINE.predict_proba(X)[0, 1])
    except Exception:
        traceback.print_exc()
        return error_page("Внутренняя ошибка сервера", 500)

    band = risk_band(probability)
    ui = BAND_UI[band]
    raw = X.iloc[0]
    query = urllib.parse.urlencode({
        'risk': band,
        'result': ui['result'],
        'rec': ui['rec'],
        'context': context_text(band),
        'age': int(raw['age']),
        'gender': 'Мужской' if raw['gender'] == 1 else 'Женский',
        'smoking': 'Да' if raw['is_smoker'] == 1 else 'Нет',
        'icon': ui['icon'],
        'color': ui['color'],
        'prob': f"{probability:.0%}",
    })
    return build_response(b"", 303, extra_headers=[f"Location: /result.html?{query}"])


STATIC_EXT = ('.css', '.js', '.png', '.jpg', '.jpeg', '.svg', '.ico', '.woff2', '.woff', '.ttf')


def handle_client(client_socket):
    try:
        client_socket.settimeout(5)
        try:
            head, body = read_request(client_socket)
        except OverflowError:
            client_socket.sendall(error_page("Слишком большой запрос", 413))
            return
        if not head:
            return

        method, full_url = head.split("\r\n", 1)[0].split()[:2]
        path, _, query = full_url.partition('?')
        print(f"{method} {path}", flush=True)

        if path.startswith("/static/") or os.path.splitext(path)[1].lower() in STATIC_EXT:
            response = serve_static(path)
        elif path == '/':
            response = handle_index()
        elif path == '/test':
            response = handle_test()
        elif path.startswith('/result'):
            response = handle_result(query)
        elif path == '/submit-test' and method == 'POST':
            response = handle_submit_test(body)
        else:
            response = build_response(b"<h1>404 Not Found</h1>", 404)

        client_socket.sendall(response)
    except Exception as e:
        print(f"Ошибка клиента: {e}", flush=True)
    finally:
        client_socket.close()


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(20)
    print(f"Сервер запущен на http://{HOST}:{PORT}", flush=True)
    while True:
        client_socket, _ = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()


if __name__ == "__main__":
    main()
