from aiogram import Router, types
from aiogram.filters import Command
from datetime import timedelta

from src.tg_bot.services.analysis_service import AnalysisService
from src.tg_bot.models.analysis_models import AnalysesQuery

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Welcome! Use /scan, /analyse, or /history commands.")

@router.message(Command("scan"))
async def cmd_scan(message: types.Message):
    if not message.photo:
        await message.reply("Please send a photo of your analysis.")
        return

    file_id = message.photo[-1].file_id  # take highest resolution
    response = AnalysisService.add_scan(user_id=message.from_user.id, file_id=file_id)
    await message.reply(response)

@router.message(Command("analyse"))
async def cmd_analyse(message: types.Message):
    result = AnalysisService.analyse_history(user_id=message.from_user.id)
    await message.reply(f"Analysis summary: {result.summary}")

@router.message(Command("history"))
async def cmd_history(message: types.Message):
    # Example: user can send "/history 7" to get last 7 days
    try:
        days = int(message.text.split()[1])
    except (IndexError, ValueError):
        days = 7

    query = AnalysesQuery(user_id=message.from_user.id, since=timedelta(days=days))
    history = AnalysisService.get_history(query)
    if not history.analyses:
        await message.reply(f"No analyses found in the last {days} days.")
    else:
        summaries = "\n".join([f"- {a.summary} ({a.generated_at.date()})" for a in history.analyses])
        await message.reply(f"Your analyses in the last {days} days:\n{summaries}")
