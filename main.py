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

# Загрузка chat_id пользователей
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

# Главное меню
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ Я скачал приложение")
    markup.add("📊 Статистика", "🔍 Мои старты")
    return markup

# Старт с отслеживанием реферала
@bot.message_handler(commands=['start'])
def send_welcome(message):
    cid = message.chat.id
    args = message.text.split()
    referrer = args[1] if len(args) > 1 else "unknown"
    username = message.from_user.username or str(cid)

    with open(referrals_file, "a") as f:
        f.write(f"{cid},{referrer},{username}\n")

    if cid != ADMIN_CHAT_ID:
        user_ids.add(cid)
        save_user_ids()

    bot.send_message(
        cid,
        "👋 Добро пожаловать!\n\n"
        "1. Скачайте Freedom Superapp по ссылке👇\n\n"
        f"{DOWNLOAD_LINK}\n\n"
        "2. Пройдите регистрацию и укажите промокод *ZAKIROVA* (если потребуется).\n"
        "3. После активации карты:\n"
        "   • пополните баланс телефона\n"
        "   • или оплатите покупку\n\n"
        "💸 Получите кэшбек 1000 ₸!\n"
        "🎁 Делитесь ссылкой и получайте ещё по 1000 ₸ за каждого друга!",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# Обработка обычных сообщений
@bot.message_handler(func=lambda msg: True)
def handle_response(message):
    cid = message.chat.id
    text = message.text.strip().lower()
    username = message.from_user.username or "без ника"

    if cid != ADMIN_CHAT_ID:
        user_ids.add(cid)
        save_user_ids()

    if text in ["я скачал", "я скачала", "✅ я скачал приложение"]:
        bot.send_message(cid, f"📲 Отлично! Вот ссылка на канал с инструкцией: {INSTRUCTION_LINK}")
        return

    if text == "📊 статистика" and cid == ADMIN_CHAT_ID:
        show_stats(message)
        return

    if text == "🔍 мои старты":
        show_my_starts(message)
        return

    admin_msg = f"📥 Новое сообщение от @{username}\n🆔 ID: {cid}\n💬: {message.text}"
    bot.send_message(ADMIN_CHAT_ID, admin_msg)

    bot.send_message(cid, "✅ Спасибо! Мы получили ваши данные.")

# Общая статистика по рефералам (для админа)
def show_stats(message):
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

# Стартовавшие по ссылке конкретного пользователя
def show_my_starts(message):
    cid = message.chat.id
    username = message.from_user.username or str(cid)
    my_ref = username

    referred_users = []
    try:
        with open(referrals_file, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 3 and parts[1] == my_ref:
                    referred_users.append(parts[2])
    except FileNotFoundError:
        bot.send_message(cid, "📂 Файл с рефералами пока не создан.")
        return

    if not referred_users:
        bot.send_message(cid, "❗ Пока никто не переходил по вашей ссылке.")
        return

    msg = f"🔍 *Ваши переходы:* {len(referred_users)} чел.\n\n"
    msg += "\n".join([f"• {u}" for u in referred_users])

    bot.send_message(cid, msg, parse_mode="Markdown")

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
