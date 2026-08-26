import customtkinter as ctk

from app.config import USERS_FILE
from app.core.permissions import has_permission
from app.core.settings import UserRole
from app.core.user_store import save_users
from app.core.users import (
    activate_user,
    add_user,
    change_user_role,
    deactivate_user,
    find_user,
)


class UsersSectionMixin:
    def _show_users_section(self) -> None:
        current_role = UserRole(self.current_role)

        if not has_permission(current_role, "manage_users"):
            self._show_default_section(
                title="Users",
                description="Access denied. Only Admin can manage user accounts.",
            )
            return

        content = self._create_content_frame()

        # Быстрая добивка бэклога: form + список раньше клали прямо в content
        # без скролла, и в небольшом окне низ (форма высокая сама по себе)
        # выталкивал список за пределы окна без возможности прокрутки.
        # Пробовали закрепить форму и скроллить только список — не сработало:
        # если самой форме не хватает места, списку достаётся 0px и он вообще
        # пропадает. Поэтому скроллим всю секцию одним контейнером — тогда
        # ничего не может схлопнуться до нуля, в крайнем случае просто больше
        # скроллить. В большом окне снизу будет немного пустого места — это
        # ожидаемо для короткого списка, не баг.
        content.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(content, corner_radius=0, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            scroll,
            text="Users",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        description = ctk.CTkLabel(
            scroll,
            text="Create and review manager accounts. Changes are saved to disk and persist between restarts.",
            font=ctk.CTkFont(size=16),
            justify="left",
        )
        description.grid(row=1, column=0, padx=30, pady=10, sticky="w")

        # Раньше это была одна узкая колонка (Create + Manage друг под
        # другом) на всю ширину окна — тот же перекос, что чинили в
        # Keys/API Tester. Create user и Manage existing user — два
        # независимых действия, кладём их рядом по колонке на каждый.
        top_row = ctk.CTkFrame(scroll, fg_color="transparent")
        top_row.grid(row=2, column=0, padx=30, pady=20, sticky="new")
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_columnconfigure(1, weight=1)

        create_panel = ctk.CTkFrame(top_row, corner_radius=12)
        create_panel.grid(row=0, column=0, padx=(0, 10), sticky="new")
        create_panel.grid_columnconfigure(1, weight=1)

        username_label = ctk.CTkLabel(create_panel, text="Username:")
        username_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        self.new_username_entry = ctk.CTkEntry(create_panel, width=240)
        self.new_username_entry.grid(row=0, column=1, padx=20, pady=15, sticky="w")

        role_label = ctk.CTkLabel(create_panel, text="Role:")
        role_label.grid(row=1, column=0, padx=20, pady=15, sticky="w")

        self.new_user_role_option = ctk.CTkOptionMenu(
            create_panel,
            values=[role.value for role in UserRole],
        )
        self.new_user_role_option.set(UserRole.TESTER.value)
        self.new_user_role_option.grid(row=1, column=1, padx=20, pady=15, sticky="w")

        create_button = ctk.CTkButton(
            create_panel,
            text="Create User",
            height=40,
            command=self._create_user_from_gui,
        )
        create_button.grid(
            row=2,
            column=0,
            columnspan=2,
            padx=20,
            pady=(10, 20),
            sticky="w",
        )

        manage_panel = ctk.CTkFrame(top_row, corner_radius=12)
        manage_panel.grid(row=0, column=1, padx=(10, 0), sticky="new")
        manage_panel.grid_columnconfigure(1, weight=1)

        manage_label = ctk.CTkLabel(
            manage_panel,
            text="Manage existing user:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        manage_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 5), sticky="w")

        manage_username_label = ctk.CTkLabel(manage_panel, text="Target username:")
        manage_username_label.grid(row=1, column=0, padx=20, pady=15, sticky="w")

        self.manage_username_entry = ctk.CTkEntry(manage_panel, width=240)
        self.manage_username_entry.grid(row=1, column=1, padx=20, pady=15, sticky="w")

        manage_role_label = ctk.CTkLabel(manage_panel, text="New role:")
        manage_role_label.grid(row=2, column=0, padx=20, pady=15, sticky="w")

        self.manage_role_option = ctk.CTkOptionMenu(
            manage_panel,
            values=[role.value for role in UserRole],
        )
        self.manage_role_option.set(UserRole.TESTER.value)
        self.manage_role_option.grid(row=2, column=1, padx=20, pady=15, sticky="w")

        change_role_button = ctk.CTkButton(
            manage_panel,
            text="Change Role",
            height=40,
            command=self._change_role_from_gui,
        )
        change_role_button.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="w")

        deactivate_button = ctk.CTkButton(
            manage_panel,
            text="Deactivate",
            height=40,
            fg_color="#8B3A3A",
            hover_color="#6E2E2E",
            command=self._deactivate_user_from_gui,
        )
        deactivate_button.grid(row=3, column=1, padx=20, pady=(10, 20), sticky="w")

        activate_button = ctk.CTkButton(
            manage_panel,
            text="Activate",
            height=40,
            fg_color="#2E6E3E",
            hover_color="#245933",
            command=self._activate_user_from_gui,
        )
        activate_button.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="w")

        self.users_message_label = ctk.CTkLabel(
            scroll,
            text="Only Admin can create users.",
            font=ctk.CTkFont(size=13),
            justify="left",
        )
        self.users_message_label.grid(row=3, column=0, padx=30, pady=(0, 10), sticky="w")

        # CTkTextbox, а не CTkLabel: из лейбла нельзя выделить и
        # скопировать текст, а с кириллицей в полях ввода (см. отдельную
        # проблему раскладки на Windows) копипаст из списка — единственный
        # надёжный способ подставить имя в "Target username" без опечаток.
        # Фиксированная высота, без своего CTkScrollableFrame — это тот же
        # общий скролл секции, что и у формы выше, ничего не вложено.
        self.users_output = ctk.CTkTextbox(
            scroll,
            height=200,
            font=ctk.CTkFont(family="Courier", size=13),
        )
        self.users_output.grid(row=4, column=0, padx=30, pady=(0, 30), sticky="ew")

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

    def _activate_user_from_gui(self) -> None:
        if self.manage_username_entry is None:
            return

        username = self.manage_username_entry.get()

        user = find_user(self.user_accounts, username)
        if user is None:
            if self.users_message_label is not None:
                self.users_message_label.configure(text=f"User not found: {username}")
            return

        activate_user(user)
        save_users(USERS_FILE, self.user_accounts)

        if self.users_message_label is not None:
            self.users_message_label.configure(text=f"User activated: {user.username}")

        self._refresh_users_list()

    def _refresh_users_list(self) -> None:
        if self.users_output is None:
            return

        lines = []
        for index, user in enumerate(self.user_accounts, start=1):
            status = "active" if user.is_active else "inactive"
            lines.append(f"{index}. {user.username} | {user.role.value} | {status}")

        output = "\n".join(lines) if lines else "No users yet."

        self.users_output.delete("1.0", "end")
        self.users_output.insert("1.0", output)
