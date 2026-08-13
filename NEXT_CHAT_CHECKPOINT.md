# WB API Workbench — checkpoint

## Как продолжить

Начать новый чат с фразы:

    Продолжаем проект WB API Workbench.
    Локальный путь: E:\projects-wb-api-workbench
    Прочитай NEXT_CHAT_CHECKPOINT.md — там актуальный статус.

## Что это за проект

Локальное desktop-приложение на Python для работы с Wildberries API.
Инструмент для менеджеров маркетплейса с разными уровнями доступа.
Портфолио-проект: внешний API, GUI, локальное хранение, безопасное
хранение ключей, ролевая модель доступа.

## Стек

Python 3.11+, customtkinter, SQLAlchemy + SQLite (слой готов, не подключён),
httpx, keyring, cryptography, pytest.

## Команды

Запуск:

    cd E:\projects-wb-api-workbench
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
      config.py            пути, DATABASE_URL, USERS_FILE
      main.py               точка входа
      core/
        permissions.py     PERMISSIONS (матрица прав) на settings.UserRole — единый enum ролей
        settings.py        UserRole, AppMode, apply_settings
        users.py           UserAccount + логика (create/add/find/change/deactivate)
        user_store.py      JSON-персистентность пользователей
        diagnostics.py     самопроверка окружения
        token_utils.py     mask_token (общий для key_storage/encrypted_file_storage)
        key_storage.py     ключи через keyring
        encrypted_file_storage.py  ключи в зашифрованном файле (Fernet)
        session_key_storage.py     ключ в памяти сессии
        http_client.py     WB HTTP-клиент (httpx), из GUI пока не используется
        wb_token.py         декодер JWT WB (oid/sid, тип, scopes+ping URL, срок, "for")
        wb_ping.py          пинг разделов WB API по битам токена, сводка статуса
        ozon_ping.py         Ozon: проверка Seller (Client-Id+Api-Key) и Performance
                              (Client ID+Client Secret, OAuth2) — ключ непрозрачный, декодера нет
        marketplace.py      Marketplace, KeyKind — метаданные для ApiKey
      gui/
        main_window.py     основное окно, рабочие разделы (включая Keys)
        api_tester.py      заглушка
        key_manager.py     заглушка (логика Keys живёт в main_window.py, не здесь)
        json_viewer.py     заглушка
        login_window.py    заглушка (реального логина нет, роль = дропдаун в Settings)
      db/
        database.py        engine, SessionLocal, init_db (вызывается при старте GUI)
        models.py          ApiKey (+marketplace/key_kind), ApiRequestLog
        key_repository.py  CRUD ApiKey
        request_log_repository.py  CRUD ApiRequestLog
      storage/
        raw_json.py        сохранение raw JSON
    tests/                 101 тестов (permissions, settings, users, user_store,
                            diagnostics, wb_token, wb_ping, ozon_ping, db-слой)
    docs/                  architecture, permissions, roadmap
    reference/             боевые GAS-скрипты (WB/Ozon key checker) как референс
                            логики; в .gitignore, не часть кодовой базы

## Текущее состояние (v0.3 / GUI MVP в работе)

