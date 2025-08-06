import telebot
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import time
from collections import defaultdict
import csv

# Загрузка .env
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
INSTRUCTION_LINK = os.getenv("INSTRUCTION_LINK")
DOWNLOAD_LINK = "https://freedombank.onelink.me/WNLd/h8jtco42"

# Список админов
admin_ids_raw = os.getenv("ADMIN_CHAT_IDS", "")
ADMIN_CHAT_IDS = set(int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit())

bot = telebot.TeleBot(TOKEN)

# Файлы
user_ids_file = "user_ids.txt"
referrals_file = "referrals.txt"
contacts_file = "contacts.txt"
users_file = "users.txt"
bloggers_file = "bloggers.txt"
verified_users_file = "verified_users.txt"
broadcast_state = {}

# Загрузка данных
def load_user_ids():
    try:
        with open(user_ids_file, "r") as f:
            return set(int(line.strip()) for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_user_ids():
    with open(user_ids_file, "w") as f:
        for uid in user_ids:
            f.write(f"{uid}\n")

def load_bloggers():
    try:
        with open(bloggers_file, "r") as f:
            return set(line.strip().lower() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_blogger(username):
    with open(bloggers_file, "a") as f:
        f.write(f"{username.lower()}\n")

def is_verified(cid):
    try:
        with open(verified_users_file, "r") as f:
            return str(cid) in [line.strip() for line in f]
    except FileNotFoundError:
        return False

def add_verified(cid):
    with open(verified_users_file, "a") as f:
        f.write(f"{cid}\n")

user_ids = load_user_ids()
bloggers = load_bloggers()

# Главное меню
def get_main_menu(username, cid):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    if username and username.lower() in bloggers:
        markup.row("📈 Мои старты")
    if cid in ADMIN_CHAT_IDS:
        markup.row("📊 Статистика", "📥 Выгрузка CSV")
        markup.row("📤 Выгрузка пользователей")
        markup.row("✏️ Добавить блогера")
        markup.row("📬 Входящие сообщения")
        markup.row("🚀 Рассылка: Группа")
    return markup

# /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    cid = message.chat.id
    username = message.from_user.username or "без ника"
    args = message.text.split()
    referrer = args[1] if len(args) > 1 else "unknown"

    if not is_verified(cid):
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        button = telebot.types.KeyboardButton("📱 Отправить номер телефона", request_contact=True)
        markup.add(button)
        bot.send_message(cid, "👋 Привет! Пожалуйста, нажмите кнопку ниже, чтобы отправить свой номер телефона для продолжения 👇", reply_markup=markup)
        with open(referrals_file, "a") as f:
            f.write(f"{cid},{referrer},{username}\n")
        with open(users_file, "a") as f:
            f.write(f"{cid},{username}\n")
        return

    bot.send_message(cid, "✅ Вы уже зарегистрированы!", reply_markup=get_main_menu(username, cid))

# Контакт
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    cid = message.chat.id
    phone = message.contact.phone_number
    username = (message.from_user.username or "без ника").lower()

    with open(contacts_file, "a") as f:
        f.write(f"{cid},{phone},{username}\n")
    add_verified(cid)
    user_ids.add(cid)
    save_user_ids()

    for admin_id in ADMIN_CHAT_IDS:
        try:
            bot.send_message(admin_id, f"📞 Контакт от @{username}:\n{phone}")
        except:
            continue

    bot.send_message(cid, "✅ Контакт получен. Спасибо!", reply_markup=get_main_menu(username, cid))
    send_instruction(cid)

# Инструкция (2 СМС)
def send_instruction(cid):
    bot.send_message(cid,
        "Привет! На связи команда Айжан Закировой.\n\n"
        "Скачайте Freedom SuperApp и получите перевод от Айжан + 1000 тенге от FREEDOM 🎉\n\n"
        f"{DOWNLOAD_LINK}\n\n"
        "1. Скачайте приложение по ссылке выше\n"
        "2. Пройдите регистрацию (введите ИИН и номер телефона)\n"
        "3. В поле «Промокод» выберите ZAKIROVA (может не запрашиваться)\n"
        "4. Дождитесь выпуска карты и напишите в бот ФИО + номер телефона или пополните карту на 100₸\n"
        "5. Совершите транзакцию: пополнение телефона или покупка\n"
        "6. Получите кэшбек 1000₸\n"
        "7. Делитесь ссылкой и зарабатывайте по 1000₸ за каждого друга ❤️\n"
        "8. Ссылка на группу WhatsApp: https://chat.whatsapp.com/JZ3IJuFodwmI0jNY6CKKLs?mode=ac_t"
    )

    time.sleep(1)

    bot.send_message(cid,
        "🎁 Заходите в группу, чтобы получать по 1500₸ за каждого друга и участвовать в гонке за Toyota Camry!"
    )

# Рассылка по группе
def send_group_invite_broadcast():
    for uid in user_ids:
        try:
            if uid not in ADMIN_CHAT_IDS:
                bot.send_message(
                    uid,
                    "🔥 Заходите в нашу группу в WhatsApp, чтобы получать по 1500₸ за каждого друга и участвовать в гонке за Toyota Camry!\n\n"
                    "👉 Присоединяйтесь: https://chat.whatsapp.com/JZ3IJuFodwmI0jNY6CKKLs?mode=ac_t"
                )
        except Exception as e:
            print(f"❌ Не удалось отправить {uid}: {e}")

@bot.message_handler(func=lambda msg: msg.text == "🚀 Рассылка: Группа" and msg.chat.id in ADMIN_CHAT_IDS)
def group_broadcast_handler(message):
    bot.send_message(message.chat.id, "📢 Начинаем рассылку приглашения в группу...")
    send_group_invite_broadcast()
    bot.send_message(message.chat.id, "✅ Рассылка завершена.")

# Обработка текста
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    cid = message.chat.id
    text = message.text.strip()
    username = (message.from_user.username or "без ника").lower()

    if not is_verified(cid):
        bot.send_message(cid, "❗ Сначала нажмите кнопку и отправьте номер телефона.")
        return

    if text == "📊 Статистика" and cid in ADMIN_CHAT_IDS:
        stats = defaultdict(int)
        try:
            with open(referrals_file, "r") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) >= 2:
                        stats[parts[1]] += 1
        except FileNotFoundError:
            bot.send_message(cid, "📂 Файл referrals.txt не найден.")
            return

        if not stats:
            bot.send_message(cid, "❗ Пока нет данных по пользователям.")
            return

        msg = "📊 Статистика по блогерам:\n\n"
        for ref, count in sorted(stats.items(), key=lambda x: -x[1]):
            msg += f"🔹 {ref} — {count} чел.\n"
        bot.send_message(cid, msg)
        return

    if text == "📥 Выгрузка CSV" and cid in ADMIN_CHAT_IDS:
        try:
            with open(contacts_file, "r") as infile, open("contacts.csv", "w", newline='') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(["Chat ID", "Контакт", "Username"])
                for line in infile:
                    parts = line.strip().split(",")
                    if len(parts) == 3:
                        writer.writerow(parts)
            with open("contacts.csv", "rb") as doc:
                bot.send_document(cid, doc)
        except Exception as e:
            bot.send_message(cid, f"❗ Ошибка при выгрузке: {e}")
        return

    if text == "📤 Выгрузка пользователей" and cid in ADMIN_CHAT_IDS:
        try:
            with open(users_file, "r") as infile, open("users.csv", "w", newline='') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(["Chat ID", "Username"])
                for line in infile:
                    parts = line.strip().split(",")
                    if len(parts) == 2:
                        writer.writerow(parts)
            with open("users.csv", "rb") as doc:
                bot.send_document(cid, doc)
        except Exception as e:
            bot.send_message(cid, f"❗ Ошибка при выгрузке: {e}")
        return

    if text == "✏️ Добавить блогера" and cid in ADMIN_CHAT_IDS:
        bot.send_message(cid, "✏️ Введите username блогера (без @):")
        broadcast_state[cid] = 'adding_blogger'
        return

    if text == "📬 Входящие сообщения" and cid in ADMIN_CHAT_IDS:
        try:
            with open("inbox.txt", "r") as f:
                lines = f.readlines()[-10:]
            if not lines:
                bot.send_message(cid, "📭 Нет новых сообщений.")
                return
            msg = "📬 Последние входящие:\n\n"
            for line in lines:
                parts = line.strip().split(",", 2)
                if len(parts) == 3:
                    user_id, uname, msg_text = parts
                    msg += f"👤 @{uname} (ID: {user_id}):\n💬 {msg_text}\n\n"
            bot.send_message(cid, msg)
        except FileNotFoundError:
            bot.send_message(cid, "📭 Сообщений пока нет.")
        return

    if broadcast_state.get(cid) == 'adding_blogger':
        save_blogger(text.lower())
        bloggers.add(text.lower())
        bot.send_message(cid, f"✅ Блогер @{text} добавлен.")
        broadcast_state.pop(cid, None)
        return

    # Сохраняем входящие
    if cid not in ADMIN_CHAT_IDS:
        with open("inbox.txt", "a") as f:
            f.write(f"{cid},{username},{text}\n")
        text_safe = text if len(text) < 1000 else text[:1000] + "…"
        for admin_id in ADMIN_CHAT_IDS:
            try:
                bot.send_message(
                    admin_id,
                    f"📩 Новое сообщение от @{username} (ID: {cid}):\n\n💬 {text_safe}"
                )
            except Exception as e:
                print(f"❌ Не удалось отправить админу: {e}")

    bot.send_message(cid, "❗ Неизвестная команда. Если вы уже отправили номер — следуйте инструкции выше.")

# Напоминания
def send_daily_reminders():
    for uid in user_ids:
        try:
            if uid not in ADMIN_CHAT_IDS:
                bot.send_message(uid,
                    f"⏰ Напоминание: не забудьте скачать Freedom SuperApp и пройти регистрацию!\n\nСсылка: {DOWNLOAD_LINK}"
                )
        except Exception as e:
            print(f"❌ Не удалось отправить {uid}: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(
    send_daily_reminders,
    'cron',
    hour=11,
    minute=0,
    timezone=pytz.timezone('Asia/Almaty')
)
scheduler.start()

print("✅ Бот запущен. Ожидаем сообщения...")

if __name__ == "__main__":
    print("🔁 Starting bot polling...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"⚠️ Ошибка polling: {e}")
            time.sleep(5)