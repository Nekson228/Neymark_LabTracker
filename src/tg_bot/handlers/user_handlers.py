import io
import csv
from datetime import timedelta, datetime

from PIL import Image

from aiogram import Router, types, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext


from src.tg_bot.services.analysis_service import AnalysisService
from src.tg_bot.models.analysis_models import AnalysesQuery

router = Router()

# Состояния FSM для процесса выбора периода
class AnalysisPeriod(StatesGroup):
    choosing_start = State()
    entering_start_date = State()
    choosing_end = State()
    entering_end_date = State()

class ScanState(StatesGroup):
    waiting_for_photo = State()

class PromptState(StatesGroup):
    waiting_for_prompt = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="/scan"), types.KeyboardButton(text="/analyse")],
            [types.KeyboardButton(text="/ask")],
            [types.KeyboardButton(text="/history")]
        ],
        resize_keyboard=True
    )
    await message.answer("Welcome! Use /scan, /analyse, /history or /ask commands.", reply_markup=keyboard)

@router.message(Command("ask"))
async def cmd_ask_start(message: types.Message, state: FSMContext):
    await state.clear() # Сбрасываем предыдущее состояние на всякий случай
    await message.answer(
        "Задайте ваш вопрос к истории анализов. Например: 'какой у меня был последний гемоглобин?' или 'покажи динамику холестерина'.\n\nДля отмены введите /cancel."
    )
    # Переводим бота в состояние ожидания вопроса
    await state.set_state(PromptState.waiting_for_prompt)

@router.message(StateFilter(PromptState.waiting_for_prompt), F.text)
async def process_user_prompt(message: types.Message, state: FSMContext):
    # Сначала проверяем, не хочет ли пользователь отменить действие
    if message.text.lower() in ['/cancel', 'отмена']:
        await message.reply("Действие отменено.")
        await state.clear()
        await cmd_start(message)
        return

    # Отправляем уведомление о том, что запрос обрабатывается
    processing_message = await message.reply("🧠 Анализирую ваш запрос и историю... Пожалуйста, подождите.")

    try:
        user_id = message.from_user.id
        user_prompt = message.text

        # Вызываем ваш метод из AnalysisService
        # ВАЖНО: т.к. pandas и GPT могут работать долго, в реальном приложении
        # этот вызов стоит обернуть в asyncio.to_thread, чтобы не блокировать бота.
        result = AnalysisService.analyse_by_prompt(user_id=user_id, user_prompt=user_prompt)

        # Отправляем результат пользователю
        await processing_message.edit_text(result.summary)

    except Exception as e:
        await processing_message.edit_text(f"Произошла ошибка при анализе вашего запроса: {e}")
    finally:
        # Вне зависимости от результата, выходим из состояния
        await state.clear()
    
@router.message(StateFilter(PromptState.waiting_for_prompt))
async def incorrect_prompt_input(message: types.Message):
    await message.reply("Я ожидаю текстовый вопрос. Пожалуйста, отправьте ваш запрос текстом или отмените действие командой /cancel.")

@router.message(Command("scan"))
async def cmd_scan_start(message: types.Message, state: FSMContext):
    await state.clear() # На случай, если пользователь был в другом состоянии
    await message.answer("Пожалуйста, отправьте фото вашего анализа.\nДля отмены введите /cancel.")
    # Устанавливаем состояние ожидания фото
    await state.set_state(ScanState.waiting_for_photo)

@router.message(StateFilter(ScanState.waiting_for_photo), F.photo)
async def cmd_scan(message: types.Message, bot: Bot, state: FSMContext):
    if not message.photo:
        await message.reply("Пожалуйста, отправьте фото вашего анализа.")
        return
    
    processing_message = await message.reply("🔬 Анализирую изображение... Это может занять некоторое время.")

    try:
        file_id = message.photo[-1].file_id
        file_info = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file_info.file_path)

        image_stream = io.BytesIO(downloaded_file.read())
        image = Image.open(image_stream)

        recognized_csv_text = AnalysisService.run_ocr_on_image(image)
        print(recognized_csv_text)

        if not recognized_csv_text:
            await processing_message.edit_text("Не удалось распознать данные на изображении. Попробуйте фото лучшего качества.")
            return

        user_id = message.from_user.id

        # Parse the recognized CSV safely
        reader = csv.reader(io.StringIO(recognized_csv_text))
        rows = list(reader)

        if not rows:
            await processing_message.edit_text("Ошибка: CSV пуст.")
            return

        data_rows = [[user_id] + row for row in rows if len(row) > 0]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(data_rows)
        updated_csv_text = output.getvalue()

        AnalysisService.save_scan_to_csv(updated_csv_text)

        await processing_message.edit_text(
            "✅ Данные успешно распознаны и сохранены в вашу историю."
        )

    except Exception as e:
        await processing_message.edit_text(
            f"Произошла ошибка при обработке файла: <code>{e}</code>", parse_mode="HTML"
        )
    finally:
        await state.clear()

