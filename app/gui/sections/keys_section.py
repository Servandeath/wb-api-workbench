import asyncio
import json

import customtkinter as ctk
import httpx

from app.gui.layout import (
    CONTENT_PADX,
    ENTRY_WIDTH,
    ENTRY_WIDTH_WIDE,
    FIELD_PADX,
    FIELD_PADY,
    LABEL_WIDTH,
    PANEL_CORNER_RADIUS,
    PANEL_GAP,
    build_group_header,
)
from app.core.marketplace import KeyKind, Marketplace
from app.core.ozon_ping import check_performance_key, check_seller_key
from app.core.permissions import has_permission
from app.core.settings import UserRole
from app.core.wb_ping import ping_token_detailed, reduce_ping_results
from app.core.token_utils import mask_ozon_credentials
from app.core.wb_token import token_info
from app.db.database import SessionLocal
from app.db.key_repository import (
    add_api_key,
    get_api_key_by_name,
    list_api_keys,
    record_check_result,
)


class KeysSectionMixin:
    def _show_keys_section(self) -> None:
        current_role = UserRole(self.current_role)

        if not has_permission(current_role, "view_masked_keys"):
            self._show_default_section(
                title="Keys",
                description="Access denied.",
            )
            return

        content = self._create_content_frame()
        # _create_content_frame даёт weight=1 строке 2 по умолчанию — после
        # удаления дублирующего заголовка на этой строке иногда оказывается
        # message_label, а не растягиваемый список. Сбрасываем дефолт,
        # настоящий вес строке списка ставим ниже явно (next_row).
        content.grid_rowconfigure(2, weight=0)

        # Заголовок раздела уже есть в topbar (см. MainWindow.show_section) —
        # повторять его здесь второй раз тем же текстом было чистым
        # дублированием. Оставляем только описание.
        description = ctk.CTkLabel(
            content,
            text="Store and check WB and Ozon API keys.",
            font=ctk.CTkFont(size=16),
            justify="left",
        )
        description.grid(row=0, column=0, padx=CONTENT_PADX, pady=(30, 10), sticky="w")

        # Add и Check — разные права: сохранять/менять хранилище ключей
        # может только Admin (add_key), а проверить, жив ли уже сохранённый
        # ключ (Check) — это canned-скрипт (wb_ping/ozon_ping), ничего
        # руками не пишешь, поэтому доступно и Tester/Operator
        # (check_key_liveness). Раньше обе кнопки сидели за одним add_key.
        can_add = has_permission(current_role, "add_key")
        can_check = has_permission(current_role, "check_key_liveness")
        # Полный (расшифрованный) секрет нужен, когда тот же ключ заводят
        # ещё и в другом инструменте/проекте — раньше единственный способ
        # был руками читать encrypted_keys.json. view_full_key был заведён
        # в правах заранее, но нигде не использовался — вот его применение.
        can_copy = has_permission(current_role, "view_full_key")
        next_row = 1

        # Add и Check/Copy — два независимых блока в один столбец каждый.
        # Раньше все три сидели в одной узкой форме, а справа от неё
        # пустовала половина ширины окна. Когда доступны оба блока (Admin)
        # — кладём их рядом, по колонке на каждый. Когда доступен только
        # один (например Tester видит лишь Check) — он один растягивается
        # на всю ширину, а не жмётся в узкую половину рядом с пустотой.
        has_add_panel = can_add
        has_check_panel = can_check or can_copy
        both_panels = has_add_panel and has_check_panel

        if has_add_panel or has_check_panel:
            top_row = ctk.CTkFrame(content, fg_color="transparent")
            top_row.grid(row=1, column=0, padx=CONTENT_PADX, pady=(10, 10), sticky="new")
            top_row.grid_columnconfigure(0, weight=1)
            top_row.grid_columnconfigure(1, weight=1)

            if has_add_panel:
                add_panel = ctk.CTkFrame(top_row, corner_radius=PANEL_CORNER_RADIUS)
                add_panel.grid(
                    row=0,
                    column=0,
                    columnspan=1 if both_panels else 2,
                    padx=(0, PANEL_GAP) if both_panels else 0,
                    sticky="new",
                )
                add_panel.grid_columnconfigure(1, weight=1)

                build_group_header(add_panel, "New key")

                row = 1

                marketplace_label = ctk.CTkLabel(add_panel, text="Marketplace:", width=LABEL_WIDTH, anchor="w")
                marketplace_label.grid(row=row, column=0, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

                self.keys_marketplace_option = ctk.CTkOptionMenu(
                    add_panel,
                    values=[Marketplace.WB.value, Marketplace.OZON.value],
                    command=lambda _choice: self._build_keys_credential_fields(),
                    width=ENTRY_WIDTH,
                )
                self.keys_marketplace_option.set(Marketplace.WB.value)
                self.keys_marketplace_option.grid(row=row, column=1, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")
                row += 1

                self.keys_fields_frame = ctk.CTkFrame(add_panel, fg_color="transparent")
                self.keys_fields_frame.grid(row=row, column=0, columnspan=2, sticky="w")
                row += 1

                name_label = ctk.CTkLabel(add_panel, text="Name:", width=LABEL_WIDTH, anchor="w")
                name_label.grid(row=row, column=0, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

                self.keys_name_entry = ctk.CTkEntry(add_panel, width=ENTRY_WIDTH)
                self.keys_name_entry.grid(row=row, column=1, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")
                row += 1

                save_button = ctk.CTkButton(
                    add_panel,
                    text="Save Key",
                    height=40,
                    command=self._save_key_from_gui,
                )
                save_button.grid(row=row, column=0, padx=FIELD_PADX, pady=(10, 20), sticky="w")
                row += 1

                self._build_keys_credential_fields()

            if has_check_panel:
                check_panel = ctk.CTkFrame(top_row, corner_radius=PANEL_CORNER_RADIUS)
                check_panel.grid(
                    row=0,
                    column=1 if both_panels else 0,
                    columnspan=1 if both_panels else 2,
                    padx=(PANEL_GAP, 0) if both_panels else 0,
                    sticky="new",
                )
                check_panel.grid_columnconfigure(1, weight=1)

                build_group_header(check_panel, "Check / copy key")

                row = 1

                # Одно поле имени на оба действия (Check и Copy), не два
                # рядом с одинаковым значением — выбор строки чекбоксом
                # в таблице ниже подставляет имя сюда один раз.
                name_label = ctk.CTkLabel(check_panel, text="Key name:", width=LABEL_WIDTH, anchor="w")
                name_label.grid(row=row, column=0, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

                self.keys_selected_name_entry = ctk.CTkEntry(check_panel, width=ENTRY_WIDTH)
                self.keys_selected_name_entry.grid(row=row, column=1, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")
                row += 1

                if can_check:
                    check_button = ctk.CTkButton(
                        check_panel,
                        text="Check",
                        height=32,
                        command=self._check_key_from_gui,
                    )
                    check_button.grid(row=row, column=0, padx=FIELD_PADX, pady=(0, 15), sticky="w")

                if can_copy:
                    copy_button = ctk.CTkButton(
                        check_panel,
                        text="Copy full secret to clipboard",
                        height=32,
                        command=self._copy_key_from_gui,
                    )
                    copy_button.grid(
                        row=row,
                        column=1 if can_check else 0,
                        columnspan=1 if can_check else 2,
                        padx=FIELD_PADX,
                        pady=(0, 15),
                        sticky="w",
                    )
                row += 1

            next_row = 2

        self.keys_message_label = ctk.CTkLabel(
            content, text="", font=ctk.CTkFont(size=13), justify="left"
        )
        self.keys_message_label.grid(
            row=next_row, column=0, padx=CONTENT_PADX, pady=(0, 10), sticky="w"
        )
        next_row += 1

        content.grid_rowconfigure(next_row, weight=1)

        list_frame = ctk.CTkFrame(content, corner_radius=PANEL_CORNER_RADIUS)
        list_frame.grid(row=next_row, column=0, padx=CONTENT_PADX, pady=(10, 30), sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        list_header = ctk.CTkFrame(list_frame, fg_color="transparent")
        list_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        list_header.grid_columnconfigure(0, weight=1)

        list_title = ctk.CTkLabel(
            list_header,
            text="Saved keys",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        list_title.grid(row=0, column=0, sticky="w")

        refresh_button = ctk.CTkButton(
            list_header,
            text="Refresh",
            height=32,
            width=100,
            command=self._refresh_keys_list,
        )
        refresh_button.grid(row=0, column=1, sticky="e", padx=(10, 0))

        # Настоящая таблица вместо текстового блока: колонки + чекбокс на
        # строку. Чекбокс не для массовых операций — он один раз подставляет
        # имя ключа в поля Check/Copy выше, чтобы не перепечатывать его
        # руками (актуально с учётом отдельной проблемы кириллицы в полях
        # ввода на Windows).
        self.keys_table_frame = ctk.CTkScrollableFrame(
            list_frame, fg_color="transparent"
        )
        self.keys_table_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))

        self._refresh_keys_list()

    def _build_keys_credential_fields(self) -> None:
        """
        Пересобрать поля ввода credentials под выбранный маркетплейс.

        Вызывается при смене Marketplace-дропдауна. Не трогает сам
        дропдаун (он живёт в родительском form, а не в keys_fields_frame),
        поэтому безопасно вызывать это из command= самого дропдауна.
        """
        if self.keys_fields_frame is None or self.keys_marketplace_option is None:
            return

        for widget in self.keys_fields_frame.winfo_children():
            widget.destroy()

        self.keys_field_entries = {}
        self.keys_kind_option = None
        self.keys_ozon_entries_frame = None

        marketplace = self.keys_marketplace_option.get()

        if marketplace == Marketplace.WB.value:
            token_label = ctk.CTkLabel(self.keys_fields_frame, text="WB Token (JWT):", width=LABEL_WIDTH, anchor="w")
            token_label.grid(row=0, column=0, padx=FIELD_PADX, pady=10, sticky="w")

            token_entry = ctk.CTkEntry(self.keys_fields_frame, width=ENTRY_WIDTH_WIDE, show="*")
            token_entry.grid(row=0, column=1, padx=FIELD_PADX, pady=10, sticky="w")
            self.keys_field_entries["token"] = token_entry
            return

        # OZON: два независимых типа credentials на одного продавца.
        kind_label = ctk.CTkLabel(self.keys_fields_frame, text="Key type:", width=LABEL_WIDTH, anchor="w")
        kind_label.grid(row=0, column=0, padx=FIELD_PADX, pady=10, sticky="w")

        self.keys_kind_option = ctk.CTkOptionMenu(
            self.keys_fields_frame,
            values=[KeyKind.SELLER.value, KeyKind.PERFORMANCE.value],
            command=lambda _choice: self._build_ozon_credential_entries(),
            width=ENTRY_WIDTH,
        )
        self.keys_kind_option.set(KeyKind.SELLER.value)
        self.keys_kind_option.grid(row=0, column=1, padx=FIELD_PADX, pady=10, sticky="w")

        self.keys_ozon_entries_frame = ctk.CTkFrame(self.keys_fields_frame, fg_color="transparent")
        self.keys_ozon_entries_frame.grid(row=1, column=0, columnspan=2, sticky="w")

        self._build_ozon_credential_entries()

    def _build_ozon_credential_entries(self) -> None:
        """
        Пересобрать пару полей id/secret под выбранный тип Ozon-ключа.

        Живёт в отдельном под-фрейме, не трогает keys_kind_option — это
        важно, потому что вызывается из command= самого keys_kind_option.
        """
        if self.keys_ozon_entries_frame is None or self.keys_kind_option is None:
            return

        for widget in self.keys_ozon_entries_frame.winfo_children():
            widget.destroy()

        self.keys_field_entries = {
            key: entry
            for key, entry in self.keys_field_entries.items()
            if key not in ("client_id", "api_key", "client_secret")
        }

        kind = self.keys_kind_option.get()

        if kind == KeyKind.SELLER.value:
            id_label_text, secret_label_text = "Client-Id:", "Api-Key:"
            id_field, secret_field = "client_id", "api_key"
        else:
            id_label_text, secret_label_text = "Client ID:", "Client Secret:"
            id_field, secret_field = "client_id", "client_secret"

        id_label = ctk.CTkLabel(self.keys_ozon_entries_frame, text=id_label_text, width=LABEL_WIDTH, anchor="w")
        id_label.grid(row=0, column=0, padx=FIELD_PADX, pady=10, sticky="w")
        id_entry = ctk.CTkEntry(self.keys_ozon_entries_frame, width=ENTRY_WIDTH)
        id_entry.grid(row=0, column=1, padx=FIELD_PADX, pady=10, sticky="w")
        self.keys_field_entries[id_field] = id_entry

        secret_label = ctk.CTkLabel(self.keys_ozon_entries_frame, text=secret_label_text, width=LABEL_WIDTH, anchor="w")
        secret_label.grid(row=1, column=0, padx=FIELD_PADX, pady=10, sticky="w")
        secret_entry = ctk.CTkEntry(self.keys_ozon_entries_frame, width=ENTRY_WIDTH, show="*")
        secret_entry.grid(row=1, column=1, padx=FIELD_PADX, pady=10, sticky="w")
        self.keys_field_entries[secret_field] = secret_entry

    def _collect_wb_secret(self) -> tuple[str, str]:
        entry = self.keys_field_entries.get("token")
        token = entry.get().strip() if entry is not None else ""

        if not token:
            raise ValueError("WB token is required.")

        try:
            token_info(token)
        except Exception as error:
            raise ValueError(f"Invalid WB token: {error}") from error

        return token, KeyKind.JWT.value

    def _collect_ozon_secret(self) -> tuple[str, str]:
        kind = self.keys_kind_option.get() if self.keys_kind_option is not None else KeyKind.SELLER.value

        id_entry = self.keys_field_entries.get("client_id")
        client_id = id_entry.get().strip() if id_entry is not None else ""

        if kind == KeyKind.SELLER.value:
            secret_entry = self.keys_field_entries.get("api_key")
            api_key = secret_entry.get().strip() if secret_entry is not None else ""

            if not client_id or not api_key:
                raise ValueError("Client-Id and Api-Key are required.")

            secret = json.dumps({"client_id": client_id, "api_key": api_key})
            return secret, KeyKind.SELLER.value

        secret_entry = self.keys_field_entries.get("client_secret")
        client_secret = secret_entry.get().strip() if secret_entry is not None else ""

        if not client_id or not client_secret:
            raise ValueError("Client ID and Client Secret are required.")

        secret = json.dumps({"client_id": client_id, "client_secret": client_secret})
        return secret, KeyKind.PERFORMANCE.value

    def _set_keys_message(self, text: str) -> None:
        if self.keys_message_label is not None:
            self.keys_message_label.configure(text=text)

    def _clear_keys_credential_entries(self) -> None:
        """
        Стереть введённый секрет из полей формы после успешного сохранения.

        Поля и так маскируются (show="*") пока вводишь, но не очищались
        после Save — секрет продолжал висеть в открытом виде в поле ввода
        сколько угодно, пока не переключишь маркетплейс/тип ключа.
        """
        for entry in self.keys_field_entries.values():
            entry.delete(0, "end")

    def _save_key_from_gui(self) -> None:
        if self.keys_name_entry is None or self.keys_marketplace_option is None:
            return

        name = self.keys_name_entry.get().strip()
        marketplace = self.keys_marketplace_option.get()

        if not name:
            self._set_keys_message("Name is required.")
            return

        try:
            if marketplace == Marketplace.WB.value:
                secret, key_kind = self._collect_wb_secret()
            else:
                secret, key_kind = self._collect_ozon_secret()
        except ValueError as error:
            self._set_keys_message(str(error))
            return

        session = SessionLocal()
        try:
            if get_api_key_by_name(session, name) is not None:
                self._set_keys_message(f"Name already exists: {name}")
                return

            try:
                stored = self.key_storage.save_token(name, secret)
            except ValueError as error:
                self._set_keys_message(str(error))
                return

            # Ozon-secret — JSON, а не сырой токен: обычная маска на нём
            # маскирует байты JSON, а не сами client_id/api_key. Отдельная
            # маска поверх значений полей, для отображения в списке.
            masked_token = stored["masked_token"]
            if marketplace == Marketplace.OZON.value:
                masked_token = mask_ozon_credentials(secret)

            add_api_key(
                session,
                name=name,
                marketplace=marketplace,
                key_kind=key_kind,
                masked_token=masked_token,
                storage_type=stored["storage_type"],
            )
        finally:
            session.close()

        self.keys_name_entry.delete(0, "end")
        self._clear_keys_credential_entries()
        self._set_keys_message(f"Saved: {name} ({marketplace} / {key_kind})")
        self._refresh_keys_list()

    def _check_key_from_gui(self) -> None:
        if self.keys_selected_name_entry is None:
            return

        name = self.keys_selected_name_entry.get().strip()
        if not name:
            self._set_keys_message("Enter a key name to check.")
            return

        session = SessionLocal()
        try:
            api_key = get_api_key_by_name(session, name)
            if api_key is None:
                self._set_keys_message(f"Key not found: {name}")
                return

            secret = self.key_storage.get_token(name)
            if secret is None:
                self._set_keys_message(f"Secret not found in storage for: {name}")
                return

            try:
                status, detail = self._run_key_check(api_key.marketplace, api_key.key_kind, secret)
            except Exception as error:
                self._set_keys_message(f"Check failed: {error}")
                return

            record_check_result(session, name, status, detail)
        finally:
            session.close()

        message = f"Checked {name}: {status}"
        if detail:
            message += f"\n{detail}"
        self._set_keys_message(message)
        self._refresh_keys_list()

    def _copy_key_from_gui(self) -> None:
        """
        Скопировать расшифрованный секрет в буфер обмена — чтобы завести
        тот же ключ в другом инструменте/проекте, не читая руками
        encrypted_keys.json. Секрет НИКОГДА не выводится в саму форму —
        только в буфер, только по явному запросу с правом view_full_key.
        """
        if self.keys_selected_name_entry is None:
            return

        name = self.keys_selected_name_entry.get().strip()
        if not name:
            self._set_keys_message("Enter a key name to copy.")
            return

        secret = self.key_storage.get_token(name)
        if secret is None:
            self._set_keys_message(f"Secret not found in storage for: {name}")
            return

        self.clipboard_clear()
        self.clipboard_append(secret)
        self.update()

        self._set_keys_message(f"Copied full secret to clipboard: {name}")

    def _run_key_check(self, marketplace: str, key_kind: str, secret: str) -> tuple[str, str | None]:
        """
        Синхронная обёртка вокруг async-проверок wb_ping/ozon_ping.

        Блокирует GUI на время запроса(ов) — для WB это может быть
        несколько секунд (пинг нескольких разделов с паузой между ними).
        Приемлемо для v1, вынесение в отдельный поток — на будущее.

        Возвращает (агрегированный статус, детальная расшифровка по
        разделам | None). Для WB детализация — по разделам API (Content,
        Analytics, ...), т.к. один токен покрывает несколько разделов и
        они могут отвечать по-разному. Для Ozon такого деления нет —
        один seller/performance ключ = один статус, detail всегда None.
        """
        if marketplace == Marketplace.WB.value:
            info = token_info(secret)
            results = asyncio.run(ping_token_detailed(secret, info["bitmask"]))
            if not results:
                return "NO_SCOPES", None
            status = reduce_ping_results([code for _name, code in results])
            detail = "\n".join(f"  {name}: {code}" for name, code in results)
            return status, detail

        credentials = json.loads(secret)

        async def check() -> dict:
            async with httpx.AsyncClient() as client:
                if key_kind == KeyKind.SELLER.value:
                    return await check_seller_key(
                        client, credentials["client_id"], credentials["api_key"]
                    )
                return await check_performance_key(
                    client, credentials["client_id"], credentials["client_secret"]
                )

        result = asyncio.run(check())
        return result["status"], None

    _KEYS_TABLE_COLUMNS = ("", "Name", "Marketplace", "Kind", "Masked", "Status", "Checked at")

    def _refresh_keys_list(self) -> None:
        if self.keys_table_frame is None:
            return

        for widget in self.keys_table_frame.winfo_children():
            widget.destroy()

        for col in range(len(self._KEYS_TABLE_COLUMNS)):
            self.keys_table_frame.grid_columnconfigure(col, weight=0)

        for col, heading in enumerate(self._KEYS_TABLE_COLUMNS):
            header = ctk.CTkLabel(
                self.keys_table_frame,
                text=heading,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            )
            header.grid(row=0, column=col, padx=(0, 16), pady=(0, 8), sticky="w")

        session = SessionLocal()
        try:
            keys = list_api_keys(session)
        finally:
            session.close()

        self.keys_row_checkboxes = {}

        if not keys:
            empty_label = ctk.CTkLabel(self.keys_table_frame, text="No keys saved yet.")
            empty_label.grid(
                row=1, column=0, columnspan=len(self._KEYS_TABLE_COLUMNS),
                padx=0, pady=10, sticky="w",
            )
            return

        grid_row = 1
        for key in keys:
            # Кеш последнего Check (record_check_result) — не "проверяем
            # прямо сейчас", а последнее, что мы знаем. checked_at всегда
            # берём из last_used_at, т.к. это единственное поле, куда
            # Check пишет время (см. key_repository.record_check_result).
            status = key.last_check_status or ("active" if key.is_active else "not checked")
            checked_at = (
                key.last_used_at.strftime("%Y-%m-%d %H:%M:%S")
                if key.last_used_at
                else "never"
            )

            checkbox = ctk.CTkCheckBox(self.keys_table_frame, text="", width=20)
            checkbox.configure(command=lambda name=key.name: self._select_key_row(name))
            checkbox.grid(row=grid_row, column=0, padx=(0, 16), pady=6, sticky="w")
            self.keys_row_checkboxes[key.name] = checkbox

            values = (key.name, key.marketplace, key.key_kind, key.masked_token, status, checked_at)
            for col, value in enumerate(values, start=1):
                cell = ctk.CTkLabel(self.keys_table_frame, text=value, anchor="w")
                cell.grid(row=grid_row, column=col, padx=(0, 16), pady=6, sticky="w")

            grid_row += 1

            if key.last_check_detail:
                detail_text = "  |  ".join(key.last_check_detail.splitlines())
                detail_label = ctk.CTkLabel(
                    self.keys_table_frame,
                    text=detail_text,
                    font=ctk.CTkFont(size=11),
                    text_color="#9AA0A6",
                    anchor="w",
                    justify="left",
                )
                detail_label.grid(
                    row=grid_row, column=1, columnspan=len(self._KEYS_TABLE_COLUMNS) - 1,
                    padx=(0, 16), pady=(0, 6), sticky="w",
                )
                grid_row += 1

    def _select_key_row(self, name: str) -> None:
        """
        Один чекбокс за раз: выбор строки подставляет её имя в общее поле
        Key name выше (одно на Check и Copy — раньше было два одинаковых
        поля рядом, что было лишним), а не копит несколько выбранных
        ключей сразу.
        """
        for row_name, checkbox in self.keys_row_checkboxes.items():
            if row_name != name:
                checkbox.deselect()

        if self.keys_selected_name_entry is not None:
            self.keys_selected_name_entry.delete(0, "end")
            self.keys_selected_name_entry.insert(0, name)

