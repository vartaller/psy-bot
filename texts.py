from __future__ import annotations

# (tz_id, display_label) — label is language-neutral (city names are similar in uk/ru)
TIMEZONES: list[tuple[str, str]] = [
    ("Europe/Kyiv",         "🇺🇦 Київ / Киев          UTC+2/+3"),
    ("Europe/Minsk",        "🇧🇾 Мінськ / Минск        UTC+3"),
    ("Europe/Moscow",       "🇷🇺 Москва                UTC+3"),
    ("Europe/Samara",       "🇷🇺 Самара                UTC+4"),
    ("Asia/Yekaterinburg",  "🇷🇺 Єкатеринбург          UTC+5"),
    ("Asia/Omsk",           "🇷🇺 Омськ / Омск          UTC+6"),
    ("Asia/Novosibirsk",    "🇷🇺 Новосибірськ          UTC+7"),
    ("Asia/Krasnoyarsk",    "🇷🇺 Красноярськ           UTC+7"),
    ("Asia/Irkutsk",        "🇷🇺 Іркутськ / Иркутск   UTC+8"),
    ("Asia/Yakutsk",        "🇷🇺 Якутськ / Якутск     UTC+9"),
    ("Asia/Vladivostok",    "🇷🇺 Владивосток           UTC+10"),
    ("Asia/Magadan",        "🇷🇺 Магадан               UTC+11"),
    ("Asia/Kamchatka",      "🇷🇺 Камчатка              UTC+12"),
    ("Asia/Tbilisi",        "🇬🇪 Тбілісі / Тбилиси    UTC+4"),
    ("Asia/Baku",           "🇦🇿 Баку                  UTC+4"),
    ("Asia/Yerevan",        "🇦🇲 Єреван / Ереван       UTC+4"),
    ("Asia/Tashkent",       "🇺🇿 Ташкент               UTC+5"),
    ("Asia/Almaty",         "🇰🇿 Алмати / Алматы       UTC+6"),
    ("Europe/London",       "🇬🇧 Лондон                UTC+0/+1"),
    ("Europe/Berlin",       "🇩🇪 Берлін / Берлин       UTC+1/+2"),
    ("Europe/Paris",        "🇫🇷 Париж                 UTC+1/+2"),
    ("Europe/Istanbul",     "🇹🇷 Стамбул               UTC+3"),
    ("Asia/Dubai",          "🇦🇪 Дубай                 UTC+4"),
    ("Asia/Jerusalem",      "🇮🇱 Єрусалим              UTC+2/+3"),
    ("Asia/Bangkok",        "🇹🇭 Бангкок               UTC+7"),
    ("Asia/Singapore",      "🇸🇬 Сінгапур              UTC+8"),
    ("Asia/Tokyo",          "🇯🇵 Токіо / Токио         UTC+9"),
    ("America/New_York",    "🇺🇸 Нью-Йорк              UTC-5/-4"),
    ("America/Chicago",     "🇺🇸 Чикаго                UTC-6/-5"),
    ("America/Los_Angeles", "🇺🇸 Лос-Анджелес          UTC-8/-7"),
    ("Australia/Sydney",    "🇦🇺 Сідней / Сидней       UTC+10/+11"),
    ("Pacific/Auckland",    "🇳🇿 Окленд                UTC+12/+13"),
]

_TZ_DISPLAY: dict[str, str] = {tz_id: label for tz_id, label in TIMEZONES}

