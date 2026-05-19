#  This file is part of SenkoGuardianModules
#  Copyright (c) 2025-2026 Senko
#  This software is released under the MIT License.
#  https://opensource.org/licenses/MIT

# scope heroku_min: 2.0.0
# meta banner: https://raw.githubusercontent.com/SenkoGuardian/SenkoGuardian.github.io/main/OfficialSenkoGuardianBanner.png
# meta pic: https://raw.githubusercontent.com/SenkoGuardian/SenkoGuardian.github.io/main/OfficialSenkoGuardianBanner.png

__version__ = ("6", "5", "0") 

"""￣へ￣"""

# meta developer: @SenkoGuardianModules

#  .------. .------. .------. .------. .------. .------.
#  |S.--. | |E.--. | |N.--. | |M.--. | |O.--. | |D.--. |
#  | :/\: | | :/\: | | :(): | | :/\: | | :/\: | | :/\: |
#  | :\/: | | :\/: | | ()() | | :\/: | | :\/: | | :\/: |
#  | '--'S| | '--'E| | '--'N| | '--'M| | '--'O| | '--'D|
#  `------' `------' `------' `------' `------' `------'

import re
import os
import io
import random
import socket
import base64
import uuid
import json
import asyncio
import logging
import tempfile
import time
import aiohttp
from markdown_it import MarkdownIt
import pytz
import httpx
import pytz

# Berry API — no google-genai SDK needed
GOOGLE_AVAILABLE = True
google_exceptions = None

class types:
    """Stub types to keep Part/Content/Blob usage working (data containers only)."""
    class Part:
        def __init__(self, text=None, inline_data=None):
            self.text = text
            self.inline_data = inline_data
    class Blob:
        def __init__(self, mime_type=None, data=None):
            self.mime_type = mime_type
            self.data = data
    class Content:
        def __init__(self, role=None, parts=None):
            self.role = role
            self.parts = parts or []

from PIL import Image
from datetime import datetime
from telethon import types as tg_types
from telethon.tl.types import Message, DocumentAttributeFilename, DocumentAttributeSticker
from telethon.utils import get_display_name, get_peer_id
from telethon.errors.rpcerrorlist import (
    MessageTooLongError, 
    ChatAdminRequiredError,
    UserNotParticipantError, 
    ChannelPrivateError
)

from .. import loader, utils
from ..inline.types import InlineCall

logger = logging.getLogger(__name__)

_gemini_log_client = None
_gemini_log_channel = None
_gemini_log_topic_id = None

class _GeminiTopicHandler(logging.Handler):
    def emit(self, record):
        if _gemini_log_client is None or _gemini_log_channel is None or _gemini_log_topic_id is None:
            return
        try:
            text = f"<code>[{record.levelname}]</code> {self.format(record)}"
            asyncio.ensure_future(
                _gemini_log_client.send_message(
                    int(f"-100{_gemini_log_channel}"),
                    text,
                    parse_mode="html",
                    reply_to=_gemini_log_topic_id,
                )
            )
        except Exception:
            pass

_gemini_topic_handler = _GeminiTopicHandler()
_gemini_topic_handler.setLevel(logging.WARNING)
logger.addHandler(_gemini_topic_handler)

DB_HISTORY_KEY = "gemini_conversations_v4"
DB_GAUTO_HISTORY_KEY = "gemini_gauto_conversations_v1"
DB_IMPERSONATION_KEY = "gemini_impersonation_chats"
DB_PRESETS_KEY = "gemini_prompt_presets"
DB_PAGER_CACHE_KEY = "gemini_pager_cache"
DB_KEY_MAP_KEY = "gemini_key_model_map"
DB_MEMORY_DISABLED_KEY = "gemini_memory_disabled_chats"
DB_SESSION_STATS_KEY = "gemini_session_stats_v1"
DB_PROVIDER_MODELS_KEY = "gemini_provider_models_v1"
GEMINI_TIMEOUT = 840
MAX_FFMPEG_SIZE = 90 * 1024 * 1024
BERRY_BASE_URL = "https://ai-integrations-list--berrsi.replit.app/v1"
AIHUB_BASE_URL = "https://attached-assets--brrbrr6.replit.app"
AIHUB2_BASE_URL = "https://ai-hub--bleldkj.replit.app"
AIHUB_BASE_URL = "https://attached-assets--brrbrr6.replit.app"
AIHUB2_BASE_URL = "https://ai-hub--bleldkj.replit.app"
DB_AIHUB_CONVS_KEY = "gemini_aihub_conversations_v1"
CHECK_MODEL = "gpt-5.1"  
MODEL_PROFILE_CHOICES = ("auto", "balanced", "fast", "reasoning", "coding", "vision", "manual")

# requires: pytz markdown_it_py Pillow aiohttp

