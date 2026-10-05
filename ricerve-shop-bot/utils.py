"""
Утилиты для работы с сообщениями.
"""
import os
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, FSInputFile
from aiogram.types import InputMediaPhoto


async def edit_message(call: CallbackQuery, text: str,
                       reply_markup: InlineKeyboardMarkup = None,
                       parse_mode: str = "HTML"):
    """
    Редактирует сообщение (текст или caption у фото).
    Если не получается — удаляет старое и отправляет новое.
    """
    msg = call.message
    is_photo = bool(msg.photo) or getattr(msg, 'content_type', None) == 'photo'

    if is_photo:
        # Для фото-сообщения редактируем caption
        try:
            await msg.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception:
            pass
        # Не вышло — удаляем и шлём текст
        try:
            await msg.delete()
        except Exception:
            pass
        await msg.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        try:
            await msg.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            await msg.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


async def send_with_photo(call: CallbackQuery, text: str,
                          image_path: str,
                          reply_markup: InlineKeyboardMarkup = None,
                          parse_mode: str = "HTML"):
    """
    Отправляет сообщение с фото (если файл существует).

    Логика:
    1. Если текущее сообщение уже фото → edit_media (заменяем медиа + caption)
    2. Если текущее сообщение текстовое → удаляем его и отправляем answer_photo
    3. Если файла нет → обычный edit_message (текст)
    """
    if os.path.exists(image_path):
        msg = call.message
        is_photo = bool(msg.photo) or getattr(msg, 'content_type', None) == 'photo'

        if is_photo:
            # Пробуем заменить медиа
            try:
                await msg.edit_media(
                    media=InputMediaPhoto(
                        media=FSInputFile(image_path),
                        caption=text,
                        parse_mode=parse_mode
                    ),
                    reply_markup=reply_markup
                )
                return
            except Exception:
                pass

        # Текстовое сообщение (или edit_media не сработал) — удаляем и шлём фото
        try:
            await msg.delete()
        except Exception:
            pass
        await msg.answer_photo(
            photo=FSInputFile(image_path),
            caption=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    else:
        # Файла нет — обычный текст
        await edit_message(call, text, reply_markup=reply_markup, parse_mode=parse_mode)
