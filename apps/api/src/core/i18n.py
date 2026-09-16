"""API i18n (docs: multi-language required; current language: English).

Language from `Accept-Language` via request-scoped contextvar.
All user-facing error strings go through `t()`.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Literal

Lang = Literal["en", "ru"]

DEFAULT_LANG: Lang = "en"

_current_lang: ContextVar[Lang] = ContextVar("api_lang", default=DEFAULT_LANG)

_MESSAGES: dict[str, dict[Lang, str]] = {
    "unauthorized.missing_token": {
        "en": "Missing bearer token",
        "ru": "Отсутствует bearer token",
    },
    "unauthorized.invalid_token": {
        "en": "Invalid or expired token",
        "ru": "Невалидный или истёкший токен",
    },
    "unauthorized.user_not_found": {
        "en": "User not found",
        "ru": "Пользователь не найден",
    },
    "unauthorized.sso_failed": {
        "en": "SSO authentication failed",
        "ru": "Ошибка входа через SSO",
    },
    "unauthorized.email_conflict": {
        "en": "Email already linked to another SSO account",
        "ru": "Email уже привязан к другому SSO-аккаунту",
    },
    "unauthorized.refresh_invalid": {
        "en": "Invalid refresh token",
        "ru": "Невалидный refresh token",
    },
    "forbidden.moderator_required": {
        "en": "Moderator role required",
        "ru": "Требуется роль модератора",
    },
    "forbidden.sudo_required": {
        "en": "Sudo privileges required",
        "ru": "Требуются sudo-права",
    },
    "forbidden.club_leader_required": {
        "en": "Club leader role required",
        "ru": "Требуется роль лидера клуба",
    },
    "forbidden.not_leader_of_club": {
        "en": "Not a leader of this club",
        "ru": "Вы не являетесь лидером этого клуба",
    },
    "forbidden.insufficient_role": {
        "en": "Insufficient role",
        "ru": "Недостаточно прав",
    },
    "forbidden.cannot_create_report": {
        "en": "Moderators cannot create club reports",
        "ru": "Модераторы не создают отчёты клубов",
    },
    "forbidden.use_moderation_endpoints": {
        "en": "Use moderation endpoints",
        "ru": "Используйте endpoint'ы модерации",
    },
    "forbidden.cannot_submit": {
        "en": "Moderators cannot submit reports",
        "ru": "Модераторы не отправляют отчёты",
    },
    "forbidden.moderator_not_leader": {
        "en": "Moderator cannot be a club leader",
        "ru": "Модератор не может быть лидером клуба",
    },
    "report.not_found": {"en": "Report not found", "ru": "Отчёт не найден"},
    "report.criteria_not_found": {
        "en": "Criteria not found",
        "ru": "Критерий не найден",
    },
    "report.delete_only_draft": {
        "en": "Only DRAFT reports can be deleted by a leader",
        "ru": "Лидер может удалить только черновик",
    },
    "moderation.comment_required": {
        "en": "Comment is required for CHANGES_REQUIRED or custom finalPoints",
        "ru": "Комментарий обязателен для CHANGES_REQUIRED или изменения баллов",
    },
    "rules.version_not_found": {
        "en": "No rules version configured",
        "ru": "Не настроена версия правил",
    },
    "sync.failed": {"en": "Yandex sync failed", "ru": "Ошибка синхронизации с Яндексом"},
    "sudo.reason_required": {
        "en": "reason is required",
        "ru": "Поле reason обязательно",
    },
    "archive.no_candidates": {
        "en": "No COMPLETED or CLOSED reports to archive",
        "ru": "Нет COMPLETED/CLOSED отчётов для архивации",
    },
    "rate.limited": {
        "en": "Too many requests",
        "ru": "Слишком много запросов",
    },
    "validation.invalid": {
        "en": "Validation failed",
        "ru": "Ошибка валидации",
    },
}


def normalize_lang(header: str | None) -> Lang:
    if not header:
        return DEFAULT_LANG
    first = header.split(",")[0].split(";")[0].strip().lower()
    if first.startswith("ru"):
        return "ru"
    return "en"


def set_request_lang(lang: Lang) -> None:
    _current_lang.set(lang)


def get_request_lang() -> Lang:
    return _current_lang.get()


def t(key: str, lang: Lang | None = None, **kwargs: object) -> str:
    active = lang or _current_lang.get()
    entry = _MESSAGES.get(key)
    if entry is None:
        return key
    text = entry.get(active) or entry["en"]
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
