import time
import requests
import threading

# ==========================================
#              НАЛАШТУВАННЯ
# ==========================================

# 1. Сюди вставиш свій секретний токен, коли його надішлють
API_TOKEN = "ЗАМІНИ_ЦЕЙ_ТЕКСТ_НА_СВІЙ_ОФІЦІЙНИЙ_ТОКЕН"

# 2. Налаштування Телеграм-бота
BOT_TOKEN = "8875992669:AAGk1vhNSgDxHbhNuWpyLrS_6rgR7i594YA"
CHANNEL_ID = "@e_Trivoga"

# 3. Список локацій, які ми відстежуємо (м. Київ + усі 7 районів Київщини)
TARGET_LOCATIONS = [
    "м. Київ",
    "Білоцерківський район",
    "Бориспільський район",
    "Броварський район",
    "Бучанський район",
    "Вишгородський район",
    "Обухівський район",
    "Фастівський район"
]

# Словник для збереження поточного стану тривог (True - тривога, False - відбій)
alarms_state = {location: False for location in TARGET_LOCATIONS}

minute_of_silence_sent = False


# ==========================================
#              ФУНКЦІЇ БОТА
# ==========================================

def send_tg_message(text):
    """Надсилання повідомлень в Telegram з підтримкою синіх гіперпосилань"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True  # Щоб посилання не створювало велику прев'ю-картинку під постом
        }
        res = requests.post(url, json=payload, timeout=5)
        return res.status_code == 200
    except Exception as e:
        print(f"⚠️ Помилка надсилання в ТГ: {e}")
        return False


def minute_of_silence_worker():
    """Фоновий потік для хвилини мовчання о 09:00"""
    global minute_of_silence_sent
    while True:
        current_time = time.strftime("%H:%M")
        if current_time == "09:00":
            if not minute_of_silence_sent:
                text = (
                    "⏳ **09:00 — Загальнонаціональна хвилина мовчання.**\n\n"
                    "Вшануймо пам'ять усіх співвітчизників, які віддали своє життя за волю та незалежність України... 🇺🇦\n\n"
                    "👉 [Підписатись на канал](https://t.me/e_Trivoga) | [ППО РАДАР](https://t.me/e_Trivoga)"
                )
                if send_tg_message(text):
                    print(f"[{time.strftime('%H:%M:%S')}] 🕊️ Хвилина мовчання надіслана.")
                    minute_of_silence_sent = True
        else:
            minute_of_silence_sent = False
        time.sleep(30)


# ==========================================
#          ОСНОВНИЙ ЦИКЛ МОНІТОРИНГУ
# ==========================================

print("=== СИСТЕМА МОНІТОРИНГУ КИЄВА ТА ОБЛАСТІ ЗАПУЩЕНА ===")
send_tg_message("🤖 **Система моніторингу успішно запущена в тестовому режимі!**\n\n*Очікуємо підключення офіційного API...*")

# Запуск хвилини мовчання у фоні
threading.Thread(target=minute_of_silence_worker, daemon=True).start()

# Заголовки для авторизації на сервері alerts.in.ua
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "User-Agent": "PythonAlertBot/1.0"
}

while True:
    # Якщо токен ще не вставили, не забиваємо консоль помилками запитів
    if "ЗАМІНИ_ЦЕЙ_ТЕКСТ" in API_TOKEN:
        print(f"[{time.strftime('%H:%M:%S')}] Скрипт готовий. Очікуємо токен від alerts.in.ua...")
        time.sleep(10)
        continue

    try:
        # Запит до офіційного ендпоінту активних тривог
        response = requests.get("https://api.alerts.in.ua/v1/alerts/active.json", headers=headers, timeout=6)
        
        if response.status_code == 200:
            data = response.json()
            active_alerts = data.get("alerts", [])
            
            # Тимчасовий словник для зчитування свіжого статусу з сервера
            current_api_state = {location: False for location in TARGET_LOCATIONS}
            
            # Перебираємо всі активні тривоги в Україні
            for alert in active_alerts:
                location_title = alert.get("location_title")
                
                # Якщо локація є в нашому списку (Київ або район області)
                if location_title in current_api_state:
                    current_api_state[location_title] = True

            # Порівнюємо старий стан із новим та надсилаємо сповіщення
            for location in TARGET_LOCATIONS:
                is_now_active = current_api_state[location]
                was_active_before = alarms_state[location]
                
                # 1. Почалася НОВА тривога
                if is_now_active and not was_active_before:
                    text = (
                        f"🔴 **УВАГА! Повітряна тривога в: {location}!**\n"
                        "Пройдіть в найближче укриття! 🛑\n\n"
                        "👉 [Підписатись на канал](https://t.me/e_Trivoga) | [ППО РАДАР](https://t.me/e_Trivoga)"
                    )
                    send_tg_message(text)
                    print(f"🔔 [ТРИВОГА] -> {location}")
                    alarms_state[location] = True
                
                # 2. Звіт про ВІДБІЙ тривоги
                elif not is_now_active and was_active_before:
                    text = (
                        f"🟢 **ВІДБІЙ повітряної тривоги: {location}!**\n"
                        "Загроза в цій локації минула. 🕊️\n\n"
                        "👉 [Підписатись на канал](https://t.me/e_Trivoga) | [ППО РАДАР](https://t.me/e_Trivoga)"
                    )
                    send_tg_message(text)
                    print(f"🔕 [ВІДБІЙ] -> {location}")
                    alarms_state[location] = False
                    
            print(f"[{time.strftime('%H:%M:%S')}] Моніторинг району... Статус Київської області стабільний.")
            
        elif response.status_code == 401:
            print("❌ Помилка авторизації! Перевір правильність введеного API_TOKEN.")
            time.sleep(30)
        else:
            print(f"⚠️ Сервер повернув код: {response.status_code}")

    except Exception as e:
        print(f"⚠️ Помилка мережі або обробки даних: {e}")
        
    # Офіційне API дозволено опитувати раз на 12-15 секунд
    time.sleep(12)
