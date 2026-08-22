# WB API Workbench — checkpoint

## Как продолжить

Начать новый чат с фразы:

    Продолжаем проект WB API Workbench.
    Локальный путь: E:\wb-api-workbench
    Прочитай NEXT_CHAT_CHECKPOINT.md — там актуальный статус.

## Что это за проект

Локальное desktop-приложение на Python для работы с Wildberries API.
Инструмент для менеджеров маркетплейса с разными уровнями доступа.
Портфолио-проект: внешний API, GUI, локальное хранение, безопасное
хранение ключей, ролевая модель доступа.

Отдельно зафиксировано (см. project instructions зонтичного проекта):
это НЕ аналитическая платформа по кабинету — та идея изначально и
осознанно живёт в соседнем репозитории wb-boss-widget (дашборд метрик
по нескольким кабинетам). wb-api-workbench с первого коммита — про
ключи/роли/тестер API, roadmap.md это подтверждает с самого начала.

## Стек

Python 3.11+, customtkinter, SQLAlchemy + SQLite (подключено — init_db()
вызывается при старте GUI, репозитории под ApiKey/ApiRequestLog),
httpx, keyring, cryptography, pytest.

## Команды

Запуск:

    cd E:\wb-api-workbench
    .\.venv\Scripts\Activate.ps1
    python -m app.main

Тесты:

    python -m pytest -q

Git:

    git status
    git add .
    git commit -m "message"
    git push

## Структура проекта

    app/
      config.py            пути, DATABASE_URL, USERS_FILE, SESSION_FILE
      main.py               точка входа
      core/
        permissions.py     PERMISSIONS (матрица прав) на settings.UserRole — единый enum ролей
        settings.py        UserRole, AppMode, apply_settings, can_use_real_mode
        session_state.py   load/save_session_state — role+mode переживают перезапуск (data/session.json)
        users.py           UserAccount + логика (create/add/find/change/deactivate)
        user_store.py      JSON-персистентность пользователей
        diagnostics.py     самопроверка окружения
        token_utils.py     mask_token + mask_ozon_credentials (Ozon — JSON, маскируем поля отдельно)
        key_storage.py     ключи через keyring
        encrypted_file_storage.py  ключи в зашифрованном файле (Fernet)
        session_key_storage.py     ключ в памяти сессии (используется в API Tester, Test mode)
        http_client.py     WBHttpClient — НЕ используется нигде (см. "Заглушки" ниже, там же почему)
        wb_token.py         декодер JWT WB (oid/sid, тип, scopes+ping URL, срок, "for"),
                             + get_scope_hosts() — базовый хост на каждый раздел API (для API Tester)
        wb_ping.py          пинг разделов WB API по битам токена, сводка статуса
        ozon_ping.py         Ozon: проверка Seller (Client-Id+Api-Key) и Performance
                              (Client ID+Client Secret, OAuth2) — ключ непрозрачный, декодера нет
        marketplace.py      Marketplace, KeyKind — метаданные для ApiKey
        api_tester.py       parse_json_body, send_wb_request (прямой httpx, не через http_client —
                             у него raise_for_status() глотает тело ошибочных ответов)
      gui/
        main_window.py     тонкий каркас (~250 строк): __init__, layout/sidebar/topbar,
                            show_section-диспетчер. Разделы вынесены в sections/ миксинами
                            (main_window.py был 978 строк одним классом — разобрали один в один
                            с разделами GUI, методы переехали почти без правок).
        sections/
          diagnostics_section.py  DiagnosticsSectionMixin
          settings_section.py    SettingsSectionMixin (+ сохраняет session_state при Apply)
          users_section.py       UsersSectionMixin (весь раздел скроллится одним CTkScrollableFrame)
          keys_section.py        KeysSectionMixin (WB + Ozon, самый большой, ~430 строк)
          api_tester_section.py  ApiTesterSectionMixin (см. раздел ниже)
        MainWindow(DiagnosticsSectionMixin, SettingsSectionMixin, UsersSectionMixin,
                   KeysSectionMixin, ApiTesterSectionMixin, ctk.CTk) — набирает разделы
                   через наследование, каждый метод обращается к self как раньше.
      db/
        database.py        engine, SessionLocal, init_db (вызывается при старте GUI)
        models.py          ApiKey (+marketplace/key_kind), ApiRequestLog
        key_repository.py  CRUD ApiKey
        request_log_repository.py  CRUD ApiRequestLog
      storage/
        raw_json.py        сохранение raw JSON (пока нигде не вызывается, задел под Imports)
    tests/                 127 тестов (permissions, settings, session_state, users, user_store,
                            token_utils, api_tester, diagnostics, wb_token, wb_ping, ozon_ping, db-слой)
    docs/                  architecture, permissions, roadmap
    reference/             боевые GAS-скрипты (WB/Ozon key checker) как референс
                            логики; в .gitignore, не часть кодовой базы

