
import customtkinter as ctk

from app.core.encrypted_file_storage import EncryptedFileKeyStorage
from app.gui.sections.diagnostics_section import DiagnosticsSectionMixin
from app.gui.sections.settings_section import SettingsSectionMixin
from app.gui.sections.users_section import UsersSectionMixin
from app.gui.sections.keys_section import KeysSectionMixin
from app.gui.sections.api_tester_section import ApiTesterSectionMixin
from app.gui.sections.history_section import HistorySectionMixin
from app.core.settings import UserRole
from app.config import SESSION_FILE, USERS_FILE
from app.core.session_state import load_session_state
from app.core.session_key_storage import SessionKeyStorage
from app.core.user_store import load_users, save_users
from app.db.database import init_db
from app.core.users import UserAccount, create_user


class MainWindow(
    DiagnosticsSectionMixin,
    SettingsSectionMixin,
    UsersSectionMixin,
    KeysSectionMixin,
    ApiTesterSectionMixin,
    HistorySectionMixin,
    ctk.CTk,
):
    def __init__(self) -> None:
        super().__init__()

        self.title("WB API Workbench")
        self.geometry("1100x720")
        self.minsize(1000, 650)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.current_section = "API Tester"

        # Роль и режим — с прошлого запуска (Settings -> Apply Settings их
        # сохраняет), а не всегда Viewer/Test по умолчанию.
        saved_role, saved_mode = load_session_state(SESSION_FILE)
        self.current_role = saved_role.value
        self.current_mode = saved_mode.value

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
        self.keys_selected_name_entry: ctk.CTkEntry | None = None
        self.keys_table_frame: ctk.CTkScrollableFrame | None = None
        self.keys_row_checkboxes: dict[str, ctk.CTkCheckBox] = {}

        self.api_tester_section_option: ctk.CTkOptionMenu | None = None
        self.api_tester_method_option: ctk.CTkOptionMenu | None = None
        self.api_tester_path_entry: ctk.CTkEntry | None = None
        self.api_tester_body_textbox: ctk.CTkTextbox | None = None
        self.api_tester_temp_key_entry: ctk.CTkEntry | None = None
        self.api_tester_key_option: ctk.CTkOptionMenu | None = None
        self.api_tester_save_checkbox: ctk.CTkCheckBox | None = None
        self.api_tester_message_label: ctk.CTkLabel | None = None
        self.api_tester_output: ctk.CTkTextbox | None = None

        self.history_output: ctk.CTkTextbox | None = None

        init_db()
        self.key_storage = EncryptedFileKeyStorage()
        # Только в памяти процесса — временный ключ из API Tester (Test
        # mode) никогда не должен попасть на диск, в отличие от Keys.
        self.session_key_storage = SessionKeyStorage()

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

        # Imports убран из сайдбара — заглушка без данных и функционала
        # (см. обсуждение в чате), не стоит показывать в портфолио-версии.
        # Вернём, когда появится реальный импорт JSON/CSV/Excel.
        sections = [
            "API Tester",
            "Keys",
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

    def show_section(self, section_name: str) -> None:
        self.current_section = section_name
        self.title_label.configure(text=section_name)

        descriptions = {
            "API Tester": "Test Wildberries API methods here.",
            "Keys": "Manage temporary, saved and encrypted API keys here.",
            "Settings": "Configure app settings, storage modes and access rules here.",
            "Users": "Manage manager accounts and roles here.",
        }

        if section_name == "API Tester":
            self._show_api_tester_section()
            return

        if section_name == "Keys":
            self._show_keys_section()
            return

        if section_name == "History":
            self._show_history_section()
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
