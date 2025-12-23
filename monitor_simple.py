import time
from datetime import datetime

# Сайты для мониторинга
SITES = [
    "https://barnhouse1.ru",
    "https://barnhouse1.ru/company",
    "https://barnhouse1.ru/catalog"
]


def check_site(url):
    """Проверяет один сайт"""
    try:
        start = time.time()
        response = requests.get(url, timeout=5)
        end = time.time()

        response_time = round((end - start) * 1000)  # в миллисекундах

        if response.status_code == 200:
            return "✅ UP", response.status_code, response_time
        else:
            return "⚠️  WARN", response.status_code, response_time

    except Exception as e:
        return "❌ DOWN", 0, 0


def main():
    print("=" * 50)
    print("МОНИТОРИНГ BARNHOUSE")
    print("=" * 50)

    check_count = 0

    try:
        while True:
            check_count += 1
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Проверка #{check_count}")
            print("-" * 40)

            for site in SITES:
                status, code, time_ms = check_site(site)
                short_name = site.replace("https://barnhouse1.ru", "")
                if short_name == "":
                    short_name = "/"

                print(f"{status} {short_name:20} код: {code:3} время: {time_ms:4}ms")

            print(f"\nСледующая проверка через 30 секунд...")
            time.sleep(30)  # Ждем 30 секунд

    except KeyboardInterrupt:
        print("\n\nМониторинг остановлен")


if __name__ == "__main__":
    # Сначала установим библиотеку requests
    try:
        import requests
    except ImportError:
        print("Устанавливаю библиотеку requests...")
        import subprocess

        subprocess.check_call(["pip", "install", "requests"])
        import requests

    main()