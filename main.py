import telebot
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import time
from collections import defaultdict
import csv
import threading

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
INSTRUCTION_LINK = os.getenv("INSTRUCTION_LINK")
DOWNLOAD_LINK = "https://freedombank.onelink.me/WNLd/h8jtco42"

bot = telebot.TeleBot(TOKEN)
user_ids_file = "user_ids.txt"
referrals_file = "referrals.txt"
contacts_file = "contacts.txt"
bloggers_file = "bloggers.txt"
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

user_ids = load_user_ids()
bloggers = load_bloggers()

# Кнопки
def get_main_menu(username, cid):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    if username and username.lower() in bloggers:
        markup.row("📈 Мои старты")
    if cid == ADMIN_CHAT_ID:
        markup.row("📊 Статистика", "📥 Выгрузка CSV")
        markup.row("✏️ Добавить блогера")
    return markup

# /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    cid = message.chat.id
    args = message.text.split()
    referrer = args[1] if len(args) > 1 else "unknown"
    username = message.from_user.username or "без ника"

    with open(referrals_file, "a") as f:
        f.write(f"{cid},{referrer},{username}\n")

    if cid != ADMIN_CHAT_ID:
        user_ids.add(cid)
        save_user_ids()
        bot.send_message(
            ADMIN_CHAT_ID,
            f"👤 Новый пользователь:\n\n🆔 Chat ID: {cid}\n🔗 Реферал: {referrer}\n👤 Username: @{username}"
        )

    markup = get_main_menu(username, cid)

    # Первое сообщение
    bot.send_message(cid, 
        "Привет! На связи команда Айжан Закировой. Ниже будет ссылка на приложение Банка FREEDOM, "
        "выполнив все условия вы сможете сразу получить перевод на карту от Айжан, и 1000 тенге от FREEDOM\n"
        "Плюс получите инструкцию «три метода как заработать на FREEDOM\n\n"
        f"{DOWNLOAD_LINK}"
    )

    # Второе сообщение через 60 сек
    def send_second():
        bot.send_message(
            cid,
            "1. Скачайте Freedom Superapp по ссылке👇\n\n"
            f"{DOWNLOAD_LINK}\n\n"
            "2. Пройдите регистрацию (введите ИИН и номер телефона).\n\n"
            "3. В поле «Промокод» выберите ZAKIROVA (большими буквами. Промокод могут и не запрашивать)\n\n"
            "4. Дождитесь оформления карты SuperCard и напишите в бот фио и номер телефона чтоб мы вам закинули денег на активацию. "
            "(Или сами закиньте себе на карту 100 тенге)\n\n"
            "5. После получения 100 тенге Совершите любую транзакцию - рекомендуем:\n"
            "• пополнить баланс телефона (операции - платежи - мобильная связь)\n"
            "• либо совершить любую покупку в магазине, оплатив ее картой SuperCard.\n\n"
            "6. Получите свой первый кэшбек 1000 тенге 🎉\n\n"
            "7. Далее можете делиться своей ссылкой и зарабатывать по 1000 тенге за каждое скачивание ❤️\n\n"
            "8. Ниже будет телеграмм канал с информацией как дальше зарабатывать на Фридом кроме рассылки ссылок"
        )

    def ask_name():
        bot.send_message(cid, "👋 Напишите, пожалуйста, свою фамилию и номер телефона.", reply_markup=markup)

    threading.Timer(60, send_second).start()
    threading.Timer(90, ask_name).start()

# Обработка текста
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    cid = message.chat.id
    text = message.text.strip()
    username = (message.from_user.username or "без ника").lower()

    if cid != ADMIN_CHAT_ID:
        user_ids.add(cid)
        save_user_ids()

    if text.startswith("+7") or any(char.isdigit() for char in text):
        with open(contacts_file, "a") as f:
            f.write(f"{cid},{text}\n")
        bot.send_message(cid, "✅ Контакт получен. Спасибо!")
        bot.send_message(ADMIN_CHAT_ID, f"📞 Контакт от @{username}:\n{text}")
        return

    if text == "📊 Статистика" and cid == ADMIN_CHAT_ID:
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

        msg = "📊 *Статистика по блогерам:*\n\n"
        for ref, count in sorted(stats.items(), key=lambda x: -x[1]):
            msg += f"🔹 {ref} — {count} чел.\n"
        bot.send_message(cid, msg, parse_mode="Markdown")
        return

    if text == "📈 Мои старты":
        starts = []
        try:
            with open(referrals_file, "r") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) >= 3 and parts[1].lower() == username:
                        starts.append(parts[2])
        except FileNotFoundError:
            bot.send_message(cid, "📂 Файл referrals.txt не найден.")
            return

        if not starts:
            bot.send_message(cid, "😕 Пока никто не пришел по вашей ссылке.")
        else:
            msg = "📥 Люди, пришедшие по вашей ссылке:\n\n"
            for user in starts:
                msg += f"🔹 @{user}\n"
            bot.send_message(cid, msg)
        return

    if text == "📥 Выгрузка CSV" and cid == ADMIN_CHAT_ID:
        try:
            with open(contacts_file, "r") as infile, open("contacts.csv", "w", newline='') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(["Chat ID", "Контакт"])
                for line in infile:
                    writer.writerow(line.strip().split(","))
            with open("contacts.csv", "rb") as doc:
                bot.send_document(cid, doc)
        except Exception as e:
            bot.send_message(cid, f"❗ Ошибка при выгрузке: {e}")
        return

    if text == "✏️ Добавить блогера" and cid == ADMIN_CHAT_ID:
        bot.send_message(cid, "✏️ Введите username блогера (без @):")
        broadcast_state[cid] = 'adding_blogger'
        return

    if broadcast_state.get(cid) == 'adding_blogger':
        save_blogger(text.lower())
        bloggers.add(text.lower())
        bot.send_message(cid, f"✅ Блогер @{text} добавлен.")
        broadcast_state.pop(cid, None)
        return

    bot.send_message(cid, "❗ Неизвестная команда. Напишите номер телефона или фамилию.")

# Планировщик

def send_daily_reminders():
    for uid in user_ids:
        try:
            if uid != ADMIN_CHAT_ID:
                bot.send_message(uid,
                    f"⏰ Напоминание: не забудьте скачать *Freedom SuperApp* и пройти регистрацию!\n\nСсылка: {DOWNLOAD_LINK}",
                    parse_mode="Markdown"
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

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"❗ Ошибка polling: {e}")
        time.sleep(10)