TEXTS: dict[str, dict] = {
    "uk": {
        # Language selection
        "choose_lang": "🇺🇦 Оберіть мову / 🇷🇺 Выберите язык:",

        # Welcome
        "welcome": (
            "Привіт! Це застосунок для психологічної роботи.\n\n"
            "Оберіть розділ нижче 👇"
        ),

        # Main menu buttons
        "btn_activities": "📚 Заняття",
        "btn_history": "📊 Мої записи",   # kept for backward-compat with old keyboards
        "btn_records": "📊 Мої записи",   # inline button inside activity detail

        # General
        "back": "← Назад",
        "cancel_btn": "✖️ Скасувати",
        "yes_btn": "✅ Так",
        "no_btn": "❌ Ні",
        "error": "Сталася помилка. Спробуйте ще раз.",

        # Activities list
        "activities_title": "📚 Доступні заняття:\n\nОберіть заняття для деталей.",
        "activities_empty": "Наразі немає доступних занять.",

        # Activity detail template (built dynamically in handler)
        "status_subscribed": "✅ Підписаний",
        "status_not_subscribed": "⚪ Не підписаний",
        "reminder_info": "⏰ Щодня о {time} ({tz})",
        "btn_subscribe": "✅ Підписатися",
        "btn_unsubscribe": "❌ Відписатися",
        "btn_change_reminder": "⏰ {time} | {tz}",
        "btn_start_now": "🚀 Розпочати зараз",

        # Subscribe flow
        "sub_ask_time": (
            "Вкажіть час щоденного нагадування.\n"
            "Формат: ГГ:ХХ (наприклад, <code>20:30</code>)"
        ),
        "sub_time_invalid": (
            "Невірний формат. Введіть час у вигляді ГГ:ХХ\n"
            "(наприклад, <code>21:00</code>):"
        ),
        "sub_ask_tz": "Оберіть ваш часовий пояс:",
        "sub_done": "✅ Підписано!\nНагадування щодня о {time} ({tz}).",
        "time_updated": "⏰ Час нагадування змінено: {time} ({tz}).",
        "unsub_confirm": "Відписатися від заняття «{name}»?",
        "unsub_done": "Відписано.",

        # Timezone display names
        # Thinking pattern — intro and cancel
        "tp_intro": (
            "🧠 <b>Аналіз важливої події дня</b>\n\n"
            "Згадайте одну значущу подію сьогоднішнього дня і відповідайте чесно.\n\n"
            "Щоб скасувати — натисніть ✖️ Скасувати."
        ),
        "tp_already_done": "✅ Ви вже заповнили запис за сьогодні.",
        "tp_btn_view": "👁 Переглянути запис",
        "tp_btn_redo": "🔄 Заповнити знову",
        "tp_cancelled": "❌ Аналіз скасовано.",
        "tp_no_subscription": (
            "Щоб розпочати, спочатку підпишіться на заняття "
            "і вкажіть часовий пояс."
        ),

        # Thinking pattern — step questions
        "tp_step_irritation": (
            "<b>1 / 8 — Блок 1: Фізіологічний</b>\n\n"
            "🟠 <b>Роздратування</b>\n"
            "Оцініть рівень роздратування сьогодні:"
        ),
        "tp_step_excitement": (
            "<b>2 / 8 — Блок 1: Фізіологічний</b>\n\n"
            "🟠 <b>Збудження</b>\n"
            "Оцініть рівень збудження (внутрішньої напруги) сьогодні:"
        ),
        "tp_step_sensation": (
            "<b>3 / 8 — Блок 1: Фізіологічний</b>\n\n"
            "🟠 <b>Відчуття</b>\n"
            "Опишіть тілесне відчуття\n"
            "<i>(наприклад: тиснення в грудях, легкість, напруга в плечах)</i>"
        ),
        "tp_step_feeling": (
            "<b>4 / 8 — Блок 2: Емоційний</b>\n\n"
            "💚 <b>Почуття</b>\n"
            "Оберіть почуття або введіть своє:"
        ),
        "tp_step_emotion": (
            "<b>5 / 8 — Блок 2: Емоційний</b>\n\n"
            "💚 <b>Емоція</b>\n"
            "Оберіть емоцію або введіть свою:"
        ),
        "tp_step_impression": (
            "<b>6 / 8 — Блок 2: Емоційний</b>\n\n"
            "💚 <b>Враження</b>\n"
            "Яке враження залишила ця ситуація?"
        ),
        "tp_step_meaning": (
            "<b>7 / 8 — Блок 3: Ментальний</b>\n\n"
            "🔵 <b>Смисл поняття</b>\n"
            "Який смисл ви вбачаєте в цій ситуації?"
        ),
        "tp_step_idea": (
            "<b>8 / 8 — Блок 3: Ментальний</b>\n\n"
            "🔵 <b>Ідея</b>\n"
            "Яка ідея або висновок виникає у вас?"
        ),
        "tp_custom_prompt": "✏️ Введіть свій варіант:",

        # Summary / record display
        "tp_summary_header": "✅ <b>Аналіз збережено!</b>\n📅 {0}",
        "tp_block1_header": "🟠 <b>Блок 1 — Фізіологічний</b>",
        "tp_block2_header": "💚 <b>Блок 2 — Емоційний</b>",
        "tp_block3_header": "🔵 <b>Блок 3 — Ментальний</b>",
        "tp_field_labels": {
            "irritation": "Роздратування",
            "excitement": "Збудження",
            "sensation":  "Відчуття",
            "feeling":    "Почуття",
            "emotion":    "Емоція",
            "impression": "Враження",
            "meaning":    "Смисл",
            "idea":       "Ідея",
        },

        # Predefined choices
        "feelings": [
            "Радість", "Сум", "Страх", "Злість",
            "Любов", "Ніжність", "Образа", "Сором",
            "Тривога", "Провина",
        ],
        "emotions": [
            "Радість", "Злість", "Страх", "Смуток",
            "Здивування", "Огида", "Інтерес", "Сором",
            "Збентеження", "Захоплення",
        ],
        "custom_option": "✏️ Свій варіант",
        "scale_hint": "1 — мінімум · 5 — максимум",

        # Reminder (sent by scheduler)
        "reminder_text": (
            "🔔 <b>Час для щоденного аналізу!</b>\n\n"
            "Проаналізуйте найважливішу подію сьогоднішнього дня."
        ),
        "btn_start_analysis": "🧠 Розпочати аналіз",

        # History
        "history_no_subs": (
            "У вас немає активних занять.\n"
            "Перейдіть до розділу 📚 Заняття та підпишіться."
        ),
        "history_title": "📊 <b>Мої записи — {name}</b>",
        "week_stats":  "Тиждень: {filled}/{total} ({pct}%)",
        "month_stats": "Місяць:  {filled}/{total} ({pct}%)",
        "history_select": "\nОберіть день або введіть дату:",
        "btn_enter_date": "📅 Ввести дату",
        "date_ask": "Введіть дату у форматі <code>ДД.ММ.РРРР</code>:",
        "date_invalid": "Невірний формат. Введіть <code>ДД.ММ.РРРР</code>:",
        "no_record_for_date": "📭 За {date} запис відсутній.",
        "record_header": "📋 <b>Запис за {date}</b>",
        "hist_day_done": "✅ {date}",
        "hist_day_miss": "⬜ {date}",
    },

    "ru": {
        "choose_lang": "🇺🇦 Оберіть мову / 🇷🇺 Выберите язык:",

        "welcome": (
            "Привет! Это приложение для психологической работы.\n\n"
            "Выберите раздел ниже 👇"
        ),

        "btn_activities": "📚 Занятия",
        "btn_history": "📊 Мои записи",   # kept for backward-compat with old keyboards
        "btn_records": "📊 Мои записи",   # inline button inside activity detail

        "back": "← Назад",
        "cancel_btn": "✖️ Отмена",
        "yes_btn": "✅ Да",
        "no_btn": "❌ Нет",
        "error": "Произошла ошибка. Попробуйте ещё раз.",

        "activities_title": "📚 Доступные занятия:\n\nВыберите занятие для деталей.",
        "activities_empty": "Сейчас нет доступных занятий.",

        "status_subscribed": "✅ Подписан",
        "status_not_subscribed": "⚪ Не подписан",
        "reminder_info": "⏰ Каждый день в {time} ({tz})",
        "btn_subscribe": "✅ Подписаться",
        "btn_unsubscribe": "❌ Отписаться",
        "btn_change_reminder": "⏰ {time} | {tz}",
        "btn_start_now": "🚀 Начать сейчас",

        "sub_ask_time": (
            "Укажите время ежедневного напоминания.\n"
            "Формат: ЧЧ:ММ (например, <code>20:30</code>)"
        ),
        "sub_time_invalid": (
            "Неверный формат. Введите время в виде ЧЧ:ММ\n"
            "(например, <code>21:00</code>):"
        ),
        "sub_ask_tz": "Выберите ваш часовой пояс:",
        "sub_done": "✅ Подписка оформлена!\nНапоминание каждый день в {time} ({tz}).",
        "time_updated": "⏰ Время напоминания изменено: {time} ({tz}).",
        "unsub_confirm": "Отписаться от занятия «{name}»?",
        "unsub_done": "Отписка выполнена.",

        "tp_intro": (
            "🧠 <b>Анализ важного события дня</b>\n\n"
            "Вспомните одно значимое событие сегодняшнего дня и отвечайте честно.\n\n"
            "Чтобы отменить — нажмите ✖️ Отмена."
        ),
        "tp_already_done": "✅ Вы уже заполнили запись за сегодня.",
        "tp_btn_view": "👁 Просмотреть запись",
        "tp_btn_redo": "🔄 Заполнить заново",
        "tp_cancelled": "❌ Анализ отменён.",
        "tp_no_subscription": (
            "Чтобы начать, сначала подпишитесь на занятие "
            "и укажите часовой пояс."
        ),

        "tp_step_irritation": (
            "<b>1 / 8 — Блок 1: Физиологический</b>\n\n"
            "🟠 <b>Раздражение</b>\n"
            "Оцените уровень раздражения сегодня:"
        ),
        "tp_step_excitement": (
            "<b>2 / 8 — Блок 1: Физиологический</b>\n\n"
            "🟠 <b>Возбуждение</b>\n"
            "Оцените уровень возбуждения (внутреннего напряжения) сегодня:"
        ),
        "tp_step_sensation": (
            "<b>3 / 8 — Блок 1: Физиологический</b>\n\n"
            "🟠 <b>Ощущение</b>\n"
            "Опишите телесное ощущение\n"
            "<i>(например: давление в груди, лёгкость, напряжение в плечах)</i>"
        ),
        "tp_step_feeling": (
            "<b>4 / 8 — Блок 2: Эмоциональный</b>\n\n"
            "💚 <b>Чувство</b>\n"
            "Выберите чувство или введите своё:"
        ),
        "tp_step_emotion": (
            "<b>5 / 8 — Блок 2: Эмоциональный</b>\n\n"
            "💚 <b>Эмоция</b>\n"
            "Выберите эмоцию или введите свою:"
        ),
        "tp_step_impression": (
            "<b>6 / 8 — Блок 2: Эмоциональный</b>\n\n"
            "💚 <b>Впечатление</b>\n"
            "Какое впечатление оставила эта ситуация?"
        ),
        "tp_step_meaning": (
            "<b>7 / 8 — Блок 3: Ментальный</b>\n\n"
            "🔵 <b>Смысл понятия</b>\n"
            "Какой смысл вы видите в этой ситуации?"
        ),
        "tp_step_idea": (
            "<b>8 / 8 — Блок 3: Ментальный</b>\n\n"
            "🔵 <b>Идея</b>\n"
            "Какая идея или вывод возникает у вас?"
        ),
        "tp_custom_prompt": "✏️ Введите свой вариант:",

        "tp_summary_header": "✅ <b>Анализ сохранён!</b>\n📅 {0}",
        "tp_block1_header": "🟠 <b>Блок 1 — Физиологический</b>",
        "tp_block2_header": "💚 <b>Блок 2 — Эмоциональный</b>",
        "tp_block3_header": "🔵 <b>Блок 3 — Ментальный</b>",
        "tp_field_labels": {
            "irritation": "Раздражение",
            "excitement": "Возбуждение",
            "sensation":  "Ощущение",
            "feeling":    "Чувство",
            "emotion":    "Эмоция",
            "impression": "Впечатление",
            "meaning":    "Смысл",
            "idea":       "Идея",
        },

        "feelings": [
            "Радость", "Грусть", "Страх", "Злость",
            "Любовь", "Нежность", "Обида", "Стыд",
            "Тревога", "Вина",
        ],
        "emotions": [
            "Радость", "Злость", "Страх", "Грусть",
            "Удивление", "Отвращение", "Интерес", "Стыд",
            "Смущение", "Восхищение",
        ],
        "custom_option": "✏️ Свой вариант",
        "scale_hint": "1 — минимум · 5 — максимум",

        "reminder_text": (
            "🔔 <b>Время для ежедневного анализа!</b>\n\n"
            "Проанализируйте самое важное событие сегодняшнего дня."
        ),
        "btn_start_analysis": "🧠 Начать анализ",

        "history_no_subs": (
            "У вас нет активных занятий.\n"
            "Перейдите в раздел 📚 Занятия и подпишитесь."
        ),
        "history_title": "📊 <b>Мои записи — {name}</b>",
        "week_stats":  "Неделя: {filled}/{total} ({pct}%)",
        "month_stats": "Месяц:  {filled}/{total} ({pct}%)",
        "history_select": "\nВыберите день или введите дату:",
        "btn_enter_date": "📅 Ввести дату",
        "date_ask": "Введите дату в формате <code>ДД.ММ.ГГГГ</code>:",
        "date_invalid": "Неверный формат. Введите <code>ДД.ММ.ГГГГ</code>:",
        "no_record_for_date": "📭 За {date} запись отсутствует.",
        "record_header": "📋 <b>Запись за {date}</b>",
        "hist_day_done": "✅ {date}",
        "hist_day_miss": "⬜ {date}",
    },
}

