import customtkinter as ctk

from app.core.diagnostics import format_diagnostics, run_diagnostics
from app.core.permissions import has_permission
from app.core.settings import AppMode, UserRole, apply_settings
from app.config import USERS_FILE
from app.core.user_store import load_users, save_users
from app.db.database import init_db
from app.core.users import (
    UserAccount,
    add_user,
    change_user_role,
    create_user,
    deactivate_user,
    find_user,
)


class MainWindow(ctk.CTk):
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

        init_db()

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

    def _show_diagnostics_section(self) -> None:
        content = self._create_content_frame()

        title = ctk.CTkLabel(
            content,
            text="Diagnostics",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        run_button = ctk.CTkButton(
            content,
            text="Run Diagnostics",
            height=40,
            command=self._run_diagnostics,
        )
        run_button.grid(row=1, column=0, padx=30, pady=10, sticky="w")

        self.diagnostics_output = ctk.CTkTextbox(content, height=360)
        self.diagnostics_output.grid(
            row=2,
            column=0,
            padx=30,
            pady=(10, 30),
            sticky="nsew",
        )
        self.diagnostics_output.insert(
            "1.0",
            "Click Run Diagnostics to check the local app environment.",
        )

    def _run_diagnostics(self) -> None:
        if self.diagnostics_output is None:
            return

        results = run_diagnostics()
        output = format_diagnostics(results)

        self.diagnostics_output.delete("1.0", "end")
        self.diagnostics_output.insert("1.0", output)

    def _show_settings_section(self) -> None:
        content = self._create_content_frame()

        title = ctk.CTkLabel(
            content,
            text="Settings",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        description = ctk.CTkLabel(
            content,
            text="Configure manager role and API mode.",
            font=ctk.CTkFont(size=16),
            justify="left",
        )
        description.grid(row=1, column=0, padx=30, pady=10, sticky="w")

        form = ctk.CTkFrame(content, corner_radius=12)
        form.grid(row=2, column=0, padx=30, pady=20, sticky="nw")
        form.grid_columnconfigure(1, weight=1)

        role_label = ctk.CTkLabel(form, text="Role:")
        role_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        self.role_option = ctk.CTkOptionMenu(
            form,
            values=[role.value for role in UserRole],
        )
        self.role_option.set(self.current_role)
        self.role_option.grid(row=0, column=1, padx=20, pady=15, sticky="w")

        mode_label = ctk.CTkLabel(form, text="Mode:")
        mode_label.grid(row=1, column=0, padx=20, pady=15, sticky="w")

        self.mode_option = ctk.CTkOptionMenu(
            form,
            values=[mode.value for mode in AppMode],
        )
        self.mode_option.set(self.current_mode)
        self.mode_option.grid(row=1, column=1, padx=20, pady=15, sticky="w")

        apply_button = ctk.CTkButton(
            form,
            text="Apply Settings",
            height=40,
            command=self._apply_settings_from_gui,
        )
        apply_button.grid(
            row=2,
            column=0,
            columnspan=2,
            padx=20,
            pady=20,
            sticky="w",
        )

        self.settings_message_label = ctk.CTkLabel(
            form,
            text="Viewer and Tester can use Test mode only.",
            font=ctk.CTkFont(size=13),
        )
        self.settings_message_label.grid(
            row=3,
            column=0,
            columnspan=2,
            padx=20,
            pady=(0, 20),
            sticky="w",
        )

    def _apply_settings_from_gui(self) -> None:
        if self.role_option is None or self.mode_option is None:
            return

        selected_role = UserRole(self.role_option.get())
        selected_mode = AppMode(self.mode_option.get())

        try:
            role, mode = apply_settings(selected_role, selected_mode)
        except PermissionError as error:
            if self.settings_message_label is not None:
                self.settings_message_label.configure(text=str(error))
            return

        self.current_role = role.value
        self.current_mode = mode.value
        self._update_status_label()

        if self.settings_message_label is not None:
            self.settings_message_label.configure(
                text=f"Applied: {self.current_role} / {self.current_mode}"
            )

    def _show_users_section(self) -> None:
        current_role = UserRole(self.current_role)

        if not has_permission(current_role, "manage_users"):
            self._show_default_section(
                title="Users",
                description="Access denied. Only Admin can manage user accounts.",
            )
            return

        content = self._create_content_frame()
        content.grid_rowconfigure(2, weight=0)
        content.grid_rowconfigure(3, weight=1)

        title = ctk.CTkLabel(
            content,
            text="Users",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        description = ctk.CTkLabel(
            content,
            text="Create and review manager accounts. Changes are saved to disk and persist between restarts.",
            font=ctk.CTkFont(size=16),
            justify="left",
        )
        description.grid(row=1, column=0, padx=30, pady=10, sticky="w")

        form = ctk.CTkFrame(content, corner_radius=12)
        form.grid(row=2, column=0, padx=30, pady=20, sticky="nw")
        form.grid_columnconfigure(1, weight=1)

        username_label = ctk.CTkLabel(form, text="Username:")
        username_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        self.new_username_entry = ctk.CTkEntry(form, width=240)
        self.new_username_entry.grid(row=0, column=1, padx=20, pady=15, sticky="w")

        role_label = ctk.CTkLabel(form, text="Role:")
        role_label.grid(row=1, column=0, padx=20, pady=15, sticky="w")

        self.new_user_role_option = ctk.CTkOptionMenu(
            form,
            values=[role.value for role in UserRole],
        )
        self.new_user_role_option.set(UserRole.TESTER.value)
        self.new_user_role_option.grid(row=1, column=1, padx=20, pady=15, sticky="w")

        create_button = ctk.CTkButton(
            form,
            text="Create User",
            height=40,
            command=self._create_user_from_gui,
        )
        create_button.grid(
            row=2,
            column=0,
            columnspan=2,
            padx=20,
            pady=20,
            sticky="w",
        )

        self.users_message_label = ctk.CTkLabel(
            form,
            text="Only Admin can create users.",
            font=ctk.CTkFont(size=13),
        )
        self.users_message_label.grid(
            row=3,
            column=0,
            columnspan=2,
            padx=20,
            pady=(0, 20),
            sticky="w",
        )

        manage_label = ctk.CTkLabel(
            form,
            text="Manage existing user:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        manage_label.grid(row=4, column=0, columnspan=2, padx=20, pady=(10, 5), sticky="w")

        manage_username_label = ctk.CTkLabel(form, text="Target username:")
        manage_username_label.grid(row=5, column=0, padx=20, pady=15, sticky="w")

        self.manage_username_entry = ctk.CTkEntry(form, width=240)
        self.manage_username_entry.grid(row=5, column=1, padx=20, pady=15, sticky="w")

        manage_role_label = ctk.CTkLabel(form, text="New role:")
        manage_role_label.grid(row=6, column=0, padx=20, pady=15, sticky="w")

        self.manage_role_option = ctk.CTkOptionMenu(
            form,
            values=[role.value for role in UserRole],
        )
        self.manage_role_option.set(UserRole.TESTER.value)
        self.manage_role_option.grid(row=6, column=1, padx=20, pady=15, sticky="w")

        change_role_button = ctk.CTkButton(
            form,
            text="Change Role",
            height=40,
            command=self._change_role_from_gui,
        )
        change_role_button.grid(row=7, column=0, padx=20, pady=(10, 20), sticky="w")

        deactivate_button = ctk.CTkButton(
            form,
            text="Deactivate",
            height=40,
            fg_color="#8B3A3A",
            hover_color="#6E2E2E",
            command=self._deactivate_user_from_gui,
        )
        deactivate_button.grid(row=7, column=1, padx=20, pady=(10, 20), sticky="w")
        self.users_output = ctk.CTkTextbox(content, height=220)
        self.users_output.grid(
            row=3,
            column=0,
            padx=30,
            pady=(0, 30),
            sticky="nsew",
        )

        self._refresh_users_list()

    def _create_user_from_gui(self) -> None:
        if self.new_username_entry is None or self.new_user_role_option is None:
            return

        username = self.new_username_entry.get()
        role = UserRole(self.new_user_role_option.get())

        try:
            user = add_user(self.user_accounts, username, role)
        except ValueError as error:
            if self.users_message_label is not None:
                self.users_message_label.configure(text=str(error))
            return

        save_users(USERS_FILE, self.user_accounts)
        self.new_username_entry.delete(0, "end")

        if self.users_message_label is not None:
            self.users_message_label.configure(
                text=f"Created user: {user.username} / {user.role.value}"
            )

        self._refresh_users_list()

    def _change_role_from_gui(self) -> None:
        if self.manage_username_entry is None or self.manage_role_option is None:
            return

        username = self.manage_username_entry.get()
        new_role = UserRole(self.manage_role_option.get())

        user = find_user(self.user_accounts, username)
        if user is None:
            if self.users_message_label is not None:
                self.users_message_label.configure(text=f"User not found: {username}")
            return

        change_user_role(user, new_role)
        save_users(USERS_FILE, self.user_accounts)

        if self.users_message_label is not None:
            self.users_message_label.configure(
                text=f"Role changed: {user.username} -> {new_role.value}"
            )

        self._refresh_users_list()

    def _deactivate_user_from_gui(self) -> None:
        if self.manage_username_entry is None:
            return

        username = self.manage_username_entry.get()

        user = find_user(self.user_accounts, username)
        if user is None:
            if self.users_message_label is not None:
                self.users_message_label.configure(text=f"User not found: {username}")
            return

        deactivate_user(user)
        save_users(USERS_FILE, self.user_accounts)

        if self.users_message_label is not None:
            self.users_message_label.configure(text=f"User deactivated: {user.username}")

        self._refresh_users_list()
    def _refresh_users_list(self) -> None:
        if self.users_output is None:
            return

        lines = []
        for index, user in enumerate(self.user_accounts, start=1):
            status = "active" if user.is_active else "inactive"
            lines.append(f"{index}. {user.username} | {user.role.value} | {status}")

        output = "\n".join(lines)

        self.users_output.delete("1.0", "end")
        self.users_output.insert("1.0", output)

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
