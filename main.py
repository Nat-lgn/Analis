import asyncio
import logging
import os
import datetime
import hashlib
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from parser import parse_report
from database import init_db, save_report, get_analytics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StatFlow(StatesGroup):
    waiting_for_period = State()


load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Моя статистика")],
        [KeyboardButton(text="ℹ️ Як користуватись")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Надішли мені звіт із гри..."
)


category_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🏹 Лови", callback_data="cat_Лови"),
     InlineKeyboardButton(text="🏕 Походи", callback_data="cat_Походи")],
    [InlineKeyboardButton(text="📜 Справи", callback_data="cat_Справи"),
     InlineKeyboardButton(text="👹 Бос", callback_data="cat_Бос")],
    [InlineKeyboardButton(text="⛰ Катакомби", callback_data="cat_Катакомби"),
     InlineKeyboardButton(text="🛡 Стояння", callback_data="cat_Стояння")],
    [InlineKeyboardButton(text="🌍 ВСІ КАТЕГОРІЇ", callback_data="cat_all")]
])

# Клавиатура Шаг 2 (Периоды)
period_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Сьогодні", callback_data="period_today"),
     InlineKeyboardButton(text="Ічора", callback_data="period_yesterday")],
    [InlineKeyboardButton(text="За тиждень", callback_data="period_week"),
     InlineKeyboardButton(text="За місяць", callback_data="period_month")],
    [InlineKeyboardButton(text="Весь час", callback_data="period_all")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_categories")]
])

# ==========================================
# 4. БАЗОВЫЕ ОБРАБОТЧИКИ СООБЩЕНИЙ
# ==========================================
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        "Привіт! Я твій особистий трекер для гри @Zapaleni_bot.\n\n"
        "Просто пересилай мені повідомлення про фарму, і я все підрахую. "
        "Твоя статистика повністю приватна."
    )
    await message.reply(welcome_text, reply_markup=main_menu)

@dp.message(Command("stat"))
@dp.message(F.text == "📊 Моя статистика")
async def stat_command_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.reply("📊 Крок 1: Виберіть категорію для аналізу:", reply_markup=category_kb)

@dp.message(F.text == "ℹ️ Як користуватись")
async def help_handler(message: types.Message, state: FSMContext):
    await state.clear()
    instructions = (
        "📝 *Інструкція:*\n"
        "1. Зайди в гру.\n"
        "2. Виділили повідомлення з успішним фармом (де є досвід та золото).\n"
        "3. Натисни «Переслати» і відправ його мені.\n"
        "4. Я зафіксую дані та захищу їх від дублювання."
    )
    await message.reply(instructions, parse_mode="Markdown")


@dp.message(F.text | F.caption)
async def forward_handler(message: types.Message, state: FSMContext):
    await state.clear()
    try:
        raw_text = message.text or message.caption

        report = parse_report(raw_text)
        if report:
            orig_date = message.forward_origin.date if message.forward_origin else message.date
            raw_string = f"{message.from_user.id}_{orig_date.timestamp()}_{raw_text}"
            report_hash = hashlib.md5(raw_string.encode()).hexdigest()

            formatted_date = orig_date.strftime("%Y-%m-%d %H:%M:%S")

            is_saved = await save_report(
                message.from_user.id, report.activity, report.gold, report.exp,
                report.nebesna, report.svaroja, report.fragment,
                report.armor_scroll, report.weapon_scroll,
                report_hash, formatted_date
            )

            if is_saved:
                reply_text = f"✅ Записано!\nАктивність: {report.activity}\n+{report.gold} 💰 | +{report.exp} ⭐️"

                materials = []
                if report.nebesna > 0: materials.append(f"⭐ Небесна: {report.nebesna}")
                if report.svaroja > 0: materials.append(f"🪨 Сварожа: {report.svaroja}")
                if report.fragment > 0: materials.append(f"🧩 Фрагмент: {report.fragment}")
                if report.armor_scroll > 0: materials.append(f"🛡 Сувій обладунку: {report.armor_scroll}")
                if report.weapon_scroll > 0: materials.append(f"🗡 Сувій зброї: {report.weapon_scroll}")

                if materials:
                    reply_text += f"\n📦 Здобуто: {', '.join(materials)}"

                logger.info(
                    f"Распарсено: {report.activity} | +{report.gold}💰 | +{report.exp}⭐️ | Матеріали: {materials}")
                await message.reply(reply_text)
            else:
                logger.info("Виявлено дублікат. Запис відхилено.")
                await message.reply("⚠️ Цей звіт уже було записано раніше. Дублікат проігноровано.")
        else:
            logger.debug("Сообщение проигнорировано (не подошло под регулярные выражения).")

    except Exception as e:
        logger.error(f"Сбой при обработке сообщения: {e}", exc_info=True)