BTN_ACTIVITIES = {t["btn_activities"] for t in TEXTS.values()}
BTN_HISTORY    = {t["btn_history"]    for t in TEXTS.values()}


def T(lang: str, key: str, *args, **kwargs):
    value = TEXTS[lang][key]
    if isinstance(value, str):
        if kwargs:
            return value.format(**kwargs)
        if args:
            return value.format(*args)
    return value


def tz_name(lang: str, tz: str) -> str:
    return _TZ_DISPLAY.get(tz, tz)


def activity_name(lang: str, row) -> str:
    return row[f"name_{lang}"] or row["name_uk"]


def activity_desc(lang: str, row) -> str:
    return row[f"description_{lang}"] or row["description_uk"] or ""


def _stars(n: int) -> str:
    return "⭐" * n + "☆" * (5 - n)


def format_tp_body(lang: str, responses: dict) -> str:
    """Format the three blocks without the header line."""
    labels = T(lang, "tp_field_labels")
    lines = [
        T(lang, "tp_block1_header"),
        f"  {labels['irritation']}: {_stars(responses.get('irritation', 0))} ({responses.get('irritation', '?')}/5)",
        f"  {labels['excitement']}: {_stars(responses.get('excitement', 0))} ({responses.get('excitement', '?')}/5)",
        f"  {labels['sensation']}: {responses.get('sensation', '—')}",
        "",
        T(lang, "tp_block2_header"),
        f"  {labels['feeling']}: {responses.get('feeling', '—')}",
        f"  {labels['emotion']}: {responses.get('emotion', '—')}",
        f"  {labels['impression']}: {responses.get('impression', '—')}",
        "",
        T(lang, "tp_block3_header"),
        f"  {labels['meaning']}: {responses.get('meaning', '—')}",
        f"  {labels['idea']}: {responses.get('idea', '—')}",
    ]
    return "\n".join(lines)


def format_tp_summary(lang: str, responses: dict, date_str: str) -> str:
    """Full completion message: header + body."""
    return T(lang, "tp_summary_header", date_str) + "\n\n" + format_tp_body(lang, responses)
