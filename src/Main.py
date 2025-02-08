import logging
import requests
import asyncio
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

TELEGRAM_BOT_TOKEN = "7920831452:AAFcF8yfsAwVzTDw5V1nLQYeVPjJ90X9sZs"
GOOGLE_AI_API_KEY = "AIzaSyCNNru0ExmeXJeeMLm8NRrg0dS6qGgpl04"
GOOGLE_AI_API_KEY_GUESS = "AIzaSyDhW_bCxFRXRtf03zIEF0CNmw0rCRqzcQE"

CHOOSING, FIX_TEXT, FEEDBACK = range(3)
GUESS_DIFFICULTY, GUESS_ANSWER, GUESS_FEEDBACK = 3, 4, 5


FALLBACK_LETTER = (
    "Тема: Заказ\n\n"
    "Привет,\n"
    "Я пишу к вам потому что мой заказ пришёл не так как я ожидал. "
    "Это было очень разочаровывающе. Вы должны делать лучше.\n\n"
    "Пока,\n"
    "Клиент"
)

# ===================== Общее меню и переходы =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("Угадай что сказать", callback_data='guess'),
         InlineKeyboardButton("Исправь текст", callback_data='fix_text')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(
            "Выберите игру:\n\n"
            "Исправь текст – редактирование неудачно составленных писем\n"
            "Угадай что сказать – тренировка правильных формулировок ответов в деловой среде",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.edit_message_text(
            text="Выберите игру:\n\n"
                 "Исправь текст – редактирование неудачно составленных писем\n"
                 "Угадай что сказать – тренировка правильных формулировок ответов в деловой среде",
            reply_markup=reply_markup
        )
    return CHOOSING

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "fix_text":
        bad_letter = await asyncio.to_thread(generate_bad_letter)
        if not bad_letter or "Ошибка" in bad_letter:
            bad_letter = FALLBACK_LETTER
        context.user_data["bad_letter"] = bad_letter
        keyboard = [
            [InlineKeyboardButton("Главная", callback_data="back"),
             InlineKeyboardButton("Другое письмо", callback_data="new_letter")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="Игра 'Исправь текст'. Отредактируйте следующее письмо:\n\n" + bad_letter,
            reply_markup=reply_markup
        )
        return FIX_TEXT
    elif query.data == "guess":
        return await guess_game_start(update, context)
    else:
        await query.edit_message_text(text="Неизвестная игра.")
        return ConversationHandler.END

# ===================== Функционал игры "Исправь текст" =====================

async def fix_text_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "back":
        return await start(update, context)
    elif query.data == "new_letter":
        bad_letter = await asyncio.to_thread(generate_bad_letter)
        if not bad_letter or "Ошибка" in bad_letter:
            bad_letter = FALLBACK_LETTER
        context.user_data["bad_letter"] = bad_letter
        keyboard = [
            [InlineKeyboardButton("Главная", callback_data="back"),
             InlineKeyboardButton("Другое письмо", callback_data="new_letter")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="Игра 'Исправь текст'. Отредактируйте следующее письмо:\n\n" + bad_letter,
            reply_markup=reply_markup
        )
        return FIX_TEXT

async def fix_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text
    original_text = context.user_data.get("bad_letter", FALLBACK_LETTER)
    context.user_data["corrected_letter"] = user_text
    feedback = await asyncio.to_thread(get_feedback, original_text, user_text)
    response_message = (
        "Ваш вариант письма:\n\n"
        f"{user_text}\n\n"
        "Советы по улучшению:\n\n"
        f"{feedback}"
    )
    keyboard = [
        [InlineKeyboardButton("Еще раз", callback_data="try_again"),
         InlineKeyboardButton("Другое письмо", callback_data="new_letter"),
         InlineKeyboardButton("Главная", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(response_message, reply_markup=reply_markup)
    return FEEDBACK

async def feedback_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "try_again":
        bad_letter = context.user_data.get("bad_letter", FALLBACK_LETTER)
        keyboard = [
            [InlineKeyboardButton("Главная", callback_data="back"),
             InlineKeyboardButton("Другое письмо", callback_data="new_letter")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="Пожалуйста, попробуйте исправить этот вариант письма ещё раз:\n\n" + bad_letter,
            reply_markup=reply_markup
        )
        return FIX_TEXT
    elif query.data == "new_letter":
        bad_letter = await asyncio.to_thread(generate_bad_letter)
        if not bad_letter or "Ошибка" in bad_letter:
            bad_letter = FALLBACK_LETTER
        context.user_data["bad_letter"] = bad_letter
        keyboard = [
            [InlineKeyboardButton("Главная", callback_data="back"),
             InlineKeyboardButton("Другое письмо", callback_data="new_letter")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="Игра 'Исправь текст'. Отредактируйте следующее письмо:\n\n" + bad_letter,
            reply_markup=reply_markup
        )
        return FIX_TEXT
    elif query.data == "back":
        return await start(update, context)

# ===================== Функционал игры "Угадай, что сказать" =====================

async def guess_game_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Легкий", callback_data="guess_easy"),
         InlineKeyboardButton("Сложный", callback_data="guess_hard")],
        [InlineKeyboardButton("Главная", callback_data="guess_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Выбери уровень сложности:",
        reply_markup=reply_markup
    )
    return GUESS_DIFFICULTY


async def guess_difficulty_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает выбор уровня сложности в игре "Угадай, что сказать" и генерирует ситуацию с вариантами ответа.
    Также, если нажата кнопка "Главная", возвращает пользователя в главное меню.
    """
    query = update.callback_query
    await query.answer()
    #
    if query.data == "guess_back":
        return await start(update, context)

    difficulty = "легкий" if query.data == "guess_easy" else "сложный"
    guess_data = await asyncio.to_thread(generate_guess_situation, difficulty)
    if not guess_data:
        guess_data = {
            "situation": "Клиент недоволен задержкой проекта и требует срочной встречи.",
            "options": [
                "Извинитесь и пообещайте ускорить работу.",
                "Скажите, что задержка не ваша вина.",
                "Обещайте компенсацию без встречи.",
                "Предложите обсудить ситуацию на встрече."
            ],
            "correct_option": 1,
            "explanation": "Вариант 1 демонстрирует ответственность и готовность решать проблему."
        }
    guess_data["difficulty"] = difficulty
    context.user_data["guess_data"] = guess_data

    situation = guess_data.get("situation", "Ситуация не сгенерирована.")
    options = guess_data.get("options", ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"])
    options_text = "\n".join(f"{i}) {option}" for i, option in enumerate(options, start=1))
    message_text = f"Ситуация:\n\n{situation}\n\nВыберите один из вариантов ответа:\n{options_text}"

    keyboard_buttons = [
        InlineKeyboardButton(f"Вариант {i}", callback_data=f"guess_option_{i}")
        for i in range(1, len(options) + 1)
    ]
    keyboard = [keyboard_buttons]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=message_text,
        reply_markup=reply_markup
    )
    return GUESS_ANSWER


async def guess_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_option = int(query.data.split("_")[-1])
    guess_data = context.user_data.get("guess_data", {})
    correct_option = guess_data.get("correct_option", 1)
    explanation = guess_data.get("explanation", "Нет объяснения.")
    if selected_option == correct_option:
        result_text = "Правильно! "
    else:
        result_text = f"Неправильно! Правильный вариант: вариант {correct_option}. "
    result_text += explanation
    keyboard = [
        [InlineKeyboardButton("Попробовать еще", callback_data="guess_try_again"),
         InlineKeyboardButton("Главная", callback_data="guess_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=result_text,
        reply_markup=reply_markup
    )
    return GUESS_FEEDBACK

async def guess_feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "guess_try_again":
        guess_data = context.user_data.get("guess_data", {})
        difficulty = guess_data.get("difficulty", "легкий")
        new_guess_data = await asyncio.to_thread(generate_guess_situation, difficulty)
        if not new_guess_data:
            new_guess_data = guess_data
        context.user_data["guess_data"] = new_guess_data
        options = new_guess_data.get("options", ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"])
        keyboard_buttons = [InlineKeyboardButton(option, callback_data=f"guess_option_{i}")
                            for i, option in enumerate(options, start=1)]
        keyboard = [keyboard_buttons]
        reply_markup = InlineKeyboardMarkup(keyboard)
        situation = new_guess_data.get("situation", "Ситуация не сгенерирована.")
        await query.edit_message_text(
            text=f"Ситуация:\n\n{situation}\n\nВыберите один из вариантов ответа:",
            reply_markup=reply_markup
        )
        return GUESS_ANSWER
    elif query.data == "guess_back":
        return await start(update, context)

# ===================== Синхронные функции генерации через Google AI Studio =====================

def generate_bad_letter() -> str:
    prompt = (
        "Сгенерируй плохой пример делового письма, где тема может быть разнообразной: "
        "например, жалоба, заказ, договоры, работа, запрос информации, приглашение на встречу, отчёт о мероприятии или любой другой деловой вопрос. "
        "Письмо должно быть составлено небрежно, с ошибками, неструктурированно и не соответствовать стандартам деловой переписки, но не настолько ужасно. "
        "Избегай использования грубой лексики (например, не использовать слова 'говно', 'дерьмо' и подобные выражения). "
        "Каждый раз генерируй уникальный вариант, чтобы письма не повторялись. "
        "Ограничь текст до 70 слов.Письмо должно быть написано на русском языке"
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_AI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        print("Google AI (generate_bad_letter) response:", json.dumps(result, ensure_ascii=False, indent=2))
        if "candidates" in result and isinstance(result["candidates"], list) and result["candidates"]:
            candidate = result["candidates"][0]
            if ("content" in candidate and "parts" in candidate["content"] and
                isinstance(candidate["content"]["parts"], list) and candidate["content"]["parts"]):
                generated_text = candidate["content"]["parts"][0].get("text", "").strip()
                return generated_text if generated_text else "Нет ответа от Google AI."
            else:
                return "Неверный формат ответа от Google AI (generate_bad_letter): " + json.dumps(result, ensure_ascii=False)
        else:
            return "Неверный формат ответа от Google AI (generate_bad_letter): " + json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return "Ошибка при запросе к Google AI (generate_bad_letter): " + str(e)

def get_feedback(original: str, corrected: str) -> str:
    prompt = (
        "Ты — эксперт по деловой переписке. Проанализируй два варианта письма.\n\n"
        "Оригинальное письмо (с ошибками):\n" + original + "\n\n"
        "Исправленный вариант, предложенный пользователем:\n" + corrected + "\n\n"
        "Дай рекомендации по улучшению делового стиля: что можно ещё исправить, какие формулировки использовать, "
        "чтобы письмо выглядело профессиональнее."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_AI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        print("Google AI (get_feedback) response:", json.dumps(result, ensure_ascii=False, indent=2))
        if "candidates" in result and isinstance(result["candidates"], list) and result["candidates"]:
            candidate = result["candidates"][0]
            if ("content" in candidate and "parts" in candidate["content"] and
                isinstance(candidate["content"]["parts"], list) and candidate["content"]["parts"]):
                generated_text = candidate["content"]["parts"][0].get("text", "").strip()
                return generated_text if generated_text else "Нет ответа от Google AI."
            else:
                return "Неверный формат ответа от Google AI (get_feedback): " + json.dumps(result, ensure_ascii=False)
        else:
            return "Неверный формат ответа от Google AI (get_feedback): " + json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return "Ошибка при запросе к Google AI (get_feedback): " + str(e)

def generate_guess_situation(difficulty: str) -> dict:
    prompt = (
        f"Сгенерируй разнообразную ситуацию из деловой среды для игры 'Угадай, что сказать'. "
        f"Уровень сложности: {difficulty}.Если уровень сложности сложный , то сделай его ситуацию и варианты ответа запутанными и сложным "
        "В данной ситуации опиши конкретную деловую ситуацию, которая может включать разные роли"
        "специалист по обслуживанию клиентов, руководитель проекта, HR-менеджер, IT-специалист, бухгалтер,директор,бизнесмен,журналист,комик,диктор или другой сотрудник. "
        "Ситуация должна требовать дать ответ на конкретный деловой вопрос, например: запрос встречи, ответ на претензию клиента, "
        "отказ партнёру, уточнение деталей проекта, или предложение по оптимизации процессов. "
        "Верни результат строго в формате JSON, где ключи и строковые значения заключены в двойные кавычки. "
        "Структура должна быть такой: "
        '{"situation": "<описание ситуации>", "options": ["<вариант 1>", "<вариант 2>", "<вариант 3>", "<вариант 4>"], '
        '"correct_option": <номер правильного варианта (число)>, "explanation": "<краткое объяснение>"}'
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_AI_API_KEY_GUESS}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        print("Google AI (generate_guess_situation) response:", json.dumps(result, ensure_ascii=False, indent=2))
        if "candidates" in result and isinstance(result["candidates"], list) and result["candidates"]:
            candidate = result["candidates"][0]
            if ("content" in candidate and "parts" in candidate["content"] and
                isinstance(candidate["content"]["parts"], list) and candidate["content"]["parts"]):
                generated_text = candidate["content"]["parts"][0].get("text", "").strip()
                print("Raw generated text:", generated_text)
                # Удаляем code fences, если они присутствуют
                if generated_text.startswith("```"):
                    lines = generated_text.splitlines()
                    # Если первая строка содержит что-то вроде "```json", удаляем её
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    # Если последняя строка содержит "```", удаляем её
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    generated_text = "\n".join(lines).strip()
                    print("Cleaned generated text:", generated_text)
                try:
                    data = json.loads(generated_text)
                    return data
                except Exception as e:
                    print("Ошибка при разборе JSON:", str(e))
                    return {}
            else:
                print("Неверный формат ответа от Google AI:", json.dumps(result, ensure_ascii=False))
                return {}
        else:
            print("Нет кандидатов в ответе от Google AI:", json.dumps(result, ensure_ascii=False))
            return {}
    except Exception as e:
        print("Ошибка при запросе к Google AI (generate_guess_situation):", str(e))
        return {}



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Игра отменена.")
    return ConversationHandler.END

def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [CallbackQueryHandler(button_handler)],
            FIX_TEXT: [
                CallbackQueryHandler(fix_text_buttons_handler, pattern="^(back|new_letter)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, fix_text_handler)
            ],
            FEEDBACK: [CallbackQueryHandler(feedback_buttons_handler, pattern="^(try_again|new_letter|back)$")],
            GUESS_DIFFICULTY: [CallbackQueryHandler(guess_difficulty_handler, pattern="^(guess_easy|guess_hard|guess_back)$")],
            GUESS_ANSWER: [CallbackQueryHandler(guess_answer_handler, pattern="^guess_option_[1-4]$")],
            GUESS_FEEDBACK: [CallbackQueryHandler(guess_feedback_handler, pattern="^(guess_try_again|guess_back)$")]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(conv_handler)
    logging.info("Бот запущен.")
    application.run_polling()

if __name__ == '__main__':
    main()
