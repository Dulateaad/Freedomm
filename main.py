import telebot
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import time
from collections import defaultdict

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
INSTRUCTION_LINK = os.getenv("INSTRUCTION_LINK")
DOWNLOAD_LINK = "https://freedombank.onelink.me/WNLd/h8jtco42"

bot = telebot.TeleBot(TOKEN)
user_ids_file = "user_ids.txt"
referrals_file = "referrals.txt"
broadcast_state = {}

# Загружаем chat_id пользователей
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

user_ids = load_user_ids()

# Старт + отслеживание реферала
@bot.message_handler(commands=['start'])
def send_welcome(message):
    cid = message.chat.id
    args = message.text.split()
    referrer = args[1] if len(args) > 1 else "unknown"
    username = message.from_user.username or "без ника"

    # записываем реферала
    with open(referrals_file, "a") as f:
        f.write(f"{cid},{referrer},{username}\n")

    if cid != ADMIN_CHAT_ID:
        user_ids.add(cid)
        save_user_ids()

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ Я скачал приложение")

    bot.send_message(
        cid,
        "1. Скачайте Freedom Superapp по ссылке👇\n\n"
        f"{DOWNLOAD_LINK}\n\n"
        "2. Пройдите регистрацию (введите ИИН и номер телефона).\n\n"
        "3. В поле «Промокод» выберите ZAKIROVA (большими буквами. Промокод могут и не запрашивать).\n\n"
        "4. Дождитесь оформления карты SuperCard и напишите в бот ФИО и номер телефона чтоб мы вам закинули денег на активацию. (Или сами закиньте себе на карту 100 тенге)\n\n"
        "5. После получения 100 тенге совершите любую транзакцию:\n"
        "• пополните баланс телефона (операции - платежи - мобильная связь)\n"
        "• либо оплатите покупку картой\n\n"
        "6. Получите свой первый кэшбек 1000 ₸ 🎉\n\n"
        "7. Делитесь своей ссылкой и зарабатывайте по 1000 ₸ за каждое скачивание ❤️\n\n"
        "8. Ниже будет телеграм-канал с инфой, как зарабатывать дальше.",
        reply_markup=markup
    )

# Узнать свой chat ID
@bot.message_handler(commands=['myid'])
def get_my_id(message):
    bot.reply_to(message, f"Ваш chat ID: `{message.chat.id}`", parse_mode='Markdown')

# Команда рассылки
@bot.message_handler(commands=['рассылка'])
def start_broadcast(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    bot.send_message(message.chat.id, "📝 Введите текст рассылки:")
    broadcast_state[message.chat.id] = 'waiting_for_message'

# Обработка текста рассылки
@bot.message_handler(func=lambda message: broadcast_state.get(message.chat.id) == 'waiting_for_message')
def handle_broadcast_text(message):
    text = message.text
    bot.send_message(ADMIN_CHAT_ID, f"📨 Начинаю рассылку:\n\n{text}")

    success = 0
    fail = 0
    for uid in user_ids:
        try:
            if uid != ADMIN_CHAT_ID:
                bot.send_message(uid, f"📢 Новость от команды Freedom:\n\n{text}")
                success += 1
        except Exception as e:
            fail += 1
            print(f"❌ Ошибка при отправке {uid}: {e}")

    bot.send_message(ADMIN_CHAT_ID, f"✅ Рассылка завершена.\nУспешно: {success}, ошибок: {fail}")
    broadcast_state.pop(message.chat.id)

# Команда статистики
@bot.message_handler(commands=['статистика'])
def show_stats(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return

    stats = defaultdict(int)
    try:
        with open(referrals_file, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    stats[parts[1]] += 1
    except FileNotFoundError:
        bot.send_message(message.chat.id, "📂 Файл referrals.txt не найден.")
        return

    if not stats:
        bot.send_message(message.chat.id, "❗ Пока нет данных по пользователям.")
        return

    msg = "📊 *Статистика по блогерам:*\n\n"
    for ref, count in sorted(stats.items(), key=lambda x: -x[1]):
        msg += f"🔹 {ref} — {count} чел.\n"

    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# Обработка обычных сообщений
@bot.message_handler(func=lambda msg: True)
def handle_response(message):
    cid = message.chat.id
    text = message.text.strip()
    username = message.from_user.username or "без ника"

    if cid != ADMIN_CHAT_ID:
        user_ids.add(cid)
        save_user_ids()

    if text.lower() in ["я скачал", "я скачала", "✅ я скачал приложение"]:
        bot.send_message(cid, f"📲 Отлично! Вот ссылка на Telegram-канал с инструкцией: {INSTRUCTION_LINK}")
        return

    admin_msg = f"📥 Новое сообщение от @{username}\n🆔 ID: {cid}\n💬: {text}"
    bot.send_message(ADMIN_CHAT_ID, admin_msg)

    bot.send_message(cid, "✅ Спасибо! Мы получили ваши данные.")

    if "скачал" in text.lower() or "скачала" in text.lower():
        bot.send_message(cid, f"📲 Вот ссылка на Telegram-канал с инструкцией: {INSTRUCTION_LINK}")
    else:
        bot.send_message(
            cid,
            f"🔔 Пожалуйста, скачайте приложение *Freedom SuperApp*, чтобы мы могли отправить вам перевод.\n\nСсылка: {DOWNLOAD_LINK}",
            parse_mode="Markdown"
        )

# Планировщик напоминаний
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

# Основной цикл
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"❗ Ошибка polling: {e}")
        time.sleep(10)