@router.message(StateFilter(ScanState.waiting_for_photo), F.text)
async def process_scan_cancel(message: types.Message, state: FSMContext):
    if message.text.lower() in ['/cancel', 'отмена']:
        await message.reply("Действие отменено.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        await cmd_start(message) # Возвращаем главное меню
    else:
        await message.reply("Я ожидаю фото. Пожалуйста, отправьте изображение или отмените действие командой /cancel.")


@router.message(Command("analyse"))
async def cmd_analyse(message: types.Message):
    # Уведомляем пользователя, что процесс запущен
    processing_message = await message.reply("🧠 Составляю общую картину по вашей истории... Пожалуйста, подождите.")
    
    # Этот вызов теперь работает с распознанным текстом из всех сканов!
    result = AnalysisService.analyse_history(user_id=message.from_user.id)
    
    # Редактируем сообщение с финальным результатом
    await processing_message.edit_text(f"**Сводка по анализам:**\n\n{result.summary}")

@router.message(Command("history"))
async def cmd_history(message: types.Message):
    # Example: user can send "/history 7" to get last 7 days
    try:
        days = int(message.text.split()[1])
    except (IndexError, ValueError):
        days = None # all

    history = AnalysisService.get_history(message.from_user.id, days)
    if history.empty:
        await message.reply(f"Нет анализов за последние {days} дней" if days is not None else "Вы не отправляли ваши анализы") 
        return
    answer = []
    for _, row in history.iterrows():
        analysis_card = (
            f"📅 *Дата:* `{row.get('date', 'N/A').strftime('%Y-%m-%d')}`\n"
            f"🔬 *Анализ:* {row.get('analysis', 'N/A')}\n"
            f"📈 *Результат:* `{row.get('result', 'N/A')}`\n"
            f"🩺 *Статус:* {row.get('status', 'N/A')}\n" +
            "─" * 20 + "\n"
        )
        answer.append(analysis_card)
    await message.reply(''.join(answer))

# Обработчик кнопки "посмотреть результаты анализов за период"
@router.message(F.text == "посмотреть результаты анализов за период")
async def view_analysis_period(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="ввести начало периода")],
            [types.KeyboardButton(text="с самого раннего результата")],
            [types.KeyboardButton(text="назад")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите вариант для начала периода:", reply_markup=keyboard)
    await state.set_state(AnalysisPeriod.choosing_start)

# Обработчик выбора начала периода
@router.message(AnalysisPeriod.choosing_start, F.text.in_(["ввести начало периода", "с самого раннего результата"]))
async def process_start_period(message: types.Message, state: FSMContext):
    if message.text == "ввести начало периода":
        await message.answer("Введите начало периода в формате YYYY-MM-DD")
        await state.set_state(AnalysisPeriod.entering_start_date)
    else:
        # Сохраняем минимальную дату из CSV как начало периода
        await state.update_data(start_date=None)  # None будет означать "с самой ранней даты"
        
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="ввести конец периода")],
                [types.KeyboardButton(text="до самого позднего результата")],
                [types.KeyboardButton(text="назад")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выберите вариант для конца периода:", reply_markup=keyboard)
        await state.set_state(AnalysisPeriod.choosing_end)

# Обработчик ввода даты начала периода
@router.message(AnalysisPeriod.entering_start_date)
async def process_start_date(message: types.Message, state: FSMContext):
    if message.text == "назад":
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="ввести начало периода")],
                [types.KeyboardButton(text="с самого раннего результата")],
                [types.KeyboardButton(text="назад")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выберите вариант для начала периода:", reply_markup=keyboard)
        await state.set_state(AnalysisPeriod.choosing_start)
        return
    
    try:
        start_date = datetime.strptime(message.text, '%Y-%m-%d').date()
        await state.update_data(start_date=start_date)
        
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="ввести конец периода")],
                [types.KeyboardButton(text="до самого позднего результата")],
                [types.KeyboardButton(text="назад")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выберите вариант для конца периода:", reply_markup=keyboard)
        await state.set_state(AnalysisPeriod.choosing_end)
    except ValueError:
        await message.answer("Неверный формат даты. Введите дату в формате YYYY-MM-DD")

# Обработчик выбора конца периода
@router.message(AnalysisPeriod.choosing_end, F.text.in_(["ввести конец периода", "до самого позднего результата"]))
async def process_end_period(message: types.Message, state: FSMContext):
    if message.text == "ввести конец периода":
        await message.answer("Введите конец периода в формате YYYY-MM-DD")
        await state.set_state(AnalysisPeriod.entering_end_date)
    else:
        # Получаем данные о начале периода
        data = await state.get_data()
        start_date = data.get('start_date')
        
        # Получаем и отображаем результаты
        await show_analysis_results(message, start_date, None)
        await state.clear()

# Обработчик ввода даты конца периода
@router.message(AnalysisPeriod.entering_end_date)
async def process_end_date(message: types.Message, state: FSMContext):
    if message.text == "назад":
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="ввести конец периода")],
                [types.KeyboardButton(text="до самого позднего результата")],
                [types.KeyboardButton(text="назад")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выберите вариант для конца периода:", reply_markup=keyboard)
        await state.set_state(AnalysisPeriod.choosing_end)
        return
    
    try:
        end_date = datetime.strptime(message.text, '%Y-%m-%d').date()
        
        # Получаем данные о начале периода
        data = await state.get_data()
        start_date = data.get('start_date')
        
        # Получаем и отображаем результаты
        await show_analysis_results(message, start_date, end_date)
        await state.clear()
    except ValueError:
        await message.answer("Неверный формат даты. Введите дату в формате YYYY-MM-DD")

# Обработчик кнопки "назад" в разных состояниях
@router.message(StateFilter(AnalysisPeriod), F.text == "назад")
async def process_back(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state == AnalysisPeriod.choosing_start:
        await cmd_start(message)
        await state.clear()
    elif current_state == AnalysisPeriod.choosing_end:
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="ввести начало периода")],
                [types.KeyboardButton(text="с самого раннего результата")],
                [types.KeyboardButton(text="назад")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выберите вариант для начала периода:", reply_markup=keyboard)
        await state.set_state(AnalysisPeriod.choosing_start)

# Функция для отображения результатов анализов
async def show_analysis_results(message: types.Message, start_date, end_date):
    """
    Читает историю анализов для конкретного пользователя из CSV,
    фильтрует по дате и красиво выводит результат.
    """
    user_id_to_find = str(message.from_user.id) # CSV хранит все как строки
    output_filename = '/home/lopatin/Neymark_LabTracker/analysis_results.csv'

    try:
        with open(output_filename, 'r', encoding='utf-8') as file:
            # Используем DictReader для удобного доступа к колонкам по имени
            reader = csv.DictReader(file)
            user_analyses = [
                row for row in reader 
                if row.get('user_id') == user_id_to_find
            ]
            
            if not user_analyses:
                await message.answer("В вашей истории пока нет записей.")
                await cmd_start(message)
                return

            # Определяем границы периода для фильтрации
            min_date = min(datetime.strptime(row['date'], '%Y-%m-%d').date() for row in user_analyses if row.get('date'))
            max_date = max(datetime.strptime(row['date'], '%Y-%m-%d').date() for row in user_analyses if row.get('date'))
            
            actual_start = start_date if start_date else min_date
            actual_end = end_date if end_date else max_date
            
            # Фильтруем анализы по дате
            filtered_analyses = []
            for row in user_analyses:
                try:
                    analysis_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                    if actual_start <= analysis_date <= actual_end:
                        filtered_analyses.append(row)
                except (ValueError, TypeError):
                    # Пропускаем строки с некорректной датой
                    continue
            
            # Формируем красивое сообщение
            if filtered_analyses:
                # Сортируем по дате для красивого вывода
                filtered_analyses.sort(key=lambda x: x['date'])

                result_message = f"📊 *Ваши результаты за период с {actual_start} по {actual_end}:*\n\n"
                for analysis in filtered_analyses:
                    # Используем Markdown для форматирования
                    result_message += f"📅 *Дата:* `{analysis.get('date', 'N/A')}`\n"
                    result_message += f"🔬 *Анализ:* {analysis.get('analysis', 'N/A')}\n"
                    result_message += f"📈 *Результат:* `{analysis.get('result', 'N/A')}`\n"
                    result_message += f"🩺 *Статус:* {analysis.get('status', 'N/A')}\n"
                    result_message += "─" * 20 + "\n"
                
                # Отправка длинных сообщений частями
                if len(result_message) > 4096:
                    for i in range(0, len(result_message), 4096):
                        await message.answer(result_message[i:i+4096], parse_mode="Markdown")
                else:
                    await message.answer(result_message, parse_mode="Markdown")
            else:
                await message.answer(f"Не найдено результатов за период с {actual_start} по {actual_end}.")
    
    except FileNotFoundError:
        await message.answer("Файл с историей анализов еще не создан. Загрузите свой первый скан.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при чтении истории: {str(e)}")
    
    # Возвращаем пользователя в главное меню
    await cmd_start(message)