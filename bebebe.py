# meta developer: @SKBERRYXXX
# scope: inline
# scope heroku_min: 1.7.2
# requires: aiohttp

"""
AI Hub v4 — полный модуль для Heroku/Hikka.

Возможности:
  • Чаты с AI (OpenAI, Anthropic, Gemini, OpenRouter, кастомный)
  • Отдельные API-ключи для каждого провайдера
  • Бесконечная память с лимитом
  • Анализ фото / видео / стикеров / файлов / GIF из reply
  • Генерация изображений (DALL-E, Gemini)
  • Генерация кода → файл с правильным расширением
  • Создание и запуск скиллов через AI
  • TG Bridge — управление аккаунтом через AI
  • Веб-поиск (через нативные инструменты провайдеров)
  • Красивый вывод: [N/∞] модель | Xс | токены
  • Сворачиваемые цитаты (blockquote expandable)
  • Авто-ответ в чатах
  • Проверка inline-совместимости чата
  • Настройка температуры, max_tokens, персоны, языка ответа
"""

__version__ = (4, 0, 0)

import asyncio
import base64
import io
import json
import re
import time

import aiohttp

from .. import loader, utils
from telethon.tl.custom import Message
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    DocumentAttributeVideo,
    DocumentAttributeAnimated,
    DocumentAttributeSticker,
    Channel,
)

# ─────────────────────────────────────────────────────────────────────────────
#  Константы
# ─────────────────────────────────────────────────────────────────────────────

AIHUB_BASE = "https://attached-assets--brrbrr6.replit.app/api"

BUILTIN_PROVIDERS = ["openai", "anthropic", "gemini", "openrouter"]
ALL_PROVIDERS     = BUILTIN_PROVIDERS + ["custom"]
IMAGE_PROVIDERS   = ["openai", "gemini"]

PROVIDER_ICON = {
    "openai":     "✨",
    "anthropic":  "🔮",
    "gemini":     "💎",
    "openrouter": "🌐",
    "custom":     "🔧",
}

# Премиум эмодзи для интерфейса
PE = {
    "brain":    "🧠",
    "star":     "✨",
    "fire":     "🔥",
    "zap":      "⚡",
    "search":   "🔍",
    "img":      "🖼",
    "key":      "🔑",
    "robot":    "🤖",
    "magic":    "🪄",
    "bridge":   "🌉",
    "check":    "✅",
    "cross":    "❌",
    "gear":     "⚙️",
    "clock":    "⏳",
    "art":      "🎨",
    "code":     "⌨️",
    "trash":    "🗑",
    "back":     "◀️",
    "down":     "📋",
    "prompt":   "📋",
    "temp":     "🌡",
    "tokens":   "🔢",
    "model":    "🤖",
    "wave":     "👋",
    "send":     "📨",
}

PROVIDER_BRAND = {
    "openai":    "OpenAI",
    "anthropic": "Claude",
    "gemini":    "Gemini",
}

# Быстрый выбор моделей по провайдеру
QUICK_MODELS = {
    "openai": [
        "gpt-4o",
        "gpt-4.1",
        "gpt-4o-mini",
        "gpt-5",
        "o3",
        "o4-mini",
    ],
    "anthropic": [
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ],
    "gemini": [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ],
    "openrouter": [
        "meta-llama/llama-3.1-70b-instruct",
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mistral-7b-instruct",
        "mistralai/mixtral-8x22b-instruct",
        "deepseek/deepseek-r1",
        "deepseek/deepseek-chat",
        "x-ai/grok-3",
        "x-ai/grok-3-mini",
        "google/gemini-2.5-pro",
        "qwen/qwen-2.5-72b-instruct",
    ],
    "custom": [],
}

# Дефолтные модели если пользователь ничего не выбрал
DEFAULT_MODEL = {
    "openai":     "gpt-4o",
    "anthropic":  "claude-sonnet-4-5",
    "gemini":     "gemini-2.5-flash",
    "openrouter": "meta-llama/llama-3.1-70b-instruct",
    "custom":     "gpt-3.5-turbo",
}

# Расширения файлов для ahcode
LANG_EXT = {
    "python": ".py",     "py": ".py",
    "javascript": ".js", "js": ".js",
    "typescript": ".ts", "ts": ".ts",
    "java": ".java",
    "kotlin": ".kt",
    "swift": ".swift",
    "c": ".c",
    "c++": ".cpp",       "cpp": ".cpp",
    "csharp": ".cs",     "c#": ".cs",
    "go": ".go",
    "rust": ".rs",
    "ruby": ".rb",
    "php": ".php",
    "bash": ".sh",       "shell": ".sh",  "sh": ".sh",
    "powershell": ".ps1",
    "sql": ".sql",
    "html": ".html",
    "css": ".css",
    "scss": ".scss",
    "json": ".json",
    "yaml": ".yaml",     "yml": ".yml",
    "xml": ".xml",
    "toml": ".toml",
    "markdown": ".md",   "md": ".md",
    "dart": ".dart",
    "lua": ".lua",
    "r": ".r",
    "perl": ".pl",
    "haskell": ".hs",
    "scala": ".scala",
    "elixir": ".ex",
    "clojure": ".clj",
    "dockerfile": "",
}

# Действия TG Bridge
BRIDGE_ACTIONS = {
    "send_message":   "Отправить сообщение в чат",
    "set_name":       "Изменить имя профиля",
    "set_bio":        "Изменить описание профиля",
    "set_username":   "Изменить username",
    "delete_message": "Удалить последнее сообщение в чате",
    "react":          "Поставить реакцию на сообщение",
    "pin_message":    "Закрепить сообщение",
}

# Триггеры для Bridge watcher
BRIDGE_TRIGGERS = [
    "ai,", "аи,", "ии,", "/ai ",
    "отправь за меня", "напиши за меня",
    "смени имя", "смени bio", "смени описание",
    "поставь реакцию", "закрепи сообщение",
    "удали моё сообщение", "удали последнее",
]

MAX_TG_MSG = 3500  # символов — при превышении отправляем файлом


# ─────────────────────────────────────────────────────────────────────────────
#  Модуль
# ─────────────────────────────────────────────────────────────────────────────