## Текущее состояние (v0.4 — API и данные, в работе)

Core — готово и покрыто тестами:
- ролевая модель (Viewer / Tester / Operator / Admin), единая матрица прав;
- режимы Test / Real с правилом доступа к Real; выбор role/mode переживает
  перезапуск приложения (session_state.py, data/session.json);
- логика пользователей: создание, защита от дублей, поиск, смена роли,
  деактивация, JSON-персистентность;
- три варианта хранения ключей (keyring / шифрованный файл / сессия);
- декодер JWT-ключей WB (wb_token): кабинет, тип, права по битам, срок
  действия, "for" + список всех разделов API с их базовым хостом
  (get_scope_hosts — у каждого раздела WB свой домен, единого нет);
- пинг живости ключа: wb_ping (WB) и ozon_ping (Ozon Seller + Performance);
- маскировка секретов для списка: mask_token (WB, сырой JWT) и отдельно
  mask_ozon_credentials (Ozon — JSON, маскируем client_id/api_key по
  полям, а не байты JSON целиком);
- БД-слой: init_db(), key_repository/request_log_repository (полный CRUD);
- api_tester.py: разбор JSON-тела запроса, прямой HTTP-вызов к WB
  (не через http_client — см. "Заглушки").

GUI — все разделы рабочие:
- каркас (sidebar, topbar, статус Role/Mode/Key), main_window.py разобран
  на миксины по разделам (app/gui/sections/);
- Diagnostics, Settings (сохраняет role/mode в session_state);
- Users — полностью рабочий, вся секция в одном CTkScrollableFrame
  (форма + список не могут схлопнуться друг под друга в маленьком окне);
- Keys — полный цикл WB + Ozon: сохранение, проверка живости, список
  с масками (Ozon — читаемая маска по полям);
- API Tester — новый раздел (см. подробности ниже).

Тесты: 127 passed. GUI-код тестами не покрыт (нет реального Tk в
песочнице ревьюера) — только ручная проверка на твоей стороне.

## Хранение секретов ключей (кто спросит — вот ответ)

Два независимых места, оба вне git:
- Сам секрет (WB JWT целиком, или JSON `{"client_id":..,"api_key":..}` /
  `{"client_id":..,"client_secret":..}` для Ozon) — EncryptedFileKeyStorage,
  Fernet-шифрование, файл data/secure/encrypted_keys.json, ключ шифрования
  data/secure/master.key (создаётся сам при первом использовании).
- Метаданные (имя, marketplace, key_kind, ТОЛЬКО маскированный токен,
  storage_type, is_active, created_at, last_used_at) — SQLite,
  data/wb_workbench.db. Сырой секрет туда никогда не попадает.
- Временный ключ из API Tester (Test mode) — только в памяти процесса
  (session_key_storage.py), на диск не попадает вообще, теряется при
  закрытии приложения. Это осознанно: Test mode — для разового поиска,
  не для хранения.
Оба файловых пути (data/secure/, *.db) в .gitignore.

## Заглушки / не подключено

- GUI: Imports, History — плейсхолдеры, ждут своей очереди (raw_json.py
  и request_log_repository.list_request_logs под них уже готовы);
- http_client.py (WBHttpClient) по-прежнему нигде не используется и
  вдобавок сейчас точно неправильный: у него один захардкоженный
  base_url ("seller-api.wildberries.ru"), а у WB такого единого домена
  нет вообще — у каждого раздела API свой хост (см. wb_token.WB_SCOPES /
  get_scope_hosts). Это всплыло при постройке API Tester — там ту же
  проблему решили через get_scope_hosts() + собственный api_tester.py,
  http_client.py в стороне остался нетронутым и по-прежнему сломанным
  для реального использования. Решить: чинить (на per-раздел base_url)
  или удалить как мёртвый/неверный код — он и так дублирует то, что
  теперь есть в api_tester.py;
- кэширование результата пинга (как в reference-скриптах, по хэшу+дню) —
  не портировано, каждый клик Check в Keys — новый live-запрос;
- логина нет (роль — просто дропдаун в Settings без проверки личности).

## Известные проблемы и бэклог

- Keys: список — обычный текстовый вывод без построчных кнопок, "Check"
  через отдельное поле "имя ключа" (как manage-паттерн в Users), не клик
  по строке. Апгрейд до реальной таблицы — отдельная задача.
- Keys: кнопка Check завязана на то же право add_key (Admin), что и
  сохранение — по смыслу это ближе к "использовать ключ", чем к
  "изменить хранилище". Матрица прав не даёт отдельного права под это,
  осознанно не стал придумывать новое значение сам — решить отдельно.
- http_client.py — см. "Заглушки" выше, решить судьбу.
- Реальная аутентификация не спроектирована — отдельный большой разговор,
  когда дойдёт очередь.