Core — готово и покрыто тестами:
- ролевая модель (Viewer / Tester / Operator / Admin), единая матрица прав
  (permissions.PERMISSIONS keyed by settings.UserRole — раньше были два
  параллельных enum'а, свели в один);
- режимы Test / Real с правилом доступа к Real;
- логика пользователей: создание, защита от дублей (без учёта регистра),
  поиск, смена роли, деактивация;
- JSON-персистентность пользователей (user_store);
- диагностика окружения;
- три варианта хранения ключей (keyring / шифрованный файл / сессия);
- декодер JWT-ключей WB (wb_token): кабинет (oid, с fallback на sid),
  тип, права по битам (scopes + ping URL на раздел), срок действия, "for";
- пинг живости ключа: wb_ping (WB, по разделам bitmask) и ozon_ping
  (Ozon Seller + Performance — два независимых типа credentials,
  ключ непрозрачный, декодера нет, только live-check);
- БД-слой подключён: init_db() вызывается при старте GUI, репозитории
  key_repository/request_log_repository (полный CRUD) поверх ApiKey/
  ApiRequestLog; ApiKey несёт marketplace/key_kind (app.core.marketplace) —
  один и тот же формат хранит и WB JWT, и Ozon Seller/Performance.

GUI — рабочие разделы:
- каркас приложения (sidebar, topbar, статус Role/Mode/Key);
- Diagnostics (кнопка Run Diagnostics);
- Settings (выбор роли и режима, проверка запрещённых комбинаций);
- Users (полностью рабочий): создание с защитой от дублей,
  смена роли, деактивация, сохранение в JSON, загрузка при старте,
  автосоздание admin если файла нет, доступ к разделу через
  has_permission(role, "manage_users");
- Keys (полный цикл, WB + Ozon; см. раздел ниже) — построено, прошло
  скриптовый смоук-тест, ждёт ручной проверки в реальном Tk (ты как раз
  этим занимаешься).

Пользователи переживают перезапуск приложения (data/users.json,
в .gitignore — локальные данные).

Тесты: 101 passed (в песочнице ревьюера дополнительно 1 ожидаемый fail —
там Python 3.10, а diagnostics проверяет >=3.11; у тебя локально не фейлит).
GUI-код тестами не покрыт (нет реального Tk в песочнице ревьюера) — Keys
проверен скриптовым смоук-тестом на поддельном customtkinter + один
ручной прогон с реальным WB-токеном.

## Хранение секретов ключей (кто спросит — вот ответ)

Два независимых места, оба вне git:
- Сам секрет (WB JWT целиком, или JSON `{"client_id":..,"api_key":..}` /
  `{"client_id":..,"client_secret":..}` для Ozon) — EncryptedFileKeyStorage,
  Fernet-шифрование, файл data/secure/encrypted_keys.json, ключ шифрования
  data/secure/master.key (создаётся сам при первом использовании).
- Метаданные (имя, marketplace, key_kind, ТОЛЬКО маскированный токен,
  storage_type, is_active, created_at, last_used_at) — SQLite,
  data/wb_workbench.db. Сырой секрет туда никогда не попадает.
Оба пути (data/secure/, *.db) в .gitignore.

## Заглушки / не подключено

- GUI: API Tester, Imports, History (плейсхолдеры) — весь core под них
  (http_client, декодер, пинг WB/Ozon, БД-репозитории) готов, но не отрисован;
- http_client готов, но из GUI не используется (ping-модули дёргают
  httpx напрямую, у http_client другая задача — реальные вызовы методов
  API Tester, raise_for_status там кстати не подходит для ping-сценариев);
- кэширование результата пинга (как в reference-скриптах, по хэшу+дню) —
  не портировано, каждый клик Check в Keys — новый live-запрос;
- логина нет (login_window.py — заглушка): роль сейчас просто дропдаун
  в Settings без всякой проверки личности, любой может выставить себе Admin.

## Известные проблемы и бэклог

- Users: список пользователей без скроллбара, обрезается в маленьком окне
  (в полный экран видно). Быстрая добивка: CTkScrollableFrame.
- Keys: список тоже обычный CTkTextbox без построчных кнопок — "Check"
  сделан через отдельное поле "имя ключа" (как manage-паттерн в Users),
  не клик по строке. Апгрейд до реальной таблицы — отдельная задача.
- Keys: кнопка Check завязана на то же право add_key (Admin), что и
  сохранение — по смыслу это ближе к "использовать ключ", чем к
  "изменить хранилище". Матрица прав не даёт отдельного права под это,
  осознанно не стал придумывать новое значение сам.
- Keys: masked_token для Ozon выглядит криво (mask_token считался под
  сырую JWT-строку, а тут JSON) — работает, но косметически не очень.
- can_manage_users(role) в users.py осталась (и её тесты), но в GUI больше
  не используется — решить, удалять или оставить как утилиту.
- Реальная аутентификация не спроектирована — отдельный большой разговор,
  когда дойдёт очередь.

## Ошибки, найденные и исправленные по ходу

- В рабочей копии были порезаны users.py и test_users.py (потеряна логика
  дублей и часть тестов) — восстановлено.
- 4 нерабочих GUI-черновика (users_gui_*.py) ссылались на несуществующие
  модули — удалены.
- Двойной append при создании пользователя в GUI — убран.
- В GUI вызывался create_user вместо add_user (не ловил дубли,
  не добавлял в список) — заменён на add_user.
- init_db() вызывал Base.metadata.create_all(), но models.py нигде не
  импортировался по пути вызова из GUI — создавался файл БД без единой
  таблицы, молча. Починено импортом models внутри init_db(); есть
  regression-тест в отдельном subprocess (иначе баг маскируется —
  другие тесты в общем прогоне уже импортировали models).
- Текст в разделе Users утверждал "data is temporary for this session" —
  устарело с тех пор, как подключили save_users в JSON. Поправлено.
- Keys: поле ввода WB-токена/Ozon-секрета не маскировалось (show="*" не
  стоял) и не очищалось после сохранения — секрет висел открытым текстом
  в форме сколько угодно. Нашли ручным тестом. Поправлено: маскировка на
  секрет-полях (client_id не трогали, он не секрет) + очистка всех полей
  формы после успешного Save.

## Правила работы

- Маленькими шагами: обсудить -> маленький блок кода -> запустить ->
  исправить -> закоммитить.
- Для каждого раздела: core-логика + pytest-тесты + проверка в GUI.
- Команды для PowerShell, по одной за раз.

## Раздел Keys (core + GUI построены, идёт ручная проверка)

Цель: админка учёта и контроля ключей доступа к WB/Ozon API (и дальше —
другим маркетплейсам, если у них появится смысл проверять ключи;
Lamoda/Деловые линии/МойСклад/МоЕх — ключи практически бессрочные с
полным доступом, для них ping-проверка сейчас не нужна).

Core (всё с тестами):
- wb_token.py — декодер JWT WB (oid/sid, тип, scopes+ping URL, срок, "for").
  Золотой образец — реальный токен в test_wb_token.py.
- wb_ping.py — пинг разделов WB API по bitmask, сводка статуса
  (200 у любого раздела -> OK, иначе 401 -> 429 -> 403 -> ERROR).
  Логика 1-в-1 портирована из reference/api_key_stats.gs.
- ozon_ping.py — Ozon Seller (Client-Id+Api-Key, POST /v3/product/list)
  и Performance (Client ID+Client Secret, OAuth2 client_credentials).
  Портировано из reference/ozon_key_stats.gs. У Ozon ключ непрозрачный —
  декодера нет, только live-check, и credentials двух разных типов.
- marketplace.py — Marketplace (WB/OZON), KeyKind (jwt/seller/performance).
- db/models.py ApiKey несёт marketplace+key_kind — одна таблица для обоих
  маркетплейсов. key_repository.py — полный CRUD поверх неё.

GUI (main_window.py, раздел Keys):
- Marketplace-дропдаун (WB/Ozon), поля перестраиваются динамически;
  для Ozon — свой дропдаун Seller/Performance, тоже динамические поля.
- Save: WB-токен валидируется через token_info() до сохранения (кривой
  токен отклоняется с сообщением, не сохраняется). Ozon-credentials
  сериализуются в JSON и идут в тот же encrypted_file_storage — его
  менять не пришлось, он и так хранит произвольную строку под именем.
  Проверка на дубль имени — до записи секрета, не после (иначе дубль
  мог тихо переписать чужой секрет в файле).
- Check по имени: расшифровывает секрет, вызывает wb_ping/ozon_ping
  по marketplace/key_kind, проставляет is_active. Синхронно (asyncio.run
  внутри обработчика клика) — на время запроса GUI подвисает, для WB
  это может быть несколько секунд (пинг нескольких разделов с паузой).
  Вынесение в фон — на будущее.
- Список сохранённых ключей с масками, кнопка Refresh.
- Права по матрице: view_masked_keys (все роли) — виден список,
  add_key (только Admin) — виден блок добавления/проверки.

Проверено: скриптовый смоук-тест (poddельный customtkinter, реального
Tk в песочнице ревьюера нет) — сохранение WB + оба типа Ozon, защита от
дублей, Check с замоканной сетью, Viewer/Admin-гейтинг, переключение по
всем разделам без исключений. Плюс твой первый ручной прогон с реальным
WB-токеном нашёл реальный баг (см. "Ошибки" выше) — уже поправлено.

## Следующий шаг

Ты сейчас гоняешь GUI руками (реальный Tk, реальные токены). По итогам —
чинить найденное, потом ещё раз прогнать, сделать скриншоты для README,
снова обновить README/checkpoint. Параллельно в очереди, не начато:
- кэш результата пинга (data/cache/, уже зарезервирован в config.py) —
  без него Check дёргает живой API на каждый клик;
- реальная таблица для списка ключей вместо CTkTextbox;
- API Tester поверх http_client.
Быстрая добивка вне очереди: скролл в списке Users (CTkScrollableFrame).