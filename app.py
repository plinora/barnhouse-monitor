import os
from flask import Flask, render_template, jsonify, request
import sqlite3
from datetime import datetime, timedelta
import threading
import time
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-123')


# Конфигурация
class Config:
    SITES = [
        {'name': 'Главная', 'url': 'https://barnhouse1.ru', 'interval': 300},
        {'name': 'О компании', 'url': 'https://barnhouse1.ru/company', 'interval': 300},
        {'name': 'Каталог', 'url': 'https://barnhouse1.ru/catalog', 'interval': 300},
        {'name': 'Контакты', 'url': 'https://barnhouse1.ru/contacts', 'interval': 300},
        {'name': 'Доставка', 'url': 'https://barnhouse1.ru/delivery', 'interval': 300},
    ]
    TIMEOUT = 10


# База данных
def get_db():
    conn = sqlite3.connect('monitoring.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name TEXT,
            url TEXT,
            status TEXT,
            status_code INTEGER,
            response_time INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name TEXT,
            message TEXT,
            level TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


# Маршруты
@app.route('/')
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    # Последние 20 проверок
    cursor.execute('SELECT * FROM checks ORDER BY timestamp DESC LIMIT 20')
    checks = cursor.fetchall()

    # Статистика за 24 часа
    stats = {}
    for site in Config.SITES:
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status_code = 200 THEN 1 ELSE 0 END) as success,
                AVG(response_time) as avg_time
            FROM checks 
            WHERE site_name = ? AND timestamp > datetime('now', '-1 day')
        ''', (site['name'],))
        result = cursor.fetchone()
        stats[site['name']] = result

    conn.close()

    return render_template('dashboard.html',
                           checks=checks,
                           stats=stats,
                           sites=Config.SITES,
                           current_time=datetime.now().strftime("%H:%M:%S"),
                           current_date=datetime.now().strftime("%d.%m.%Y"))


@app.route('/api/check-now', methods=['POST'])
def check_now():
    """API для ручной проверки"""
    site_url = request.json.get('url')

    try:
        start = time.time()
        response = requests.get(site_url, timeout=10)
        end = time.time()

        response_time = round((end - start) * 1000)
        status = 'UP' if response.status_code == 200 else 'DOWN'

        # Сохраняем в БД
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO checks (site_name, url, status, status_code, response_time)
            VALUES (?, ?, ?, ?, ?)
        ''', ('Ручная проверка', site_url, status, response.status_code, response_time))
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'status': status,
            'code': response.status_code,
            'response_time': response_time
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats')
def get_stats():
    """API для получения статистики"""
    conn = get_db()
    cursor = conn.cursor()

    # Статистика за последние 7 дней
    cursor.execute('''
        SELECT 
            site_name,
            DATE(timestamp) as date,
            COUNT(*) as total,
            SUM(CASE WHEN status_code = 200 THEN 1 ELSE 0 END) as success
        FROM checks 
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY site_name, DATE(timestamp)
        ORDER BY date DESC
    ''')

    stats = cursor.fetchall()
    conn.close()

    return jsonify([dict(row) for row in stats])


# Фоновая задача для мониторинга
def monitor_task():
    """Фоновая задача проверки сайтов"""
    while True:
        for site in Config.SITES:
            try:
                start = time.time()
                response = requests.get(site['url'], timeout=Config.TIMEOUT)
                end = time.time()

                response_time = round((end - start) * 1000)
                status = 'UP' if response.status_code == 200 else 'DOWN'

                # Сохраняем в БД
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO checks (site_name, url, status, status_code, response_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (site['name'], site['url'], status, response.status_code, response_time))
                conn.commit()
                conn.close()

                # Логируем
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {site['name']}: {status} ({response_time}ms)")

            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {site['name']}: ERROR - {str(e)}")

        # Ждем 5 минут до следующей проверки
        time.sleep(300)


if __name__ == '__main__':
    # Инициализируем БД
    init_db()

    # Запускаем фоновый мониторинг в отдельном потоке
    monitor_thread = threading.Thread(target=monitor_task, daemon=True)
    monitor_thread.start()

    print("=" * 50)
    print("🚀 Barnhouse Мониторинг запущен!")
    print(f"👉 Доступно по адресу: http://127.0.0.1:5000")
    print(f"👉 Мониторинг {len(Config.SITES)} сайтов")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=False)