@loader.tds
class AIHubMod(loader.Module):
    """AI Hub v4 — чаты, изображения, медиа-анализ, TG Bridge, скиллы."""

    strings = {
        "name": "AIHub",
        "_cls_doc": "AI Hub v4 — чаты с AI, изображения, анализ медиа, TG Bridge, скиллы.",

        # ── Общие ──────────────────────────────────────────────
        "no_key":            "❌ API-ключ не задан.\nОткрой меню: <code>{p}aihub</code>",
        "sending":           "⏳ Отправляю запрос...",
        "generating_img":    "🎨 Генерирую изображение...",
        "error":             "❌ Ошибка: <code>{}</code>",
        "no_args":           "❌ Аргументы не указаны.",

        # ── Провайдеры ─────────────────────────────────────────
        "provider_set":      "✅ Активный провайдер: <b>{}</b>",
        "provider_menu":     "🤖 <b>Выбери AI-провайдера:</b>\n\nТекущий: <b>{}</b>",

        # ── Ключи ──────────────────────────────────────────────
        "key_saved":         "✅ API-ключ сохранён.",
        "keys_removed":      "✅ Ключи удалены.",
        "key_valid":         "✅ <b>{}</b> — ключ действителен",
        "key_invalid":       "❌ <b>{}</b> — ключ недействителен или не задан",
        "checking":          "🔍 Проверяю ключи...",
        "keys_menu": (
            "🔑 <b>API-ключи провайдеров</b>\n\n"
            "AI Hub (универсальный): <code>{aihub}</code>\n"
            "OpenAI: <code>{openai}</code>\n"
            "Anthropic/Claude: <code>{anthropic}</code>\n"
            "Google Gemini: <code>{gemini}</code>\n"
            "Grok / xAI: <code>{grok}</code>\n"
            "Groq: <code>{groq}</code>\n"
            "OpenRouter: <code>{openrouter}</code>\n\n"
            "<i>Если задан специфичный ключ — используется прямой API.\n"
            "Иначе — универсальный AI Hub ключ.</i>"
        ),

        # ── Контекст ───────────────────────────────────────────
        "ctx_reset":         "🗑 Контекст для <b>{}</b> сброшен.",
        "ctx_reset_all":     "🗑 Все контексты сброшены.",
        "convs_list":        "📋 <b>Разговоры для {}:</b>\n\n{}",
        "no_convs":          "📋 Нет разговоров для <b>{}</b>.",

        # ── Промпт ─────────────────────────────────────────────
        "prompt_set":        "✅ Системный промпт задан.",
        "prompt_cleared":    "✅ Системный промпт очищен.",
        "prompt_show":       "📋 <b>Системный промпт:</b>\n\n<blockquote>{}</blockquote>",
        "no_prompt":         "📋 Системный промпт не задан.",

        # ── Модель ─────────────────────────────────────────────
        "model_set":         "✅ Модель: <b>{}</b>",

        # ── Конфиг ─────────────────────────────────────────────
        "cfg_updated":       "✅ <b>{}</b> = <code>{}</code>",

        # ── Авто-ответ ─────────────────────────────────────────
        "auto_on":           "✅ Авто-ответ AI <b>включён</b> в этом чате.",
        "auto_off":          "🔕 Авто-ответ AI <b>выключен</b> в этом чате.",

        # ── Поиск ──────────────────────────────────────────────
        "search_on":         "🔍 Поиск в интернете: <b>включён</b>",
        "search_off":        "🔕 Поиск в интернете: <b>выключен</b>",



        # ── Bridge ─────────────────────────────────────────────
        "bridge_on":         "🌉 <b>TG Bridge включён</b> в этом чате.",
        "bridge_off":        "🔕 <b>TG Bridge выключен</b> в этом чате.",

        # ── Главное меню ───────────────────────────────────────
        "main_menu": (
            "🤖 <b>AI Hub v4</b>\n\n"
            "⚙️ Провайдер: <b>{provider}</b>\n"
            "🤖 Модель: <b>{model}</b>\n"
            "🧠 Память: <b>{mem} сообщ.</b>\n"
            "🔍 Поиск: <b>{search}</b>\n"
            "💬 Авто-ответ: <b>{auto}</b>\n"
            "🌡 Температура: <b>{temp}</b>\n"
            "🔢 Макс. токены: <b>{maxtok}</b>"
        ),
    }

    strings_ru = strings  # основной язык русский

    # ─────────────────────────────────────────────────────────
    #  Конфиг
    # ─────────────────────────────────────────────────────────

    def __init__(self):
        self.config = loader.ModuleConfig(
            # ── Ключи ──────────────────────────────────────────
            loader.ConfigValue(
                "aihub_key", "",
                "Универсальный AI Hub API-ключ (aihub_... или sk-...).\n"
                "Используется если не задан специфичный ключ провайдера.",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "openai_key", "",
                "OpenAI API-ключ (sk-...). Если задан — используется прямой API OpenAI.",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "anthropic_key", "",
                "Anthropic/Claude API-ключ. Если задан — используется прямой API Anthropic.",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "gemini_key", "",
                "Google Gemini API-ключ (AIzaSy...). Если задан — используется прямой API Gemini.",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "grok_key", "",
                "xAI Grok API-ключ.",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "groq_key", "",
                "Groq API-ключ (быстрый inference).",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "openrouter_key", "",
                "OpenRouter API-ключ (доступ к сотням моделей).",
                validator=loader.validators.String(),
            ),
            # ── Основные настройки ─────────────────────────────
            loader.ConfigValue(
                "provider", "openai",
                "Активный AI-провайдер: openai / anthropic / gemini / openrouter / custom",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "model", "",
                "Модель для активного провайдера. Пусто = дефолтная.",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "temperature", 0.7,
                "Температура генерации (0.0–2.0). Ниже = точнее, выше = креативнее.",
                validator=loader.validators.Float(minimum=0.0, maximum=2.0),
            ),
            loader.ConfigValue(
                "max_tokens", 16000,
                "Максимальное количество токенов в ответе AI.",
                validator=loader.validators.Integer(minimum=100, maximum=128000),
            ),
            loader.ConfigValue(
                "mem_limit", 100,
                "Максимум пар сообщений в памяти на чат (0 = без лимита).",
                validator=loader.validators.Integer(minimum=0),
            ),
            loader.ConfigValue(
                "persona", "",
                "Персона AI. Например: 'Ты — я, общайся от первого лица, в моём стиле.'",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "reply_lang", "",
                "Язык ответов AI. Например: Russian, English. Пусто = авто.",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "web_search", False,
                "Включить поиск в интернете по умолчанию.",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "collapse_quotes", True,
                "Сворачивать цитаты (blockquote expandable). Поддерживается в Telegram 10.3+.",
                validator=loader.validators.Boolean(),
            ),
            # ── Изображения ────────────────────────────────────
            loader.ConfigValue(
                "image_provider", "openai",
                "Провайдер для генерации изображений: openai / gemini",
                validator=loader.validators.Choice(["openai", "gemini"]),
            ),
            loader.ConfigValue(
                "image_model", "dall-e-3",
                "Модель генерации изображений: dall-e-3 / dall-e-2 / gpt-image-1",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "image_size", "1024x1024",
                "Размер изображения (OpenAI): 1024x1024 / 512x512 / 256x256",
                validator=loader.validators.Choice(["1024x1024", "512x512", "256x256"]),
            ),
            loader.ConfigValue(
                "image_quality", "standard",
                "Качество изображения (OpenAI dall-e-3): standard / hd",
                validator=loader.validators.Choice(["standard", "hd"]),
            ),
            loader.ConfigValue(
                "image_style", "vivid",
                "Стиль изображения (OpenAI dall-e-3): vivid / natural",
                validator=loader.validators.Choice(["vivid", "natural"]),
            ),
            # ── Кастомный провайдер ────────────────────────────
            loader.ConfigValue(
                "custom_base_url", "",
                "Base URL кастомного провайдера.\n"
                "Для OpenAI-совместимых: https://api.example.com/v1\n"
                "Для AI Hub: оставь пустым.",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "custom_api_key", "",
                "API-ключ кастомного провайдера (если отличается от основного).",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "custom_type", "openai",
                "Тип кастомного API:\n"
                "  openai     — OpenAI-совместимый (/chat/completions)\n"
                "  openrouter — OpenRouter-совместимый\n"
                "  aihub      — AI Hub conversations API",
                validator=loader.validators.Choice(["openai", "openrouter", "aihub"]),
            ),
            loader.ConfigValue(
                "custom_model", "",
                "Модель для кастомного провайдера.",
                validator=loader.validators.String(),
            ),
        )

    # ─────────────────────────────────────────────────────────
    #  Инициализация
    # ─────────────────────────────────────────────────────────

    async def client_ready(self):
        """Инициализация БД при первом запуске."""
        defaults = {
            "conversations":  {},   # {provider: conv_id}
            "auto_chats":     [],   # чаты с авто-ответом
            "system_prompt":  "",   # текущий системный промпт

            "msg_counter":    {},   # {chat_id: count}
            "bridge_chats":   [],   # чаты где Bridge активен
            "bridge_allowed": [],   # разрешённые цели Bridge
            "bridge_confirm": True, # требовать подтверждение
        }
        for key, val in defaults.items():
            if self.get(key) is None:
                self.set(key, val)

    # ─────────────────────────────────────────────────────────
    #  Хелперы: ключи и заголовки
    # ─────────────────────────────────────────────────────────

    def _key(self, provider: str = None) -> str:
        """Возвращает подходящий API-ключ для провайдера."""
        p = provider or self.config["provider"]
        specific = {
            "openai":     self.config["openai_key"],
            "anthropic":  self.config["anthropic_key"],
            "gemini":     self.config["gemini_key"],
            "openrouter": self.config["openrouter_key"],
            "custom":     self.config["custom_api_key"],
        }
        return specific.get(p, "") or self.config["aihub_key"]

    def _has_key(self, provider: str = None) -> bool:
        return bool(self._key(provider))

    def _auth_headers(self, provider: str = None) -> dict:
        return {
            "Authorization": f"Bearer {self._key(provider)}",
            "Content-Type":  "application/json",
        }

    # ─────────────────────────────────────────────────────────
    #  Хелперы: провайдер и модель
    # ─────────────────────────────────────────────────────────

    def _prov(self) -> str:
        return self.config["provider"]

    def _base_url(self, provider: str = None) -> str:
        p = provider or self._prov()
        if p == "custom":
            url = self.config["custom_base_url"].strip().rstrip("/")
            return url if url else AIHUB_BASE
        return AIHUB_BASE

    def _model(self, provider: str = None) -> str:
        p = provider or self._prov()
        if p == "custom":
            return self.config["custom_model"] or self.config["model"] or DEFAULT_MODEL["custom"]
        return self.config["model"] or DEFAULT_MODEL.get(p, "gpt-4o")

    # ─────────────────────────────────────────────────────────
    #  Хелперы: память (бесконечная, хранится в БД)
    # ─────────────────────────────────────────────────────────

    def _mkey(self, provider: str, chat_id) -> str:
        return f"hist_{provider}_{chat_id}"

    def _hist(self, provider: str, chat_id) -> list:
        """Получить историю сообщений для чата и провайдера."""
        return self.get(self._mkey(provider, chat_id)) or []

    def _push_hist(self, provider: str, chat_id, role: str, content: str):
        """Добавить сообщение в историю, обрезая по лимиту."""
        key  = self._mkey(provider, chat_id)
        hist = self.pointer(key, [])
        hist.append({"role": role, "content": content})
        limit = int(self.config.get("mem_limit", 100) or 0)
        if limit > 0 and len(hist) > limit * 2:
            # Удаляем старые пары с начала
            del hist[: len(hist) - limit * 2]

    def _clear_hist(self, provider: str, chat_id):
        self.set(self._mkey(provider, chat_id), [])

    def _hist_count(self, provider: str, chat_id) -> int:
        return len(self._hist(provider, chat_id))

    # ─────────────────────────────────────────────────────────
    #  Хелперы: счётчик сообщений
    # ─────────────────────────────────────────────────────────

    def _next_n(self, chat_id) -> int:
        key  = str(chat_id)
        cnts = self.pointer("msg_counter", {})
        cnts[key] = cnts.get(key, 0) + 1
        return cnts[key]

    # ─────────────────────────────────────────────────────────
    #  Хелперы: conversations (AI Hub API)
    # ─────────────────────────────────────────────────────────

    def _conv_id(self, provider: str = None) -> str | None:
        p = provider or self._prov()
        return (self.get("conversations") or {}).get(p)

    async def _save_conv(self, provider: str, cid: str):
        convs = self.pointer("conversations", {})
        convs[provider] = cid

    # ─────────────────────────────────────────────────────────
    #  Хелпер: извлечение медиа из сообщения
    # ─────────────────────────────────────────────────────────

    async def _extract_media(self, msg) -> tuple:
        """
        Анализирует медиа из сообщения.
        Возвращает (image_b64: str|None, extra_media: list, desc: str).

        image_b64  — base64 основного изображения (для Vision API)
        extra_media — список доп. медиа: [{type, data, mime, name, text}]
        desc        — текстовое описание медиа для добавления к запросу
        """
        if not msg or not getattr(msg, "media", None):
            return None, [], ""

        image_b64   = None
        extra_media = []
        desc        = ""

        try:
            media = msg.media

            # ── Фотография ─────────────────────────────────────
            if isinstance(media, MessageMediaPhoto):
                raw = await msg.download_media(bytes)
                if raw:
                    image_b64 = base64.b64encode(raw).decode()
                    desc = "[фотография]"

            # ── Документ (видео, стикер, GIF, файл) ───────────
            elif isinstance(media, MessageMediaDocument):
                doc   = media.document
                mime  = doc.mime_type or "application/octet-stream"
                fname = next(
                    (a.file_name for a in (doc.attributes or []) if hasattr(a, "file_name")),
                    "",
                )
                attr_types = {type(a).__name__ for a in (doc.attributes or [])}

                # Стикер
                if "DocumentAttributeSticker" in attr_types:
                    raw = await msg.download_media(bytes)
                    if raw:
                        image_b64 = base64.b64encode(raw).decode()
                        sticker_attr = next(
                            (a for a in (doc.attributes or [])
                             if isinstance(a, DocumentAttributeSticker)), None
                        )
                        emoji = getattr(sticker_attr, "alt", "") if sticker_attr else ""
                        desc  = f"[стикер {emoji}]"

                # Видео — берём thumbnail как превью
                elif "DocumentAttributeVideo" in attr_types:
                    if doc.thumbs:
                        try:
                            thumb_bytes = await msg.client.download_media(msg, thumb=-1)
                            if isinstance(thumb_bytes, bytes) and thumb_bytes:
                                image_b64 = base64.b64encode(thumb_bytes).decode()
                            elif thumb_bytes and isinstance(thumb_bytes, str):
                                with open(thumb_bytes, "rb") as f_:
                                    image_b64 = base64.b64encode(f_.read()).decode()
                        except Exception:
                            pass
                    video_attr = next(
                        (a for a in (doc.attributes or []) if isinstance(a, DocumentAttributeVideo)), None
                    )
                    duration = getattr(video_attr, "duration", 0) if video_attr else 0
                    w = getattr(video_attr, "w", 0) if video_attr else 0
                    h = getattr(video_attr, "h", 0) if video_attr else 0
                    desc = f"[видео, {duration}с, {w}×{h}]"

                # GIF / анимация
                elif "DocumentAttributeAnimated" in attr_types:
                    raw = await msg.download_media(bytes)
                    if raw:
                        image_b64 = base64.b64encode(raw).decode()
                        desc = "[анимация GIF]"

                # Изображение в документе
                elif mime.startswith("image/"):
                    raw = await msg.download_media(bytes)
                    if raw:
                        image_b64 = base64.b64encode(raw).decode()
                        desc = f"[изображение {fname or mime}]"

                # Текстовые файлы — читаем содержимое
                elif (
                    mime.startswith("text/")
                    or mime in ("application/json", "application/xml", "application/javascript")
                    or (fname and fname.rsplit(".", 1)[-1].lower() in
                        {"txt", "md", "py", "js", "ts", "json", "yaml", "yml",
                         "toml", "sh", "bash", "css", "html", "xml", "sql",
                         "rs", "go", "rb", "php", "java", "kt", "swift", "cs",
                         "cpp", "c", "h", "lua", "r", "pl", "ex", "clj"})
                ):
                    raw = await msg.download_media(bytes)
                    if raw:
                        try:
                            text_content = raw.decode("utf-8", errors="replace")
                            # Ограничиваем размер для API
                            if len(text_content) > 30000:
                                text_content = text_content[:30000] + "\n...[обрезано]"
                        except Exception:
                            text_content = "[не удалось прочитать текст]"
                        extra_media.append({
                            "type": "file",
                            "mime": mime,
                            "name": fname or "file.txt",
                            "text": text_content,
                            "data": "",
                        })
                        desc = f"[файл: {fname or mime}]"

                # PDF
                elif mime == "application/pdf":
                    raw = await msg.download_media(bytes)
                    if raw:
                        extra_media.append({
                            "type": "file",
                            "mime": "application/pdf",
                            "name": fname or "document.pdf",
                            "text": f"[PDF файл: {fname}, размер {len(raw)} байт. "
                                    f"Я не могу извлечь текст из PDF напрямую, "
                                    f"но могу ответить на вопросы о нём если ты его опишешь.]",
                            "data": base64.b64encode(raw).decode() if len(raw) < 5_000_000 else "",
                        })
                        desc = f"[PDF: {fname}]"

                # Прочие файлы
                else:
                    extra_media.append({
                        "type": "file",
                        "mime": mime,
                        "name": fname or mime,
                        "text": (
                            f"Прикреплён файл: {fname or mime}, "
                            f"тип: {mime}, размер: {doc.size} байт. "
                            f"Я не могу прочитать этот тип файла напрямую."
                        ),
                        "data": "",
                    })
                    desc = f"[файл: {fname or mime}]"

        except Exception as e:
            desc = f"[медиа — ошибка извлечения: {e}]"

        return image_b64, extra_media, desc

    # ─────────────────────────────────────────────────────────
    #  Хелпер: системный промпт (базовый + персона + Bridge)
    # ─────────────────────────────────────────────────────────

    def _sys_prompt(self) -> str:
        """Собирает итоговый системный промпт из всех источников."""
        parts = []

        base = self.get("system_prompt") or ""
        if base:
            parts.append(base)

        persona = self.config.get("persona", "")
        if persona:
            parts.append(persona)

        lang = self.config.get("reply_lang", "")
        if lang:
            parts.append(f"Всегда отвечай на языке: {lang}.")

        allowed_chats = self.get("bridge_allowed") or []
        # Bridge всегда активен — AI всегда знает о своих возможностях
        bridge_prompt = (
            "СИСТЕМНАЯ ИНФОРМАЦИЯ: Ты встроен в Telegram userbot пользователя и ИМЕЕШЬ "
            "прямой доступ к его аккаунту через TG Bridge. "
            "Ты МОЖЕШЬ выполнять следующие действия по просьбе пользователя:\n"
            "- Отправить сообщение в любой разрешённый чат\n"
            "- Изменить имя профиля (имя и фамилию)\n"
            "- Изменить описание профиля (bio)\n"
            "- Изменить username\n"
            "- Удалить последнее сообщение в чате\n"
            "- Поставить реакцию на сообщение\n"
            "- Закрепить сообщение\n"
            "Когда пользователь просит выполнить такое действие — НЕ ОТКАЗЫВАЙСЯ и НЕ ГОВОРИ "
            "что у тебя нет доступа. Вместо этого отвечай СТРОГО в формате JSON "
            "(без markdown, без backticks, только чистый JSON):\n"
            '{"action":"<название>","params":{<параметры>},"comment":"<подтверждение для пользователя>"}\n'
            "Названия действий: send_message, set_name, set_bio, set_username, "
            "delete_message, react, pin_message.\n"
            f"Разрешённые чаты для send_message: {allowed_chats if allowed_chats else 'добавь через .ahbridge allow'}.\n"
            "Если пользователь задаёт обычный вопрос не связанный с управлением аккаунтом — "
            "отвечай как обычно без JSON."
        )
        parts.append(bridge_prompt)

        return "\n\n".join(parts)

    # ─────────────────────────────────────────────────────────
    #  Веб-поиск (DuckDuckGo Instant Answer + HTML scraping)
    # ─────────────────────────────────────────────────────────

    async def _do_web_search(self, query: str) -> str:
        """
        Выполняет веб-поиск и возвращает результаты как текст.
        Использует DuckDuckGo (без ключа) или кастомный поисковик если задан.
        """
        results_text = ""

        # Метод 1: DuckDuckGo Instant Answer API (JSON, без ключа)
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q":      query,
                        "format": "json",
                        "no_html": "1",
                        "no_redirect": "1",
                        "kl":    "ru-ru",
                    },
                    headers={"User-Agent": "Mozilla/5.0 (compatible; AIHub/4.0)"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        # Instant answer
                        abstract = data.get("AbstractText", "")
                        answer   = data.get("Answer", "")
                        infobox  = ""
                        if data.get("Infobox"):
                            try:
                                rows = data["Infobox"].get("content", [])[:5]
                                infobox = "\n".join(
                                    f"{r.get('label','')}: {r.get('value','')}"
                                    for r in rows if r.get("value")
                                )
                            except Exception:
                                pass
                        related = []
                        for r in data.get("RelatedTopics", [])[:5]:
                            if isinstance(r, dict) and r.get("Text"):
                                related.append(r["Text"][:200])

                        parts = []
                        if answer:
                            parts.append(f"Ответ: {answer}")
                        if abstract:
                            parts.append(f"Краткая информация: {abstract}")
                        if infobox:
                            parts.append(f"Данные:\n{infobox}")
                        if related:
                            parts.append("Связанные темы:\n" + "\n".join(related))

                        if parts:
                            results_text = "\n\n".join(parts)
        except Exception:
            pass

        # Метод 2: DuckDuckGo HTML поиск (если Instant Answer пустой)
        if not results_text:
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(
                        "https://html.duckduckgo.com/html/",
                        params={"q": query},
                        headers={
                            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                        },
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            html = await resp.text()
                            # Простой парсинг результатов
                            import re as _re
                            # Заголовки результатов
                            titles = _re.findall(
                                r'class="result__title"[^>]*>.*?<a[^>]*>([^<]{10,200})</a>',
                                html
                            )
                            # Сниппеты
                            snippets = _re.findall(
                                r'class="result__snippet"[^>]*>([^<]{20,400})<',
                                html
                            )
                            # Убираем HTML entities
                            def clean(t):
                                t = _re.sub(r'&amp;', '&', t)
                                t = _re.sub(r'&lt;', '<', t)
                                t = _re.sub(r'&gt;', '>', t)
                                t = _re.sub(r'&quot;', '"', t)
                                t = _re.sub(r'&#x27;', "'", t)
                                t = _re.sub(r'\s+', ' ', t)
                                return t.strip()

                            items = []
                            for i, (title, snippet) in enumerate(
                                zip(titles[:5], snippets[:5])
                            ):
                                items.append(f"{i+1}. {clean(title)}\n   {clean(snippet)}")

                            if items:
                                results_text = (
                                    f"Результаты поиска по запросу «{query}»:\n\n"
                                    + "\n\n".join(items)
                                )
            except Exception:
                pass

        # Метод 3: текущая дата/время (всегда добавляем)
        import datetime as _dt
        now = _dt.datetime.utcnow()
        date_str = now.strftime("%d.%m.%Y %H:%M UTC")

        if results_text:
            return f"[Текущая дата и время: {date_str}]\n\n{results_text}"
        else:
            return f"[Текущая дата и время: {date_str}]\n[Поиск не вернул результатов для: {query}]"

    # ─────────────────────────────────────────────────────────
    #  Основной роутер отправки сообщений
    # ─────────────────────────────────────────────────────────

    async def _send(
        self,
        provider:    str,
        text:        str,
        chat_id      = None,
        image_b64:   str  = None,
        extra_media: list = None,
        use_search:  bool = False,
    ) -> dict:
        """
        Главная точка входа. Определяет метод отправки и вызывает нужный хелпер.
        Возвращает: {text, model, tokens, elapsed}
        """
        t0          = time.time()
        model       = self._model(provider)
        sys_p       = self._sys_prompt()
        extra_media = extra_media or []
        cid         = self._conv_id(provider)

        # Выполняем поиск и инжектируем результаты в запрос
        if use_search and text:
            try:
                search_results = await self._do_web_search(text)
                if search_results:
                    text = (
                        f"{text}\n\n"
                        f"[Данные из интернета для ответа на этот вопрос:]\n"
                        f"{search_results}\n\n"
                        f"Используй эти данные чтобы дать актуальный ответ."
                    )
            except Exception:
                pass
        elif text:
            # Всегда добавляем текущую дату (даже без поиска)
            import datetime as _dt
            now = _dt.datetime.utcnow()
            # Только если вопрос о времени/дате/актуальном
            date_keywords = [
                "дата", "число", "сегодня", "сейчас", "год", "месяц",
                "date", "today", "now", "year", "current", "latest",
                "новый", "последний", "актуальн", "недавн",
            ]
            if any(kw in text.lower() for kw in date_keywords):
                now_str = now.strftime("%d.%m.%Y %H:%M UTC")
                text = f"{text}\n\n[Текущая дата и время: {now_str}]"

        # ── Роутинг ────────────────────────────────────────────
        # Прямой API используется ТОЛЬКО если задан специфичный ключ провайдера.
        # Иначе — AI Hub conversations API.

        result = None

        if provider == "custom":
            ctype    = self.config["custom_type"]
            base_url = self._base_url("custom")
            key      = self._key("custom")
            if ctype in ("openai", "openrouter") and self.config["custom_base_url"].strip():
                # Кастомный OpenAI-совместимый
                result = await self._call_openai_compat(
                    url       = f"{base_url}/chat/completions",
                    key       = key,
                    model     = model,
                    sys_p     = sys_p,
                    text      = text,
                    chat_id   = chat_id,
                    provider  = "custom",
                    image_b64 = image_b64,
                    extra     = extra_media,
                    search    = use_search,
                )
            else:
                # AI Hub conversations API с кастомным base_url
                result = await self._call_aihub(
                    base_url = base_url,
                    key      = key,
                    provider = "custom",
                    pname    = "openai",
                    cid      = cid,
                    model    = model,
                    sys_p    = sys_p,
                    text     = text,
                    chat_id  = chat_id,
                    search   = use_search,
                )

        elif provider == "openai" and self.config["openai_key"]:
            result = await self._call_openai_compat(
                url       = "https://api.openai.com/v1/chat/completions",
                key       = self.config["openai_key"],
                model     = model,
                sys_p     = sys_p,
                text      = text,
                chat_id   = chat_id,
                provider  = "openai",
                image_b64 = image_b64,
                extra     = extra_media,
                search    = use_search,
            )

        elif provider == "anthropic" and self.config["anthropic_key"]:
            result = await self._call_anthropic(
                key       = self.config["anthropic_key"],
                model     = model,
                sys_p     = sys_p,
                text      = text,
                chat_id   = chat_id,
                image_b64 = image_b64,
                extra     = extra_media,
                search    = use_search,
            )

        elif provider == "gemini" and self.config["gemini_key"]:
            result = await self._call_gemini(
                key       = self.config["gemini_key"],
                model     = model,
                sys_p     = sys_p,
                text      = text,
                chat_id   = chat_id,
                image_b64 = image_b64,
                extra     = extra_media,
                search    = use_search,
            )

        elif provider == "openrouter" and self.config["openrouter_key"]:
            result = await self._call_openai_compat(
                url       = "https://openrouter.ai/api/v1/chat/completions",
                key       = self.config["openrouter_key"],
                model     = model,
                sys_p     = sys_p,
                text      = text,
                chat_id   = chat_id,
                provider  = "openrouter",
                image_b64 = image_b64,
                extra     = extra_media,
                search    = use_search,
            )

        else:
            # ── AI Hub conversations API (универсальный) ───────
            result = await self._call_aihub(
                base_url = AIHUB_BASE,
                key      = self._key(provider),
                provider = provider,
                pname    = provider,
                cid      = cid,
                model    = model,
                sys_p    = sys_p,
                text     = text,
                chat_id  = chat_id,
                search   = use_search,
            )

        result["elapsed"] = time.time() - t0
        result.setdefault("model", model)
        return result

    # ─────────────────────────────────────────────────────────
    #  OpenAI-совместимый API (/chat/completions)
    # ─────────────────────────────────────────────────────────

    async def _call_openai_compat(
        self, url, key, model, sys_p, text, chat_id, provider,
        image_b64=None, extra=None, search=False
    ) -> dict:
        """Универсальный вызов для OpenAI / OpenRouter / Groq / Grok / custom."""
        extra    = extra or []
        headers  = {
            "Authorization": f"Bearer {key}",
            "Content-Type":  "application/json",
        }
        messages = []
        if sys_p:
            messages.append({"role": "system", "content": sys_p})
        # История
        for m in self._hist(provider, chat_id or 0):
            messages.append(m)

        # Текущее сообщение с медиа
        user_content = []
        if image_b64:
            user_content.append({
                "type":      "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
            })
        for em in extra:
            if em.get("type") in ("image", "video_frame") and em.get("data"):
                user_content.append({
                    "type":      "image_url",
                    "image_url": {"url": f"data:{em.get('mime','image/jpeg')};base64,{em['data']}"},
                })
            elif em.get("type") == "file" and em.get("text"):
                fname = em.get("name", "file")
                user_content.append({
                    "type": "text",
                    "text": f"=== Файл: {fname} ===\n{em['text']}\n=== Конец файла ===",
                })

        query = text or ("Что на изображении?" if image_b64 else "Привет")
        user_content.append({"type": "text", "text": query})

        if len(user_content) == 1:
            messages.append({"role": "user", "content": query})
        else:
            messages.append({"role": "user", "content": user_content})

        payload = {
            "model":      model,
            "messages":   messages,
            "max_tokens": int(self.config.get("max_tokens", 16000)),
        }
        try:
            payload["temperature"] = float(self.config.get("temperature", 0.7))
        except Exception:
            pass

        if search:
            payload["tools"] = [{"type": "web_search_preview"}]

        reply  = ""
        tokens = None
        rmodel = model

        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    url, headers=headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    data = await resp.json(content_type=None)

            # Парсим ответ
            if "choices" in data:
                choice = data["choices"][0]
                msg    = choice.get("message", {})
                reply  = msg.get("content") or ""
                # Если поиск вернул tool_calls
                if not reply and msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        out = (tc.get("function") or {}).get("output", "")
                        if out:
                            reply = out
                            break
                if "usage" in data:
                    tokens = (
                        data["usage"].get("total_tokens")
                        or data["usage"].get("completion_tokens")
                    )
                rmodel = data.get("model", model)
            elif "output" in data:
                # Responses API
                for item in data.get("output", []):
                    if item.get("type") == "message":
                        for part in item.get("content", []):
                            if part.get("type") == "output_text":
                                reply += part.get("text", "")
                rmodel = data.get("model", model)
            elif "error" in data:
                reply = f"❌ API error: {data['error'].get('message', str(data['error']))}"

        except Exception as e:
            reply = f"❌ Ошибка запроса: {e}"

        if chat_id and reply and not reply.startswith("❌"):
            self._push_hist(provider, chat_id, "user", text or "[медиа]")
            self._push_hist(provider, chat_id, "assistant", reply)

        return {"text": reply.strip() or "...", "model": rmodel, "tokens": tokens}

    # ─────────────────────────────────────────────────────────
    #  Anthropic API
    # ─────────────────────────────────────────────────────────

    async def _call_anthropic(
        self, key, model, sys_p, text, chat_id,
        image_b64=None, extra=None, search=False
    ) -> dict:
        extra   = extra or []
        headers = {
            "x-api-key":         key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        }
        messages = []
        for m in self._hist("anthropic", chat_id or 0):
            messages.append(m)

        user_content = []
        if image_b64:
            user_content.append({
                "type":   "image",
                "source": {
                    "type":       "base64",
                    "media_type": "image/jpeg",
                    "data":       image_b64,
                },
            })
        for em in extra:
            if em.get("type") in ("image", "video_frame") and em.get("data"):
                user_content.append({
                    "type":   "image",
                    "source": {
                        "type":       "base64",
                        "media_type": em.get("mime", "image/jpeg"),
                        "data":       em["data"],
                    },
                })
            elif em.get("type") == "file" and em.get("text"):
                fname = em.get("name", "file")
                user_content.append({
                    "type": "text",
                    "text": f"=== Файл: {fname} ===\n{em['text']}\n=== Конец файла ===",
                })

        query = text or ("Что на изображении?" if image_b64 else "Привет")
        user_content.append({"type": "text", "text": query})

        if len(user_content) == 1:
            messages.append({"role": "user", "content": query})
        else:
            messages.append({"role": "user", "content": user_content})

        payload = {
            "model":      model,
            "max_tokens": int(self.config.get("max_tokens", 16000)),
            "messages":   messages,
        }
        if sys_p:
            payload["system"] = sys_p
        try:
            payload["temperature"] = float(self.config.get("temperature", 0.7))
        except Exception:
            pass
        if search:
            payload["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

        reply  = ""
        tokens = None

        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    data = await resp.json(content_type=None)

            for block in data.get("content", []):
                if block.get("type") == "text":
                    reply += block.get("text", "")
            if "usage" in data:
                tokens = data["usage"].get("output_tokens")
            if "error" in data:
                reply = f"❌ Anthropic error: {data['error'].get('message', str(data['error']))}"

        except Exception as e:
            reply = f"❌ Ошибка запроса: {e}"

        if chat_id and reply and not reply.startswith("❌"):
            self._push_hist("anthropic", chat_id, "user", text or "[медиа]")
            self._push_hist("anthropic", chat_id, "assistant", reply)

        return {"text": reply.strip() or "...", "model": model, "tokens": tokens}

    # ─────────────────────────────────────────────────────────
    #  Google Gemini API
    # ─────────────────────────────────────────────────────────

    async def _call_gemini(
        self, key, model, sys_p, text, chat_id,
        image_b64=None, extra=None, search=False
    ) -> dict:
        extra   = extra or []
        api_url = (
            f"https://generativelanguage.googleapis.com/v1beta"
            f"/models/{model}:generateContent?key={key}"
        )
        parts = []
        if image_b64:
            parts.append({"inlineData": {"mimeType": "image/jpeg", "data": image_b64}})
        for em in extra:
            if em.get("type") in ("image", "video_frame") and em.get("data"):
                parts.append({
                    "inlineData": {
                        "mimeType": em.get("mime", "image/jpeg"),
                        "data":     em["data"],
                    }
                })
            elif em.get("type") == "file" and em.get("text"):
                fname = em.get("name", "file")
                parts.append({
                    "text": f"=== Файл: {fname} ===\n{em['text']}\n=== Конец файла ==="
                })

        query = text or ("Что на изображении?" if image_b64 else "Привет")
        parts.append({"text": query})

        contents = []
        for m in self._hist("gemini", chat_id or 0):
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        contents.append({"role": "user", "parts": parts})

        payload = {"contents": contents}
        if sys_p:
            payload["systemInstruction"] = {"parts": [{"text": sys_p}]}
        if search:
            payload["tools"] = [{"googleSearch": {}}]
        try:
            payload["generationConfig"] = {
                "temperature":     float(self.config.get("temperature", 0.7)),
                "maxOutputTokens": int(self.config.get("max_tokens", 8192)),
            }
        except Exception:
            pass

        reply  = ""
        tokens = None

        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    api_url, json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    data = await resp.json(content_type=None)

            candidates = data.get("candidates", [])
            if candidates:
                for part in candidates[0].get("content", {}).get("parts", []):
                    reply += part.get("text", "")
            if "usageMetadata" in data:
                tokens = data["usageMetadata"].get("totalTokenCount")
            if "error" in data:
                reply = f"❌ Gemini error: {data['error'].get('message', str(data['error']))}"

        except Exception as e:
            reply = f"❌ Ошибка запроса: {e}"

        if chat_id and reply and not reply.startswith("❌"):
            self._push_hist("gemini", chat_id, "user", text or "[медиа]")
            self._push_hist("gemini", chat_id, "assistant", reply)

        return {"text": reply.strip() or "...", "model": model, "tokens": tokens}

    # ─────────────────────────────────────────────────────────
    #  AI Hub conversations API (SSE)
    # ─────────────────────────────────────────────────────────

    async def _call_aihub(
        self, base_url, key, provider, pname, cid,
        model, sys_p, text, chat_id, search=False
    ) -> dict:
        """
        AI Hub conversations API.
        Создаёт разговор если нет cid, отправляет сообщение, парсит SSE.
        """
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type":  "application/json",
        }

        # ── Создаём разговор если нужно ───────────────────────
        if not cid:
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.post(
                        f"{base_url}/{pname}/conversations",
                        headers=headers,
                        json={"title": f"Heroku · {provider}"},
                        timeout=aiohttp.ClientTimeout(total=20),
                    ) as resp:
                        ct   = resp.headers.get("Content-Type", "")
                        body = await resp.text()
                        if resp.status in (200, 201) and "json" in ct:
                            data = json.loads(body)
                            cid  = data.get("id")
                            if cid:
                                await self._save_conv(provider, cid)
                        else:
                            return {
                                "text": (
                                    f"❌ Сервер AI Hub вернул {resp.status}.\n"
                                    f"Проверь API-ключ командой .ahcheckkeys\n"
                                    f"Ответ: {body[:200]}"
                                ),
                                "model": model, "tokens": None,
                            }
            except Exception as e:
                return {
                    "text": f"❌ Не удалось подключиться к AI Hub: {e}",
                    "model": model, "tokens": None,
                }

            if not cid:
                return {
                    "text": "❌ Не удалось создать разговор. Проверь ключ: .ahcheckkeys",
                    "model": model, "tokens": None,
                }

        # ── Отправляем сообщение ──────────────────────────────
        payload = {"content": text}
        if sys_p:
            payload["system"] = sys_p
        if model:
            payload["model"] = model
        if search:
            payload["web_search"] = True

        raw_body = ""
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    f"{base_url}/{pname}/conversations/{cid}/messages",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    raw_body = await resp.text()
        except Exception as e:
            return {"text": f"❌ Ошибка отправки: {e}", "model": model, "tokens": None}

        # ── Парсим SSE-поток ──────────────────────────────────
        full   = ""
        tokens = None
        for line in raw_body.splitlines():
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                obj   = json.loads(chunk)
                delta = (
                    obj.get("choices", [{}])[0]
                    .get("delta", {})
                    .get("content", "")
                )
                if delta:
                    full += delta
                if "usage" in obj:
                    u      = obj["usage"]
                    tokens = u.get("total_tokens") or u.get("completion_tokens")
            except Exception:
                pass

        # ── Fallback: GET последних сообщений ─────────────────
        if not full:
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(
                        f"{base_url}/{pname}/conversations/{cid}/messages",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=20),
                    ) as resp2:
                        ct = resp2.headers.get("Content-Type", "")
                        if "json" in ct:
                            msgs = await resp2.json(content_type=None)
                            if isinstance(msgs, list):
                                for m in reversed(msgs):
                                    if m.get("role") == "assistant":
                                        full = m.get("content", "").strip()
                                        break
            except Exception:
                pass

        if chat_id and full:
            self._push_hist(provider, chat_id, "user", text)
            self._push_hist(provider, chat_id, "assistant", full)

        return {
            "text":   full.strip() or "...",
            "model":  model,
            "tokens": tokens,
        }

    # ─────────────────────────────────────────────────────────
    #  Генерация изображений
    # ─────────────────────────────────────────────────────────

    async def _gen_image(self, prompt: str) -> tuple:
        """Возвращает (bytes, None) или (None, error_str)."""
        provider = self.config["image_provider"]
        key      = self._key(provider) or self._key()
        payload  = {
            "prompt":   prompt,
            "provider": provider,
        }
        if provider == "openai":
            payload["model"]   = self.config.get("image_model", "dall-e-3")
            payload["size"]    = self.config["image_size"]
            payload["quality"] = self.config.get("image_quality", "standard")
            payload["style"]   = self.config.get("image_style",   "vivid")

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type":  "application/json",
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    f"{AIHUB_BASE}/images/generate",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        return None, f"HTTP {resp.status}: {body[:200]}"
                    data = await resp.json(content_type=None)
        except Exception as e:
            return None, str(e)

        b64 = data.get("b64_json")
        if not b64:
            return None, f"Нет b64_json в ответе. Ответ: {str(data)[:200]}"

        try:
            return base64.b64decode(b64), None
        except Exception as e:
            return None, f"Ошибка декодирования base64: {e}"

    # ─────────────────────────────────────────────────────────
    #  Форматирование ответа (стиль Codex)
    # ─────────────────────────────────────────────────────────

    def _fmt(
        self,
        result:     dict,
        provider:   str,
        n:          int,
        user_text:  str  = "",
        has_image:  bool = False,
    ) -> str:
        """
        Формирует красивое сообщение:

        ✨ [3/∞] gpt-4o | 5с | 🔢 847

        💬 Запрос:
        <blockquote expandable>текст запроса</blockquote>

        ✦ OpenAI:
        <blockquote expandable>ответ AI</blockquote>
        """
        model   = result.get("model") or self._model(provider)
        elapsed = result.get("elapsed", 0)
        tokens  = result.get("tokens")
        icon    = PROVIDER_ICON.get(provider, "🤖")

        tok_str = f" | 🔢 {tokens}" if tokens else ""
        icon_p  = f"{icon} " if icon else ""
        header  = f"{icon_p}[{n}/∞] <code>{model}</code> | {elapsed:.0f}с{tok_str}"

        # Текст запроса
        if has_image and not user_text:
            q_display = "🖼 [изображение]"
        elif user_text:
            q_display = user_text[:400] + ("..." if len(user_text) > 400 else "")
        else:
            q_display = "..."

        # Бренд для заголовка ответа
        m_lower = model.lower()
        if   "gemini"   in m_lower or provider == "gemini":
            brand = "Gemini"
        elif any(x in m_lower for x in ("gpt", "o1-", "o3", "o4")) or provider == "openai":
            brand = "OpenAI"
        elif "claude"   in m_lower or provider == "anthropic":
            brand = "Claude"
        elif "llama"    in m_lower:
            brand = "Llama"
        elif "mistral"  in m_lower or "mixtral" in m_lower:
            brand = "Mistral"
        elif "deepseek" in m_lower:
            brand = "DeepSeek"
        elif "grok"     in m_lower:
            brand = "Grok"
        elif "qwen"     in m_lower:
            brand = "Qwen"
        elif "command"  in m_lower:
            brand = "Cohere"
        elif provider == "openrouter":
            brand = model.split("/")[-1] if "/" in model else "OpenRouter"
        else:
            brand = model.split("/")[-1] if "/" in model else model

        # Сворачиваемые цитаты
        col  = self.config.get("collapse_quotes", True)
        tag  = "blockquote expandable" if col else "blockquote"
        ctag = "blockquote"  # закрывающий тег всегда без атрибутов

        q_block = f"💬 <b>Запрос:</b>\n<{tag}>{q_display}</{ctag}>"
        a_block = f"✦ <b>{brand}:</b>\n<{tag}>{result['text']}</{ctag}>"

        return f"{header}\n\n{q_block}\n\n{a_block}"

    # ─────────────────────────────────────────────────────────
    #  Умная отправка ответа (с файлом если длинный)
    # ─────────────────────────────────────────────────────────

    def _response_markup(self, provider: str, chat_id, use_search: bool, mem_count: int = 0) -> list:
        """Стандартная разметка кнопок под ответом AI."""
        mem_label = f"🗑 [{mem_count}/∞]" if mem_count > 0 else "🗑 Память"
        return [
            [
                {
                    "text":     "🔄 Регенерировать",
                    "callback": self._cb_regen,
                    "args":     (provider, chat_id),
                },
                {
                    "text":     mem_label,
                    "callback": self._cb_clear_mem,
                    "args":     (provider, chat_id),
                },
            ],
            [
                {
                    "text":     "🔍 Поиск: " + ("вкл 🟢" if use_search else "выкл ⚪"),
                    "callback": self._cb_toggle_search,
                },
            ],
            [{"text": "❌ Закрыть", "action": "close"}],
        ]

    async def _deliver(
        self,
        target,
        response:   str,
        inline_ok:  bool,
        provider:   str,
        chat_id,
        use_search: bool,
        is_call:    bool = False,
    ):
        """
        Отправляет ответ.
        Если response > MAX_TG_MSG символов — отправляет файлом.
        is_call=True — target это call (call.edit вместо utils.answer).
        """
        mem_count = self._hist_count(provider, chat_id) if chat_id else 0
        markup = self._response_markup(provider, chat_id, use_search, mem_count)

        if len(response) > MAX_TG_MSG:
            # Отправляем файлом
            plain = re.sub(r"<[^>]+>", "", response)
            f     = io.BytesIO(plain.encode("utf-8"))
            f.name = "answer.txt"
            short = response[:300].rsplit("\n", 1)[0] + "\n\n<i>📄 Ответ слишком длинный — отправлен файлом</i>"

            if is_call:
                try:
                    await target.edit(short)
                except Exception:
                    pass
                await target.client.send_file(
                    chat_id, f,
                    caption="📄 <b>Полный ответ AI</b>",
                )
            else:
                try:
                    await utils.answer(target, short)
                except Exception:
                    pass
                await target.client.send_file(
                    target.chat_id if hasattr(target, "chat_id") else chat_id,
                    f,
                    caption="📄 <b>Полный ответ AI</b>",
                )
            return

        # Обычный ответ
        if is_call:
            try:
                await target.edit(
                    response,
                    reply_markup=markup if inline_ok else None,
                )
            except Exception:
                pass
        elif inline_ok:
            await utils.answer(target, response, reply_markup=markup)
        else:
            await utils.answer(target, response)

    # ─────────────────────────────────────────────────────────
    #  Проверка поддержки inline-кнопок в чате
    # ─────────────────────────────────────────────────────────

    async def _inline_ok(self, message) -> bool:
        """
        Проверяет можно ли использовать inline-кнопки.
        Broadcast-каналы не поддерживают.
        Результат кешируется в БД.
        """
        chat_id   = str(message.chat_id)
        cache_key = f"inline_ok_{chat_id}"
        cached    = self.get(cache_key)
        if cached is not None:
            return bool(cached)

        try:
            entity = await message.client.get_entity(message.chat_id)
            ok     = not (isinstance(entity, Channel) and entity.broadcast)
        except Exception:
            ok = True

        self.set(cache_key, ok)
        return ok

    # ─────────────────────────────────────────────────────────
    #  TG Bridge: выполнение действий
    # ─────────────────────────────────────────────────────────

    async def _bridge_exec(self, client, action: str, params: dict, origin_chat) -> str:
        """Выполняет действие Bridge. Возвращает строку результата."""
        allowed = self.get("bridge_allowed") or []

        def to_peer(s):
            s = str(s).strip()
            return int(s) if s.lstrip("-").isdigit() else s

        try:
            if action == "send_message":
                target = str(params.get("chat_id", ""))
                text   = str(params.get("text", ""))
                if not text:
                    return "❌ Пустой текст"
                if target not in allowed:
                    return f"🚫 Чат {target} не в списке разрешённых"
                await client.send_message(to_peer(target), text)
                return f"✅ Отправлено в {target}"

            elif action == "set_name":
                from telethon.tl.functions.account import UpdateProfileRequest
                fn = str(params.get("first_name", "")).strip()
                ln = str(params.get("last_name",  "")).strip()
                if not fn:
                    return "❌ Нужен first_name"
                await client(UpdateProfileRequest(first_name=fn, last_name=ln))
                return f"✅ Имя изменено: {fn} {ln}".strip()

            elif action == "set_bio":
                from telethon.tl.functions.account import UpdateProfileRequest
                bio = str(params.get("bio", ""))
                await client(UpdateProfileRequest(about=bio))
                return "✅ Bio обновлено"

            elif action == "set_username":
                from telethon.tl.functions.account import UpdateUsernameRequest
                uname = str(params.get("username", "")).strip().lstrip("@")
                if not uname:
                    return "❌ Нужен username"
                await client(UpdateUsernameRequest(username=uname))
                return f"✅ Username изменён: @{uname}"

            elif action == "delete_message":
                target = str(params.get("chat_id", str(origin_chat)))
                if target not in allowed and target != str(origin_chat):
                    return f"🚫 Чат {target} не разрешён"
                msgs = await client.get_messages(to_peer(target), limit=10, from_user="me")
                if not msgs:
                    return "❌ Нет твоих сообщений в этом чате"
                await client.delete_messages(to_peer(target), [msgs[0].id])
                return "✅ Последнее сообщение удалено"

            elif action == "react":
                target = str(params.get("chat_id", str(origin_chat)))
                emoji  = str(params.get("emoji", "👍"))
                if target not in allowed and target != str(origin_chat):
                    return f"🚫 Чат {target} не разрешён"
                msgs = await client.get_messages(to_peer(target), limit=1)
                if not msgs:
                    return "❌ Нет сообщений"
                try:
                    from telethon.tl.functions.messages import SendReactionRequest
                    from telethon.tl.types import ReactionEmoji
                    await client(SendReactionRequest(
                        peer     = to_peer(target),
                        msg_id   = msgs[0].id,
                        reaction = [ReactionEmoji(emoticon=emoji)],
                    ))
                    return f"✅ Реакция {emoji} поставлена"
                except Exception as e:
                    return f"❌ Ошибка реакции: {e}"

            elif action == "pin_message":
                target = str(params.get("chat_id", str(origin_chat)))
                msg_id = params.get("message_id")
                if not msg_id:
                    return "❌ Нужен message_id"
                if target not in allowed and target != str(origin_chat):
                    return f"🚫 Чат {target} не разрешён"
                from telethon.tl.functions.messages import UpdatePinnedMessageRequest
                await client(UpdatePinnedMessageRequest(
                    peer = to_peer(target),
                    id   = int(msg_id),
                ))
                return "✅ Сообщение закреплено"

            else:
                return f"❌ Неизвестное действие: {action}"

        except Exception as e:
            return f"❌ Ошибка выполнения: {e}"

    # ─────────────────────────────────────────────────────────
    #  UI: главное меню
    # ─────────────────────────────────────────────────────────

    def _menu_text(self, chat_id=None) -> str:
        provider = self._prov()
        model    = self._model(provider)
        auto_c   = self.get("auto_chats") or []
        auto     = "вкл ✅" if (chat_id and str(chat_id) in auto_c) else "выкл 🔕"
        search   = "вкл 🔍" if self.config["web_search"] else "выкл"
        mem      = self._hist_count(provider, chat_id) if chat_id else 0
        pdisp    = (
            f"custom ({self.config['custom_type']})"
            if provider == "custom"
            else provider
        )
        return self.strings["main_menu"].format(
            provider = pdisp,
            model    = model,
            mem      = mem,
            search   = search,
            auto     = auto,
            temp     = self.config.get("temperature", 0.7),
            maxtok   = self.config.get("max_tokens", 16000),
        )

    def _menu_markup(self) -> list:
        p = self._prov()
        return [
            [
                {"text": "🔄 Провайдер",   "callback": self._cb_prov_menu},
                {"text": "🤖 Модель",       "callback": self._cb_model_menu},
            ],
            [
                {"text": "🔑 Ключи",         "callback": self._cb_keys_menu},
                {"text": "🔍 Поиск",          "callback": self._cb_toggle_search},
            ],
            [
                {"text": "🖼 Изображения",    "callback": self._cb_img_menu},
                {"text": "📋 Промпт",          "callback": self._cb_prompt_menu},
            ],
            [
                {"text": "⚙️ Кастомный",      "callback": self._cb_custom_menu},
                {"text": "🌡 Температура",
                 "input":   "Введи температуру (0.0–2.0)",
                 "handler": self._inp_temp},
            ],
            [
                {"text": "🌉 TG Bridge",        "callback": self._cb_bridge_menu},
            ],
            [
                {"text": "🗑 Сбросить контекст", "callback": self._cb_reset_confirm, "args": (p,)},
            ],
            [{"text": "❌ Закрыть", "action": "close"}],
        ]

    def _prov_buttons(self) -> list:
        current = self._prov()
        btns, row = [], []
        for p in ALL_PROVIDERS:
            mark  = "✅ " if p == current else ""
            icon  = PROVIDER_ICON.get(p, "")
            label = f"{mark}{icon} {p}" if icon else f"{mark}{p}"
            row.append({
                "text":     label,
                "callback": self._cb_set_prov,
                "args":     (p,),
            })
            if len(row) == 2:
                btns.append(row)
                row = []
        if row:
            btns.append(row)
        return btns

    def _custom_text(self) -> str:
        url    = self.config["custom_base_url"] or "(не задан)"
        ctype  = self.config["custom_type"]
        ckey   = self.config["custom_api_key"]
        cmodel = self.config["custom_model"] or "(не задан)"
        kdisp  = ckey[:8] + "…" if ckey else "(основной ключ)"
        return (
            "⚙️ <b>Кастомный провайдер</b>\n\n"
            f"🌐 Base URL: <code>{url}</code>\n"
            f"🔧 Тип: <b>{ctype}</b>\n"
            f"🔑 Ключ: <code>{kdisp}</code>\n"
            f"🤖 Модель: <code>{cmodel}</code>\n\n"
            "<i>openai/openrouter → /chat/completions\n"
            "aihub → conversations API</i>"
        )

    def _custom_markup(self) -> list:
        ctype = self.config["custom_type"]
        return [
            [
                {"text": "🌐 Base URL", "input": "Base URL провайдера", "handler": self._inp_custom_url},
                {"text": "🔑 Ключ",    "input": "API-ключ",            "handler": self._inp_custom_key},
            ],
            [
                {"text": "🤖 Модель", "input": "Название модели", "handler": self._inp_custom_model},
            ],
            [
                {
                    "text":     f"{'✅ ' if ctype == 'openai'     else ''}openai",
                    "callback": self._cb_custom_type, "args": ("openai",),
                },
                {
                    "text":     f"{'✅ ' if ctype == 'openrouter' else ''}openrouter",
                    "callback": self._cb_custom_type, "args": ("openrouter",),
                },
                {
                    "text":     f"{'✅ ' if ctype == 'aihub'      else ''}aihub",
                    "callback": self._cb_custom_type, "args": ("aihub",),
                },
            ],
            [{"text": "🗑 Очистить", "callback": self._cb_custom_clear}],
            [
                {"text": "◀️ Назад",   "callback": self._cb_main_menu},
                {"text": "❌ Закрыть", "action":   "close"},
            ],
        ]

    def _keys_text(self) -> str:
        def mask(k: str) -> str:
            return (k[:6] + "…") if k else "не задан"
        return self.strings["keys_menu"].format(
            aihub     = mask(self.config["aihub_key"]),
            openai    = mask(self.config["openai_key"]),
            anthropic = mask(self.config["anthropic_key"]),
            gemini    = mask(self.config["gemini_key"]),
            grok      = mask(self.config["grok_key"]),
            groq      = mask(self.config["groq_key"]),
            openrouter= mask(self.config["openrouter_key"]),
        )

    def _keys_markup(self) -> list:
        return [
            [
                {"text": "✨ OpenAI",    "input": "OpenAI sk-...",          "handler": self._inp_key_openai},
                {"text": "🔮 Anthropic", "input": "Anthropic API-ключ",      "handler": self._inp_key_anthropic},
            ],
            [
                {"text": "💎 Gemini",    "input": "Gemini AIzaSy...",       "handler": self._inp_key_gemini},
                {"text": "🌐 OpenRouter","input": "OpenRouter API-ключ",    "handler": self._inp_key_openrouter},
            ],
            [
                {"text": "🤖 Grok/xAI", "input": "xAI API-ключ",           "handler": self._inp_key_grok},
                {"text": "⚡ Groq",      "input": "Groq API-ключ",          "handler": self._inp_key_groq},
            ],
            [
                {"text": "🔗 AI Hub (универсальный)",
                 "input":   "aihub_... или sk-...",
                 "handler": self._inp_key_aihub},
            ],
            [{"text": "◀️ Назад", "callback": self._cb_main_menu}],
        ]

    def _img_text(self) -> str:
        return (
            "🖼 <b>Настройки генерации изображений</b>\n\n"
            f"Провайдер: <b>{self.config['image_provider']}</b>\n"
            f"Модель: <b>{self.config.get('image_model','dall-e-3')}</b>\n"
            f"Размер: <b>{self.config['image_size']}</b>\n"
            f"Качество: <b>{self.config.get('image_quality','standard')}</b>\n"
            f"Стиль: <b>{self.config.get('image_style','vivid')}</b>"
        )

    def _img_markup(self) -> list:
        cp = self.config["image_provider"]
        cs = self.config["image_size"]
        cq = self.config.get("image_quality", "standard")
        cy = self.config.get("image_style",   "vivid")
        return [
            [
                {"text": f"{'✅ ' if cp=='openai' else ''}OpenAI",
                 "callback": self._cb_img_prov, "args": ("openai",)},
                {"text": f"{'✅ ' if cp=='gemini' else ''}Gemini",
                 "callback": self._cb_img_prov, "args": ("gemini",)},
            ],
            [
                {"text": "🖌 Модель", "input": "Модель: dall-e-3 / dall-e-2 / gpt-image-1",
                 "handler": self._inp_img_model},
            ],
            [
                {"text": f"{'✅ ' if cs=='1024x1024' else ''}1024×1024",
                 "callback": self._cb_img_size, "args": ("1024x1024",)},
                {"text": f"{'✅ ' if cs=='512x512'   else ''}512×512",
                 "callback": self._cb_img_size, "args": ("512x512",)},
                {"text": f"{'✅ ' if cs=='256x256'   else ''}256×256",
                 "callback": self._cb_img_size, "args": ("256x256",)},
            ],
            [
                {"text": f"{'✅ ' if cq=='standard' else ''}standard",
                 "callback": self._cb_img_quality, "args": ("standard",)},
                {"text": f"{'✅ ' if cq=='hd'       else ''}hd",
                 "callback": self._cb_img_quality, "args": ("hd",)},
            ],
            [
                {"text": f"{'✅ ' if cy=='vivid'   else ''}vivid",
                 "callback": self._cb_img_style, "args": ("vivid",)},
                {"text": f"{'✅ ' if cy=='natural' else ''}natural",
                 "callback": self._cb_img_style, "args": ("natural",)},
            ],
            [{"text": "◀️ Назад", "callback": self._cb_main_menu}],
        ]

    def _bridge_text(self) -> str:
        ba  = self.get("bridge_allowed") or []
        bco = self.get("bridge_confirm")
        if bco is None:
            bco = True
        actions = "\n".join(
            f"• <code>{k}</code> — {v}" for k, v in BRIDGE_ACTIONS.items()
        )
        return (
            "🌉 <b>TG Bridge</b>\n\n"
            f"Подтверждение: <b>{'✅ вкл' if bco else '⚠️ выкл'}</b>\n"
            f"Разрешённых чатов-целей: <b>{len(ba)}</b>\n\n"
            f"<b>Доступные действия:</b>\n{actions}\n\n"
            "<i>AI всегда знает о доступе к твоему аккаунту.\n"
            "Просто попроси — например: 'отправь привет в чат 123456'\n"
            "Чтобы AI мог отправлять в чат — сначала добавь его кнопкой ниже.</i>"
        )

    def _bridge_markup(self, chat_id: str) -> list:
        ba  = self.get("bridge_allowed") or []
        bco = self.get("bridge_confirm")
        if bco is None:
            bco = True
        return [
            [
                {"text": ("🚫 Убрать чат из целей" if chat_id in ba else "✅ Разрешить этот чат как цель"),
                 "callback": (self._cb_bridge_deny if chat_id in ba else self._cb_bridge_allow),
                 "args": (chat_id,)},
            ],
            [
                {"text": f"🔔 Подтверждение: {'вкл ✅' if bco else 'выкл ⚠️'}",
                 "callback": self._cb_bridge_toggle_confirm},
            ],
            [
                {"text": "◀️ Назад",   "callback": self._cb_main_menu},
                {"text": "❌ Закрыть", "action":   "close"},
            ],
        ]


    # ═══════════════════════════════════════════════════════════
    #  КОМАНДЫ
    # ═══════════════════════════════════════════════════════════

    @loader.command(ru_doc="Главное меню AI Hub")
    async def aihub(self, message: Message):
        """Открыть главное меню AI Hub"""
        await utils.answer(
            message,
            self._menu_text(message.chat_id),
            reply_markup=self._menu_markup(),
        )

    # ── .ah — главный запрос ──────────────────────────────────
    @loader.command(ru_doc="Отправить запрос AI. Поддерживает reply на фото/видео/файл/стикер")
    async def ah(self, message: Message):
        """Отправить запрос активному AI-провайдеру.
        Поддерживает reply на: фото, видео, стикер, GIF, текстовый файл, PDF."""
        if not self._has_key():
            await utils.answer(message, self.strings["no_key"].format(p=self.get_prefix()))
            return

        text  = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not text and reply:
            text = reply.message or ""

        # Извлекаем медиа из reply или из текущего сообщения
        media_src = (
            reply
            if reply and getattr(reply, "media", None)
            else message
        )
        image_b64, extra_media, media_desc = await self._extract_media(media_src)

        # Добавляем описание медиа к тексту
        if media_desc:
            text = (f"{text} {media_desc}".strip()) if text else media_desc

        if not text and not image_b64 and not extra_media:
            await utils.answer(message, self.strings["no_args"])
            return

        ok_inline  = await self._inline_ok(message)
        m          = await utils.answer(message, self.strings["sending"])
        provider   = self._prov()
        chat_id    = message.chat_id
        use_search = bool(self.config["web_search"])

        # Сохраняем для регенерации
        self.set(f"last_{chat_id}", {
            "text":      text,
            "image_b64": image_b64,
            "extra":     [],  # не сохраняем большие данные
        })

        try:
            result   = await self._send(
                provider   = provider,
                text       = text,
                chat_id    = chat_id,
                image_b64  = image_b64,
                extra_media= extra_media,
                use_search = use_search,
            )
            # Проверяем — не вернул ли API ошибку о неверной модели
            result_text = result.get("text", "")
            if result_text.startswith("❌") and any(
                kw in result_text.lower()
                for kw in ("model", "модел", "does not exist", "invalid model",
                           "not found", "no such", "unknown model", "404")
            ):
                current_model = self._model(provider)
                err_msg = (
                    "❌ <b>Неверная модель:</b> <code>"
                    + current_model
                    + "</code>\n\n"
                    + result_text
                    + "\n\nВыбери другую модель: <code>.ahmodel</code>"
                )
                await m.edit(
                    err_msg,
                    reply_markup=[
                        [{"text": "🤖 Выбрать модель", "callback": self._cb_model_menu}],
                        [{"text": "❌ Закрыть", "action": "close"}],
                    ],
                )
                return
            n        = self._next_n(chat_id)
            response = self._fmt(result, provider, n,
                                 user_text=text, has_image=bool(image_b64))
            await self._deliver(m, response, ok_inline, provider, chat_id, use_search)

        except Exception as e:
            await m.edit(self.strings["error"].format(str(e)))

    # ── .ahimg — генерация изображения ────────────────────────
    @loader.command(ru_doc="Сгенерировать изображение: ahimg [промпт]")
    async def ahimg(self, message: Message):
        """Сгенерировать изображение через AI."""
        if not self._has_key():
            await utils.answer(message, self.strings["no_key"].format(p=self.get_prefix()))
            return

        text  = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not text and reply:
            text = reply.message or ""
        if not text:
            await utils.answer(message, self.strings["no_args"])
            return

        m = await utils.answer(message, self.strings["generating_img"])
        img_bytes, err = await self._gen_image(text)

        if err:
            img_model = self.config.get("image_model", "dall-e-3")
            # Проверяем — ошибка модели или другая
            model_err = any(
                kw in err.lower()
                for kw in ("model", "модел", "does not exist", "invalid", "not found", "404")
            )
            if model_err:
                img_err_msg = (
                    "❌ <b>Неверная модель изображений:</b> <code>"
                    + img_model + "</code>\n\n"
                    + "<code>" + err + "</code>\n\n"
                    + "Доступные модели: <code>dall-e-3</code>, <code>dall-e-2</code>, <code>gpt-image-1</code>\n"
                    + "Измени: <code>.ahcfg image_model dall-e-3</code>"
                )
                await m.edit(
                    img_err_msg,
                    reply_markup=[
                        [{"text": "🖼 Настройки изображений", "callback": self._cb_img_menu}],
                        [{"text": "❌ Закрыть", "action": "close"}],
                    ],
                )
            else:
                await m.edit(self.strings["error"].format(err))
            return

        provider  = self.config["image_provider"]
        img_model = self.config.get("image_model", "dall-e-3")
        size      = self.config["image_size"]
        quality   = self.config.get("image_quality", "standard")
        style     = self.config.get("image_style",   "vivid")

        f = io.BytesIO(img_bytes)
        f.name = "image.png"
        caption = (
            f"🎨 [{provider}] <code>{img_model}</code>\n"
            f"<b>{text[:150]}</b>\n"
            f"<i>{size} | {quality} | {style}</i>"
        )
        await message.client.send_file(message.chat_id, f, caption=caption)
        await m.delete()

    # ── .ahauth — переключить провайдера ──────────────────────
    @loader.command(ru_doc="Переключить AI-провайдера: ahauth [имя]")
    async def ahauth(self, message: Message):
        """Переключить активного AI-провайдера."""
        args = utils.get_args_raw(message).strip().lower()
        if args in ALL_PROVIDERS:
            self.config["provider"] = args
            extra = (
                [[{"text": "⚙️ Настроить", "callback": self._cb_custom_menu}]]
                if args == "custom"
                else []
            )
            await utils.answer(
                message,
                self.strings["provider_set"].format(args),
                reply_markup=extra + [[{"text": "❌ Закрыть", "action": "close"}]],
            )
            return

        await utils.answer(
            message,
            self.strings["provider_menu"].format(self._prov()),
            reply_markup=self._prov_buttons() + [
                [{"text": "❌ Закрыть", "action": "close"}]
            ],
        )

    # ── .ahmodel — выбор модели ───────────────────────────────
    @loader.command(ru_doc="Выбрать модель: ahmodel [название]")
    async def ahmodel(self, message: Message):
        """Выбрать модель для активного провайдера."""
        args = utils.get_args_raw(message).strip()
        if args:
            self.config["model"] = args
            await utils.answer(message, self.strings["model_set"].format(args))
            return

        provider = self._prov()
        current  = self._model(provider)
        quick    = QUICK_MODELS.get(provider, [])
        btns, row = [], []
        for qm in quick:
            row.append({
                "text":     qm,
                "callback": self._cb_set_model,
                "args":     (qm,),
            })
            if len(row) == 2:
                btns.append(row)
                row = []
        if row:
            btns.append(row)
        btns.append([{
            "text":    "✏️ Ввести вручную",
            "input":   "Введи точное название модели",
            "handler": self._inp_model,
        }])
        btns.append([{"text": "🗑 Сбросить (дефолт)", "callback": self._cb_model_reset}])
        btns.append([{"text": "❌ Закрыть", "action": "close"}])

        await utils.answer(
            message,
            f"🤖 <b>Модель:</b> <code>{current}</code>\n<b>Провайдер:</b> {provider}",
            reply_markup=btns,
        )

    # ── .ahprompt — системный промпт ──────────────────────────
    @loader.command(ru_doc="Системный промпт: ahprompt [текст | reply .txt | -c]")
    async def ahprompt(self, message: Message):
        """Системный промпт: ahprompt [текст | reply на .txt файл | -c для очистки]"""
        args  = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if args.strip() == "-c":
            self.set("system_prompt", "")
            await utils.answer(message, self.strings["prompt_cleared"])
            return

        # Reply на файл .txt / .md
        if reply and getattr(reply, "media", None):
            try:
                from telethon.tl.types import MessageMediaDocument
                if isinstance(reply.media, MessageMediaDocument):
                    doc   = reply.media.document
                    mime  = doc.mime_type or ""
                    fname = next(
                        (a.file_name for a in (doc.attributes or []) if hasattr(a, "file_name")),
                        "",
                    )
                    if mime.startswith("text/") or fname.lower().endswith((".txt", ".md")):
                        raw = await reply.download_media(bytes)
                        if raw:
                            file_text = raw.decode("utf-8", errors="replace")
                            self.set("system_prompt", file_text)
                            await utils.answer(
                                message,
                                f"✅ Промпт загружен из <b>{fname}</b> ({len(file_text)} символов)",
                            )
                            return
            except Exception as e:
                await utils.answer(message, self.strings["error"].format(str(e)))
                return

        if not args and reply:
            args = reply.message or ""

        if args.strip():
            self.set("system_prompt", args.strip())
            await utils.answer(message, self.strings["prompt_set"])
            return

        # Показываем меню промпта
        prompt = self.get("system_prompt") or ""
        if prompt:
            markup = [
                [
                    {"text": "✏️ Изменить", "input": "Новый системный промпт", "handler": self._inp_prompt},
                    {"text": "🗑 Очистить", "callback": self._cb_prompt_clear},
                ],
                [{"text": "❌ Закрыть", "action": "close"}],
            ]
            await utils.answer(
                message,
                self.strings["prompt_show"].format(prompt[:2000]),
                reply_markup=markup,
            )
        else:
            await utils.answer(
                message,
                self.strings["no_prompt"],
                reply_markup=[
                    [{"text": "✏️ Задать", "input": "Системный промпт", "handler": self._inp_prompt}],
                    [{"text": "❌ Закрыть", "action": "close"}],
                ],
            )

    # ── .ahres — сбросить контекст ────────────────────────────
    @loader.command(ru_doc="Сбросить контекст: ahres [-a = все]")
    async def ahres(self, message: Message):
        """Сбросить ВСЮ память и историю. -a = полная очистка всех данных."""
        args = utils.get_args_raw(message).strip()
        
        # Полная очистка: все провайдеры, все чаты
        if args == "-a":
            self.set("conversations", {})
            # Сканируем все ключи памяти и удаляем
            for p in ALL_PROVIDERS:
                for chat_key in list((self.get("msg_counter") or {}).keys()):
                    self._clear_hist(p, int(chat_key) if chat_key.lstrip("-").isdigit() else chat_key)
            self.set("msg_counter", {})
            await utils.answer(message, self.strings["ctx_reset_all"])
            return
        
        # Сброс текущего провайдера для текущего чата + conversation ID
        provider = self._prov()
        convs    = self.pointer("conversations", {})
        convs[provider] = None
        self._clear_hist(provider, message.chat_id)
        await utils.answer(message, self.strings["ctx_reset"].format(provider))

    # ── .ahcfg — конфиг ───────────────────────────────────────
    @loader.command(ru_doc="Конфигурация: ahcfg [поле] [значение]")
    async def ahcfg(self, message: Message):
        """Конфигурация AI Hub: ahcfg [поле] [значение]

        Поля: aihub_key, openai_key, anthropic_key, gemini_key,
              grok_key, groq_key, openrouter_key, provider, model,
              temperature, max_tokens, mem_limit, persona, reply_lang,
              web_search, collapse_quotes, image_provider, image_model,
              image_size, image_quality, image_style,
              custom_base_url, custom_api_key, custom_type, custom_model"""
        args = utils.get_args(message)
        if len(args) < 2:
            await utils.answer(
                message,
                self._menu_text(message.chat_id),
                reply_markup=self._menu_markup(),
            )
            return
        field = args[0]
        value = " ".join(args[1:])
        allowed = {
            "aihub_key", "openai_key", "anthropic_key", "gemini_key",
            "grok_key", "groq_key", "openrouter_key",
            "provider", "model", "temperature", "max_tokens", "mem_limit",
            "persona", "reply_lang", "web_search", "collapse_quotes",
            "image_provider", "image_model", "image_size", "image_quality", "image_style",
            "custom_base_url", "custom_api_key", "custom_type", "custom_model",
        }
        if field not in allowed:
            await utils.answer(
                message,
                self.strings["error"].format(f"Неизвестное поле: {field}"),
            )
            return
        try:
            self.config[field] = value
            await utils.answer(message, self.strings["cfg_updated"].format(field, value))
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    # ── .ahcheckkeys — проверить ключи ────────────────────────
    @loader.command(ru_doc="Проверить API-ключи: ahcheckkeys [all|provider]")
    async def ahcheckkeys(self, message: Message):
        """Проверить валидность API-ключей."""
        if not self._has_key():
            await utils.answer(message, self.strings["no_key"].format(p=self.get_prefix()))
            return

        args    = utils.get_args_raw(message).strip()
        targets = BUILTIN_PROVIDERS if (not args or args == "all") else [args]
        m       = await utils.answer(message, self.strings["checking"])
        results = []

        async with aiohttp.ClientSession() as s:
            for p in targets:
                try:
                    async with s.get(
                        f"{AIHUB_BASE}/{p}/conversations",
                        headers=self._auth_headers(p),
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status in (200, 201):
                            results.append(self.strings["key_valid"].format(p))
                        else:
                            results.append(self.strings["key_invalid"].format(p))
                except Exception:
                    results.append(self.strings["key_invalid"].format(p))

        await utils.answer(
            m,
            "🔑 <b>Результаты проверки:</b>\n\n" + "\n".join(results),
            reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
        )

    # ── .ahauto — авто-ответ ──────────────────────────────────
    @loader.command(ru_doc="Авто-ответ AI в чате: ahauto [on/off]")
    async def ahauto(self, message: Message):
        """Включить/выключить авто-ответ AI в этом чате."""
        args    = utils.get_args_raw(message).strip().lower()
        chat_id = str(message.chat_id)
        auto_c  = self.pointer("auto_chats", [])
        enabled = chat_id in auto_c

        if args == "on" or (not args and not enabled):
            if chat_id not in auto_c:
                auto_c.append(chat_id)
            await utils.answer(
                message,
                self.strings["auto_on"],
                reply_markup=[
                    [{"text": "🔕 Выключить", "callback": self._cb_auto_off, "args": (chat_id,)}],
                    [{"text": "❌ Закрыть", "action": "close"}],
                ],
            )
        else:
            if chat_id in auto_c:
                auto_c.remove(chat_id)
            await utils.answer(
                message,
                self.strings["auto_off"],
                reply_markup=[
                    [{"text": "✅ Включить", "callback": self._cb_auto_on, "args": (chat_id,)}],
                    [{"text": "❌ Закрыть", "action": "close"}],
                ],
            )

    # ── .ahsearch — веб-поиск ─────────────────────────────────
    @loader.command(ru_doc="Переключить веб-поиск: ahsearch [on/off]")
    async def ahsearch(self, message: Message):
        """Включить/выключить поиск в интернете."""
        args = utils.get_args_raw(message).strip().lower()
        if args == "on":
            self.config["web_search"] = True
        elif args == "off":
            self.config["web_search"] = False
        else:
            self.config["web_search"] = not bool(self.config["web_search"])
        state = bool(self.config["web_search"])
        await utils.answer(
            message,
            self.strings["search_on" if state else "search_off"],
            reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
        )

    # ── .ahcode — код файлом ──────────────────────────────────
    @loader.command(ru_doc="Попросить AI написать код и получить файлом: ahcode [задача]")
    async def ahcode(self, message: Message):
        """Генерация кода через AI с отправкой файлом (правильное расширение)."""
        if not self._has_key():
            await utils.answer(message, self.strings["no_key"].format(p=self.get_prefix()))
            return

        desc  = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not desc and reply:
            desc = reply.message or ""
        if not desc:
            await utils.answer(message, self.strings["no_args"])
            return

        m        = await utils.answer(message, "⌨️ Генерирую код...")
        provider = self._prov()

        code_prompt = (
            "Ответь ТОЛЬКО кодом без пояснений, без markdown-блоков (без ```).\n"
            "Самая первая строка — язык программирования одним словом в нижнем регистре "
            "(python, javascript, typescript, bash, sql, html, css, go, rust, etc.).\n"
            "Со второй строки — сам код.\n\n"
            f"Задача: {desc}"
        )

        try:
            result = await self._send(provider=provider, text=code_prompt)
            raw    = (result.get("text") or "").strip()
            lines  = raw.splitlines()

            if not lines:
                await m.edit(self.strings["error"].format("Пустой ответ"))
                return

            # Определяем язык из первой строки
            lang_raw = lines[0].strip().lower().lstrip("`#/! ").split()[0] if lines[0].strip() else ""
            ext      = LANG_EXT.get(lang_raw, "")
            body     = "\n".join(lines[1:]).strip() if len(lines) > 1 else raw

            # Если язык не распознан — угадываем по содержимому
            if not ext and lang_raw not in LANG_EXT:
                cb = body.lower()
                if "def " in cb or ("import " in cb and "print(" in cb):
                    lang_raw, ext = "python", ".py"
                elif "function " in cb or "const " in cb or "let " in cb:
                    lang_raw, ext = "javascript", ".js"
                elif "<?php" in cb:
                    lang_raw, ext = "php", ".php"
                elif "#!/bin/bash" in cb or "#!/bin/sh" in cb:
                    lang_raw, ext = "bash", ".sh"
                elif "<html" in cb:
                    lang_raw, ext = "html", ".html"
                elif "select " in cb and "from " in cb:
                    lang_raw, ext = "sql", ".sql"
                else:
                    lang_raw, ext = "txt", ".txt"
                body = raw  # берём весь текст если язык не определили

            # Dockerfile не имеет расширения
            fname = "Dockerfile" if lang_raw == "dockerfile" else f"code{ext}"

            f = io.BytesIO(body.encode("utf-8"))
            f.name = fname

            used_model = result.get("model") or self._model(provider)
            caption = (
                f"⌨️ <b>{lang_raw.capitalize()}</b> | <code>{used_model}</code>\n"
                f"<i>{desc[:150]}</i>"
            )
            await message.client.send_file(message.chat_id, f, caption=caption)
            await m.delete()

        except Exception as e:
            await m.edit(self.strings["error"].format(str(e)))


    # ── .ahbridge — TG Bridge ─────────────────────────────────
    @loader.command(ru_doc="TG Bridge: ahbridge [allow/deny/confirm/status]")
    async def ahbridge(self, message: Message):
        """TG Bridge — управление аккаунтом через AI.

        AI ВСЕГДА знает о доступе к аккаунту и выполняет действия по просьбе.

        .ahbridge allow   — разрешить этот чат как цель (куда AI может слать сообщения)
        .ahbridge deny    — убрать чат из разрешённых целей
        .ahbridge confirm — переключить подтверждение перед действием (по умолч. вкл)
        .ahbridge status  — показать настройки"""
        args    = utils.get_args_raw(message).strip().lower()
        chat_id = str(message.chat_id)
        ba      = self.pointer("bridge_allowed", [])

        if args == "allow":
            if chat_id not in ba:
                ba.append(chat_id)
            await utils.answer(
                message,
                f"✅ Чат <code>{chat_id}</code> добавлен как разрешённая цель. Теперь AI сможет отправлять сюда сообщения.",
                reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
            )
        elif args == "deny":
            if chat_id in ba:
                ba.remove(chat_id)
            await utils.answer(message, f"🚫 Чат <code>{chat_id}</code> убран из целей.")
        elif args == "confirm":
            cur = self.get("bridge_confirm")
            if cur is None:
                cur = True
            self.set("bridge_confirm", not cur)
            await utils.answer(
                message,
                f"🔔 Подтверждение: {'✅ вкл' if not cur else '⚠️ выкл'}",
            )
        else:
            await utils.answer(
                message,
                self._bridge_text(),
                reply_markup=self._bridge_markup(chat_id),
            )

    # ── .ahconvs — разговоры ──────────────────────────────────
    @loader.command(ru_doc="Список разговоров: ahconvs [provider]")
    async def ahconvs(self, message: Message):
        """Список разговоров провайдера в AI Hub."""
        if not self._has_key():
            await utils.answer(message, self.strings["no_key"].format(p=self.get_prefix()))
            return

        args     = utils.get_args_raw(message).strip()
        provider = args if args in BUILTIN_PROVIDERS else self._prov()

        if provider == "custom":
            hist  = self._hist("custom", message.chat_id)
            pairs = len(hist) // 2
            await utils.answer(
                message,
                f"📋 <b>Кастомный провайдер</b>\nПар сообщений: <b>{pairs}</b>",
                reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
            )
            return

        m = await utils.answer(message, "⏳ Загружаю...")
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"{AIHUB_BASE}/{provider}/conversations",
                    headers=self._auth_headers(provider),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        await m.edit(self.strings["error"].format(f"HTTP {resp.status}"))
                        return
                    convs = await resp.json(content_type=None)
        except Exception as e:
            await m.edit(self.strings["error"].format(str(e)))
            return

        if not convs:
            await utils.answer(m, self.strings["no_convs"].format(provider))
            return

        lines = [
            f"<code>{c['id']}</code> — {c.get('title', 'Без названия')}"
            for c in convs[:20]
        ]
        await utils.answer(
            m,
            self.strings["convs_list"].format(provider, "\n".join(lines)),
            reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
        )

    # ── .ahimportkey / .ahik ──────────────────────────────────
    @loader.command(ru_doc="Импорт универсального AI Hub ключа: ahimportkey [ключ]")
    async def ahimportkey(self, message: Message):
        """Импорт AI Hub API-ключа (aihub_... или sk-...)."""
        args  = utils.get_args_raw(message).strip()
        reply = await message.get_reply_message()
        if not args and reply:
            args = (reply.message or "").strip()

        if not args:
            await utils.answer(
                message,
                "🔑 <b>Импорт AI Hub API-ключа</b>",
                reply_markup=[
                    [{"text": "✏️ Ввести ключ", "input": "aihub_... или sk-...", "handler": self._inp_key_aihub}],
                    [{"text": "❌ Отмена", "action": "close"}],
                ],
            )
            return

        if args.startswith(("aihub_", "sk-")):
            self.config["aihub_key"] = args
            await utils.answer(message, self.strings["key_saved"])
        else:
            await utils.answer(
                message,
                self.strings["error"].format("Неверный формат ключа. Нужен aihub_... или sk-..."),
            )

    @loader.command(ru_doc="Алиас: ahimportkey")
    async def ahik(self, message: Message):
        """Алиас команды ahimportkey."""
        await self.ahimportkey(message)

    @loader.command(ru_doc="Удалить универсальный AI Hub ключ")
    async def ahck(self, message: Message):
        """Удалить универсальный AI Hub API-ключ."""
        self.config["aihub_key"] = ""
        await utils.answer(message, self.strings["keys_removed"])

    # ── .ahinline — управление inline ────────────────────────
    @loader.command(ru_doc="Управление inline-кнопками: ahinline [on/off/reset]")
    async def ahinline(self, message: Message):
        """Управление inline-кнопками в текущем чате.
        on — принудительно включить
        off — отключить
        reset — вернуть авто-определение"""
        args      = utils.get_args_raw(message).strip().lower()
        chat_id   = str(message.chat_id)
        cache_key = f"inline_ok_{chat_id}"

        if args == "on":
            self.set(cache_key, True)
            await utils.answer(
                message,
                "✅ Inline-кнопки <b>включены</b> для этого чата.",
                reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
            )
        elif args == "off":
            self.set(cache_key, False)
            await utils.answer(message, "🔕 Inline-кнопки <b>отключены</b> для этого чата.")
        elif args == "reset":
            self.set(cache_key, None)
            await utils.answer(message, "🔄 Авто-определение inline сброшено.")
        else:
            cur = self.get(cache_key)
            if cur is True:
                status = "✅ включены (вручную)"
            elif cur is False:
                status = "🔕 отключены (вручную)"
            else:
                detected = await self._inline_ok(message)
                status = f"{'✅' if detected else '🔕'} {'включены' if detected else 'отключены'} (авто)"
            await utils.answer(
                message,
                f"🔘 Inline-кнопки: <b>{status}</b>",
                reply_markup=[
                    [
                        {"text": "✅ Включить",  "callback": self._cb_inline_on,    "args": (chat_id,)},
                        {"text": "🔕 Отключить", "callback": self._cb_inline_off,   "args": (chat_id,)},
                    ],
                    [{"text": "🔄 Авто",         "callback": self._cb_inline_reset, "args": (chat_id,)}],
                    [{"text": "❌ Закрыть", "action": "close"}],
                ],
            )

    # ═══════════════════════════════════════════════════════════
    #  CALLBACKS
    # ═══════════════════════════════════════════════════════════

    # ── Главное меню ──────────────────────────────────────────
    async def _cb_main_menu(self, call):
        await call.edit(self._menu_text(), reply_markup=self._menu_markup())

    # ── Провайдеры ────────────────────────────────────────────
    async def _cb_prov_menu(self, call):
        await call.edit(
            self.strings["provider_menu"].format(self._prov()),
            reply_markup=self._prov_buttons() + [
                [{"text": "◀️ Назад", "callback": self._cb_main_menu}],
            ],
        )

    async def _cb_set_prov(self, call, provider: str):
        self.config["provider"] = provider
        await call.answer(f"✅ {provider}")
        if provider == "custom":
            await call.edit(self._custom_text(), reply_markup=self._custom_markup())
        else:
            await call.edit(
                self.strings["provider_set"].format(provider),
                reply_markup=[
                    [{"text": "◀️ Назад", "callback": self._cb_main_menu}],
                    [{"text": "❌ Закрыть", "action": "close"}],
                ],
            )

    # ── Поиск ─────────────────────────────────────────────────
    async def _cb_toggle_search(self, call):
        self.config["web_search"] = not bool(self.config["web_search"])
        state = bool(self.config["web_search"])
        await call.answer("🔍 вкл" if state else "🔕 выкл")
        await call.edit(
            self.strings["search_on" if state else "search_off"],
            reply_markup=[
                [{"text": "◀️ Назад", "callback": self._cb_main_menu}],
                [{"text": "❌ Закрыть", "action": "close"}],
            ],
        )

    # ── Ключи ─────────────────────────────────────────────────
    async def _cb_keys_menu(self, call):
        await call.edit(self._keys_text(), reply_markup=self._keys_markup())

    async def _inp_key_aihub(self, call, data: str):
        self.config["aihub_key"] = data.strip()
        await call.answer("✅")
        await call.edit(self._keys_text(), reply_markup=self._keys_markup())

    async def _inp_key_openai(self, call, data: str):
        self.config["openai_key"] = data.strip()
        await call.answer("✅")
        await call.edit(self._keys_text(), reply_markup=self._keys_markup())

    async def _inp_key_anthropic(self, call, data: str):
        self.config["anthropic_key"] = data.strip()
        await call.answer("✅")
        await call.edit(self._keys_text(), reply_markup=self._keys_markup())

    async def _inp_key_gemini(self, call, data: str):
        self.config["gemini_key"] = data.strip()
        await call.answer("✅")
        await call.edit(self._keys_text(), reply_markup=self._keys_markup())

    async def _inp_key_openrouter(self, call, data: str):
        self.config["openrouter_key"] = data.strip()
        await call.answer("✅")
        await call.edit(self._keys_text(), reply_markup=self._keys_markup())

    async def _inp_key_grok(self, call, data: str):
        self.config["grok_key"] = data.strip()
        await call.answer("✅")
        await call.edit(self._keys_text(), reply_markup=self._keys_markup())

    async def _inp_key_groq(self, call, data: str):
        self.config["groq_key"] = data.strip()
        await call.answer("✅")
        await call.edit(self._keys_text(), reply_markup=self._keys_markup())

    # ── Кастомный провайдер ───────────────────────────────────
    async def _cb_custom_menu(self, call):
        await call.edit(self._custom_text(), reply_markup=self._custom_markup())

    async def _inp_custom_url(self, call, data: str):
        self.config["custom_base_url"] = data.strip().rstrip("/")
        await call.answer("✅")
        await call.edit(self._custom_text(), reply_markup=self._custom_markup())

    async def _inp_custom_key(self, call, data: str):
        self.config["custom_api_key"] = data.strip()
        await call.answer("✅")
        await call.edit(self._custom_text(), reply_markup=self._custom_markup())

    async def _inp_custom_model(self, call, data: str):
        self.config["custom_model"] = data.strip()
        await call.answer("✅")
        await call.edit(self._custom_text(), reply_markup=self._custom_markup())

    async def _cb_custom_type(self, call, ctype: str):
        self.config["custom_type"] = ctype
        await call.answer(f"✅ {ctype}")
        await call.edit(self._custom_text(), reply_markup=self._custom_markup())

    async def _cb_custom_clear(self, call):
        for f in ("custom_base_url", "custom_api_key", "custom_model"):
            self.config[f] = ""
        self.config["custom_type"] = "openai"
        await call.answer("🗑 Очищено")
        await call.edit(self._custom_text(), reply_markup=self._custom_markup())

    # ── Модель ────────────────────────────────────────────────
    async def _cb_model_menu(self, call):
        provider = self._prov()
        current  = self._model(provider)
        quick    = QUICK_MODELS.get(provider, [])
        btns, row = [], []
        for qm in quick:
            row.append({"text": qm, "callback": self._cb_set_model, "args": (qm,)})
            if len(row) == 2:
                btns.append(row)
                row = []
        if row:
            btns.append(row)
        btns.append([{
            "text":    "✏️ Ввести вручную",
            "input":   "Название модели",
            "handler": self._inp_model,
        }])
        btns.append([{"text": "🗑 Сбросить (дефолт)", "callback": self._cb_model_reset}])
        btns.append([{"text": "◀️ Назад", "callback": self._cb_main_menu}])
        await call.edit(
            f"🤖 <b>Модель:</b> <code>{current}</code>\n<b>Провайдер:</b> {provider}",
            reply_markup=btns,
        )

    async def _cb_set_model(self, call, model: str):
        self.config["model"] = model
        await call.answer(f"✅ {model}")
        await self._cb_model_menu(call)

    async def _inp_model(self, call, data: str):
        self.config["model"] = data.strip()
        await call.edit(
            self.strings["model_set"].format(data.strip()),
            reply_markup=[[{"text": "◀️ Назад", "callback": self._cb_main_menu}]],
        )

    async def _cb_model_reset(self, call):
        self.config["model"] = ""
        await call.answer("✅ Сброшено")
        await self._cb_model_menu(call)

    # ── Температура ───────────────────────────────────────────
    async def _inp_temp(self, call, data: str):
        try:
            val = float(data.strip())
            if not 0.0 <= val <= 2.0:
                raise ValueError
            self.config["temperature"] = val
            await call.edit(
                f"🌡 Температура: <b>{val}</b>",
                reply_markup=[[{"text": "◀️ Назад", "callback": self._cb_main_menu}]],
            )
        except ValueError:
            await call.answer("❌ Неверное значение (0.0–2.0)")

    # ── Промпт ────────────────────────────────────────────────
    async def _cb_prompt_menu(self, call):
        prompt = self.get("system_prompt") or ""
        markup = [
            [
                {"text": "✏️ Изменить" if prompt else "✏️ Задать",
                 "input":   "Системный промпт",
                 "handler": self._inp_prompt},
            ],
        ]
        if prompt:
            markup.append([{"text": "🗑 Очистить", "callback": self._cb_prompt_clear}])
        markup.append([{"text": "◀️ Назад", "callback": self._cb_main_menu}])
        await call.edit(
            self.strings["prompt_show"].format(prompt[:1500]) if prompt else self.strings["no_prompt"],
            reply_markup=markup,
        )

    async def _inp_prompt(self, call, data: str):
        self.set("system_prompt", data.strip())
        await call.edit(
            self.strings["prompt_set"],
            reply_markup=[[{"text": "◀️ Назад", "callback": self._cb_main_menu}]],
        )

    async def _cb_prompt_clear(self, call):
        self.set("system_prompt", "")
        await call.edit(
            self.strings["prompt_cleared"],
            reply_markup=[[{"text": "◀️ Назад", "callback": self._cb_main_menu}]],
        )

    # ── Изображения ───────────────────────────────────────────
    async def _cb_img_menu(self, call):
        await call.edit(self._img_text(), reply_markup=self._img_markup())

    async def _cb_img_prov(self, call, prov: str):
        self.config["image_provider"] = prov
        await call.answer(f"✅ {prov}")
        await call.edit(self._img_text(), reply_markup=self._img_markup())

    async def _inp_img_model(self, call, data: str):
        self.config["image_model"] = data.strip()
        await call.answer("✅")
        await call.edit(self._img_text(), reply_markup=self._img_markup())

    async def _cb_img_size(self, call, size: str):
        self.config["image_size"] = size
        await call.answer(f"✅ {size}")
        await call.edit(self._img_text(), reply_markup=self._img_markup())

    async def _cb_img_quality(self, call, q: str):
        self.config["image_quality"] = q
        await call.answer(f"✅ {q}")
        await call.edit(self._img_text(), reply_markup=self._img_markup())

    async def _cb_img_style(self, call, s: str):
        self.config["image_style"] = s
        await call.answer(f"✅ {s}")
        await call.edit(self._img_text(), reply_markup=self._img_markup())

    # ── Сброс контекста ───────────────────────────────────────
    async def _cb_reset_confirm(self, call, provider: str):
        await call.edit(
            f"⚠️ Сбросить контекст для <b>{provider}</b>?",
            reply_markup=[
                [
                    {"text": "⚠️ Да, сбросить", "callback": self._cb_do_reset,  "args": (provider,)},
                    {"text": "❌ Нет",           "callback": self._cb_main_menu},
                ],
            ],
        )

    async def _cb_do_reset(self, call, provider: str):
        # Сбрасываем conversation ID
        convs = self.pointer("conversations", {})
        convs[provider] = None
        # Сбрасываем всю историю для всех чатов этого провайдера
        for chat_key in list((self.get("msg_counter") or {}).keys()):
            self._clear_hist(
                provider,
                int(chat_key) if chat_key.lstrip("-").isdigit() else chat_key
            )
        await call.answer("🗑 Сброшено")
        await call.edit(
            self.strings["ctx_reset"].format(provider),
            reply_markup=[[{"text": "◀️ Назад", "callback": self._cb_main_menu}]],
        )

    # ── Регенерация ───────────────────────────────────────────
    async def _cb_clear_mem(self, call, provider: str, chat_id):
        """Мгновенный сброс памяти прямо из ответа."""
        # Сбрасываем conversation ID и историю
        convs = self.pointer("conversations", {})
        convs[provider] = None
        self._clear_hist(provider, chat_id)
        await call.answer("🗑 Память очищена")
        # Обновляем кнопки — показываем [0/∞]
        try:
            markup = self._response_markup(provider, chat_id,
                                           bool(self.config["web_search"]), 0)
            await call.edit(reply_markup=markup)
        except Exception:
            pass

    async def _cb_regen(self, call, provider: str, chat_id):
        last = self.get(f"last_{chat_id}") or {}
        text = last.get("text", "")
        image_b64 = last.get("image_b64")

        if not text and not image_b64:
            await call.answer("❌ Нет последнего запроса")
            return

        await call.answer("🔄 Регенерирую...")
        try:
            await call.edit("⏳ Регенерирую...")
        except Exception:
            pass

        use_search = bool(self.config["web_search"])
        try:
            result   = await self._send(
                provider  = provider,
                text      = text,
                chat_id   = chat_id,
                image_b64 = image_b64,
                use_search= use_search,
            )
            n        = self._next_n(chat_id)
            response = self._fmt(result, provider, n,
                                 user_text=text, has_image=bool(image_b64))
            await self._deliver(
                call, response, True, provider, chat_id, use_search, is_call=True
            )
        except Exception as e:
            try:
                await call.edit(self.strings["error"].format(str(e)))
            except Exception:
                pass

    # ── Авто-ответ ────────────────────────────────────────────
    async def _cb_auto_on(self, call, chat_id: str):
        lst = self.pointer("auto_chats", [])
        if chat_id not in lst:
            lst.append(chat_id)
        await call.answer("✅")
        await call.edit(
            self.strings["auto_on"],
            reply_markup=[
                [{"text": "🔕 Выключить", "callback": self._cb_auto_off, "args": (chat_id,)}],
                [{"text": "❌ Закрыть", "action": "close"}],
            ],
        )

    async def _cb_auto_off(self, call, chat_id: str):
        lst = self.pointer("auto_chats", [])
        if chat_id in lst:
            lst.remove(chat_id)
        await call.answer("🔕")
        await call.edit(
            self.strings["auto_off"],
            reply_markup=[
                [{"text": "✅ Включить", "callback": self._cb_auto_on, "args": (chat_id,)}],
                [{"text": "❌ Закрыть", "action": "close"}],
            ],
        )


    async def _cb_inline_on(self, call, chat_id: str):
        self.set(f"inline_ok_{chat_id}", True)
        await call.answer("✅")
        await call.edit(
            "✅ Inline-кнопки <b>включены</b>.",
            reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
        )

    async def _cb_inline_off(self, call, chat_id: str):
        self.set(f"inline_ok_{chat_id}", False)
        await call.answer("🔕")
        await call.edit(
            "🔕 Inline-кнопки <b>отключены</b>.",
            reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
        )

    async def _cb_inline_reset(self, call, chat_id: str):
        self.set(f"inline_ok_{chat_id}", None)
        await call.answer("🔄")
        await call.edit(
            "🔄 Авто-определение inline сброшено.",
            reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
        )

    # ── Bridge callbacks ──────────────────────────────────────
    async def _cb_bridge_menu(self, call):
        try:
            chat_id = str(call.chat_id)
        except Exception:
            chat_id = "0"
        await call.edit(
            self._bridge_text(),
            reply_markup=self._bridge_markup(chat_id),
        )

    async def _cb_bridge_on(self, call, chat_id: str):
        bc = self.pointer("bridge_chats", [])
        if chat_id not in bc:
            bc.append(chat_id)
        await call.answer("✅ Bridge вкл")
        await call.edit(self._bridge_text(), reply_markup=self._bridge_markup(chat_id))

    async def _cb_bridge_off(self, call, chat_id: str):
        bc = self.pointer("bridge_chats", [])
        if chat_id in bc:
            bc.remove(chat_id)
        await call.answer("🔕 Bridge выкл")
        await call.edit(self._bridge_text(), reply_markup=self._bridge_markup(chat_id))

    async def _cb_bridge_allow(self, call, chat_id: str):
        ba = self.pointer("bridge_allowed", [])
        if chat_id not in ba:
            ba.append(chat_id)
        await call.answer("✅ Разрешено")
        await call.edit(self._bridge_text(), reply_markup=self._bridge_markup(chat_id))

    async def _cb_bridge_deny(self, call, chat_id: str):
        ba = self.pointer("bridge_allowed", [])
        if chat_id in ba:
            ba.remove(chat_id)
        await call.answer("🚫 Убрано")
        await call.edit(self._bridge_text(), reply_markup=self._bridge_markup(chat_id))

    async def _cb_bridge_toggle_confirm(self, call):
        cur = self.get("bridge_confirm")
        if cur is None:
            cur = True
        self.set("bridge_confirm", not cur)
        await call.answer("🔔 Переключено")
        try:
            chat_id = str(call.chat_id)
        except Exception:
            chat_id = "0"
        await call.edit(self._bridge_text(), reply_markup=self._bridge_markup(chat_id))

    async def _cb_bridge_exec(self, call, action: str, params_json: str, origin_chat: str):
        """Выполняет Bridge-действие после подтверждения."""
        await call.answer("⚙️ Выполняю...")
        try:
            params = json.loads(params_json)
            result = await self._bridge_exec(call.client, action, params, origin_chat)
            await call.edit(
                f"🌉 <b>Bridge:</b> {result}",
                reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
            )
        except Exception as e:
            await call.edit(
                self.strings["error"].format(str(e)),
                reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
            )

    async def _cb_bridge_cancel(self, call):
        await call.answer("❌ Отменено")
        await call.edit(
            "🚫 Действие отменено.",
            reply_markup=[[{"text": "❌ Закрыть", "action": "close"}]],
        )

    # ═══════════════════════════════════════════════════════════
    #  WATCHERS
    # ═══════════════════════════════════════════════════════════

    # ── Авто-ответ (входящие) ─────────────────────────────────
    @loader.watcher(only_messages=True, in_=True, no_commands=True)
    async def auto_reply_watcher(self, message: Message):
        """Отвечает на входящие сообщения в чатах с авто-ответом."""
        if not getattr(message, "message", None):
            return
        if not self._has_key():
            return

        chat_id = str(message.chat_id)
        if chat_id not in (self.get("auto_chats") or []):
            return

        provider   = self._prov()
        use_search = bool(self.config["web_search"])
        ok_inline  = await self._inline_ok(message)

        try:
            result   = await self._send(
                provider  = provider,
                text      = message.message,
                chat_id   = message.chat_id,
                use_search= use_search,
            )
            n        = self._next_n(message.chat_id)
            response = self._fmt(result, provider, n, user_text=message.message)
            self.set(f"last_{message.chat_id}", {
                "text": message.message, "image_b64": None
            })

            if ok_inline:
                placeholder = await message.reply("⏳")
                await self._deliver(
                    placeholder, response, True,
                    provider, message.chat_id, use_search,
                )
            else:
                # Без inline — файл если длинный, иначе plain reply
                if len(response) > MAX_TG_MSG:
                    plain = re.sub(r"<[^>]+>", "", response)
                    f = io.BytesIO(plain.encode("utf-8"))
                    f.name = "answer.txt"
                    await message.reply("📄 Ответ отправлен файлом")
                    await message.client.send_file(
                        message.chat_id, f, caption="📄 <b>Полный ответ AI</b>"
                    )
                else:
                    await message.reply(response)

        except Exception:
            pass

    # ── Bridge (исходящие) ────────────────────────────────────
    @loader.watcher(only_messages=True, out=True, no_commands=True)
    async def bridge_watcher(self, message: Message):
        """Слушает исходящие сообщения в Bridge-чатах и обрабатывает через AI."""
        if not getattr(message, "message", None):
            return
        if not self._has_key():
            return

        chat_id = str(message.chat_id)
        # Bridge всегда активен для исходящих сообщений — AI знает о доступе

        text_lower = message.message.lower()
        if not any(t in text_lower for t in BRIDGE_TRIGGERS):
            return

        provider = self._prov()

        # Специальный промпт для Bridge
        bridge_sys = (
            "Ты управляешь Telegram-аккаунтом пользователя. "
            "Пользователь — это ты. Общайся от первого лица.\n"
            "При запросе действия отвечай ТОЛЬКО JSON (без markdown, без пояснений):\n"
            '{"action":"<действие>","params":{<параметры>},"comment":"<подтверждение>"}\n'
            "Действия: send_message (chat_id, text), set_name (first_name, last_name), "
            "set_bio (bio), set_username (username), delete_message (chat_id), "
            "react (chat_id, emoji), pin_message (chat_id, message_id).\n"
            f"Разрешённые цели: {', '.join(self.get('bridge_allowed') or [])}.\n"
            "Если запрос не про Telegram — "
            '{"action":"none","params":{},"comment":"<обычный ответ>"}.'
        )

        old_prompt = self.get("system_prompt") or ""
        self.set("system_prompt", bridge_sys)

        try:
            result = await self._send(
                provider = provider,
                text     = message.message,
            )
            self.set("system_prompt", old_prompt)

            raw = (result.get("text") or "").strip()
            # Убираем markdown если AI добавил
            raw = re.sub(r"```(?:json)?\n?|```", "", raw).strip()

            try:
                data = json.loads(raw)
            except Exception:
                # Не JSON — просто ответ на вопрос
                if raw:
                    await message.reply(f"🤖 {raw}")
                return

            action  = data.get("action", "none")
            params  = data.get("params", {})
            comment = data.get("comment", "")

            if action == "none":
                if comment:
                    await message.reply(f"🤖 {comment}")
                return

            if action not in BRIDGE_ACTIONS:
                await message.reply(f"❌ Bridge: неизвестное действие <code>{action}</code>")
                return

            action_label = BRIDGE_ACTIONS[action]
            params_json  = json.dumps(params, ensure_ascii=False)
            confirm      = self.get("bridge_confirm")
            if confirm is None:
                confirm = True

            preview = "\n".join(f"  {k}: <b>{v}</b>" for k, v in params.items())
            confirm_text = (
                f"🌉 <b>Bridge хочет выполнить:</b>\n"
                f"Действие: <code>{action}</code> — {action_label}\n"
                f"Параметры:\n{preview}\n\n"
                f"💬 <i>{comment}</i>"
            )

            ok_inline = await self._inline_ok(message)

            if confirm and ok_inline:
                placeholder = await message.reply("⏳")
                await utils.answer(
                    placeholder,
                    confirm_text,
                    reply_markup=[
                        [
                            {
                                "text":     "✅ Выполнить",
                                "callback": self._cb_bridge_exec,
                                "args":     (action, params_json, chat_id),
                            },
                            {
                                "text":     "❌ Отмена",
                                "callback": self._cb_bridge_cancel,
                            },
                        ]
                    ],
                )
            else:
                # Без подтверждения или без inline — выполняем сразу
                result_str = await self._bridge_exec(message.client, action, params, chat_id)
                await message.reply(
                    f"🌉 <b>Bridge:</b> {result_str}\n💬 <i>{comment}</i>"
                )

        except Exception:
            self.set("system_prompt", old_prompt)
