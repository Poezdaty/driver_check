import requests
from bs4 import BeautifulSoup
import time
import os

# Конфігурація Telegram
TELEGRAM_TOKEN = "5986383596:AAGp8KTjXzZRG1ZSiq-dM2d01Ust8pVzVrQ"
TELEGRAM_CHAT_ID = "313479637"

# Файли
INPUT_FILE = "driver_data.txt"  # Файл з вхідними даними
PROCESSED_FILE = "processed.txt"  # Файл для збереження оброблених даних

def send_telegram_message(message):
    """Відправляє повідомлення в Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Помилка відправки повідомлення в Telegram: {e}")

def check_driver_license(seria, number, birthday, csrf_token):
    """
    Перевіряє посвідчення водія на сайті, повертає результат.

    Args:
        seria (str): Серія посвідчення.
        number (str): Номер посвідчення.
        birthday (str): Дата народження у форматі YYYY-MM-DD.
        csrf_token (str): Токен для POST запиту.

    Returns:
        tuple: (bool, str) - (успішна перевірка, повідомлення).
    """
    url = "https://opendata.hsc.gov.ua/check-driver-license/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    data = {
        'seria': seria,
        'number': number,
        'birthday_system': birthday,
        'csrfmiddlewaretoken': csrf_token
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()  # Перевірка на HTTP помилки
        soup = BeautifulSoup(response.content, 'html.parser')

        if "Результат перевірки посвідчення водія" in str(soup):
            return True, "Перевірку пройдено!"
        elif "ІНФОРМАЦІЮ НЕ ЗНАЙДЕНО" in str(soup):
            return False, "Інформацію не знайдено!"
        else:
            return False, "Неочікувана відповідь сайту!"

    except requests.exceptions.RequestException as e:
        return False, f"Помилка запиту: {e}"


def get_csrf_token():
    """Отримує csrf token зі сторінки"""
    url = "https://opendata.hsc.gov.ua/check-driver-license/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
        return csrf_token
    except requests.exceptions.RequestException as e:
         print(f"Помилка отримання CSRF token: {e}")
         return None
    except Exception as e:
        print(f"Невідома помилка отримання CSRF token: {e}")
        return None


def load_processed_data():
    """Завантажує вже оброблені дані з файлу."""
    if not os.path.exists(PROCESSED_FILE):
        return set()  # Повертаємо порожню множину, якщо файл не існує

    with open(PROCESSED_FILE, 'r', encoding='utf-8') as file:
        return set(line.strip() for line in file)


def save_processed_data(seria, number):
    """Зберігає оброблені дані у файл."""
    with open(PROCESSED_FILE, 'a', encoding='utf-8') as file:
        file.write(f"{seria},{number}\n")


def main():
    # Завантажуємо вже оброблені дані
    processed_data = load_processed_data()

    while True:  # Нескінченний цикл для періодичної перевірки
        # Отримуємо csrf токен
        csrf_token = get_csrf_token()

        if not csrf_token:
            print("Не вдалося отримати CSRF токен, перевірка неможлива.")
            time.sleep(3600)  # Затримка на 1 годину перед наступною спробою
            continue

        print(f"CSRF token: {csrf_token}")

        # Читаємо дані з файлу
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line:  # Ігноруємо пусті рядки
                        parts = line.split(',')
                        if len(parts) == 4:
                            surname, seria, number, birthday = [part.strip() for part in parts]

                            # Перевіряємо, чи вже обробляли ці дані
                            if f"{seria},{number}" in processed_data:
                                print(f"Пропускаємо вже оброблені дані: {surname} ({seria}, {number})")
                                continue

                            print(f"Перевіряємо {surname}...")

                            success, message = check_driver_license(seria, number, birthday, csrf_token)

                            if success:
                                print(f"{surname} - {message}")
                                # Відправляємо повідомлення в Telegram
                                telegram_message = f"✅ Посвідчення дійсне!\nПрізвище: {surname}\nСерія: {seria}\nНомер: {number}"
                                send_telegram_message(telegram_message)
                                # Зберігаємо оброблені дані
                                save_processed_data(seria, number)
                                processed_data.add(f"{seria},{number}")  # Додаємо до множини
                            else:
                                print(f"{surname} - {message}")
                            time.sleep(2)  # Затримка 2 секунди між запитами
                        else:
                            print(f"Неправильний формат рядка: {line}. Потрібно: Прізвище,Серія,Номер,Дата")
        except FileNotFoundError:
            print("Файл driver_data.txt не знайдено.")
        except Exception as e:
            print(f"Помилка при обробці файлу: {e}")

        # Затримка на 1 годину перед наступною перевіркою
        print("Очікування наступної перевірки через 1 годину...")
        time.sleep(3600)


if __name__ == "__main__":
    main()