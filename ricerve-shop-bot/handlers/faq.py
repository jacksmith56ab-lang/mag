import os
from aiogram import Router, F
from aiogram.types import CallbackQuery

import keyboards as kb
import database as db
from utils import send_with_photo

router = Router()

IMG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "faq.jpg")

FAQ_TEXT = (
    "📖 <b>FAQ — Часто задаваемые вопросы</b>\n\n"
    "Здесь вы найдёте ответы на популярные вопросы о магазине.\n"
    "Подпишитесь на информационный канал, чтобы быть в курсе новинок и акций 👇"
)


@router.callback_query(F.data == "menu_faq")
async def show_faq(call: CallbackQuery):
    await send_with_photo(call, FAQ_TEXT, IMG, reply_markup=kb.faq_menu(db.get_info_channel()))
