import requests
import time
from datetime import datetime

# === Конфигурация ===
BOT_TOKEN = "8120902367:AAHQaLf2_UcEYvNpqxD6bfxppg-BTP89TSk"
URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
DEVELOPER_CHAT_ID = "1256326847"  # Ваш ID
OFFSET = 0  # Для отслеживания обновлений

# === Хранилище данных ===
messages = {}  # Словарь для хранения сообщений (ID пользователя -> список сообщений)
current_user_reply = {}  # Текущий пользователь для ответа

# === Основные функции ===
def get_updates():
    """Получение новых сообщений от Telegram."""
    global OFFSET
    response = requests.get(f"{URL}/getUpdates", params={"offset": OFFSET + 1, "timeout": 10})
    result = response.json()

    if result.get("ok"):
        updates = result.get("result", [])
        if updates:
            OFFSET = updates[-1]["update_id"]  # Сдвигаем offset
        return updates
    else:
        print(f"[Ошибка] Не удалось получить обновления: {result}")
        return []

def send_message(chat_id, text, reply_markup=None):
    """Отправка текстового сообщения пользователю."""
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    response = requests.post(f"{URL}/sendMessage", json=data)
    result = response.json()

    if not result.get("ok"):
        print(f"[Ошибка] Не удалось отправить сообщение {chat_id}: {result}")
    else:
        print(f"[Успешно] Сообщение отправлено {chat_id}: {text}")

def forward_media(chat_id, media_type, file_id):
    """Пересылка мультимедиа (голосовые, фото, документы)."""
    url_map = {
        "voice": "sendVoice",
        "photo": "sendPhoto",
        "document": "sendDocument",
        "video": "sendVideo"
    }
    if media_type in url_map:
        response = requests.post(f"{URL}/{url_map[media_type]}", json={"chat_id": chat_id, media_type: file_id})
        if response.status_code == 200:
            print(f"[Успешно] {media_type.capitalize()} отправлен пользователю {chat_id}")
        else:
            print(f"[Ошибка] Не удалось отправить {media_type}: {response.json()}")

def save_message(chat_id, content, sender="Пользователь"):
    """Сохраняет текстовые и мультимедиа сообщения."""
    if chat_id not in messages:
        messages[chat_id] = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages[chat_id].append({"content": content, "timestamp": timestamp, "sender": sender})
    print(f"[DEBUG] Сообщение сохранено: {messages}")

# === Инлайн-кнопки ===
def generate_user_buttons():
    """Генерирует кнопки для пользователей."""
    inline_keyboard = []
    for user_id in messages.keys():
        inline_keyboard.append([{"text": f"Ответить {user_id}", "callback_data": f"reply_{user_id}"}])
        inline_keyboard.append([{"text": f"История {user_id}", "callback_data": f"history_{user_id}"}])
    return {"inline_keyboard": inline_keyboard}

# === Обработка сообщений ===
def handle_updates(updates):
    """Обрабатывает полученные сообщения."""
    global current_user_reply

    for update in updates:
        if "message" in update:
            message = update["message"]
            chat_id = message.get("chat", {}).get("id")

            # Обработка текста
            if "text" in message:
                text = message["text"]
                if chat_id != int(DEVELOPER_CHAT_ID):
                    save_message(chat_id, text, sender="Пользователь")
                    send_message(DEVELOPER_CHAT_ID, f"Сообщение от пользователя {chat_id}: {text}", reply_markup=generate_user_buttons())
                elif chat_id == int(DEVELOPER_CHAT_ID) and chat_id in current_user_reply:
                    target_user = current_user_reply[chat_id]
                    send_message(target_user, text)
                    save_message(target_user, text, sender="Разработчик")
                    del current_user_reply[chat_id]

            # Обработка мультимедиа (голосовые, фото, документы)
            elif "voice" in message or "photo" in message or "document" in message:
                handle_media(message, chat_id)

        elif "callback_query" in update:
            handle_callback_query(update["callback_query"])

def handle_media(message, chat_id):
    """Обрабатывает голосовые, фото и документы."""
    if "voice" in message:
        voice = message["voice"]
        file_id = voice["file_id"]
        if chat_id != int(DEVELOPER_CHAT_ID):
            save_message(chat_id, "[Голосовое сообщение]", sender="Пользователь")
            forward_media(DEVELOPER_CHAT_ID, "voice", file_id)
        else:
            if chat_id in current_user_reply:
                target_user = current_user_reply[chat_id]
                forward_media(target_user, "voice", file_id)
                save_message(target_user, "[Голосовое сообщение отправлено]", sender="Разработчик")
                del current_user_reply[chat_id]

    elif "photo" in message:
        photo = message["photo"][-1]  # Максимальный размер
        file_id = photo["file_id"]
        if chat_id != int(DEVELOPER_CHAT_ID):
            save_message(chat_id, "[Фото]", sender="Пользователь")
            forward_media(DEVELOPER_CHAT_ID, "photo", file_id)
        else:
            if chat_id in current_user_reply:
                target_user = current_user_reply[chat_id]
                forward_media(target_user, "photo", file_id)
                save_message(target_user, "[Фото отправлено]", sender="Разработчик")
                del current_user_reply[chat_id]

    elif "document" in message:
        document = message["document"]
        file_id = document["file_id"]
        if chat_id != int(DEVELOPER_CHAT_ID):
            save_message(chat_id, "[Документ]", sender="Пользователь")
            forward_media(DEVELOPER_CHAT_ID, "document", file_id)
        else:
            if chat_id in current_user_reply:
                target_user = current_user_reply[chat_id]
                forward_media(target_user, "document", file_id)
                save_message(target_user, "[Документ отправлен]", sender="Разработчик")
                del current_user_reply[chat_id]

def handle_callback_query(callback_query):
    """Обрабатывает нажатия на Inline-кнопки."""
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]
    data = callback_query["data"]

    if data.startswith("reply_"):
        user_id = int(data.split("_")[1])
        current_user_reply[chat_id] = user_id
        send_message(chat_id, f"Введите сообщение для пользователя {user_id}:")
    elif data.startswith("history_"):
        user_id = int(data.split("_")[1])
        if user_id in messages:
            history = "\n".join(
                [f"[{msg['timestamp']}] {msg['sender']}: {msg['content']}" for msg in messages[user_id]]
            )
            send_message(chat_id, f"История сообщений с {user_id}:\n{history}")
        else:
            send_message(chat_id, f"Нет истории сообщений с пользователем {user_id}.")

# === Основной цикл ===
def main():
    print("Бот запущен...")
    while True:
        updates = get_updates()
        if updates:
            handle_updates(updates)
        time.sleep(2)

if __name__ == "__main__":
    main()