## Ошибки, найденные и исправленные по ходу

- В рабочей копии были порезаны users.py и test_users.py — восстановлено.
- 4 нерабочих GUI-черновика (users_gui_*.py) — удалены.
- init_db() не импортировал models.py по пути вызова из GUI — создавал
  файл БД без единой таблицы, молча. Починено.
- Keys: поле ввода WB-токена/Ozon-секрета не маскировалось и не
  очищалось после сохранения — секрет висел открытым текстом в форме.
  Поправлено.
- Users: форма + список без скролла обрезались в небольшом окне (видно
  было только в развёрнутом). Пробовали закрепить форму и скроллить
  только список — не сработало (форме самой не хватало места, списку
  доставалось 0px). Решение — скроллить всю секцию одним контейнером.
- Keys: masked_token для Ozon был кашей из байт JSON (mask_token считал
  под сырую JWT-строку, а тут JSON-объект) — заменено на
  mask_ozon_credentials, маскирует значения полей по отдельности.
- can_manage_users(role) в users.py дублировала has_permission(role,
  "manage_users") и была не подключена к GUI — удалена вместе с тестами.
- API Tester изначально бил на несуществующий домен ("seller-api.
  wildberries.ru" по образцу http_client.py) — у WB нет единого хоста,
  у каждого раздела свой. Поправлено через wb_token.get_scope_hosts() +
  dropdown "Section" в форме, который определяет base_url запроса.

## Правила работы

- Маленькими шагами: обсудить -> маленький блок кода -> запустить ->
  исправить -> закоммитить.
- Для каждого раздела: core-логика + pytest-тесты + проверка в GUI.
- Команды для PowerShell, по одной за раз.

## Раздел Keys (готово, WB + Ozon)

Core (всё с тестами): wb_token.py (декодер JWT WB), wb_ping.py (пинг по
bitmask), ozon_ping.py (Ozon Seller + Performance), marketplace.py
(Marketplace/KeyKind), db/models.py + key_repository.py (CRUD).

GUI (app/gui/sections/keys_section.py): marketplace-дропдаун (WB/Ozon) с
динамическими полями, Ozon — свой дропдаун Seller/Performance. Save
валидирует WB-токен через token_info() до записи, проверяет дубль имени
до записи секрета. Check по имени — расшифровывает, вызывает wb_ping/
ozon_ping, синхронно (asyncio.run в обработчике клика, GUI на время
запроса подвисает — вынесение в фон на будущее). Список с масками,
Refresh. Права: view_masked_keys (все роли) — виден список, add_key
(только Admin) — виден блок добавления/проверки.

## Раздел API Tester (новое, готово)

Цель: "тестирование методов Wildberries API" из README — форма для
ручных GET/POST запросов к WB, без каталога методов (строить его —
по сути работа api-crash-dog, отдельного проекта; не дублируем).

Источник ключа зависит от режима (см. docs/permissions.md):
- Test mode (Tester+): временный ключ вписывается прямо в форму,
  живёт только в памяти (session_key_storage.py), право
  run_test_request;
- Real mode (Operator/Admin): выбор одного из уже сохранённых WB-ключей
  из Keys по имени, расшифровка через тот же key_storage, право
  run_real_request.

Форма: Section (dropdown из wb_token.get_scope_hosts() — определяет
base_url, у каждого раздела WB свой домен) -> Method (GET/POST) -> Path
-> JSON body (для POST). Send отправляет запрос напрямую через httpx
(api_tester.send_wb_request), не через http_client.py — там
raise_for_status() прячет тело ошибочных ответов, а тестеру как раз
важно видеть 400/401/429 с телом, а не поймать исключение.

"Save response" (чекбокс, право save_test_response/save_response по
режиму) — пишет метод/путь/тело/ответ/статус в request_log_repository
(История запросов, раздел History её пока не показывает — сам раздел
ещё не отрисован).

Права по ролям для формы: Viewer видит форму, но без Send/полей ключа
(view_api_methods есть у всех, run_*_request — нет). Проверено вручную
в реальном Tk с реальным сохранённым WB-ключом.

## Следующий шаг

Пул мелких правок и рефакторинга main_window.py закрыт, API Tester
построен и проверен. Дальше по roadmap.md (v0.4 → v1.0), не начато:
- Imports (импорт JSON/CSV/Excel) и History (просмотр request_log) —
  core под них уже есть (raw_json.py, list_request_logs);
- кэш результата пинга в Keys (data/cache/, зарезервировано в config.py);
- реальная таблица для списка ключей в Keys;
- решить судьбу http_client.py (чинить per-раздел base_url или удалить);
- реальная аутентификация — отдельный большой разговор;
- актуальные скриншоты для README (текущие — до всех этих правок).