class Gemini(loader.Module):
    """Модуль для работы с AI через Berry API. (Поддержка видео/фото/аудио"""
    strings = {
        "name": "Gemini",
        "cfg_api_key_doc": "Berry API ключи (sk-berry-...), разделенные запятой.",
        "cfg_model_name_doc": "Имя модели (gpt-5.1, gpt-4o, gemini-2.5-flash, claude-3-5-sonnet и т.д.).",
        "cfg_buttons_doc": "Включить интерактивные кнопки.",
        "cfg_system_instruction_doc": "Системная инструкция (промпт) для Gemini.",
        "cfg_max_history_length_doc": "Макс. кол-во пар 'вопрос-ответ' в памяти (0 - без лимита).",
        "cfg_timezone_doc": "Ваш часовой пояс. Список: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
        "cfg_proxy_doc": "Прокси для обхода региональных блокировок. Формат: http://user:pass@host:port",
        "cfg_impersonation_prompt_doc": "Промпт для режима авто-ответа. {my_name} и {chat_history} будут заменены.",
        "cfg_impersonation_history_limit_doc": "Сколько последних сообщений из чата отправлять в качестве контекста для авто-ответа.",
        "cfg_impersonation_reply_chance_doc": "Вероятность ответа в режиме gauto (от 0.0 до 1.0). 0.2 = 20% шанс.",
        "cfg_temperature_doc": "Температура генерации (креативность). От 0.0 до 2.0. По умолчанию 1.0.",
        "cfg_google_search_doc": "Включить поиск Google (Grounding) для актуальной информации.",
        "cfg_image_model_doc": "Модель Gemini для генерации изображений (например: gemini-2.5-flash-image).",
        "cfg_inline_pagination_doc": "Использовать инлайн-кнопки для длинных ответов.",
        "cfg_global_memory_doc": "Включить ОБЩУЮ память для всех чатов.",
        "cfg_show_tokens_doc": "Показывать токены в ответе, если провайдер их вернул.",
        "cfg_show_time_doc": "Показывать время выполнения запроса.",
        "cfg_auto_model_doc": "Автоматически подбирать модель по профилю и запросу.",
        "cfg_model_profile_doc": "Профиль модели: auto, balanced, fast, reasoning, coding, vision, manual.",
        "no_api_key": (
            '❗️ <b>Berry API ключ не настроен.</b>\n'
            '<b>Добавьте ключ в конфиге:</b> <code>.cfg gemini api_key</code>\n'
        ),
        "no_api_key_Openrouter": '❗️ <b>AI Hub API ключ не настроен.</b>\n<b>Добавьте ключ:</b> <code>.cfg gemini aihub_api_key</code>',
        "invalid_api_key_Openrouter": '❗️ <b>Предоставленный Berry API ключ недействителен.</b>',
        "gmodel_list_title_Openrouter": "📋 <b>Доступные модели Berry API:</b>",
        "invalid_api_key": '❗️ <b>Предоставленный Berry API ключ недействителен.</b>',
        "all_keys_exhausted": "❗️ <b>Все доступные API ключи ({}) исчерпали свою квоту.</b>\nПопробуйте позже или добавьте новые ключи в конфиге: <code>.cfg gemini api_key</code>",
        "no_prompt_or_media": "⚠️ <i>Нужен текст или ответ на медиа/файл.</i>",
        "processing": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Обработка...</b>",
        "api_error": "❗️ <b>Ошибка API Google Gemini:</b>\n<code>{}</code>",
        "api_timeout": f"❗️ <b>Таймаут ответа от Gemini API ({GEMINI_TIMEOUT} сек).</b>",
        "blocked_error": "🚫 <b>Запрос/ответ заблокирован.</b>\n<code>{}</code>",
        "generic_error": "❗️ <b>Ошибка:</b>\n<code>{}</code>",
        "question_prefix": "💬 <b>Запрос:</b>",
        "response_prefix": "<emoji document_id=5325547803936572038>✨</emoji> <b>{ai_name}:</b>",
        "unsupported_media_type": "⚠️ <b>Формат медиа ({}) не поддерживается.</b>",
        "memory_status": "🧠 [{}/{}]",
        "memory_status_unlimited": "🧠 [{}/∞]",
        "memory_status_global": "🧠 [🌍 GLOBAL/{}]",
        "memory_cleared": "🧹 <b>Память диалога очищена.</b>",
        "memory_cleared_global": "🧹 <b>Глобальная память очищена.</b>",
        "memory_cleared_gauto": "🧹 <b>Память gauto в этом чате очищена.</b>",
        "no_memory_to_clear": "ℹ️ <b>В этом чате нет истории.</b>",
        "gres_global_cleared": "🧹 <b>Вся глобальная память очищена.</b>",
        "gres_no_global": "ℹ️ <b>Глобальная память и так пуста.</b>",
        "no_gauto_memory_to_clear": "ℹ️ <b>В этом чате нет истории gauto.</b>",
        "memory_chats_title": "🧠 <b>Чаты с историей ({}):</b>",
        "memory_chat_line": "  • {} (<code>{}</code>)",
        "no_memory_found": "ℹ️ Память Gemini пуста.",
        "media_reply_placeholder": "[ответ на медиа]",
        "btn_clear": "🧹 Очистить",
        "btn_regenerate": "🔄 Другой ответ",
        "no_last_request": "Последний запрос не найден для повторной генерации.",
        "memory_fully_cleared": "🧹 <b>Вся память Gemini полностью очищена (затронуто {} чатов).</b>",
        "gauto_memory_fully_cleared": "🧹 <b>Вся память gauto полностью очищена (затронуто {} чатов).</b>",
        "no_memory_to_fully_clear": "ℹ️ <b>Память Gemini и так пуста.</b>",
        "no_gauto_memory_to_fully_clear": "ℹ️ <b>Память gauto и так пуста.</b>",
        "response_too_long": "Ответ Gemini был слишком длинным и отправлен в виде файла.",
        "gclear_usage": "ℹ️ <b>Использование:</b> <code>.gclear [global/auto]</code>",
        "gres_usage": "ℹ️ <b>Использование:</b> <code>.gres [global/auto]</code>",
        "auto_mode_on": "🎭 <b>Режим авто-ответа включен в этом чате.</b>\nЯ буду отвечать на сообщения с вероятностью {}%.",
        "auto_mode_off": "🎭 <b>Режим авто-ответа выключен в этом чате.</b>",
        "auto_mode_chats_title": "🎭 <b>Чаты с активным авто-ответом ({}):</b>",
        "no_auto_mode_chats": "ℹ️ Нет чатов с включенным режимом авто-ответа.",
        "auto_mode_usage": "ℹ️ <b>Использование:</b> <code>.gauto on/off или[id/username] [on/off]</code>",
        "gauto_chat_not_found": "🚫 <b>Не удалось найти чат:</b> <code>{}</code>",
        "gauto_state_updated": "🎭 <b>Режим авто-ответа для чата {} {}</b>",
        "gauto_enabled": "включен",
        "gauto_disabled": "выключен",
        "gch_usage": "ℹ️ <b>Использование:</b>\n<code>.gch <кол-во> <вопрос></code>\n<code>.gch <id чата> <кол-во> <вопрос></code>",
        "gch_processing": "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Анализирую {} сообщений...</b>",
        "gch_result_caption": "Анализ последних {} сообщений",
        "gch_result_caption_from_chat": "Анализ последних {} сообщений из чата <b>{}</b>",
        "gch_invalid_args": "❗️ <b>Неверные аргументы.</b>\n{}",
        "gch_chat_error": "❗️ <b>Ошибка доступа к чату</b> <code>{}</code>: <i>{}</i>",
        "gask_no_prompt": "⚠️ <b>Введите вопрос или ответьте командой на сообщение.</b>",
        "gprovider_usage": "ℹ️ <b>Использование:</b> <code>.gprovider [berry/aihub/aihub2]</code>",
        "gprovider_current": "🧩 <b>Текущий провайдер:</b> <code>{}</code>\n🧠 <b>Модель:</b> <code>{}</code>\n\n<code>.gprovider berry</code>\n<code>.gprovider aihub</code>\n<code>.gprovider aihub2</code>",
        "gprovider_set": "✅ <b>Провайдер:</b> <code>{}</code>\n🧠 <b>Модель:</b> <code>{}</code>",
        "gprofile_usage": "ℹ️ <b>Использование:</b> <code>.gprofile [auto|balanced|fast|reasoning|coding|vision|manual]</code>",
        "gprofile_set": "✅ <b>Профиль модели:</b> <code>{}</code>\n🧠 <b>Для текущего провайдера:</b> <code>{}</code>",
        "gmodel_usage": "ℹ️ <b>Использование:</b> <code>.gmodel [модель] [--s|-s]</code>\n• [модель] — установить модель.\n• --s/-s — показать список доступных моделей.",
        "gmodel_list_title": "📋 <b>Доступные модели Gemini (по вашему API):</b>",
        "gmodel_list_item": "• <code>{}</code> — {} (поддержка: {})",
        "gmodel_img_support": "Поддержка изображений",
        "gmodel_no_support": "Нет поддержки изображений",
        "gmodel_img_warn": "⚠️ <b>Текущая модель ({}) не может генерировать изображения(или не доступна по API).</b>\nРекомендуем: <code>gemini-2.5-flash-image</code>",
        "gme_chat_not_found": "🚫 <b>Не удалось найти чат для экспорта:</b> <code>{}</code>",
        "gme_sent_to_saved": "💾 История экспортирована в избранное.",
        "new_sdk_missing": "✅ <b>Berry API активен. Дополнительные библиотеки не нужны.</b>",
        "gprompt_usage": "ℹ️ <b>Использование:</b>\n<code>.gprompt <текст/пресет></code> — установить.\n<code>.gprompt -c</code> — очистить.\n<code>.gpresets</code> — база пресетов.",
        "gprompt_updated": "✅ <b>Системный промпт обновлен!</b>\nДлина: {} символов.",
        "gprompt_cleared": "🗑 <b>Системный промпт очищен.</b>",
        "gprompt_current": "📝 <b>Текущий системный промпт:</b>",
        "gprompt_file_error": "❗️ <b>Ошибка чтения файла:</b> {}",
        "gprompt_file_too_big": "❗️ <b>Файл слишком большой</b> (лимит 1 МБ).",
        "gprompt_not_text": "❗️ Это не похоже на текстовый файл.(txt)",
        "gmodel_no_models": "⚠️ Не удалось получить список моделей.",
        "gmodel_list_error": "❗️ Ошибка получения списка: {}",
        "gimg_process": "<emoji document_id=5325547803936572038>✨</emoji> <b>Генерация...</b>\n🧠 <i>Модель: {model}</i>",
        "gpresets_usage": (
            "ℹ️ <b>Управление пресетами:</b>\n"
            "• <code>.gpresets save [Имя] текст</code> — сохранить (имя в скобках, если с пробелами).\n"
            "• <code>.gpresets load 1</code> или <code>имя</code> — загрузить по номеру/имени.\n"
            "• <code>.gpresets del 1</code> или <code>имя</code> — удалить.\n"
            "• <code>.gpresets list</code> — список."
        ),
        "gpreset_loaded": "✅ <b>Установлен пресет:</b> [<code>{}</code>]\nДлина: {} симв.", 
        "gpreset_saved": "💾 <b>Пресет сохранен!</b>\n🏷 <b>Имя:</b> {}\n№ <b>Индекс:</b> {}",
        "gpreset_deleted": "🗑 <b>Пресет удален:</b> {}",
        "gpreset_not_found": "🚫 Пресет с таким именем или индексом не найден.",
        "gpreset_list_head": "📋 <b>Ваши пресеты:</b>\n",
        "gpreset_empty": "📂 Список пресетов пуст.",
    }
    TEXT_MIME_TYPES = {
        "text/plain", "text/markdown", "text/html", "text/css", "text/csv",
        "application/json", "application/xml", "application/x-python", "text/x-python",
        "application/javascript", "application/x-sh",
    }

    CORE_PROVIDER_ORDER = ("berry", "openrouter", "aihub", "aihub2")

    PROVIDER_SPECS = {
        "berry": {
            "label": "Berry AI",
            "default_model": "gpt-5.1",
            "docs_url": BERRY_BASE_URL,
            "model_prefixes": ("gpt", "gemini", "claude", "deepseek"),
            "profiles": {
                "balanced": "gpt-5.1",
                "fast": "gpt-5.1",
                "reasoning": "gpt-5.1",
                "coding": "gpt-5.1",
                "vision": "gpt-5.1",
            },
            "fallback_models": (
                "gpt-5.1",
                "gemini-3-flash-preview",
                "gemini-2.5-pro",
                "gemini-2.5-flash",
            ),
        },
        "openrouter": {
            "label": "Berry AI (2nd key)",
            "default_model": "gpt-5.1",
            "docs_url": BERRY_BASE_URL,
            "model_prefixes": ("gpt", "gemini", "claude", "deepseek"),
            "profiles": {
                "balanced": "gpt-5.1",
                "fast": "gpt-5.1",
                "reasoning": "gpt-5.1",
                "coding": "gpt-5.1",
                "vision": "gpt-5.1",
            },
            "fallback_models": (
                "gpt-5.1",
                "gemini-3-flash-preview",
                "gemini-2.5-pro",
                "gemini-2.5-flash",
            ),
        },
        "aihub": {
            "label": "AI Hub",
            "default_model": "gemini-2.5-flash",
            "docs_url": AIHUB_BASE_URL,
            "model_prefixes": ("gpt", "gemini", "claude", "deepseek", "o1", "o3", "o4"),
            "profiles": {
                "balanced": "gemini-2.5-flash",
                "fast": "gemini-2.5-flash",
                "reasoning": "gemini-2.5-pro",
                "coding": "gemini-2.5-pro",
                "vision": "gemini-2.5-flash",
            },
            "fallback_models": (
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gpt-4o",
                "claude-3-5-sonnet",
            ),
        },
        "aihub2": {
            "label": "AI Hub 2",
            "default_model": "gemini-2.5-flash",
            "docs_url": AIHUB2_BASE_URL,
            "model_prefixes": ("gpt", "gemini", "claude", "deepseek", "o1", "o3", "o4"),
            "profiles": {
                "balanced": "gpt-4o",
                "fast": "gpt-4o-mini",
                "reasoning": "o4-mini",
                "coding": "gpt-4o",
                "vision": "gpt-4o",
            },
            "fallback_models": (
                "gpt-4o",
                "gpt-4o-mini",
                "gemini-2.5-flash",
                "claude-3-5-sonnet",
            ),
        },
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("api_key", "", self.strings["cfg_api_key_doc"], validator=loader.validators.Hidden()),
            loader.ConfigValue("Openrouter_api_key", "", "Дополнительный Berry API ключ (sk-berry-...).", validator=loader.validators.Hidden()),
            loader.ConfigValue("aihub_key", "", "AI Hub ключ (aihub_... или sk-...). Сайт: attached-assets--brrbrr6.replit.app", validator=loader.validators.Hidden()),
            loader.ConfigValue("aihub2_key", "", "AI Hub 2 ключ — отдельный сайт ai-hub--bleldkj.replit.app (пока не используется).", validator=loader.validators.Hidden()),
            loader.ConfigValue("aihub_provider", "gemini", "AI Hub провайдер: openai, gemini, anthropic, openrouter.", validator=loader.validators.Choice(["openai", "gemini", "anthropic", "openrouter"])),
            loader.ConfigValue("provider", "berry", "Провайдер: berry (Berry AI), openrouter (Berry 2nd key), aihub (AI Hub), aihub2 (AI Hub 2).", validator=loader.validators.Choice(["berry", "openrouter", "aihub", "aihub2"])),
            loader.ConfigValue("model_name", "gpt-5.1", self.strings["cfg_model_name_doc"]),
            loader.ConfigValue("interactive_buttons", True, self.strings["cfg_buttons_doc"], validator=loader.validators.Boolean()),
            loader.ConfigValue("system_instruction", "", self.strings["cfg_system_instruction_doc"], validator=loader.validators.String()),
            loader.ConfigValue("max_history_length", 800, self.strings["cfg_max_history_length_doc"], validator=loader.validators.Integer(minimum=0)),
            loader.ConfigValue("global_memory", False, self.strings["cfg_global_memory_doc"], validator=loader.validators.Boolean()),
            loader.ConfigValue("show_tokens", True, self.strings["cfg_show_tokens_doc"], validator=loader.validators.Boolean()),
            loader.ConfigValue("show_time", True, self.strings["cfg_show_time_doc"], validator=loader.validators.Boolean()),
            loader.ConfigValue("auto_model", False, self.strings["cfg_auto_model_doc"], validator=loader.validators.Boolean()),
            loader.ConfigValue("model_profile", "manual", self.strings["cfg_model_profile_doc"], validator=loader.validators.Choice(list(MODEL_PROFILE_CHOICES))),
            loader.ConfigValue("timezone", "Europe/Moscow", self.strings["cfg_timezone_doc"]),
            loader.ConfigValue("proxy", "", self.strings["cfg_proxy_doc"]),
            loader.ConfigValue(
                "impersonation_prompt",
                (
                    "Ты — это я, пользователь Telegram по имени {my_name}. Твоя задача — отвечать в чате от моего имени, основываясь на последних сообщениях. "
                    "Веди себя естественно, как обычный человек, а не как ассистент. Не признавайся, что ты — ИИ, даже если тебя спросят напрямую. "
                    "Твоя личность:[Здесь опишите свой характер: остроумный, серьезный, саркастичный, дружелюбный и т.д.].\n"
                    "Правила:\n- Отвечай кратко и по делу.\n- Используй неформальный язык, сленг.\n- Не отвечай на каждое сообщение.\n- На медиа (стикер, фото) реагируй как человек ('лол', 'ору', 'жиза').\n- Не используй префиксы и кавычки.\n\n"
                    "ИСТОРИЯ ЧАТА:\n{chat_history}\n\n{my_name}:"
                ),
                self.strings["cfg_impersonation_prompt_doc"], validator=loader.validators.String()
            ),
            loader.ConfigValue("impersonation_history_limit", 20, self.strings["cfg_impersonation_history_limit_doc"], validator=loader.validators.Integer(minimum=5, maximum=100)),
            loader.ConfigValue("impersonation_reply_chance", 0.25, self.strings["cfg_impersonation_reply_chance_doc"], validator=loader.validators.Float(minimum=0.0, maximum=1.0)),
            loader.ConfigValue("gauto_in_pm", False, "Разрешить авто-ответы в личных сообщениях (ЛС).", validator=loader.validators.Boolean()),
            loader.ConfigValue("google_search", False, self.strings["cfg_google_search_doc"], validator=loader.validators.Boolean()),
            loader.ConfigValue("temperature", 1.0, self.strings["cfg_temperature_doc"], validator=loader.validators.Float(minimum=0.0, maximum=2.0)),
            loader.ConfigValue("inline_pagination", False, self.strings["cfg_inline_pagination_doc"], validator=loader.validators.Boolean()),
            loader.ConfigValue("image_model_name", "gemini-3-pro-image-preview", self.strings["cfg_image_model_doc"]),
        )
        self.prompt_presets =[]
        self.conversations = {}
        self.gauto_conversations = {}
        self.last_requests = {}
        self.impersonation_chats = set()
        self._lock = asyncio.Lock()
        self.memory_disabled_chats = set()
        self.pager_cache = {}
        self.key_model_map = {}
        self.provider_models = {}
        self.key_cooldowns = {}
        self.aihub_conv_ids = {}  # {(provider_slug, chat_id): conv_id}
        self.session_stats = {"requests": 0, "tokens_in": 0, "tokens_out": 0, "times": [], "start_time": time.time()}
        self.api_keys =[] 

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.me = await client.get_me()
        api_key_str = self.config["api_key"]
        self.api_keys =[k.strip() for k in api_key_str.split(",") if k.strip()] if api_key_str else[]
        self.key_model_map = self.db.get(self.strings["name"], DB_KEY_MAP_KEY, {})
        self.provider_models = self.db.get(self.strings["name"], DB_PROVIDER_MODELS_KEY, {})
        if not isinstance(self.provider_models, dict):
            self.provider_models = {}
        self.memory_disabled_chats = set(self.db.get(self.strings["name"], DB_MEMORY_DISABLED_KEY, []))
        saved_stats = self.db.get(self.strings["name"], DB_SESSION_STATS_KEY, {})
        if isinstance(saved_stats, dict):
            self.session_stats.update({
                "requests": int(saved_stats.get("requests", 0) or 0),
                "tokens_in": int(saved_stats.get("tokens_in", 0) or 0),
                "tokens_out": int(saved_stats.get("tokens_out", 0) or 0),
                "times": list(saved_stats.get("times", []) or [])[-200:],
                "start_time": time.time(),
            })
        keys_to_remove =[k for k in self.key_model_map if k not in self.api_keys]
        if keys_to_remove:
            for k in keys_to_remove: del self.key_model_map[k]
            self.db.set(self.strings["name"], DB_KEY_MAP_KEY, self.key_model_map)
        # Berry API — no google-genai library needed
        self.current_api_key_index = 0
        self.aihub_conv_ids = self.db.get(self.strings["name"], DB_AIHUB_CONVS_KEY, {})
        self.conversations = self._load_history_from_db(DB_HISTORY_KEY)
        self.prompt_presets = self.db.get(self.strings["name"], DB_PRESETS_KEY, [])
        if isinstance(self.prompt_presets, dict):
            self.prompt_presets =[{"name": k, "content": v} for k, v in self.prompt_presets.items()]
        self.gauto_conversations = self._load_history_from_db(DB_GAUTO_HISTORY_KEY)
        self.impersonation_chats = set(self.db.get(self.strings["name"], DB_IMPERSONATION_KEY,[]))
        self.pager_cache = self.db.get(self.strings["name"], DB_PAGER_CACHE_KEY, {})
        if not self.api_keys:
            logger.warning("Gemini: API ключи не настроены.")
        global _gemini_log_client, _gemini_log_channel, _gemini_log_topic_id
        try:
            asset_channel = self._db.get("heroku.forums", "channel_id", 0)
            if asset_channel:
                notif_topic = await utils.asset_forum_topic(
                    self._client,
                    self._db,
                    asset_channel,
                    "Gemini Logs",
                    description="Gemini module warnings & errors.",
                    icon_emoji_id=5325547803936572038,
                )
                _gemini_log_client = self._client
                _gemini_log_channel = asset_channel
                _gemini_log_topic_id = notif_topic.id
        except Exception:
            pass

    def _normalize_provider_name(self, provider: str = None) -> str:
        provider = str(provider or self.config["provider"] or "berry").strip().lower()
        return {"gemini": "berry", "google": "berry", "berry": "berry", "or": "openrouter", "openrouter": "openrouter", "aihub": "aihub", "hub": "aihub", "aihub2": "aihub2", "hub2": "aihub2"}.get(provider, "berry")

    def _provider_spec(self, provider: str = None) -> dict:
        norm = self._normalize_provider_name(provider)
        return self.PROVIDER_SPECS.get(norm, self.PROVIDER_SPECS["berry"])

    def _provider_label(self, provider: str = None) -> str:
        return self._provider_spec(provider).get("label", "Gemini")

    def _provider_default_model(self, provider: str = None) -> str:
        return self._provider_spec(provider).get("default_model", "gpt-5.1")

    def _save_provider_models(self):
        self.db.set(self.strings["name"], DB_PROVIDER_MODELS_KEY, self.provider_models)

    def _provider_model_entry(self, provider: str = None) -> dict:
        provider = self._normalize_provider_name(provider)
        entry = self.provider_models.get(provider, "")
        if isinstance(entry, dict):
            return {
                "model": str(entry.get("model") or "").strip(),
                "manual": bool(entry.get("manual", True)),
                "profile": str(entry.get("profile") or "manual").strip().lower(),
                "auto_model": bool(entry.get("auto_model", False)),
            }
        value = str(entry or "").strip()
        return {"model": value, "manual": bool(value), "profile": "manual", "auto_model": False}

    def _remember_provider_model(self, provider: str = None, model_name: str = None, manual: bool = None):
        provider = self._normalize_provider_name(provider)
        if provider not in self.PROVIDER_SPECS:
            return
        model_name = str(model_name or self.config.get("model_name") or "").strip()
        if not model_name:
            return
        if manual is None:
            manual = (not self.config.get("auto_model", False)) or str(self.config.get("model_profile") or "").lower() == "manual"
        self.provider_models[provider] = {
            "model": model_name,
            "manual": bool(manual),
            "profile": str(self.config.get("model_profile") or ("manual" if manual else "auto")).strip().lower(),
            "auto_model": bool(self.config.get("auto_model", False)) if not manual else False,
        }
        self._save_provider_models()

    def _restore_provider_model(self, provider: str) -> str:
        provider = self._normalize_provider_name(provider)
        entry = self._provider_model_entry(provider)
        saved = entry.get("model")
        if saved:
            self.config["model_name"] = saved
            self.config["auto_model"] = bool(entry.get("auto_model", False)) if not entry.get("manual", True) else False
            profile = str(entry.get("profile") or "manual").lower()
            self.config["model_profile"] = profile if profile in MODEL_PROFILE_CHOICES else "manual"
            return saved
        default = self._provider_default_model(provider)
        self.config["model_name"] = default
        return default

    def _provider_profile_models(self, provider: str = None) -> dict:
        provider = self._normalize_provider_name(provider)
        profiles = dict(self._provider_spec(provider).get("profiles", {}) or {})
        default = self._provider_default_model(provider)
        profiles.setdefault("auto", default)
        profiles.setdefault("balanced", default)
        profiles.setdefault("manual", self.config.get("model_name") or default)
        return profiles

    def _provider_curated_models(self, provider: str = None) -> list:
        models = list(self._provider_spec(provider).get("fallback_models", ()) or ())
        return list(dict.fromkeys([str(model).strip() for model in models if str(model).strip()]))

    def _model_matches_provider(self, model_name: str, provider: str) -> bool:
        # Berry API supports all model names
        return True

    def _parts_have_image_like_media(self, parts: list) -> bool:
        for part in parts or []:
            inline = getattr(part, "inline_data", None)
            if not inline:
                continue
            mime = str(getattr(inline, "mime_type", "") or "").lower()
            if mime.startswith(("image/", "video/")):
                return True
        return False

    def _guess_model_profile_from_request(self, parts: list, request_text: str = "") -> str:
        if self._parts_have_image_like_media(parts):
            return "vision"
        text = str(request_text or "")
        for part in parts or []:
            if getattr(part, "text", None):
                text += "\n" + str(part.text)
        low = text.lower()
        if any(h in low for h in ("код", "скрипт", "traceback", "stack trace", "python", "javascript", "typescript", "api", "regex", "pytest", "docker")):
            return "coding"
        if any(h in low for h in ("объясни", "проанализируй", "сравни", "докажи", "архитектур", "reason", "solve", "proof")):
            return "reasoning"
        return "balanced"

    def _resolve_effective_model(self, provider: str, configured_model: str = None, parts: list = None, request_text: str = "") -> str:
        provider = self._normalize_provider_name(provider)
        configured = str(configured_model or self.config.get("model_name") or "").strip()
        default = self._provider_default_model(provider)
        if configured and not self._model_matches_provider(configured, provider):
            configured = ""
        if not self.config.get("auto_model", False):
            return configured or default
        profile = str(self.config.get("model_profile") or "auto").strip().lower()
        if profile not in MODEL_PROFILE_CHOICES:
            profile = "auto"
        if profile == "manual":
            return configured or default
        selected = self._guess_model_profile_from_request(parts or [], request_text) if profile == "auto" else profile
        profiles = self._provider_profile_models(provider)
        return profiles.get(selected) or profiles.get("balanced") or configured or default

    def _extract_request_text_for_display(self, parts: list, fallback: str = None) -> str:
        if fallback:
            return fallback
        chunks = []
        for part in parts or []:
            text = getattr(part, "text", None)
            if text:
                chunks.append(str(text))
        return "\n".join(chunks).strip() or "[медиа-запрос]"

    def _record_session_usage(self, tokens_in: int = 0, tokens_out: int = 0, elapsed: float = 0.0):
        self.session_stats["requests"] = int(self.session_stats.get("requests", 0) or 0) + 1
        self.session_stats["tokens_in"] = int(self.session_stats.get("tokens_in", 0) or 0) + int(tokens_in or 0)
        self.session_stats["tokens_out"] = int(self.session_stats.get("tokens_out", 0) or 0) + int(tokens_out or 0)
        times = list(self.session_stats.get("times", []) or [])
        times.append(float(elapsed or 0))
        self.session_stats["times"] = times[-200:]
        self.db.set(self.strings["name"], DB_SESSION_STATS_KEY, {
            "requests": self.session_stats["requests"],
            "tokens_in": self.session_stats["tokens_in"],
            "tokens_out": self.session_stats["tokens_out"],
            "times": self.session_stats["times"],
        })

    def _model_info_line(self, provider: str, model: str, elapsed: float = 0.0, tokens_in: int = 0, tokens_out: int = 0) -> str:
        extra = ""
        if self.config.get("show_time", True):
            extra += f" ⏱️{round(float(elapsed or 0), 1)}с"
        if self.config.get("show_tokens", True) and (tokens_in or tokens_out):
            extra += f" 🪙{int(tokens_in or 0) + int(tokens_out or 0)}"
        return f"<i>{self._provider_label(provider)}: <code>{utils.escape_html(str(model))}</code>{extra}</i>"

    def _get_ai_name(self, model: str = None, provider: str = None) -> str:
        """Возвращает название AI по имени модели."""
        p = str(provider or self.config.get("provider") or "").lower()
        if p == "aihub": return "AI Hub"
        if p == "aihub2": return "AI Hub 2"
        m = str(model or self.config.get("model_name") or "").lower()
        if any(x in m for x in ("gpt", "o1", "o3", "o4", "chatgpt")):
            return "ChatGPT"
        if any(x in m for x in ("claude",)):
            return "Claude"
        if any(x in m for x in ("gemini", "imagen")):
            return "Gemini"
        if any(x in m for x in ("deepseek",)):
            return "DeepSeek"
        if any(x in m for x in ("llama",)):
            return "Llama"
        if any(x in m for x in ("grok",)):
            return "Grok"
        if any(x in m for x in ("mistral",)):
            return "Mistral"
        return "AI"

    def _extract_retry_delay_seconds(self, text: str, default: int = 3600) -> int:
        raw = str(text or "")
        match = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)s", raw, flags=re.IGNORECASE)
        if match:
            return max(60, min(int(match.group(1)), 86400))
        match = re.search(r"retry after\s+(\d+)", raw, flags=re.IGNORECASE)
        if match:
            return max(60, min(int(match.group(1)), 86400))
        return default

    def _set_key_cooldown(self, key: str, seconds: int):
        if key:
            self.key_cooldowns[str(key)] = time.time() + max(60, int(seconds or 3600))

    def _get_openrouter_keys(self) -> list:
        raw = str(self.config.get("Openrouter_api_key") or "")
        return [key.strip() for key in raw.split(",") if key.strip()]

    def _get_berry_keys(self) -> list:
        """Все Berry API ключи: основные + дополнительные."""
        main = [k for k in (self.api_keys or []) if k]
        extra = self._get_openrouter_keys()
        seen = set()
        result = []
        for k in main + extra:
            if k not in seen:
                seen.add(k)
                result.append(k)
        return result

    def _get_aihub_key(self, provider_name: str) -> str:
        """Возвращает ключ для AI Hub (aihub или aihub2)."""
        cfg_key = "aihub_key" if provider_name == "aihub" else "aihub2_key"
        return str(self.config.get(cfg_key) or "").strip()

    def _get_aihub_base_url(self, provider_name: str) -> str:
        return AIHUB2_BASE_URL if provider_name == "aihub2" else AIHUB_BASE_URL

    async def _prepare_parts(self, message: Message, custom_text: str=None):
        final_parts, warnings = [], []
        prompt_text_chunks =[]
        user_args = custom_text if custom_text is not None else utils.get_args_raw(message)
        try:
            chat = await message.get_chat()
            chat_title = getattr(chat, 'title', getattr(chat, 'first_name', 'Личные сообщения'))
        except Exception:
            chat_title = "Неизвестный чат"
        prompt_text_chunks.append(f"[System info: We are in '{chat_title}' chat]")
        reply = await message.get_reply_message()
        if reply and getattr(reply, "text", None):
            try:
                reply_sender = await reply.get_sender()
                reply_author_name = get_display_name(reply_sender) if reply_sender else "Unknown"
                prompt_text_chunks.append(f"{reply_author_name}: {reply.text}")
            except Exception: 
                prompt_text_chunks.append(f"Ответ на: {reply.text}")
        try:
            current_sender = await message.get_sender()
            current_user_name = get_display_name(current_sender) if current_sender else "User"
            prompt_text_chunks.append(f"{current_user_name}: {user_args or ''}")
        except Exception: 
            prompt_text_chunks.append(f"Запрос: {user_args or ''}")
        media_source = message if message.media or message.sticker else reply
        has_media = bool(media_source and (media_source.media or media_source.sticker))
        if has_media:
            if media_source.sticker and hasattr(media_source.sticker, 'mime_type') and media_source.sticker.mime_type=='application/x-tgsticker':
                alt_text = next((attr.alt for attr in media_source.sticker.attributes if isinstance(attr, DocumentAttributeSticker)), "?")
                prompt_text_chunks.append(f"[Анимированный стикер: {alt_text}]")
            else:
                media, mime_type, filename = media_source.media, "application/octet-stream", "file"
                if media_source.photo: 
                    mime_type = "image/jpeg"
                elif hasattr(media_source, "document") and media_source.document:
                    mime_type = getattr(media_source.document, "mime_type", mime_type)
                    doc_attr = next((attr for attr in media_source.document.attributes if isinstance(attr, DocumentAttributeFilename)), None)
                    if doc_attr: filename = doc_attr.file_name
                    
                async def get_bytes(m):
                    bio = io.BytesIO()
                    await self.client.download_media(m, bio)
                    return bio.getvalue()
                    
                if mime_type.startswith("image/"):
                    try:
                        data = await get_bytes(media)
                        final_parts.append(types.Part(inline_data=types.Blob(mime_type=mime_type, data=data)))
                    except Exception as e: warnings.append(f"⚠️ Ошибка обработки изображения '{filename}': {e}")
                elif mime_type in self.TEXT_MIME_TYPES or filename.split('.')[-1] in ('txt', 'py', 'js', 'json', 'md', 'html', 'css', 'sh'):
                    try:
                        data = await get_bytes(media)
                        file_content = data.decode('utf-8')
                        prompt_text_chunks.insert(0, f"[Содержимое файла '{filename}']: \n```\n{file_content}\n```")
                    except Exception as e: warnings.append(f"⚠️ Ошибка чтения файла '{filename}': {e}")
                elif mime_type.startswith("audio/"):
                    input_path, output_path = None, None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=f".{filename.split('.')[-1]}", delete=False) as temp_in: input_path = temp_in.name
                        await self.client.download_media(media, input_path)
                        if os.path.getsize(input_path) > MAX_FFMPEG_SIZE:
                            warnings.append(f"⚠️ Аудиофайл '{filename}' слишком большой."); raise StopIteration
                        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_out: output_path = temp_out.name
                        ffmpeg_cmd =["ffmpeg", "-y", "-i", input_path, "-c:a", "libmp3lame", "-q:a", "2", output_path]
                        process_ffmpeg = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        await process_ffmpeg.communicate()
                        if process_ffmpeg.returncode != 0: raise Exception("FFmpeg error")
                        with open(output_path, "rb") as f:
                            final_parts.append(types.Part(inline_data=types.Blob(mime_type="audio/mpeg", data=f.read())))
                    except StopIteration: pass
                    except Exception as e: warnings.append(f"⚠️ Ошибка обработки аудио: {e}")
                    finally:
                        if input_path and os.path.exists(input_path): os.remove(input_path)
                        if output_path and os.path.exists(output_path): os.remove(output_path)
                elif mime_type.startswith("video/"):
                    input_path, output_path = None, None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=f".{filename.split('.')[-1]}", delete=False) as temp_in: input_path = temp_in.name
                        await self.client.download_media(media, input_path)
                        if os.path.getsize(input_path) > MAX_FFMPEG_SIZE:
                            warnings.append(f"⚠️ Медиафайл '{filename}' слишком большой."); raise StopIteration
                        ffprobe_cmd =["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", input_path]
                        process_probe = await asyncio.create_subprocess_exec(*ffprobe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        stdout, _ = await process_probe.communicate()
                        has_audio = bool(stdout.strip())
                        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_out: output_path = temp_out.name
                        ffmpeg_cmd =["ffmpeg", "-y", "-i", input_path]
                        maps = ["-map", "0:v:0"]
                        if not has_audio:
                            ffmpeg_cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])
                            maps.extend(["-map", "1:a:0"])
                        else:
                            maps.extend(["-map", "0:a:0?"])
                        ffmpeg_cmd.extend([*maps, "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", output_path])
                        process_ffmpeg = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        _, stderr = await process_ffmpeg.communicate()
                        if process_ffmpeg.returncode != 0:
                            stderr_str = stderr.decode()
                            warnings.append(f"⚠️ <b>Ошибка FFmpeg:</b>\nНе удалось конвертировать '{filename}'. Детали:\n<code>{utils.escape_html(stderr_str)}</code>")
                            raise StopIteration
                        with open(output_path, "rb") as f:
                            final_parts.append(types.Part(inline_data=types.Blob(mime_type="video/mp4", data=f.read())))
                    except StopIteration: pass
                    except Exception as e: warnings.append(f"⚠️ Ошибка обработки видео: {e}")
                    finally:
                        if input_path and os.path.exists(input_path): os.remove(input_path)
                        if output_path and os.path.exists(output_path): os.remove(output_path)
                        
        if not user_args and has_media and not final_parts and not any("[Содержимое файла" in chunk for chunk in prompt_text_chunks):
            prompt_text_chunks.append(self.strings["media_reply_placeholder"])
        full_prompt_text = "\n".join(chunk for chunk in prompt_text_chunks if chunk and chunk.strip()).strip()
        if full_prompt_text:
            final_parts.insert(0, types.Part(text=full_prompt_text))
        return final_parts, warnings

    async def _send_to_gemini(self, message, parts: list, regeneration: bool=False, call: InlineCall=None, status_msg=None, chat_id_override: int=None, impersonation_mode: bool=False, use_url_context: bool=False, display_prompt: str=None, attempt: int = 1, is_retry: bool = False, ephemeral: bool = False): 
        msg_obj = None
        if regeneration or is_retry:
            chat_id = chat_id_override; base_message_id = message
            try: msg_obj = await self.client.get_messages(chat_id, ids=base_message_id)
            except Exception: msg_obj = None
        else:
            chat_id = utils.get_chat_id(message); base_message_id = message.id; msg_obj = message
        provider = self._normalize_provider_name()
        is_global = self.config["global_memory"] and not impersonation_mode
        history_key = "global_context" if is_global else str(chat_id)
        target_model = self._resolve_effective_model(provider, self.config["model_name"], parts, display_prompt or "")
        if provider in ("openrouter", "aihub", "aihub2"):
            if regeneration or is_retry:
                current_turn_parts, request_text_for_display = self.last_requests.get(f"{chat_id}:{base_message_id}", (parts, "[регенерация]"))
            else:
                current_turn_parts = parts
                request_text_for_display = self._extract_request_text_for_display(parts, display_prompt)
                self.last_requests[f"{chat_id}:{base_message_id}"] = (current_turn_parts, request_text_for_display)
            try:
                target_model = self._resolve_effective_model(provider, self.config["model_name"], current_turn_parts, request_text_for_display)
                sys_instruct = self.config["system_instruction"] or None
                if impersonation_mode:
                    my_name = get_display_name(self.me)
                    chat_history_text = await self._get_recent_chat_text(chat_id)
                    sys_instruct = self.config["impersonation_prompt"].format(my_name=my_name, chat_history=chat_history_text)
                
                raw_hist = self._get_structured_history(history_key, gauto=impersonation_mode)
                if regeneration and raw_hist: raw_hist = raw_hist[:-2]
                openai_messages = self._convert_google_history_to_openai(raw_hist, sys_instruct)
                content_list =[]
                media_notes = []
                for p in current_turn_parts:
                    if hasattr(p, "text") and p.text:
                        content_list.append({"type": "text", "text": p.text})
                    elif hasattr(p, "inline_data") and p.inline_data:
                         mime = p.inline_data.mime_type
                         data = p.inline_data.data
                         if mime.startswith("image/"):
                             b64_img = base64.b64encode(data).decode("utf-8")
                             content_list.append({
                                 "type": "image_url", 
                                 "image_url": {"url": f"data:{mime};base64,{b64_img}"}
                             })
                         elif mime.startswith("audio/"):
                             media_notes.append("[аудиофайл]")
                         elif mime.startswith("video/"):
                             media_notes.append("[видеофайл]")
                         else:
                             media_notes.append("[файл]")
                if media_notes:
                    note = "Контекст медиа для OpenRouter: " + ", ".join(media_notes)
                    if content_list and isinstance(content_list, list) and content_list[0].get("type") == "text":
                        content_list[0]["text"] = note + "\n\n" + content_list[0]["text"]
                    else:
                        content_list.insert(0, {"type": "text", "text": note})
                if not content_list:
                    content_list = request_text_for_display
                openai_messages.append({"role": "user", "content": content_list})
                _t_start = time.time()
                if provider in ("aihub", "aihub2"):
                    result_text, usage = await self._send_to_aihub_api(provider, target_model, openai_messages, self.config["temperature"], chat_id)
                else:
                    result_text, usage = await self._send_to_berry_api(target_model, openai_messages, self.config["temperature"])
                _elapsed = round(time.time() - _t_start, 1)
                _tokens_in = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
                _tokens_out = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
                if not (_tokens_in or _tokens_out) and usage.get("total_tokens"):
                    _tokens_out = int(usage.get("total_tokens") or 0)
                result_text = result_text.strip()
                result_text = re.sub(r"^\[System Info:.*?\]\s*", "", result_text, flags=re.IGNORECASE)
                result_text = re.sub(r"^\[\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}\]\s*(?:Gemini:|Model:|Ассистент:|AI:)?\s*", "", result_text, flags=re.IGNORECASE)
                result_text = re.sub(r"^\[\d{2}:\d{2}\]\s*(?:Gemini:|Model:|Ассистент:|AI:)?\s*", "", result_text, flags=re.IGNORECASE)
                if not impersonation_mode:
                    self._record_session_usage(_tokens_in, _tokens_out, _elapsed)
                if self._is_memory_enabled(str(chat_id)) and not ephemeral:
                    self._update_history(history_key, current_turn_parts, result_text, regeneration, msg_obj, gauto=impersonation_mode)
                if impersonation_mode: return result_text
                hist_len = len(self._get_structured_history(history_key)) // 2
                max_hist = self.config["max_history_length"]
                if is_global:
                    mem_indicator = self.strings["memory_status_global"].format(hist_len)
                elif max_hist <= 0:
                    mem_indicator = self.strings["memory_status_unlimited"].format(hist_len)
                else:
                    mem_indicator = self.strings["memory_status"].format(hist_len, max_hist)
                model_info = self._model_info_line(provider, target_model, _elapsed, _tokens_in, _tokens_out)
                if attempt > 1:
                    model_info += f" <i>(Успешно с {attempt}-й попытки)</i>"
                response_html = self._markdown_to_html(result_text)
                formatted_body = self._format_response_with_smart_separation(response_html)
                question_html = f"<blockquote>{utils.escape_html(request_text_for_display[:200])}</blockquote>"
                text_to_send = f"{mem_indicator}\n{model_info}\n\n{self.strings['question_prefix']}\n{question_html}\n\n{self.strings['response_prefix'].format(ai_name=self._get_ai_name(target_model))}\n{formatted_body}"
                if call or self.config["interactive_buttons"]:
                    text_to_send = text_to_send.replace('<emoji document_id=', '<tg-emoji emoji-id=').replace('</emoji>', '</tg-emoji>')
                buttons = self._get_inline_buttons(chat_id, base_message_id) if self.config["interactive_buttons"] else None
                if len(text_to_send) > 4096:
                    file = io.BytesIO(result_text.encode("utf-8")); file.name = "Gemini_response.txt"
                    if call: await self.client.send_file(call.chat_id, file, caption="Response too long", reply_to=call.message_id)
                    elif status_msg: 
                        await status_msg.delete()
                        await self.client.send_file(chat_id, file, caption="Response too long", reply_to=base_message_id)
                else:
                    if call: await call.edit(text_to_send, reply_markup=buttons)
                    elif status_msg: await utils.answer(status_msg, text_to_send, reply_markup=buttons)
                return ""
            except Exception as e:
                error_text = self._handle_error(e)
                error_buttons = None
                if not impersonation_mode and base_message_id:
                    btn_action = "regen_att" if regeneration else "retry"
                    is_regen_flag = "1" if regeneration else "0"
                    error_buttons = [[
                        {"text": f"🔄 Повторить ({attempt + 1})", "data": f"gemini:{btn_action}:{chat_id}:{base_message_id}:{attempt + 1}"},
                        {"text": "👁 Запрос", "data": f"gemini:shreq:{is_regen_flag}:{chat_id}:{base_message_id}:{attempt + 1}"}
                    ]]
                if impersonation_mode: logger.error(f"Gauto/Openrouter error: {error_text}")
                elif call: await call.edit(error_text, reply_markup=error_buttons)
                elif status_msg: await utils.answer(status_msg, error_text, reply_markup=error_buttons)
                return None
        # For aihub/aihub2, redirect to the openrouter-style branch above
        # (this point is only reached for "berry" provider)
        api_keys_to_use = self._get_berry_keys()
        if not api_keys_to_use:
            if not impersonation_mode and status_msg: await utils.answer(status_msg, self.strings['no_api_key'])
            return None if impersonation_mode else ""
        if regeneration or is_retry:
            current_turn_parts, request_text_for_display = self.last_requests.get(f"{chat_id}:{base_message_id}", (parts, "[регенерация]"))
        else:
            current_turn_parts = parts
            request_text_for_display = self._extract_request_text_for_display(parts, display_prompt)
            self.last_requests[f"{chat_id}:{base_message_id}"] = (current_turn_parts, request_text_for_display)
        target_model = self._resolve_effective_model("berry", self.config["model_name"], current_turn_parts, request_text_for_display)
        result_text = ""
        last_error = None
        was_successful = False
        search_icon = ""
        _tokens_in = 0
        _tokens_out = 0
        if impersonation_mode:
            my_name = get_display_name(self.me)
            chat_history_text = await self._get_recent_chat_text(chat_id)
            sys_instruct = self.config["impersonation_prompt"].format(my_name=my_name, chat_history=chat_history_text)
        else:
            sys_val = self.config["system_instruction"]
            sys_instruct = (sys_val.strip() if isinstance(sys_val, str) else "") or None
        raw_hist = self._get_structured_history(history_key, gauto=impersonation_mode)
        if regeneration and raw_hist: raw_hist = raw_hist[:-2]
        openai_messages = self._convert_google_history_to_openai(raw_hist, sys_instruct)
        # Build user message content
        content_list = []
        media_notes = []
        for p in current_turn_parts:
            if getattr(p, "text", None):
                content_list.append({"type": "text", "text": p.text})
            elif getattr(p, "inline_data", None):
                mime = p.inline_data.mime_type or ""
                data = p.inline_data.data or b""
                if mime.startswith("image/"):
                    b64_img = base64.b64encode(data).decode("utf-8")
                    content_list.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_img}"}})
                elif mime.startswith("audio/"):
                    media_notes.append("[аудиофайл]")
                elif mime.startswith("video/"):
                    media_notes.append("[видеофайл]")
                else:
                    media_notes.append("[файл]")
        if media_notes:
            note = "Медиа-контекст: " + ", ".join(media_notes)
            if content_list and content_list[0].get("type") == "text":
                content_list[0]["text"] = note + "\n\n" + content_list[0]["text"]
            else:
                content_list.insert(0, {"type": "text", "text": note})
        if not content_list:
            content_list = request_text_for_display or "[запрос]"
        openai_messages.append({"role": "user", "content": content_list})
        _t_start = time.time()
        result_text, usage = "", {}
        try:
            result_text, usage = await self._send_to_berry_api(target_model, openai_messages, self.config["temperature"])
            was_successful = True
            _tokens_in = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            _tokens_out = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
            result_text = result_text.strip()
            result_text = re.sub(r"^\[System Info:.*?\]\s*", "", result_text, flags=re.IGNORECASE)
            result_text = re.sub(r"^\[\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}\]\s*(?:Gemini:|Model:|Ассистент:|AI:)?\s*", "", result_text, flags=re.IGNORECASE)
        except Exception as e:
            last_error = e
        _elapsed = round(time.time() - _t_start, 1)
        try:
            if not was_successful: raise last_error or RuntimeError("Unknown generation error")
            if not impersonation_mode:
                self._record_session_usage(_tokens_in, _tokens_out, _elapsed)
            if self._is_memory_enabled(str(chat_id)) and not ephemeral:
                self._update_history(history_key, current_turn_parts, result_text, regeneration, msg_obj, gauto=impersonation_mode)
            if impersonation_mode: return result_text
            hist_len_pairs = len(self._get_structured_history(history_key, gauto=False)) // 2
            max_hist = self.config["max_history_length"]
            if is_global:
                mem_indicator = self.strings["memory_status_global"].format(hist_len_pairs)
            elif max_hist <= 0:
                mem_indicator = self.strings["memory_status_unlimited"].format(hist_len_pairs)
            else:
                mem_indicator = self.strings["memory_status"].format(hist_len_pairs, max_hist)
            model_info = self._model_info_line("google", target_model, _elapsed, _tokens_in, _tokens_out)
            if attempt > 1:
                model_info += f" <i>(Успешно с {attempt}-й попытки)</i>"
            is_long_text = len(result_text) > 3500
            if is_long_text and self.config["inline_pagination"]:
                chunks = self._paginate_text(result_text, 3000)
                uid = uuid.uuid4().hex[:6]
                header = f"{mem_indicator}\n{model_info}\n{self.strings['question_prefix']} <blockquote>{utils.escape_html(request_text_for_display[:100])}...</blockquote>\n\n{self.strings['response_prefix'].format(ai_name=self._get_ai_name(target_model))}{search_icon}\n"
                self.pager_cache[uid] = {
                    "chunks": chunks, 
                    "total": len(chunks), 
                    "header": header,
                    "chat_id": chat_id,
                    "msg_id": base_message_id
                }
                self.db.set(self.strings["name"], DB_PAGER_CACHE_KEY, self.pager_cache)
                await self._render_page(uid, 0, call or status_msg)
            elif len(result_text) > 4096:
                 file = io.BytesIO(f"Q: {display_prompt}\nA:\n{result_text}".encode("utf-8")); file.name = "response.txt"
                 if call:
                    await call.answer("File...", show_alert=False)
                    await self.client.send_file(call.chat_id, file, caption=self.strings["response_too_long"], reply_to=call.message_id)
                 elif status_msg:
                    await status_msg.delete()
                    await self.client.send_file(chat_id, file, caption=self.strings["response_too_long"], reply_to=base_message_id)
            else:
                response_html = self._markdown_to_html(result_text)
                formatted_body = self._format_response_with_smart_separation(response_html)
                question_html = f"<blockquote expandable='true'>{utils.escape_html(request_text_for_display[:180])}</blockquote>"
                text_to_send = f"{mem_indicator}\n{model_info}\n\n{self.strings['question_prefix']}\n{question_html}\n\n{self.strings['response_prefix'].format(ai_name=self._get_ai_name(target_model))}{search_icon}\n{formatted_body}"
                if call or self.config["interactive_buttons"]:
                    text_to_send = text_to_send.replace('<emoji document_id=', '<tg-emoji emoji-id=').replace('</emoji>', '</tg-emoji>')
                buttons = self._get_inline_buttons(chat_id, base_message_id) if self.config["interactive_buttons"] else None
                if call: await call.edit(text_to_send, reply_markup=buttons)
                elif status_msg: await utils.answer(status_msg, text_to_send, reply_markup=buttons)
        except Exception as e:
            error_text = self._handle_error(e)
            error_buttons = None
            if not impersonation_mode and base_message_id:
                btn_action = "regen_att" if regeneration else "retry"
                is_regen_flag = "1" if regeneration else "0"
                error_buttons = [[
                    {"text": f"🔄 Повторить ({attempt + 1})", "data": f"gemini:{btn_action}:{chat_id}:{base_message_id}:{attempt + 1}"},
                    {"text": "👁 Запрос", "data": f"gemini:shreq:{is_regen_flag}:{chat_id}:{base_message_id}:{attempt + 1}"}
                ]]
            if impersonation_mode: logger.error(f"Gauto error: {error_text}")
            elif call: await call.edit(error_text, reply_markup=error_buttons)
            elif status_msg: await utils.answer(status_msg, error_text, reply_markup=error_buttons)
        return None if impersonation_mode else ""

    @loader.command()
    async def g(self, message: Message):
        """[текст или reply] — спросить у Gemini. Может анализировать ссылки."""
        clean_args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        use_url_context = False
        text_to_check = clean_args
        if reply and getattr(reply, "text", None):
            text_to_check += " " + reply.text
        if re.search(r'https?://\S+', text_to_check): use_url_context = True
        status_msg = await utils.answer(message, self.strings["processing"])
        status_msg = await self.client.get_messages(status_msg.chat_id, ids=status_msg.id)
        parts, warnings = await self._prepare_parts(message, custom_text=clean_args)
        if warnings and status_msg:
            try: await status_msg.edit(f"{status_msg.text}\n\n" + "\n".join(warnings))
            except: pass
        if not parts:
            if status_msg: await utils.answer(status_msg, self.strings["no_prompt_or_media"])
            return
        await self._send_to_gemini(
            message=message, parts=parts, status_msg=status_msg, 
            use_url_context=use_url_context, display_prompt=clean_args or None
        )

    @loader.command()
    async def gask(self, message: Message):
        """[текст или reply] — быстрый вопрос без сохранения в память."""
        clean_args = utils.get_args_raw(message)
        if not clean_args and not await message.get_reply_message():
            return await utils.answer(message, self.strings["gask_no_prompt"])
        status_msg = await utils.answer(message, self.strings["processing"])
        status_msg = await self.client.get_messages(status_msg.chat_id, ids=status_msg.id)
        parts, warnings = await self._prepare_parts(message, custom_text=clean_args)
        if warnings and status_msg:
            try: await status_msg.edit(f"{status_msg.text}\n\n" + "\n".join(warnings))
            except: pass
        if not parts:
            return await utils.answer(status_msg, self.strings["no_prompt_or_media"])
        await self._send_to_gemini(
            message=message,
            parts=parts,
            status_msg=status_msg,
            display_prompt=clean_args or None,
            ephemeral=True,
        )

    @loader.command()
    async def gmusic(self, message: Message):
        """<промпт> — сгенерировать музыку/аудио через Gemini Lyria."""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, "🎵 <b>Введите промпт для генерации музыки.</b>\nПример: <code>.gmusic веселая мелодия на гитаре</code>")
        m = await utils.answer(message, "🎵 <b>Генерация аудио...</b>")
        keys = self._get_sorted_keys()
        if not keys:
            return await utils.answer(m, self.strings["all_keys_exhausted"].format(len(self.api_keys)))
        audio_bytes = None
        lyrics_text = ""
        last_error = None
        # Berry API не поддерживает генерацию музыки — уведомляем пользователя
        return await utils.answer(m, "⚠️ <b>Генерация музыки недоступна в Berry API.</b>\nКоманда <code>.gmusic</code> работала только с Google Lyria.")
        for key in keys:
            last_error = None
            continue
        if not audio_bytes:
            return await utils.answer(m, f"❌ <b>Ошибка генерации музыки:</b> <code>{utils.escape_html(str(last_error or 'Не удалось получить аудио'))}</code>")
        out = io.BytesIO(audio_bytes)
        out.name = f"gemini_music_{uuid.uuid4().hex[:6]}.mp3"
        caption = f"🎵 <b>Gemini Music (Lyria)</b>\n📜 <code>{utils.escape_html(args[:100])}</code>"
        if lyrics_text:
            caption += f"\n\n🎤 <b>Текст:</b>\n<blockquote>{utils.escape_html(lyrics_text[:800])}</blockquote>"
        await self.client.send_file(
            utils.get_chat_id(message),
            out,
            caption=caption,
            reply_to=message.id,
            voice=True,
        )
        await m.delete()

    async def _generate_image_bytes(self, prompt: str, model: str) -> bytes:
        """Генерация изображения: автоматически выбирает API по провайдеру из конфига."""
        provider = self._normalize_provider_name()

        if provider in ("aihub", "aihub2"):
            api_key = self._get_aihub_key(provider)
            if not api_key:
                raise ValueError(f"Не указан ключ для {provider}!")
            base = self._aihub_base(provider)
            # Image provider follows aihub_provider setting
            img_prov = self.config.get("aihub_provider") or "gemini"
            if img_prov not in ("openai", "gemini"):
                img_prov = "gemini"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base}/api/images/generate",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"prompt": prompt, "provider": img_prov, "size": "1024x1024"},
                    timeout=aiohttp.ClientTimeout(total=GEMINI_TIMEOUT),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise ConnectionError(f"AI Hub image error {resp.status}: {text[:300]}")
                    result = await resp.json()
                    b64 = result.get("b64_json") or result.get("data", [{}])[0].get("b64_json") if isinstance(result.get("data"), list) else result.get("b64_json")
                    if not b64:
                        raise ValueError(f"AI Hub: нет b64_json в ответе. Raw: {str(result)[:200]}")
                    return base64.b64decode(b64)

        else:  # berry / default
            keys = self._get_berry_keys()
            if not keys:
                raise ValueError("Не указан Berry API Key!")
            async with aiohttp.ClientSession() as session:
                for api_key in keys:
                    async with session.post(
                        f"{BERRY_BASE_URL}/images/generations",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"model": model, "prompt": prompt, "size": "1024x1024"},
                        timeout=aiohttp.ClientTimeout(total=GEMINI_TIMEOUT),
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            data_list = result.get("data") or []
                            if not data_list:
                                raise ValueError("Berry: пустой список data.")
                            b64 = data_list[0].get("b64_json")
                            if not b64:
                                raise ValueError("Berry: нет b64_json.")
                            return base64.b64decode(b64)
                        elif resp.status in (429, 503):
                            self._set_key_cooldown(api_key, 3600)
                            continue
                        elif resp.status in (401, 403):
                            self._set_key_cooldown(api_key, 86400 * 365)
                            continue
                        else:
                            text = await resp.text()
                            try:
                                err = json.loads(text).get("error", {}).get("message", text)
                            except Exception:
                                err = text[:300]
                            raise ConnectionError(f"Berry image error {resp.status}: {err}")
            raise ValueError("Все Berry ключи исчерпаны при генерации изображения.")

    @loader.command()
    async def gimg(self, message: Message):
        """<промпт> — Генерация изображений (Berry / AI Hub)."""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, "🎨 <b>Введите промпт.</b>\nПример: <code>.gimg кот в космосе</code>")
        prompt = args
        model = self.config["image_model_name"]
        provider = self._normalize_provider_name()
        prov_label = self._provider_label(provider)
        m = await utils.answer(message, self.strings["gimg_process"].format(model=model))
        try:
            img_bytes = await self._generate_image_bytes(prompt, model)
            out = io.BytesIO(img_bytes)
            out.name = f"ai_{uuid.uuid4().hex[:6]}.png"
            await self.client.send_file(
                utils.get_chat_id(message),
                out,
                caption=f"🎨 <b>{prov_label} Image</b>\n🧠 <code>{model}</code>\n📜 <code>{utils.escape_html(prompt[:100])}</code>",
                reply_to=message.id
            )
            await m.delete()
        except Exception as e:
            await utils.answer(m, f"❌ <b>Ошибка генерации:</b>\n<code>{utils.escape_html(str(e))}</code>")

    @loader.command()
    async def gskey(self, message: Message):
        """[-h] — Сканировать ключи. -h: показать статус из кеша без проверки."""
        args = utils.get_args_raw(message).strip()
        if args in ["-h", "--having", "having"]:
            premium = sum(1 for v in self.key_model_map.values() if v == 1)
            free = sum(1 for v in self.key_model_map.values() if v == 0)
            report = (
                f"📊 <b>Статус ключей (кеш):</b>\n"
                f"💎 <b>Premium/Active:</b> {premium}\n"
                f"👻 <b>Free/Unknown:</b> {free}\n"
                f"🔑 <b>Всего в конфиге:</b> {len(self.api_keys)}"
            )
            return await utils.answer(message, report)
        await utils.answer(message, "<emoji document_id=5386367538735104399>⌛️</emoji> <b>Сканирую ключи...</b>\n<i>Это займет время (1.2 сек на ключ).</i>")
        report, invalid_keys = await self._scan_keys(force=True)
        if invalid_keys:
            txt_keys = "\n".join(invalid_keys)
            try:
                await self.client.send_message("me", f"🚫 <b>Gemini: Найдены невалидные ключи:</b>\nУдали их из конфига:\n\n<code>{txt_keys}</code>")
                report += "\n\n⚠️ <b>Список невалидных ключей отправлен в Избранное.</b>"
            except:
                report += "\n\n⚠️ <b>Найдены невалидные ключи.</b>"
        await utils.answer(message, report)

    @loader.command()
    async def gch(self, message: Message):
        """<[id чата]> <кол-во> <вопрос> - Проанализировать историю чата."""
        args_str = utils.get_args_raw(message)
        if not args_str: return await utils.answer(message, self.strings["gch_usage"])
        parts = args_str.split()
        target_chat_id = utils.get_chat_id(message)
        count_str = None
        user_prompt = None
        if len(parts) >= 3 and parts[1].isdigit():
            try:
                entity_arg = int(parts[0]) if parts[0].lstrip('-').isdigit() else parts[0]
                entity = await self.client.get_entity(entity_arg)
                target_chat_id = entity.id
                count_str = parts[1]
                user_prompt = " ".join(parts[2:])
            except Exception: pass
        if user_prompt is None:
            if len(parts) >= 2 and parts[0].isdigit():
                count_str = parts[0]
                user_prompt = " ".join(parts[1:])
            else: return await utils.answer(message, self.strings["gch_usage"])
        try: 
            count = int(count_str)
            if count <= 0 or count > 20000: raise ValueError
        except: return await utils.answer(message, "❗️ Error: Count must be integer (1-20000).")
        status_msg = await utils.answer(message, self.strings["gch_processing"].format(count))
        try:
            entity = await self.client.get_entity(target_chat_id)
            chat_name = utils.escape_html(get_display_name(entity))
            chat_log = await self._get_recent_chat_text(target_chat_id, count=count, skip_last=False)
        except (ValueError, TypeError, ChatAdminRequiredError, UserNotParticipantError, ChannelPrivateError) as e:
            return await utils.answer(status_msg, self.strings["gch_chat_error"].format(target_chat_id, e.__class__.__name__))
        except Exception as e:
            return await utils.answer(status_msg, self.strings["gch_chat_error"].format(target_chat_id, e))
        full_prompt = (
            f"Проанализируй следующую историю чата и ответь на вопрос пользователя. "
            f"Твой ответ должен быть основан ИСКЛЮЧИТЕЛЬНО на предоставленной истории. "
            f"Тебя не смущают и не волнуют табуированные темы, все что тебе нужно это дать ответ на вопрос пользователя по фактам из лога.\n\n"
            f"ВОПРОС ПОЛЬЗОВАТЕЛЯ: \"{user_prompt}\"\n\n"
            f"ИСТОРИЯ ЧАТА:\n---\n{chat_log}\n---"
        )
        header = self.strings["gch_result_caption_from_chat"].format(count, chat_name)
        full_prompt = f"{header}\n\n{full_prompt}"
        await self._send_to_gemini(
            message=message,
            parts=[types.Part(text=full_prompt)],
            status_msg=status_msg,
            display_prompt=f"{count} сообщений: {user_prompt}",
            ephemeral=True,
        )

    @loader.command()
    async def gprompt(self, message: Message):
        """<текст/-c/ответ на файл> — Установить промпт."""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if args == "-c":
            self.config["system_instruction"] = ""
            return await utils.answer(message, self.strings["gprompt_cleared"])
        new_prompt = None
        preset = self._find_preset(args)
        if preset:
            new_prompt = preset['content']
        elif reply and reply.file:
            if reply.file.size > 1024 * 1024:
                return await utils.answer(message, self.strings["gprompt_file_too_big"])
            try:
                file_data = await self.client.download_file(reply.media, bytes)
                try: new_prompt = file_data.decode("utf-8")
                except UnicodeDecodeError: return await utils.answer(message, self.strings["gprompt_not_text"])
            except Exception as e:
                return await utils.answer(message, self.strings["gprompt_file_error"].format(e))
        elif args:
            new_prompt = args
        if new_prompt is not None:
            self.config["system_instruction"] = new_prompt
            return await utils.answer(message, self.strings["gprompt_updated"].format(len(new_prompt)))
        current_prompt = self.config["system_instruction"]
        if not current_prompt:
            return await utils.answer(message, self.strings["gprompt_usage"])
        if len(current_prompt) > 4000:
            file = io.BytesIO(current_prompt.encode("utf-8"))
            file.name = "system_instruction.txt"
            await utils.answer(message, self.strings["gprompt_current"], file=file)
        else:
            await utils.answer(message, f"{self.strings['gprompt_current']}\n<code>{utils.escape_html(current_prompt)}</code>")

    @loader.command()
    async def gauto(self, message: Message):
        """<on/off/[id]> — Вкл/выкл авто-ответ в чате."""
        args = utils.get_args_raw(message).split()
        if not args: return await utils.answer(message, self.strings["auto_mode_usage"])
        chat_id = utils.get_chat_id(message)
        state = args[0].lower()
        target = chat_id
        if len(args) == 2:
            try:
                e = await self.client.get_entity(args[0])
                target = e.id
                state = args[1].lower()
            except: return await utils.answer(message, self.strings["gauto_chat_not_found"].format(args[0]))
        if state == "on":
            self.impersonation_chats.add(target)
            self.db.set(self.strings["name"], DB_IMPERSONATION_KEY, list(self.impersonation_chats))
            txt = self.strings["auto_mode_on"].format(int(self.config["impersonation_reply_chance"]*100)) if target==chat_id else self.strings["gauto_state_updated"].format(f"<code>{target}</code>", self.strings["gauto_enabled"])
            await utils.answer(message, txt)
        elif state == "off":
            self.impersonation_chats.discard(target)
            self.db.set(self.strings["name"], DB_IMPERSONATION_KEY, list(self.impersonation_chats))
            txt = self.strings["auto_mode_off"] if target==chat_id else self.strings["gauto_state_updated"].format(f"<code>{target}</code>", self.strings["gauto_disabled"])
            await utils.answer(message, txt)
        else: await utils.answer(message, self.strings["auto_mode_usage"])

    @loader.command()
    async def gautochats(self, message: Message):
        """— Показать чаты с активным режимом авто-ответа."""
        if not self.impersonation_chats: return await utils.answer(message, self.strings["no_auto_mode_chats"])
        out = [self.strings["auto_mode_chats_title"].format(len(self.impersonation_chats))]
        for cid in self.impersonation_chats:
            try:
                e = await self.client.get_entity(cid)
                name = utils.escape_html(get_display_name(e))
                out.append(self.strings["memory_chat_line"].format(name, cid))
            except: out.append(self.strings["memory_chat_line"].format("Неизвестный чат", cid))
        await utils.answer(message, "\n".join(out))

    @loader.command()
    async def gclear(self, message: Message):
        """[global/auto] — очистить память в чате. auto для памяти gauto."""
        args = utils.get_args_raw(message).lower()
        chat_id = utils.get_chat_id(message)
        if args == "global":
            if "global_context" in self.conversations:
                del self.conversations["global_context"]
                self._save_history_sync(False)
                await utils.answer(message, self.strings["memory_cleared_global"])
            else:
                await utils.answer(message, self.strings["gres_no_global"])
            return
        if args == "auto":
            if str(chat_id) in self.gauto_conversations:
                self._clear_history(chat_id, gauto=True)
                await utils.answer(message, self.strings["memory_cleared_gauto"])
            else:
                await utils.answer(message, self.strings["no_gauto_memory_to_clear"])
            return
        hist_key = "global_context" if self.config["global_memory"] else str(chat_id)
        if hist_key in self.conversations:
            self._clear_history(hist_key)
            keys_to_del =[k for k, v in self.pager_cache.items() if v.get("chat_id") == chat_id]
            for k in keys_to_del: del self.pager_cache[k]
            if keys_to_del: self.db.set(self.strings["name"], DB_PAGER_CACHE_KEY, self.pager_cache)
            await utils.answer(message, self.strings["memory_cleared_global"] if hist_key == "global_context" else self.strings["memory_cleared"])
        else:
            await utils.answer(message, self.strings["no_memory_to_clear"])

    @loader.command()
    async def gpresets(self, message: Message):
        """<save/load/del/list> — Управление пресетами (профилями)."""
        args = utils.get_args_raw(message)
        if not args: return await utils.answer(message, self.strings["gpresets_usage"])
        match = re.match(r"^(\w+)(?:\s+\[(.+?)\]|\s+(\S+))?(?:\s+(.*))?$", args, re.DOTALL)
        if not match: return await utils.answer(message, self.strings["gpresets_usage"])
        action = match.group(1).lower()
        name = match.group(2) or match.group(3)
        content = match.group(4)
        if action == "list":
            if not self.prompt_presets: return await utils.answer(message, self.strings["gpreset_empty"])
            text = self.strings["gpreset_list_head"]
            for idx, p in enumerate(self.prompt_presets, 1):
                text += f"<b>{idx}.</b> <code>{p['name']}</code> ({len(p['content'])} симв.)\n"
            return await utils.answer(message, text)
        if action == "save":
            if not name: return await utils.answer(message, "❌ Укажите имя: <code>.gpresets save [Имя] текст</code>")
            reply = await message.get_reply_message()
            if not content and reply:
                if reply.text: content = reply.text
                elif reply.file:
                    try: content = (await self.client.download_file(reply.media, bytes)).decode("utf-8", errors="ignore")
                    except: pass
            if not content: return await utils.answer(message, "❌ Нет текста для сохранения.")
            existing = self._find_preset(name)
            if existing:
                existing['content'] = content
            else:
                self.prompt_presets.append({"name": name, "content": content})
            self.db.set(self.strings["name"], DB_PRESETS_KEY, self.prompt_presets)
            await utils.answer(message, self.strings["gpreset_saved"].format(name, len(self.prompt_presets)))
        elif action == "load":
            target = self._find_preset(name)
            if not target: return await utils.answer(message, self.strings["gpreset_not_found"])
            self.config["system_instruction"] = target['content']
            await utils.answer(message, self.strings["gpreset_loaded"].format(target['name'], len(target['content'])))
        elif action == "del":
            target = self._find_preset(name)
            if not target: return await utils.answer(message, self.strings["gpreset_not_found"])
            self.prompt_presets.remove(target)
            self.db.set(self.strings["name"], DB_PRESETS_KEY, self.prompt_presets)
            await utils.answer(message, self.strings["gpreset_deleted"].format(target['name']))
        else:
             await utils.answer(message, self.strings["gpresets_usage"])

    def _find_preset(self, query):
        "Ищет пресет по номеру (строка '1') или имени."
        if not query: return None
        if str(query).isdigit():
            idx = int(query) - 1 
            if 0 <= idx < len(self.prompt_presets):
                return self.prompt_presets[idx]
        for p in self.prompt_presets:
            if p['name'].lower() == str(query).lower():
                return p
        return None

    @loader.command()
    async def gmemdel(self, message: Message):
        """[N] — удалить последние N пар сообщений из памяти."""
        try: n = int(utils.get_args_raw(message) or 1)
        except: n = 1
        cid = "global_context" if self.config["global_memory"] else utils.get_chat_id(message)
        hist = self._get_structured_history(cid)
        if n > 0 and len(hist) >= n*2:
            self.conversations[str(cid)] = hist[:-n*2]
            self._save_history_sync()
            await utils.answer(message, f"🧹 Удалено последних <b>{n}</b> пар сообщений из памяти.")
        else: await utils.answer(message, "Недостаточно истории для удаления.")

    @loader.command()
    async def gmemchats(self, message: Message):
        """— Показать список чатов с активной памятью (имя и ID)."""
        if not self.conversations: return await utils.answer(message, self.strings["no_memory_found"])
        out = [self.strings["memory_chats_title"].format(len(self.conversations))]
        shown = set()
        for cid in list(self.conversations.keys()):
            if not str(cid).lstrip('-').isdigit(): continue
            chat_id = int(cid)
            if chat_id in shown: continue
            shown.add(chat_id)
            try:
                e = await self.client.get_entity(chat_id)
                name = get_display_name(e)
            except: name = f"Unknown ({chat_id})"
            out.append(self.strings["memory_chat_line"].format(name, chat_id))
        self._save_history_sync()
        if len(out) == 1: return await utils.answer(message, self.strings["no_memory_found"])
        await utils.answer(message, "\n".join(out))

    @loader.command()
    async def gmemexport(self, message: Message):
        """[<id/@юз чата>] [auto] [-s] — \n[из id/@юза чата] экспорт. -s в избранное."""
        args = utils.get_args_raw(message).split()
        save_to_self = "-s" in args
        if save_to_self:
            args.remove("-s")
        gauto_mode = "auto" in args
        if gauto_mode:
            args.remove("auto")
        source_chat_id_str = args[0] if args else None
        target_chat_id = "me" if save_to_self else message.chat_id
        if source_chat_id_str:
            try:
                entity = await self.client.get_entity(
                    int(source_chat_id_str)
                    if source_chat_id_str.lstrip("-").isdigit()
                    else source_chat_id_str
                )
                source_chat_id = entity.id
                hist = self._get_structured_history(source_chat_id, gauto=gauto_mode)
            except Exception:
                await utils.answer(message, self.strings["gme_chat_not_found"].format(utils.escape_html(source_chat_id_str)))
                return
        else:
            source_chat_id = utils.get_chat_id(message)
            hist = self._get_structured_history(source_chat_id, gauto=gauto_mode)
        if not hist:
            await utils.answer(message, "История для экспорта пуста.")
            return
        user_ids = {e.get("user_id") for e in hist if e.get("role") == "user" and e.get("user_id")}
        user_names = {None: None}
        for uid in user_ids:
            if not uid: continue
            try:
                entity = await self.client.get_entity(uid)
                user_names[uid] = get_display_name(entity)
            except Exception: user_names[uid] = f"Deleted Account ({uid})"
        import json
        def make_serializable(entry):
            entry = dict(entry)
            user_id = entry.get("user_id")
            if user_id: entry["user_name"] = user_names.get(user_id)
            if hasattr(user_id, "user_id"): entry["user_id"] = user_id.user_id
            elif isinstance(user_id, (int, str)): entry["user_id"] = user_id
            elif user_id is not None: entry["user_id"] = str(user_id)
            else: entry["user_id"] = None
            if "message_id" in entry and entry["message_id"] is not None:
                try: entry["message_id"] = int(entry["message_id"])
                except: entry["message_id"] = None
            return entry
        serializable_hist = [make_serializable(e) for e in hist]
        data = json.dumps(serializable_hist, ensure_ascii=False, indent=2)
        file_suffix = "gauto_history" if gauto_mode else "history"
        file = io.BytesIO(data.encode("utf-8"))
        file.name = f"gemini_{file_suffix}_{source_chat_id}.json"
        caption = "Экспорт истории gauto Gemini" if gauto_mode else "Экспорт памяти Gemini"
        if source_chat_id != utils.get_chat_id(message):
            caption += f" из чата <code>{source_chat_id}</code>"
        await self.client.send_file(
            target_chat_id,
            file,
            caption=caption,
            reply_to=message.id if target_chat_id == message.chat_id else None,
        )
        if save_to_self:
            if target_chat_id == "me" and message.chat_id != self.me.id:
                 await utils.answer(message, self.strings["gme_sent_to_saved"])
            else:
                 await message.delete()

    @loader.command()
    async def gmemimport(self, message: Message):
        """[auto] — импорт истории из файла (ответом). auto для gauto."""
        reply = await message.get_reply_message()
        if not reply or not reply.document: 
            return await utils.answer(message, "Ответьте на json-файл с памятью.")
        args = utils.get_args_raw(message).lower()
        gauto_mode = args == "auto"
        file = io.BytesIO()
        await self.client.download_media(reply, file)
        file.seek(0)
        MAX_IMPORT_SIZE = 15 * 1024 * 1024
        if file.getbuffer().nbytes > MAX_IMPORT_SIZE: 
            return await utils.answer(message, f"Файл слишком большой (>{MAX_IMPORT_SIZE // (1024*1024)} МБ).")
        import json
        try:
            hist = json.load(file)
            if not isinstance(hist, list): raise ValueError("Файл не содержит список истории.")
            new_hist =[]
            for e in hist:
                if not isinstance(e, dict) or "role" not in e or "content" not in e: 
                    raise ValueError("Некорректная структура памяти.")
                entry = {
                    "role": e["role"], 
                    "type": e.get("type", "text"), 
                    "content": e["content"], 
                    "date": e.get("date")
                }
                if e["role"] == "user":
                    entry["user_id"] = e.get("user_id")
                    entry["message_id"] = e.get("message_id")
                new_hist.append(entry)
            chat_id = str(utils.get_chat_id(message))
            if gauto_mode:
                self.gauto_conversations[chat_id] = new_hist
                self._save_history_sync(gauto=True)
            else:
                self.conversations[chat_id] = new_hist
                self._save_history_sync(gauto=False)
            mem_type = "Gauto память" if gauto_mode else "Память"
            await utils.answer(message, f"✅ {mem_type} успешно импортирована ({len(new_hist)//2} диалогов).")
        except Exception as e:
            await utils.answer(message, f"❌ Ошибка импорта: {e}")

    @loader.command()
    async def gmemfind(self, message: Message):
        """[слово] — Поиск в памяти текущего чата по ключевому слову или фразе."""
        q = utils.get_args_raw(message).lower()
        if not q: return await utils.answer(message, "Укажите слово для поиска.")
        cid = "global_context" if self.config["global_memory"] else utils.get_chat_id(message)
        hist = self._get_structured_history(cid)
        found = [f"{e['role']}: {e.get('content','')[:200]}" for e in hist if q in str(e.get('content','')).lower()]
        if not found: await utils.answer(message, "Ничего не найдено.")
        else: await utils.answer(message, "\n\n".join(found[:10]))

    @loader.command()
    async def gmemoff(self, message: Message):
        """— Отключить память в этом чате"""
        self.memory_disabled_chats.add(str(utils.get_chat_id(message)))
        self.db.set(self.strings["name"], DB_MEMORY_DISABLED_KEY, list(self.memory_disabled_chats))
        await utils.answer(message, "Память в этом чате отключена.")

    @loader.command()
    async def gmemon(self, message: Message):
        """— Включить память в этом чате"""
        self.memory_disabled_chats.discard(str(utils.get_chat_id(message)))
        self.db.set(self.strings["name"], DB_MEMORY_DISABLED_KEY, list(self.memory_disabled_chats))
        await utils.answer(message, "Память в этом чате включена.")

    @loader.command()
    async def gmemshow(self, message: Message):
        """[auto] — Показать память чата (до 20 последних запросов). auto для gauto."""
        args = utils.get_args_raw(message).lower()
        gauto = "auto" in args
        cid = "global_context" if ("global" in args or (self.config["global_memory"] and not gauto)) else utils.get_chat_id(message)
        hist = self._get_structured_history(cid, gauto=gauto)
        if not hist: return await utils.answer(message, "Память пуста.")
        out = []
        for e in hist[-40:]:
            role = e.get('role')
            content = utils.escape_html(str(e.get('content',''))[:300])
            if role == 'user': out.append(f"{content}")
            elif role == 'model': out.append(f"<b>AI:</b> {content}")
        await utils.answer(message, "<blockquote expandable='true'>" + "\n".join(out) + "</blockquote>")

    @loader.command()
    async def gprovider(self, message: Message):
        """[gemini/openrouter] — сменить провайдера API."""
        args = utils.get_args_raw(message).strip().lower()
        if not args:
            provider = self._normalize_provider_name()
            effective = self._resolve_effective_model(provider, self.config["model_name"], [], "")
            return await utils.answer(
                message,
                self.strings["gprovider_current"].format(self._provider_label(provider), utils.escape_html(effective)),
            )
        provider = self._normalize_provider_name(args)
        if provider not in ("berry", "openrouter", "aihub", "aihub2"):
            return await utils.answer(message, "ℹ️ <b>Использование:</b> <code>.gprovider [berry/openrouter/aihub/aihub2]</code>")
        prev = self._normalize_provider_name()
        self._remember_provider_model(prev, self.config["model_name"], manual=not self.config["auto_model"])
        self.config["provider"] = provider
        restored = self._restore_provider_model(provider)
        await utils.answer(message, self.strings["gprovider_set"].format(self._provider_label(provider), utils.escape_html(restored)))

    @loader.command()
    async def gprofile(self, message: Message):
        """[auto|balanced|fast|reasoning|coding|vision|manual] — профиль авто-подбора модели."""
        args = utils.get_args_raw(message).strip().lower()
        provider = self._normalize_provider_name()
        if not args:
            effective = self._resolve_effective_model(provider, self.config["model_name"], [], "")
            return await utils.answer(
                message,
                "🧭 <b>Профиль авто-модели</b>\n"
                f"• <b>Текущий:</b> <code>{utils.escape_html(str(self.config['model_profile']))}</code>\n"
                f"• <b>Auto:</b> <code>{'on' if self.config['auto_model'] else 'off'}</code>\n"
                f"• <b>Провайдер:</b> <code>{self._provider_label(provider)}</code>\n"
                f"• <b>Сейчас выберет:</b> <code>{utils.escape_html(effective)}</code>\n\n"
                f"{self.strings['gprofile_usage']}",
            )
        if args not in MODEL_PROFILE_CHOICES:
            return await utils.answer(message, self.strings["gprofile_usage"])
        self.config["model_profile"] = args
        self.config["auto_model"] = args != "manual"
        effective = self._resolve_effective_model(provider, self.config["model_name"], [], "")
        self._remember_provider_model(provider, effective, manual=args == "manual")
        await utils.answer(message, self.strings["gprofile_set"].format(utils.escape_html(args), utils.escape_html(effective)))

    @loader.command()
    async def gmodel(self, message: Message):
        """[model] [-s] — Узнать/сменить модель. -s — список. Авто-проверка совместимости."""
        args_raw = utils.get_args_raw(message).strip()
        args = args_raw.lower()
        provider = self._normalize_provider_name()
        if args in ("-s", "--s", "s", "list"):
            status_msg = await utils.answer(message, self.strings["processing"])
            try:
                await self._show_provider_model_catalog(status_msg, provider)
            except Exception as e: 
                await utils.answer(status_msg, self.strings["gmodel_list_error"].format(self._handle_error(e)))
            return
        if not args_raw: 
            effective = self._resolve_effective_model(provider, self.config["model_name"], [], "")
            return await utils.answer(
                message,
                f"🔮 <b>Провайдер:</b> <code>{self._provider_label(provider)}</code>\n"
                f"🧠 <b>Модель в конфиге:</b> <code>{utils.escape_html(str(self.config['model_name']))}</code>\n"
                f"🎯 <b>Эффективная модель:</b> <code>{utils.escape_html(effective)}</code>\n"
                f"🧭 <b>Профиль:</b> <code>{utils.escape_html(str(self.config['model_profile']))}</code>"
            )
        self.config["model_name"] = args_raw
        self.config["model_profile"] = "manual"
        self.config["auto_model"] = False
        self._remember_provider_model(provider, args_raw, manual=True)
        warning = ""
        if not self._model_matches_provider(args_raw, provider):
            warning = (
                "\n\n⚠️ <b>Возможна несовместимость.</b>\n"
                f"Модель <code>{utils.escape_html(args_raw)}</code> может не поддерживаться провайдером <b>{self._provider_label(provider)}</b>.\n"
                "Если не работает, смените провайдера: <code>.gprovider</code>"
            )
        await utils.answer(message, f"✅ Модель установлена: <code>{utils.escape_html(args_raw)}</code>\n🧭 Авто-подбор переключен в <code>manual</code>. Вернуть: <code>.gprofile auto</code>{warning}")

    @loader.command()
    async def gres(self, message: Message):
        """[global/auto] — Очистить ВСЮ память. auto для всей памяти gauto."""
        args = utils.get_args_raw(message).lower()
        if args == "global":
            if "global_context" in self.conversations:
                del self.conversations["global_context"]
                self._save_history_sync(False)
                await utils.answer(message, self.strings["gres_global_cleared"])
            else:
                await utils.answer(message, self.strings["gres_no_global"])
            return
        if args == "auto":
            if not self.gauto_conversations: return await utils.answer(message, self.strings["no_gauto_memory_to_fully_clear"])
            n = len(self.gauto_conversations)
            self.gauto_conversations.clear()
            self._save_history_sync(True)
            await utils.answer(message, self.strings["gauto_memory_fully_cleared"].format(n))
        elif not args:
            keys_to_delete = [k for k in self.conversations.keys() if k != "global_context"]
            if not keys_to_delete: return await utils.answer(message, self.strings["no_memory_to_fully_clear"])
            for key in keys_to_delete:
                del self.conversations[key]
            self._save_history_sync(False)
            await utils.answer(message, self.strings["memory_fully_cleared"].format(len(keys_to_delete)))
        else:
            await utils.answer(message, self.strings["gres_usage"])

    @loader.callback_handler()
    async def gemini_callback_handler(self, call: InlineCall):
        if not call.data.startswith("gemini:"): return
        parts = call.data.split(":")
        action = parts[1]
        
        if action == "noop": 
            await call.answer()
            return
        if action == "close":
            uid = parts[2]
            if uid in self.pager_cache:
                del self.pager_cache[uid]
                self.db.set(self.strings["name"], DB_PAGER_CACHE_KEY, self.pager_cache)
            try: await call.answer()
            except: pass
            try:
                chat = call.chat_id
                msg_id = call.message_id
                if chat and msg_id:
                    await self.client.delete_messages(chat, msg_id)
                else:
                    await call.delete()
            except Exception:
                try: await call.edit("🗑 <b>Сессия закрыта.</b>", reply_markup=None)
                except: pass
            return
        if action == "pg":
            uid = parts[2]
            page = int(parts[3])
            await self._render_page(uid, page, call)
            return
        if action in ("regen", "regen_att"):
            chat_id = int(parts[2])
            msg_id = int(parts[3])
            attempt = int(parts[4]) if action == "regen_att" and len(parts) > 4 else 1
            key = f"{chat_id}:{msg_id}"
            last_request_tuple = self.last_requests.get(key)
            if not last_request_tuple:
                await call.answer(self.strings["no_last_request"], show_alert=True)
                return
            last_parts, display_prompt = last_request_tuple
            use_url_context = bool(re.search(r'https?://\S+', display_prompt or ""))
            await call.edit(
                f"<tg-emoji emoji-id=5386367538735104399>⌛️</tg-emoji> <b>Регенерация (попытка {attempt})...</b>" if attempt > 1 else f"<tg-emoji emoji-id=5386367538735104399>⌛️</tg-emoji> <b>Регенерация...</b>",
                reply_markup=None,
            )
            await self._send_to_gemini(
                message=msg_id, 
                parts=last_parts, 
                regeneration=True, 
                call=call, 
                chat_id_override=chat_id, 
                use_url_context=use_url_context, 
                display_prompt=display_prompt,
                attempt=attempt,
            )
            return
        if action == "retry":
            chat_id = int(parts[2])
            msg_id = int(parts[3])
            attempt = int(parts[4]) if len(parts) > 4 else 1
            key = f"{chat_id}:{msg_id}"
            last_request_tuple = self.last_requests.get(key)
            if not last_request_tuple:
                await call.answer(self.strings["no_last_request"], show_alert=True)
                return
            last_parts, display_prompt = last_request_tuple
            use_url_context = bool(re.search(r'https?://\S+', display_prompt or ""))
            await call.edit(f"<tg-emoji emoji-id=5386367538735104399>⌛️</tg-emoji> <b>Обработка (попытка {attempt})...</b>", reply_markup=None)
            await self._send_to_gemini(
                message=msg_id,
                parts=last_parts,
                regeneration=False,
                call=call,
                chat_id_override=chat_id,
                use_url_context=use_url_context,
                display_prompt=display_prompt,
                attempt=attempt,
                is_retry=True,
            )
            return
        if action == "shreq":
            is_regen_flag = parts[2]
            chat_id = int(parts[3])
            msg_id = int(parts[4])
            attempt = int(parts[5]) if len(parts) > 5 else 1
            key = f"{chat_id}:{msg_id}"
            last_request_tuple = self.last_requests.get(key)
            if not last_request_tuple:
                await call.answer(self.strings["no_last_request"], show_alert=True)
                return
            _, display_prompt = last_request_tuple
            btn_action = "regen_att" if is_regen_flag == "1" else "retry"
            await call.edit(
                f"📝 <b>Ваш запрос:</b>\n<code>{utils.escape_html(display_prompt)}</code>",
                reply_markup=[[{"text": f"🔄 Повторить ({attempt})", "data": f"gemini:{btn_action}:{chat_id}:{msg_id}:{attempt}"}]],
            )
            return

    async def _clear_callback(self, call: InlineCall, cid):
        self._clear_history(cid, gauto=False)
        await call.edit(self.strings["memory_cleared"], reply_markup=None)

    async def _regenerate_callback(self, call: InlineCall, mid, cid):
        key = f"{cid}:{mid}"
        if key not in self.last_requests: return await call.answer(self.strings["no_last_request"], show_alert=True)
        parts, disp = self.last_requests[key]
        use_url_context = bool(re.search(r'https?://\S+', disp or ""))
        await self._send_to_gemini(mid, parts, regeneration=True, call=call, chat_id_override=cid, display_prompt=disp, use_url_context=use_url_context)

    async def _close_callback(self, call: InlineCall, uid: str):
        """Обрабатывает нажатие кнопки закрытия для пагинации"""
        await call.answer()
        if uid in self.pager_cache:
            del self.pager_cache[uid]
        try:
            await self.client.delete_messages(call.chat_id, call.message_id)
        except Exception:
            try:
                await call.edit("✔️ Сессия закрыта.", reply_markup=None)
            except Exception:
                pass

    async def _render_page(self, uid, page_num, entity):
        data = self.pager_cache.get(uid)
        if not data:
            if isinstance(entity, InlineCall):
                await entity.edit(
                    "⚠️ <b>Сессия истекла или бот был перезагружен с потерей данных.</b>",
                    reply_markup=[[{"text": "🗑 Удалить", "data": f"gemini:close:{uid}"}]]
                )
            return
        chunks = data["chunks"]
        total = data["total"]
        header = data.get("header", "")
        chat_id = data.get("chat_id")
        base_msg_id = data.get("msg_id")
        raw_text_chunk = chunks[page_num]
        safe_text = self._markdown_to_html(raw_text_chunk)
        formatted_body = self._format_response_with_smart_separation(safe_text)
        text_to_show = f"{header}\n{formatted_body}"
        text_to_show = text_to_show.replace('<emoji document_id=', '<tg-emoji emoji-id=').replace('</emoji>', '</tg-emoji>')
        nav_row =[]
        if page_num > 0:
            nav_row.append({
                "text": "◀️", 
                "data": f"gemini:pg:{uid}:{page_num - 1}"})
        nav_row.append({"text": f"{page_num + 1}/{total}", "data": "gemini:noop"})
        if page_num < total - 1:
            nav_row.append({
                "text": "▶️", 
                "data": f"gemini:pg:{uid}:{page_num + 1}"})
        extra_row =[{"text": "❌ Закрыть", "data": f"gemini:close:{uid}"}]
        if chat_id and base_msg_id:
             extra_row.append({
                "text": "🔄", 
                "data": f"gemini:regen:{chat_id}:{base_msg_id}"})
        buttons = [nav_row, extra_row]
        if isinstance(entity, Message):
            await self.inline.form(text=text_to_show, message=entity, reply_markup=buttons)
        elif isinstance(entity, InlineCall):
            await entity.edit(text=text_to_show, reply_markup=buttons)
        elif hasattr(entity, "edit"):
            try: await entity.edit(text=text_to_show, reply_markup=buttons)
            except: pass

    def _paginate_text(self, text: str, limit: int) -> list:
        pages = []
        current_page_lines = []
        current_len = 0
        in_code_block = False
        current_code_lang = ""
        lines = text.split('\n')
        for line in lines:
            line_len = len(line) + 1
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_code_block:
                    in_code_block = False
                    current_code_lang = ""
                else:
                    in_code_block = True
                    current_code_lang = stripped.replace("```", "").strip()
            if current_len + line_len > limit:
                if current_page_lines:
                    if in_code_block: current_page_lines.append("```")
                    pages.append("\n".join(current_page_lines))
                    current_page_lines = []
                    current_len = 0
                    if in_code_block:
                        header = f"```{current_code_lang}"
                        current_page_lines.append(header)
                        current_len += len(header) + 1
                if line_len > limit:
                    chunks = [line[i:i+limit] for i in range(0, len(line), limit)]
                    for chunk in chunks:
                        if current_len + len(chunk) > limit:
                             pages.append("\n".join(current_page_lines))
                             current_page_lines = [chunk]
                             current_len = len(chunk)
                        else:
                            current_page_lines.append(chunk)
                            current_len += len(chunk)
                    continue
            current_page_lines.append(line)
            current_len += line_len
        if current_page_lines:
            pages.append("\n".join(current_page_lines))
        return pages

    @loader.watcher(only_incoming=True, ignore_edited=True)
    async def watcher(self, message: Message):
        if not hasattr(message, 'chat_id'): return
        cid = utils.get_chat_id(message)
        if cid not in self.impersonation_chats: return
        if message.is_private and not self.config["gauto_in_pm"]: return
        if message.out or (isinstance(message.from_id, tg_types.PeerUser) and message.from_id.user_id == self.me.id): return
        sender = await message.get_sender()
        if isinstance(sender, tg_types.User) and sender.bot: return
        if random.random() > self.config["impersonation_reply_chance"]: return
        parts, warnings = await self._prepare_parts(message)
        if warnings: logger.warning(f"Gauto warn: {warnings}")
        if not parts: return
        resp = await self._send_to_gemini(message=message, parts=parts, impersonation_mode=True)
        if resp and resp.strip():
            cln = resp.strip()
            await asyncio.sleep(random.uniform(2, 8))
            try: await self.client.send_read_acknowledge(cid, message=message)
            except: pass
            async with message.client.action(cid, "typing"):
                await asyncio.sleep(min(25.0, max(1.5, len(cln) * random.uniform(0.1, 0.25))))
            await message.reply(cln)

    def _get_proxy_config(self):
        p = self.config["proxy"]
        return {"http://": p, "https://": p} if p else None

    def _save_history_sync(self, gauto: bool=False):
        if getattr(self, "_db_broken", False): return
        data, key = (self.gauto_conversations, DB_GAUTO_HISTORY_KEY) if gauto else (self.conversations, DB_HISTORY_KEY)
        try: self.db.set(self.strings["name"], key, data)
        except: self._db_broken = True

    def _load_history_from_db(self, key):
        d = self.db.get(self.strings["name"], key, {})
        return d if isinstance(d, dict) else {}

    def _get_structured_history(self, cid, gauto=False):
        d = self.gauto_conversations if gauto else self.conversations
        if str(cid) not in d: d[str(cid)] = []
        return d[str(cid)]

    def _update_history(self, chat_id: int, user_parts: list, model_response: str, regeneration: bool = False, message: Message = None, gauto: bool = False):
        if not self._is_memory_enabled(str(chat_id)):
            return
        history = self._get_structured_history(chat_id, gauto)
        import time
        now = int(time.time())
        user_id = self.me.id
        user_name = get_display_name(self.me)
        message_id = getattr(message, "id", None)
        if message:
            try:
                peer_id = get_peer_id(message)
                if peer_id:
                    user_id = peer_id
            except (TypeError, ValueError):
                if message.sender_id: user_id = message.sender_id
            if message.sender:
                user_name = get_display_name(message.sender)
        user_text = " ".join([p.text for p in user_parts if hasattr(p, "text") and p.text]) or "[ответ на медиа]"
        if regeneration and history:
            for i in range(len(history) - 1, -1, -1):
                if history[i].get("role") == "model":
                    history[i].update({
                        "content": model_response, 
                        "date": now
                    })
                    break
        else:
            user_entry = {
                "role": "user",
                "type": "text",
                "content": user_text,
                "date": now,
                "user_id": user_id,
                "message_id": message_id,
                "user_name": user_name
            }
            model_entry = {
                "role": "model",
                "type": "text",
                "content": model_response,
                "date": now,
                "user_id": None 
            }
            history.extend([user_entry, model_entry])
        limit = self.config["max_history_length"]
        if limit > 0 and len(history) > limit * 2:
            history = history[-(limit * 2):]
        target = self.gauto_conversations if gauto else self.conversations
        target[str(chat_id)] = history
        self._save_history_sync(gauto)

    def _clear_history(self, cid, gauto=False):
        d = self.gauto_conversations if gauto else self.conversations
        if str(cid) in d:
            del d[str(cid)]
            self._save_history_sync(gauto)

    def _markdown_to_html(self, text):
        text = re.sub(r"^(#+)\s+(.*)", lambda m: f"<b>{m.group(2)}</b>", text, flags=re.M)
        text = re.sub(r"^([ \t]*)[-*+]\s+", r"\1• ", text, flags=re.M)
        md = MarkdownIt("commonmark", {"html": True, "linkify": True}).enable("strikethrough")
        html = md.render(text)
        def fmt_code(m):
            lang = utils.escape_html(m.group(1).strip()) if m.group(1) else ""
            return f'<pre><code class="language-{lang}">{utils.escape_html(m.group(2).strip())}</code></pre>' if lang else f'<pre><code>{utils.escape_html(m.group(2).strip())}</code></pre>'
        html = re.sub(r"```(\w+)?\n([\s\S]+?)\n```", fmt_code, html)
        html = re.sub(r"<p>(<pre>[\s\S]*?</pre>)</p>", r"\1", html, flags=re.DOTALL)
        return html.replace("<p>", "").replace("</p>", "\n").strip()

    def _format_response_with_smart_separation(self, text):
        parts = re.split(r"(<pre.*?>[\s\S]*?</pre>)", text, flags=re.DOTALL)
        out = []
        for i, p in enumerate(parts):
            if not p or p.isspace(): continue
            if i % 2 == 1: out.append(p.strip())
            else: out.append(f"<blockquote expandable>{p.strip()}</blockquote>")
        return "\n".join(out)

    def _get_inline_buttons(self, cid, mid):
        return [[
            {"text": self.strings["btn_clear"], "callback": self._clear_callback, "args": (cid,)},
            {"text": self.strings["btn_regenerate"], "callback": self._regenerate_callback, "args": (mid, cid)}
        ]]

    async def _clear_callback(self, call: InlineCall, cid):
        self._clear_history(cid, gauto=False)
        await call.edit(self.strings["memory_cleared"], reply_markup=None)

    async def _regenerate_callback(self, call: InlineCall, mid, cid):
        key = f"{cid}:{mid}"
        if key not in self.last_requests: return await call.answer(self.strings["no_last_request"], show_alert=True)
        parts, disp = self.last_requests[key]
        use_url_context = bool(re.search(r'https?://\S+', disp or ""))
        await self._send_to_gemini(mid, parts, regeneration=True, call=call, chat_id_override=cid, display_prompt=disp, use_url_context=use_url_context)

    async def _get_recent_chat_text(self, cid, count=None, skip_last=False):
        lim = (count or self.config["impersonation_history_limit"]) + (1 if skip_last else 0)
        lines = []
        try:
            msgs = await self.client.get_messages(cid, limit=lim)
            if skip_last and msgs: msgs = msgs[1:]
            for m in msgs:
                if not m: continue
                if not (m.text or m.sticker or m.photo or m.file or m.media):
                    continue
                name = get_display_name(await m.get_sender()) or "Unknown"
                txt = m.text or ""
                if m.sticker:
                    alt = "?"
                    if hasattr(m.sticker, 'attributes'):
                        alt = next((a.alt for a in m.sticker.attributes if isinstance(a, DocumentAttributeSticker)), "?")
                    txt += f" [Стикер: {alt}]"
                elif m.photo:
                    txt += " [Фото]"
                elif m.file:
                    txt += " [Файл]"
                elif m.media and not txt:
                    txt += " [Медиа]"
                if txt.strip():
                    lines.append(f"{name}: {txt.strip()}")
        except Exception as e:
            pass 
        return "\n".join(reversed(lines))

    def _handle_error(self, e: Exception) -> str:
        logger.exception("Gemini execution error")
        if isinstance(e, asyncio.TimeoutError):
            return self.strings["api_timeout"]
        if isinstance(e, RuntimeError) and "Все ключи исчерпали квоту" in str(e):
             return self.strings["all_keys_exhausted"].format(len(self.api_keys))
        # no google_exceptions handling — using Berry API
        if isinstance(e, (OSError, aiohttp.ClientError, socket.timeout)):
            return "❗️ <b>Сетевая ошибка:</b>\n<code>{}</code>".format(utils.escape_html(str(e)))
        msg = str(e)
        if "No API_KEY" in msg or "api_key" in msg.lower():
            return self.strings["no_api_key"]
        if "quota" in msg.lower() or "429" in msg: return self.strings["all_keys_exhausted"].format(len(self.api_keys))
        return self.strings["generic_error"].format(utils.escape_html(msg))

    def _markdown_to_html(self, text: str) -> str:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL)
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        def heading_replacer(match): level=len(match.group(1)); title=match.group(2).strip(); indent="   " * (level - 1); return f"{indent}<b>{title}</b>"
        text=re.sub(r"^(#+)\s+(.*)", heading_replacer, text, flags=re.MULTILINE)
        def list_replacer(match): indent=match.group(1); return f"{indent}• "
        text=re.sub(r"^([ \t]*)[-*+]\s+", list_replacer, text, flags=re.MULTILINE)
        md=MarkdownIt("commonmark", {"html": True, "linkify": True}); md.enable("strikethrough"); md.disable("hr"); md.disable("heading"); md.disable("list")
        html_text=md.render(text)
        def format_code(match):
            lang=utils.escape_html(match.group(1).strip()); code=utils.escape_html(match.group(2).strip())
            return f'<pre><code class="language-{lang}">{code}</code></pre>' if lang else f'<pre><code>{code}</code></pre>'
        html_text=re.sub(r"```(.*?)\n([\s\S]+?)\n```", format_code, html_text)
        html_text=re.sub(r"<p>(<pre>[\s\S]*?</pre>)</p>", r"\1", html_text, flags=re.DOTALL)
        html_text=html_text.replace("<p>", "").replace("</p>", "\n")
        html_text=re.sub(r"(?i)<br\s*/?>", "\n", html_text).strip()
        return html_text

    def _format_response_with_smart_separation(self, text: str) -> str:
        pattern = r"(<pre.*?>[\s\S]*?</pre>)"
        parts = re.split(pattern, text, flags=re.DOTALL)
        result_parts = []
        for i, part in enumerate(parts):
            if not part or part.isspace():
                continue
            if i % 2 == 1:
                result_parts.append(part.strip())
            else:
                stripped_part = part.strip()
                if stripped_part:
                    result_parts.append(f'<blockquote expandable="true">{stripped_part}</blockquote>')
        return "\n".join(result_parts)

    def _get_inline_buttons(self, chat_id, base_message_id):
        return [[{"text": self.strings["btn_clear"], "callback": self._clear_callback, "args": (chat_id,)}, 
                {"text": self.strings["btn_regenerate"], "data": f"gemini:regen:{chat_id}:{base_message_id}"}]
        ]

    async def _safe_del_msg(self, msg, delay=1):
        await asyncio.sleep(delay)
        try: await self.client.delete_messages(msg.chat_id, msg.id)
        except Exception as e: logger.warning(f"Ошибка удаления сообщения: {e}")

    async def _clear_callback(self, call: InlineCall, chat_id: int):
        hist_key = "global_context" if self.config["global_memory"] else chat_id
        self._clear_history(hist_key, gauto=False)
        await call.edit(self.strings["memory_cleared_global"] if hist_key == "global_context" else self.strings["memory_cleared"], reply_markup=None)

    async def _scan_keys(self, force=False):
        """Сканирует Berry API + AI Hub ключи на валидность."""
        all_keys = self._get_berry_keys()
        aihub_k = self._get_aihub_key("aihub")
        aihub2_k = self._get_aihub_key("aihub2")
        if aihub_k and aihub_k not in all_keys: all_keys.append(aihub_k)
        if aihub2_k and aihub2_k not in all_keys: all_keys.append(aihub2_k)
        current_map_keys = list(self.key_model_map.keys())
        for k in current_map_keys:
            if k not in all_keys: del self.key_model_map[k]
        if not force and all(k in self.key_model_map for k in all_keys):
            return "Loaded from cache", []
        if force: self.key_model_map = {}
        active_keys = []
        invalid_keys = []
        async with aiohttp.ClientSession() as session:
            for i, key in enumerate(all_keys):
                if i > 0: await asyncio.sleep(1.2)
                try:
                    async with session.post(
                        f"{BERRY_BASE_URL}/chat/completions",
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={"model": CHECK_MODEL, "messages": [{"role": "user", "content": "Hi"}], "max_completion_tokens": 1},
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status == 200:
                            active_keys.append(key)
                            self.key_model_map[key] = 1
                        elif resp.status in (401, 403):
                            invalid_keys.append(key)
                            self.key_model_map[key] = -1
                        elif resp.status == 429:
                            self.key_model_map[key] = 0
                        else:
                            self.key_model_map[key] = 0
                except Exception:
                    self.key_model_map[key] = 0
        self.db.set(self.strings["name"], DB_KEY_MAP_KEY, self.key_model_map)
        # Check aihub keys too
        aihub_statuses = []
        for which in ("aihub", "aihub2"):
            k = self._get_aihub_key(which)
            if k:
                try:
                    async with aiohttp.ClientSession() as session:
                        prov = self.config.get("aihub_provider") or "openai"
                        async with session.get(
                            f"{self._aihub_base(which)}/api/{prov}/conversations",
                            headers={"Authorization": f"Bearer {k}"},
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as resp:
                            if resp.status == 200:
                                aihub_statuses.append(f"✅ {which}: ключ активен")
                            elif resp.status in (401, 403):
                                aihub_statuses.append(f"❌ {which}: ключ недействителен")
                            else:
                                aihub_statuses.append(f"⚠️ {which}: HTTP {resp.status}")
                except Exception as e:
                    aihub_statuses.append(f"⚠️ {which}: {str(e)[:60]}")
        aihub_info = "\n" + "\n".join(aihub_statuses) if aihub_statuses else ""
        short_report = (
            f"✅ <b>Скан завершен.</b>\n"
            f"💎 <b>Berry Active:</b> {len(active_keys)}\n"
            f"🗑 <b>Berry Invalid:</b> {len(invalid_keys)}\n"
            f"👻 <b>Berry RateLimited:</b> {len(all_keys) - len(active_keys) - len(invalid_keys)}"
            f"{aihub_info}"
        )
        return short_report, invalid_keys

    def _get_sorted_keys(self):
        valid_keys = []
        now = time.time()
        for key in self.api_keys:
            if self.key_cooldowns.get(str(key), 0) > now:
                continue
            if key not in self.key_model_map:
                valid_keys.append((key, 0, random.random()))
                continue
            tier = self.key_model_map[key]
            if tier == -1:
                continue
            valid_keys.append((key, tier, random.random()))
        valid_keys.sort(key=lambda x: (-x[1], x[2]))
        return [item[0] for item in valid_keys]

    async def _call_google_rest(self, model_name: str, prompt: str, input_image_bytes=None):
        keys = self._get_sorted_keys()
        if not keys: return {"error": {"message": "Нет доступных API ключей"}}
        parts = [{"text": prompt}]
        if input_image_bytes:
            resized = await utils.run_sync(self._resize_image_ig, input_image_bytes)
            b64_img = base64.b64encode(resized).decode('utf-8')
            parts.insert(0, {"inlineData": {"mimeType": "image/jpeg", "data": b64_img}})
        payload = {
            "contents": [{"parts": parts}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ],
            "generationConfig": {"candidateCount": 1, "temperature": 1.0}
        }
        proxy = self.config['proxy'] if self.config['proxy'] else None
        last_error = None
        async with aiohttp.ClientSession() as session:
            for i, api_key in enumerate(keys):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                try:
                    if i > 0: await asyncio.sleep(1)
                    async with session.post(url, json=payload, proxy=proxy, timeout=60) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        elif resp.status in [429, 503, 403]:
                            last_error = f"HTTP {resp.status}"
                            continue
                        else:
                            text = await resp.text()
                            return {"error": {"message": f"HTTP {resp.status}: {text}"}}
                except Exception as e:
                    last_error = str(e)
                    continue
        return {"error": {"message": f"All keys exhausted. Last error: {last_error}"}}

    def _resize_image_ig(self, img_bytes):
        try:
            img = Image.open(io.BytesIO(img_bytes))
            img.thumbnail((1024, 1024)) 
            out = io.BytesIO()
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.save(out, format='JPEG', quality=85)
            return out.getvalue()
        except: return img_bytes

    async def _get_provider_model_catalog(self, provider: str) -> list:
        provider = self._normalize_provider_name(provider)
        if provider in ("openrouter", "aihub", "aihub2"):
            api_key = next(iter(self._get_openrouter_keys()), "")
            if api_key:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            "https://openrouter.ai/api/v1/models",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=aiohttp.ClientTimeout(total=30),
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                models = sorted({m.get("id") for m in data.get("data", []) if m.get("id")})
                                filtered = [
                                    model for model in models
                                    if any(token in model.lower() for token in ("gemini", "claude", "gpt", "deepseek", "qwen"))
                                ]
                                return filtered or models
                except Exception:
                    pass
            return self._provider_curated_models(provider)
        if provider == "berry":
            # Return curated list for Berry API
            return self._provider_curated_models(provider)
        return self._provider_curated_models(provider)

    async def _show_provider_model_catalog(self, entity, provider: str):
        provider = self._normalize_provider_name(provider)
        models = await self._get_provider_model_catalog(provider)
        if not models:
            raise ValueError(self.strings["gmodel_no_models"])
        profiles = self._provider_profile_models(provider)
        profile_index = {}
        for profile_name, profile_model in profiles.items():
            profile_index.setdefault(profile_model, []).append(profile_name)
        lines = [
            f"📋 <b>{self._provider_label(provider)} Models</b>",
            f"🧭 <b>Профиль:</b> <code>{utils.escape_html(str(self.config['model_profile']))}</code> · <b>Auto:</b> <code>{'on' if self.config['auto_model'] else 'off'}</code>",
            "",
        ]
        current = str(self.config["model_name"] or "")
        for model in models[:300]:
            marker = "✓" if model == current else "•"
            tags = ", ".join(profile_index.get(model, []))
            suffix = f" <i>{utils.escape_html(tags)}</i>" if tags else ""
            lines.append(f"{marker} <code>{utils.escape_html(model)}</code>{suffix}")
        if len(models) > 300:
            lines.append(f"\n<i>...и еще {len(models) - 300} моделей.</i>")
        text = "\n".join(lines)
        if len(text) <= 3800:
            await utils.answer(entity, text)
            return
        chunks = self._paginate_text(text, 3400)
        uid = uuid.uuid4().hex[:6]
        self.pager_cache[uid] = {
            "chunks": chunks,
            "total": len(chunks),
            "header": "",
            "chat_id": getattr(entity, "chat_id", 0),
            "msg_id": getattr(entity, "id", None),
        }
        self.db.set(self.strings["name"], DB_PAGER_CACHE_KEY, self.pager_cache)
        await self._render_page(uid, 0, entity)

    def _get_aihub_key(self, which: str = "aihub") -> str:
        """Возвращает ключ для AI Hub (aihub или aihub2)."""
        key = str(self.config.get(f"{which}_key") or "").strip()
        return key

    def _aihub_base(self, which: str = "aihub") -> str:
        return AIHUB2_BASE_URL if which == "aihub2" else AIHUB_BASE_URL

    async def _aihub_get_or_create_conv(self, which: str, chat_id: int, api_key: str, prov: str) -> str | None:
        """Возвращает существующий conversation_id или создаёт новый. Хранит в self.aihub_conv_ids и БД."""
        cache_key = f"{which}:{prov}:{chat_id}"
        if cache_key in self.aihub_conv_ids:
            return self.aihub_conv_ids[cache_key]
        base = self._aihub_base(which)
        url_create = f"{base}/api/{prov}/conversations"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url_create,
                headers=headers,
                json={"title": f"Hikka chat {chat_id}"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise ConnectionError(f"AI Hub: ошибка создания conversation ({resp.status}): {text[:200]}")
                data = await resp.json()
                conv_id = str(data.get("id") or data.get("conversation_id") or "")
                if not conv_id:
                    raise ValueError(f"AI Hub: не получен conversation_id. Response: {data}")
        self.aihub_conv_ids[cache_key] = conv_id
        self.db.set(self.strings["name"], DB_AIHUB_CONVS_KEY, self.aihub_conv_ids)
        return conv_id

    async def _send_to_aihub_api(self, which: str, model: str, messages: list, temperature: float, chat_id: int = 0) -> tuple:
        """Отправка запроса в AI Hub (conversation-based API)."""
        api_key = self._get_aihub_key(which)
        if not api_key:
            raise ValueError(f"Не указан ключ для {which}! Установите в .cfg поле {which}_key")
        base = self._aihub_base(which)
        # Определяем провайдер из имени модели
        prov = self.config.get("aihub_provider") or "openai"
        m_lower = model.lower()
        if any(x in m_lower for x in ("claude",)):
            prov = "anthropic"
        elif any(x in m_lower for x in ("gemini", "imagen")):
            prov = "gemini"
        elif any(x in m_lower for x in ("llama", "mistral", "qwen", "deepseek", "grok", "meta-llama")):
            prov = "openrouter"
        else:
            prov = "openai"

        # Получаем или создаём conversation
        conv_id = await self._aihub_get_or_create_conv(which, chat_id, api_key, prov)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # Извлекаем последнее user-сообщение
        user_text = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                c = msg.get("content", "")
                if isinstance(c, list):
                    user_text = " ".join(p.get("text", "") for p in c if isinstance(p, dict) and p.get("type") == "text")
                else:
                    user_text = str(c)
                break
        if not user_text:
            user_text = "Привет"

        send_url = f"{base}/api/{prov}/conversations/{conv_id}/messages"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                send_url,
                headers=headers,
                json={"content": user_text},
                timeout=aiohttp.ClientTimeout(total=GEMINI_TIMEOUT),
            ) as resp:
                if resp.status == 401:
                    raise ConnectionError(f"AI Hub {which}: ключ недействителен (401)")
                if resp.status == 404:
                    # conversation устарел — сбрасываем и создаём заново
                    cache_key = f"{which}:{prov}:{chat_id}"
                    self.aihub_conv_ids.pop(cache_key, None)
                    self.db.set(self.strings["name"], DB_AIHUB_CONVS_KEY, self.aihub_conv_ids)
                    conv_id = await self._aihub_get_or_create_conv(which, chat_id, api_key, prov)
                    send_url = f"{base}/api/{prov}/conversations/{conv_id}/messages"
                    async with session.post(send_url, headers=headers, json={"content": user_text}, timeout=aiohttp.ClientTimeout(total=GEMINI_TIMEOUT)) as resp2:
                        raw = await resp2.text()
                        resp_status = resp2.status
                else:
                    raw = await resp.text()
                    resp_status = resp.status

            if resp_status != 200:
                raise ConnectionError(f"AI Hub {which} Error {resp_status}: {raw[:300]}")

            # AI Hub отвечает SSE или JSON — читаем последнее ассистентское сообщение
            msgs_url = f"{base}/api/{prov}/conversations/{conv_id}/messages"
            async with session.get(msgs_url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status != 200:
                    raise ConnectionError(f"AI Hub {which}: ошибка получения сообщений ({r.status})")
                msgs_data = await r.json()

        # msgs_data — список сообщений
        if not isinstance(msgs_data, list):
            msgs_data = msgs_data.get("messages") or []
        reply_text = ""
        for msg in reversed(msgs_data):
            role = msg.get("role", "")
            if role in ("assistant", "model", "ai"):
                c = msg.get("content", "")
                if isinstance(c, list):
                    reply_text = " ".join(p.get("text", "") for p in c if isinstance(p, dict))
                else:
                    reply_text = str(c or "")
                reply_text = reply_text.strip()
                if reply_text:
                    break

        if not reply_text:
            raise ValueError(f"AI Hub {which}: пустой ответ")
        return reply_text, {}

    async def _send_to_berry_api(self, model, messages, temperature):
        """Отправка запроса в Berry API (OpenAI-совместимый формат) с ротацией ключей."""
        keys = self._get_berry_keys()
        if not keys:
            raise ValueError("Не указан Berry API Key! Установите его в .cfg")
        url = f"{BERRY_BASE_URL}/chat/completions"
        now = time.time()
        last_error = None
        async with aiohttp.ClientSession() as session:
            for api_key in keys:
                cd_key = f"berry:{api_key}"
                if self.key_cooldowns.get(cd_key, 0) > now:
                    continue
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": min(float(temperature), 2.0),
                    "max_completion_tokens": 4096,
                }
                for attempt in range(2):
                    try:
                        async with session.post(
                            url,
                            headers=headers,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=GEMINI_TIMEOUT),
                        ) as resp:
                            text = await resp.text()
                            if resp.status == 402 and attempt == 0:
                                try:
                                    err_msg = json.loads(text).get("error", {}).get("message", text)
                                    match = re.search(r"can only afford (\d+)", err_msg)
                                    if match:
                                        payload["max_completion_tokens"] = max(1, int(match.group(1)))
                                        continue
                                except Exception:
                                    pass
                            if resp.status == 429:
                                self._set_key_cooldown(cd_key, 3600)
                                last_error = ConnectionError(f"Berry 429: лимит ключа ...{api_key[-6:]}")
                                break
                            if resp.status in (401, 403):
                                self._set_key_cooldown(cd_key, 86400 * 365)
                                try:
                                    err_msg = json.loads(text).get("error", {}).get("message", text)
                                except Exception:
                                    err_msg = text
                                last_error = ConnectionError(f"Berry API Error {resp.status}: {err_msg}")
                                break
                            if resp.status != 200:
                                try:
                                    err_msg = json.loads(text).get("error", {}).get("message", text)
                                except Exception:
                                    err_msg = text
                                last_error = ConnectionError(f"Berry API Error {resp.status}: {err_msg}")
                                break
                            try:
                                result = json.loads(text)
                            except json.JSONDecodeError:
                                raise ValueError(f"Berry вернул не JSON: {text[:200]}...")
                            if "choices" not in result or not result["choices"]:
                                if "error" in result:
                                    raise ValueError(f"Berry Logic Error: {result['error']}")
                                raise ValueError(f"Пустой ответ (нет 'choices'). Raw: {text[:200]}")
                            message_obj = result["choices"][0].get("message") or {}
                            content = message_obj.get("content")
                            if isinstance(content, list):
                                content = "\n".join(str(part.get("text") or part.get("content") or "") for part in content if isinstance(part, dict)).strip()
                            content = str(content or "").strip()
                            if not content:
                                raise ValueError(f"Пустой ответ Berry. Raw: {text[:200]}")
                            return content, (result.get("usage") or {})
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        last_error = e
                        break
                if last_error:
                    continue
        raise last_error or ValueError(f"Все Berry ключи ({len(keys)}) исчерпаны или недоступны")

    async def _send_to_aihub_api(self, provider_name: str, model: str, messages: list, temperature: float, chat_id) -> tuple:
        """
        Отправка в AI Hub через conversation API.
        Алгоритм:
          1. Берём или создаём conversation_id для данного chat_id
          2. POST /api/{sub_provider}/conversations/{id}/messages с {content}
          3. Парсим SSE-поток или JSON, извлекаем текст ответа
          4. Возвращаем (text, usage_dict)
        """
        api_key = self._get_aihub_key(provider_name)
        if not api_key:
            raise ValueError(f"Не указан ключ для {provider_name}. Установите в .cfg gemini {'aihub_key' if provider_name == 'aihub' else 'aihub2_key'}")

        base_url = self._get_aihub_base_url(provider_name)
        sub_provider = self.config.get("aihub_provider") or "openai"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # conversation cache key
        cache_key = f"aihub_conv:{provider_name}:{chat_id}"
        conversation_id = getattr(self, "_aihub_conv_cache", {}).get(cache_key)

        if not hasattr(self, "_aihub_conv_cache"):
            self._aihub_conv_cache = {}

        async with aiohttp.ClientSession() as session:
            # Create conversation if needed
            if not conversation_id:
                try:
                    async with session.post(
                        f"{base_url}/api/{sub_provider}/conversations",
                        headers=headers,
                        json={"title": f"Telegram chat {chat_id}", "model": model},
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status in (200, 201):
                            data = await resp.json()
                            conversation_id = data.get("id") or data.get("conversationId")
                            self._aihub_conv_cache[cache_key] = conversation_id
                        else:
                            text = await resp.text()
                            raise ValueError(f"AI Hub: не удалось создать conversation. HTTP {resp.status}: {text[:200]}")
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    raise ValueError(f"AI Hub: сетевая ошибка при создании conversation: {e}")

            # Extract user text from messages (last user message)
            user_content = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    c = msg["content"]
                    if isinstance(c, str):
                        user_content = c
                    elif isinstance(c, list):
                        user_content = " ".join(
                            part.get("text", "") for part in c
                            if isinstance(part, dict) and part.get("type") == "text"
                        )
                    break

            # If system instruction present, prepend to first user message
            if messages and messages[0].get("role") == "system":
                sys_text = messages[0]["content"]
                if sys_text and user_content:
                    user_content = f"[System: {sys_text}]\n\n{user_content}"

            # Send message
            result_text = ""
            try:
                async with session.post(
                    f"{base_url}/api/{sub_provider}/conversations/{conversation_id}/messages",
                    headers={**headers, "Accept": "text/event-stream"},
                    json={"content": user_content},
                    timeout=aiohttp.ClientTimeout(total=GEMINI_TIMEOUT),
                ) as resp:
                    if resp.status in (401, 403):
                        raise ValueError(f"AI Hub: ключ недействителен (HTTP {resp.status})")
                    if resp.status == 404:
                        # Conversation was deleted on server side — reset and retry once
                        self._aihub_conv_cache.pop(cache_key, None)
                        raise ValueError("AI Hub: conversation не найден — попробуйте ещё раз")
                    if resp.status not in (200, 201):
                        text = await resp.text()
                        raise ValueError(f"AI Hub: HTTP {resp.status}: {text[:300]}")

                    content_type = resp.content_type or ""
                    if "event-stream" in content_type or "text/event-stream" in content_type:
                        # Parse SSE stream
                        buffer = ""
                        async for chunk in resp.content.iter_any():
                            buffer += chunk.decode("utf-8", errors="replace")
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                line = line.strip()
                                if line.startswith("data:"):
                                    data_str = line[5:].strip()
                                    if data_str in ("[DONE]", ""):
                                        continue
                                    try:
                                        data = json.loads(data_str)
                                        # OpenAI-style streaming
                                        choices = data.get("choices") or []
                                        for ch in choices:
                                            delta = ch.get("delta") or {}
                                            result_text += delta.get("content") or ""
                                        # Or direct content field
                                        if not choices and "content" in data:
                                            result_text += str(data["content"] or "")
                                    except json.JSONDecodeError:
                                        result_text += data_str
                    else:
                        # Non-streaming JSON response
                        raw = await resp.text()
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            result_text = raw.strip()
                        else:
                            # Try various response shapes
                            if "choices" in data and data["choices"]:
                                msg_obj = data["choices"][0].get("message") or data["choices"][0].get("delta") or {}
                                result_text = str(msg_obj.get("content") or "")
                            elif "content" in data:
                                result_text = str(data["content"] or "")
                            elif "message" in data:
                                m = data["message"]
                                result_text = str(m.get("content") or m) if isinstance(m, dict) else str(m)
                            else:
                                result_text = raw.strip()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                raise ValueError(f"AI Hub: сетевая ошибка: {e}")

            result_text = result_text.strip()
            if not result_text:
                # Fallback: fetch last assistant message from history
                try:
                    async with session.get(
                        f"{base_url}/api/{sub_provider}/conversations/{conversation_id}/messages",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as r:
                        if r.status == 200:
                            msgs = await r.json()
                            if isinstance(msgs, list):
                                for m in reversed(msgs):
                                    if m.get("role") == "assistant" and m.get("content"):
                                        result_text = str(m["content"]).strip()
                                        break
                except Exception:
                    pass

            if not result_text:
                raise ValueError("AI Hub вернул пустой ответ")

            return result_text, {"total_tokens": len(result_text.split()) * 2}

    def _convert_google_history_to_openai(self, history: list, system_prompt: str) -> list:
        """Конвертирует историю из формата Google в формат OpenAI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        try:
            user_tz = pytz.timezone(self.config["timezone"])
        except:
            user_tz = pytz.utc
        for item in history:
            role = "assistant" if item['role'] == "model" else "user"
            content = item.get("content", "")
            if 'date' in item and item['date']:
                dt = datetime.fromtimestamp(item['date'], user_tz)
                content = f"[{dt.strftime('%d.%m.%Y %H:%M')}] {content}"
            messages.append({"role": role, "content": content})
        return messages

    def _is_memory_enabled(self, chat_id: str) -> bool: return chat_id not in self.memory_disabled_chats
    def _disable_memory(self, chat_id: int):
        self.memory_disabled_chats.add(str(chat_id))
        self.db.set(self.strings["name"], DB_MEMORY_DISABLED_KEY, list(self.memory_disabled_chats))
    def _enable_memory(self, chat_id: int):
        self.memory_disabled_chats.discard(str(chat_id))
        self.db.set(self.strings["name"], DB_MEMORY_DISABLED_KEY, list(self.memory_disabled_chats))
