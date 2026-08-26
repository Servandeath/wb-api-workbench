import customtkinter as ctk

from app.gui.layout import (
    CONTENT_PADX,
    ENTRY_WIDTH,
    FIELD_PADX,
    FIELD_PADY,
    LABEL_WIDTH,
    PANEL_CORNER_RADIUS,
    PANEL_GAP,
    build_group_header,
)
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
        # _create_content_frame даёт weight=1 строке 2 по умолчанию (это
        # для _show_default_section) — тут стрейчится другая строка (3,
        # список), поэтому сбрасываем дефолт, иначе message_label тоже
        # получит лишнее место и подвинет список вниз.
        content.grid_rowconfigure(2, weight=0)

        # Заголовок раздела уже есть в topbar — второй раз тем же текстом
        # его здесь не повторяем, только описание.
        description = ctk.CTkLabel(
            content,
            text="Create and review manager accounts. Changes are saved to disk and persist between restarts.",
            font=ctk.CTkFont(size=16),
            justify="left",
        )
        description.grid(row=0, column=0, padx=CONTENT_PADX, pady=(30, 10), sticky="w")

        # Раньше это была одна узкая колонка (Create + Manage друг под
        # другом) на всю ширину окна — тот же перекос, что чинили в
        # Keys/API Tester. Create user и Manage existing user — два
        # независимых действия, кладём их рядом по колонке на каждый.
        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.grid(row=1, column=0, padx=CONTENT_PADX, pady=(10, 10), sticky="new")
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_columnconfigure(1, weight=1)

        create_panel = ctk.CTkFrame(top_row, corner_radius=PANEL_CORNER_RADIUS)
        create_panel.grid(row=0, column=0, padx=(0, PANEL_GAP), sticky="new")
        create_panel.grid_columnconfigure(1, weight=1)

        build_group_header(create_panel, "New user")

        username_label = ctk.CTkLabel(create_panel, text="Username:", width=LABEL_WIDTH, anchor="w")
        username_label.grid(row=1, column=0, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        self.new_username_entry = ctk.CTkEntry(create_panel, width=ENTRY_WIDTH)
        self.new_username_entry.grid(row=1, column=1, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        role_label = ctk.CTkLabel(create_panel, text="Role:", width=LABEL_WIDTH, anchor="w")
        role_label.grid(row=2, column=0, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        self.new_user_role_option = ctk.CTkOptionMenu(
            create_panel,
            values=[role.value for role in UserRole],
            width=ENTRY_WIDTH,
        )
        self.new_user_role_option.set(UserRole.TESTER.value)
        self.new_user_role_option.grid(row=2, column=1, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        create_button = ctk.CTkButton(
            create_panel,
            text="Create User",
            height=40,
            command=self._create_user_from_gui,
        )
        create_button.grid(
            row=3,
            column=0,
            columnspan=2,
            padx=FIELD_PADX,
            pady=(10, 20),
            sticky="w",
        )

        manage_panel = ctk.CTkFrame(top_row, corner_radius=PANEL_CORNER_RADIUS)
        manage_panel.grid(row=0, column=1, padx=(PANEL_GAP, 0), sticky="new")
        manage_panel.grid_columnconfigure(1, weight=1)

        build_group_header(manage_panel, "Manage user")

        manage_username_label = ctk.CTkLabel(
            manage_panel, text="Target username:", width=LABEL_WIDTH, anchor="w"
        )
        manage_username_label.grid(row=1, column=0, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        self.manage_username_entry = ctk.CTkEntry(manage_panel, width=ENTRY_WIDTH)
        self.manage_username_entry.grid(row=1, column=1, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        manage_role_label = ctk.CTkLabel(manage_panel, text="New role:", width=LABEL_WIDTH, anchor="w")
        manage_role_label.grid(row=2, column=0, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        self.manage_role_option = ctk.CTkOptionMenu(
            manage_panel,
            values=[role.value for role in UserRole],
            width=ENTRY_WIDTH,
        )
        self.manage_role_option.set(UserRole.TESTER.value)
        self.manage_role_option.grid(row=2, column=1, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        change_role_button = ctk.CTkButton(
            manage_panel,
            text="Change Role",
            height=40,
            command=self._change_role_from_gui,
        )
        change_role_button.grid(row=3, column=0, padx=FIELD_PADX, pady=(10, 20), sticky="w")

        deactivate_button = ctk.CTkButton(
            manage_panel,
            text="Deactivate",
            height=40,
            fg_color="#8B3A3A",
            hover_color="#6E2E2E",
            command=self._deactivate_user_from_gui,
        )
        deactivate_button.grid(row=3, column=1, padx=FIELD_PADX, pady=(10, 20), sticky="w")

        activate_button = ctk.CTkButton(
            manage_panel,
            text="Activate",
            height=40,
            fg_color="#2E6E3E",
            hover_color="#245933",
            command=self._activate_user_from_gui,
        )
        activate_button.grid(row=4, column=0, padx=FIELD_PADX, pady=(0, 20), sticky="w")

        self.users_message_label = ctk.CTkLabel(
            content,
            text="Only Admin can create users.",
            font=ctk.CTkFont(size=13),
            justify="left",
        )
        self.users_message_label.grid(row=2, column=0, padx=CONTENT_PADX, pady=(0, 10), sticky="w")

        # Список растягивается на весь остаток высоты окна вместо
        # фиксированных 200px — раньше половина окна ниже списка просто
        # пустовала. content.grid_rowconfigure(weight=1) отдаёт этому ряду
        # всё свободное место; sticky="nsew" заставляет textbox его занять.
        # Панели формы выше не резиновые (sticky="new"), поэтому даже при
        # маленьком окне у списка не может остаться 0px — тот сценарий,
        # из-за которого раньше выбрали скролл всей секции целиком.
        content.grid_rowconfigure(3, weight=1)

        # CTkTextbox, а не CTkLabel: из лейбла нельзя выделить и
        # скопировать текст, а с кириллицей в полях ввода (см. отдельную
        # проблему раскладки на Windows) копипаст из списка — единственный
        # надёжный способ подставить имя в "Target username" без опечаток.
        self.users_output = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Courier", size=13),
        )
        self.users_output.grid(row=3, column=0, padx=CONTENT_PADX, pady=(0, 30), sticky="nsew")

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