# ==========================================
# 5. ОБРАБОТЧИКИ СТАТИСТИКИ
# ==========================================

@dp.callback_query(F.data == "back_to_categories")
async def back_to_categories_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("📊 Шаг 1: Обери категорію:", reply_markup=category_kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("cat_"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    activity = callback.data.split("_")[1]

    await state.update_data(activity=activity)
    await state.set_state(StatFlow.waiting_for_period)

    cat_name = "ВСІ КАТЕГОРІЇ" if activity == "all" else activity
    await callback.message.edit_text(
        f"📂 Обрана категорія: **{cat_name}**\n\n📅 Шаг 2: Обери період:",
        reply_markup=period_kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("period_"), StatFlow.waiting_for_period)
async def process_period_selection(callback: CallbackQuery, state: FSMContext):
    period = callback.data.split("_")[1]

    data = await state.get_data()
    activity = data['activity']

    stats = await get_analytics(callback.from_user.id, activity, period)
    await state.clear()

    period_names = {
        "today": "Сьогодні", "yesterday": "Вчора",
        "week": "Тиждень", "month": "Місяць", "all": "Весь час"
    }
    cat_name = "ВСІ КАТЕГОРІЇ" if activity == "all" else activity

    if not stats:
        text = f"📭 В тебе нема записів по категорії **{cat_name}** за період: *{period_names.get(period)}*."
        await callback.message.edit_text(text, parse_mode="Markdown")
        await callback.answer()
        return

    # Формирование отчета
    final_text = f"📊 Аналітика: **{cat_name}** ({period_names.get(period)})\n\n"
    total_gold = 0
    total_exp = 0

    for act_name, values in stats.items():
        final_text += f"🔹 **{act_name}**\n"
        final_text += f"   💰 Золото: {values['gold']}\n"
        final_text += f"   ⭐️ Досвід: {values['exp']}\n"

        # Динамический вывод материалов (только если они выпадали)
        materials = []
        if values['nebesna'] > 0: materials.append(f"⭐ Небесна: {values['nebesna']}")
        if values['svaroja'] > 0: materials.append(f"🪨 Сварожа: {values['svaroja']}")
        if values['fragment'] > 0: materials.append(f"🧩 Фрагмент: {values['fragment']}")
        if values['armor_scroll'] > 0: materials.append(f"🛡 Сувій обладунку: {values['armor_scroll']}")
        if values['weapon_scroll'] > 0: materials.append(f"🗡 Сувій зброї: {values['weapon_scroll']}")

        if materials:
            final_text += f"   📦 Матеріали: {', '.join(materials)}\n"
        final_text += "\n"

    if activity == "all" and len(stats) > 1:
        final_text += f"📈 **РАЗОМ:**\n💰 {total_gold} | ⭐️ {total_exp}"

    # Даем возможность выбрать другой период, не возвращаясь в самое начало
    await callback.message.edit_text(final_text, reply_markup=period_kb, parse_mode="Markdown")
    # Чтобы интерфейс не ломался, если юзер передумает, возвращаем состояние (но это опционально)
    await state.set_state(StatFlow.waiting_for_period)
    await state.update_data(activity=activity)

    await callback.answer()

# ==========================================
# 6. ЗАПУСК ПРИЛОЖЕНИЯ
# ==========================================
async def main():
    logger.info("Инициализация публичного бота...")
    await init_db()
    logger.info("Бот запущен. Ожидание пересланных сообщений.")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Работа бота завершена пользователем.")