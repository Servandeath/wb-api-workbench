import asyncio
import json

import customtkinter as ctk
import httpx

from app.core.encrypted_file_storage import EncryptedFileKeyStorage
from app.core.marketplace import KeyKind, Marketplace
from app.core.ozon_ping import check_performance_key, check_seller_key
from app.gui.sections.diagnostics_section import DiagnosticsSectionMixin
from app.gui.sections.settings_section import SettingsSectionMixin
from app.gui.sections.users_section import UsersSectionMixin
from app.core.permissions import has_permission
from app.core.settings import AppMode, UserRole
from app.config import USERS_FILE
from app.core.user_store import load_users, save_users
from app.core.wb_ping import ping_token
from app.core.wb_token import token_info
from app.db.database import SessionLocal, init_db
from app.db.key_repository import (
    activate_api_key,
    add_api_key,
    deactivate_api_key,
    get_api_key_by_name,
    list_api_keys,
    touch_api_key_last_used,
)
from app.core.users import UserAccount, create_user


class MainWindow(DiagnosticsSectionMixin, SettingsSectionMixin, UsersSectionMixin, ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("WB API Workbench")
        self.geometry("1100x720")
        self.minsize(1000, 650)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.current_section = "API Tester"
        self.current_role = UserRole.VIEWER.value
        self.current_mode = AppMode.TEST.value

        self.user_accounts: list[UserAccount] = []

        self.diagnostics_output: ctk.CTkTextbox | None = None

        self.role_option: ctk.CTkOptionMenu | None = None
        self.mode_option: ctk.CTkOptionMenu | None = None
        self.settings_message_label: ctk.CTkLabel | None = None

        self.new_username_entry: ctk.CTkEntry | None = None
        self.new_user_role_option: ctk.CTkOptionMenu | None = None
        self.users_output: ctk.CTkTextbox | None = None
        self.users_message_label: ctk.CTkLabel | None = None

        self.manage_username_entry: ctk.CTkEntry | None = None
        self.manage_role_option: ctk.CTkOptionMenu | None = None

        self.keys_marketplace_option: ctk.CTkOptionMenu | None = None
        self.keys_kind_option: ctk.CTkOptionMenu | None = None
        self.keys_fields_frame: ctk.CTkFrame | None = None
        self.keys_ozon_entries_frame: ctk.CTkFrame | None = None
        self.keys_field_entries: dict[str, ctk.CTkEntry] = {}
        self.keys_name_entry: ctk.CTkEntry | None = None
        self.keys_message_label: ctk.CTkLabel | None = None
        self.keys_check_name_entry: ctk.CTkEntry | None = None
        self.keys_output: ctk.CTkTextbox | None = None

        init_db()
        self.key_storage = EncryptedFileKeyStorage()

        self._build_layout()
        self._load_users_on_start()

    def _load_users_on_start(self) -> None:
        self.user_accounts = load_users(USERS_FILE)

        has_admin = any(
            user.role == UserRole.ADMIN for user in self.user_accounts
        )
        if not has_admin:
            self.user_accounts.append(create_user("admin", UserRole.ADMIN))
            save_users(USERS_FILE, self.user_accounts)
    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_sidebar()
        self._build_topbar()
        self._show_default_section(
            title="API Tester",
            description="Test Wildberries API methods here.",
        )

    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        title = ctk.CTkLabel(
            self.sidebar,
            text="WB Workbench",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.pack(pady=(24, 20), padx=16)

        sections = [
            "API Tester",
            "Keys",
            "Imports",
            "History",
            "Diagnostics",
            "Settings",
            "Users",
        ]

        for section in sections:
            button = ctk.CTkButton(
                self.sidebar,
                text=section,
                anchor="w",
                height=40,
                command=lambda name=section: self.show_section(name),
            )
            button.pack(fill="x", padx=16, pady=6)

    def _build_topbar(self) -> None:
        self.topbar = ctk.CTkFrame(self, height=70, corner_radius=0)
        self.topbar.grid(row=0, column=1, sticky="ew")
        self.topbar.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.topbar,
            text=self.current_section,
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.title_label.grid(row=0, column=0, padx=24, pady=18, sticky="w")

        self.status_label = ctk.CTkLabel(
            self.topbar,
            text=self._get_status_text(),
            font=ctk.CTkFont(size=13),
        )
        self.status_label.grid(row=0, column=1, padx=24, pady=18, sticky="e")

    def _get_status_text(self) -> str:
        return (
            f"Role: {self.current_role}  |  "
            f"Mode: {self.current_mode}  |  "
            "Key: not set"
        )

    def _update_status_label(self) -> None:
        self.status_label.configure(text=self._get_status_text())

    def _clear_content(self) -> None:
        for widget in self.winfo_children():
            if widget.grid_info().get("row") == 1 and widget.grid_info().get("column") == 1:
                widget.destroy()

    def _create_content_frame(self) -> ctk.CTkFrame:
        self._clear_content()

        content = ctk.CTkFrame(self, corner_radius=12)
        content.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(2, weight=1)

        return content

    def _show_default_section(self, title: str, description: str) -> None:
        content = self._create_content_frame()

        section_title = ctk.CTkLabel(
            content,
            text=title,
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        section_title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        section_description = ctk.CTkLabel(
            content,
            text=description,
            font=ctk.CTkFont(size=16),
            justify="left",
        )
        section_description.grid(row=1, column=0, padx=30, pady=10, sticky="nw")

    def _show_keys_section(self) -> None:
        current_role = UserRole(self.current_role)

        if not has_permission(current_role, "view_masked_keys"):
            self._show_default_section(
                title="Keys",
                description="Access denied.",
            )
            return

        content = self._create_content_frame()
        content.grid_rowconfigure(2, weight=0)

        title = ctk.CTkLabel(
            content,
            text="Keys",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        description = ctk.CTkLabel(
            content,
            text="Store and check WB and Ozon API keys.",
            font=ctk.CTkFont(size=16),
            justify="left",
        )
        description.grid(row=1, column=0, padx=30, pady=10, sticky="w")

        can_manage = has_permission(current_role, "add_key")
        next_row = 2

        if can_manage:
            form = ctk.CTkFrame(content, corner_radius=12)
            form.grid(row=2, column=0, padx=30, pady=(10, 20), sticky="new")
            form.grid_columnconfigure(1, weight=1)

            marketplace_label = ctk.CTkLabel(form, text="Marketplace:")
            marketplace_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")

            self.keys_marketplace_option = ctk.CTkOptionMenu(
                form,
                values=[Marketplace.WB.value, Marketplace.OZON.value],
                command=lambda _choice: self._build_keys_credential_fields(),
            )
            self.keys_marketplace_option.set(Marketplace.WB.value)
            self.keys_marketplace_option.grid(row=0, column=1, padx=20, pady=15, sticky="w")

            self.keys_fields_frame = ctk.CTkFrame(form, fg_color="transparent")
            self.keys_fields_frame.grid(row=1, column=0, columnspan=2, sticky="w")

            name_label = ctk.CTkLabel(form, text="Name:")
            name_label.grid(row=2, column=0, padx=20, pady=15, sticky="w")

            self.keys_name_entry = ctk.CTkEntry(form, width=240)
            self.keys_name_entry.grid(row=2, column=1, padx=20, pady=15, sticky="w")

            save_button = ctk.CTkButton(
                form,
                text="Save Key",
                height=40,
                command=self._save_key_from_gui,
            )
            save_button.grid(row=3, column=0, padx=20, pady=(10, 5), sticky="w")

            check_label = ctk.CTkLabel(form, text="Check key by name:")
            check_label.grid(row=4, column=0, padx=20, pady=(15, 5), sticky="w")

            self.keys_check_name_entry = ctk.CTkEntry(form, width=240)
            self.keys_check_name_entry.grid(row=4, column=1, padx=20, pady=(15, 5), sticky="w")

            check_button = ctk.CTkButton(
                form,
                text="Check",
                height=32,
                command=self._check_key_from_gui,
            )
            check_button.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="w")

            self.keys_message_label = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=13))
            self.keys_message_label.grid(
                row=6,
                column=0,
                columnspan=2,
                padx=20,
                pady=(0, 20),
                sticky="w",
            )

            self._build_keys_credential_fields()

            next_row = 3

        content.grid_rowconfigure(next_row, weight=1)

        list_frame = ctk.CTkFrame(content, corner_radius=12)
        list_frame.grid(row=next_row, column=0, padx=30, pady=(10, 30), sticky="nsew")
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

        self.keys_output = ctk.CTkTextbox(list_frame, height=260)
        self.keys_output.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))

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
            token_label = ctk.CTkLabel(self.keys_fields_frame, text="WB Token (JWT):")
            token_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

            token_entry = ctk.CTkEntry(self.keys_fields_frame, width=380, show="*")
            token_entry.grid(row=0, column=1, padx=20, pady=10, sticky="w")
            self.keys_field_entries["token"] = token_entry
            return

        # OZON: два независимых типа credentials на одного продавца.
        kind_label = ctk.CTkLabel(self.keys_fields_frame, text="Key type:")
        kind_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.keys_kind_option = ctk.CTkOptionMenu(
            self.keys_fields_frame,
            values=[KeyKind.SELLER.value, KeyKind.PERFORMANCE.value],
            command=lambda _choice: self._build_ozon_credential_entries(),
        )
        self.keys_kind_option.set(KeyKind.SELLER.value)
        self.keys_kind_option.grid(row=0, column=1, padx=20, pady=10, sticky="w")

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

        id_label = ctk.CTkLabel(self.keys_ozon_entries_frame, text=id_label_text)
        id_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        id_entry = ctk.CTkEntry(self.keys_ozon_entries_frame, width=240)
        id_entry.grid(row=0, column=1, padx=20, pady=10, sticky="w")
        self.keys_field_entries[id_field] = id_entry

        secret_label = ctk.CTkLabel(self.keys_ozon_entries_frame, text=secret_label_text)
        secret_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        secret_entry = ctk.CTkEntry(self.keys_ozon_entries_frame, width=240, show="*")
        secret_entry.grid(row=1, column=1, padx=20, pady=10, sticky="w")
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

            add_api_key(
                session,
                name=name,
                marketplace=marketplace,
                key_kind=key_kind,
                masked_token=stored["masked_token"],
                storage_type=stored["storage_type"],
            )
        finally:
            session.close()

        self.keys_name_entry.delete(0, "end")
        self._clear_keys_credential_entries()
        self._set_keys_message(f"Saved: {name} ({marketplace} / {key_kind})")
        self._refresh_keys_list()

    def _check_key_from_gui(self) -> None:
        if self.keys_check_name_entry is None:
            return

        name = self.keys_check_name_entry.get().strip()
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
                status = self._run_key_check(api_key.marketplace, api_key.key_kind, secret)
            except Exception as error:
                self._set_keys_message(f"Check failed: {error}")
                return

            if status == "OK":
                activate_api_key(session, name)
            else:
                deactivate_api_key(session, name)
            touch_api_key_last_used(session, name)
        finally:
            session.close()

        self._set_keys_message(f"Checked {name}: {status}")
        self._refresh_keys_list()

    def _run_key_check(self, marketplace: str, key_kind: str, secret: str) -> str:
        """
        Синхронная обёртка вокруг async-проверок wb_ping/ozon_ping.

        Блокирует GUI на время запроса(ов) — для WB это может быть
        несколько секунд (пинг нескольких разделов с паузой между ними).
        Приемлемо для v1, вынесение в отдельный поток — на будущее.
        """
        if marketplace == Marketplace.WB.value:
            info = token_info(secret)
            return asyncio.run(ping_token(secret, info["bitmask"]))

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
        return result["status"]

    def _refresh_keys_list(self) -> None:
        if self.keys_output is None:
            return

        session = SessionLocal()
        try:
            keys = list_api_keys(session)
        finally:
            session.close()

        lines = []
        for index, key in enumerate(keys, start=1):
            status = "active" if key.is_active else "not checked / inactive"
            lines.append(
                f"{index}. {key.name} | {key.marketplace} / {key.key_kind} | "
                f"{key.masked_token} | {status}"
            )

        output = "\n".join(lines) if lines else "No keys saved yet."

        self.keys_output.delete("1.0", "end")
        self.keys_output.insert("1.0", output)

    def show_section(self, section_name: str) -> None:
        self.current_section = section_name
        self.title_label.configure(text=section_name)

        descriptions = {
            "API Tester": "Test Wildberries API methods here.",
            "Keys": "Manage temporary, saved and encrypted API keys here.",
            "Imports": "Import local JSON, CSV and Excel files here.",
            "History": "View API request history and saved responses here.",
            "Settings": "Configure app settings, storage modes and access rules here.",
            "Users": "Manage manager accounts and roles here.",
        }

        if section_name == "Keys":
            self._show_keys_section()
            return

        if section_name == "Diagnostics":
            self._show_diagnostics_section()
            return

        if section_name == "Settings":
            self._show_settings_section()
            return

        if section_name == "Users":
            self._show_users_section()
            return

        self._show_default_section(
            title=section_name,
            description=descriptions.get(section_name, "Section is under development."),
        )


def run_gui() -> None:
    app = MainWindow()
    app.mainloop()
