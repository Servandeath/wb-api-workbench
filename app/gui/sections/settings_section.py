import customtkinter as ctk

from app.gui.layout import (
    CONTENT_PADX,
    ENTRY_WIDTH,
    FIELD_PADX,
    FIELD_PADY,
    LABEL_WIDTH,
    PANEL_CORNER_RADIUS,
    build_group_header,
)
from app.config import SESSION_FILE
from app.core.session_state import save_session_state
from app.core.settings import AppMode, UserRole, apply_settings


class SettingsSectionMixin:
    def _show_settings_section(self) -> None:
        content = self._create_content_frame()

        # Заголовок раздела уже есть в topbar — второй раз тем же текстом
        # его здесь не повторяем.
        description = ctk.CTkLabel(
            content,
            text="Configure manager role and API mode.",
            font=ctk.CTkFont(size=16),
            justify="left",
        )
        description.grid(row=0, column=0, padx=CONTENT_PADX, pady=(30, 10), sticky="w")

        form = ctk.CTkFrame(content, corner_radius=PANEL_CORNER_RADIUS)
        form.grid(row=1, column=0, padx=CONTENT_PADX, pady=20, sticky="nw")
        form.grid_columnconfigure(1, weight=1)

        build_group_header(form, "Role & mode")

        role_label = ctk.CTkLabel(form, text="Role:", width=LABEL_WIDTH, anchor="w")
        role_label.grid(row=1, column=0, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        self.role_option = ctk.CTkOptionMenu(
            form,
            values=[role.value for role in UserRole],
            width=ENTRY_WIDTH,
        )
        self.role_option.set(self.current_role)
        self.role_option.grid(row=1, column=1, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        mode_label = ctk.CTkLabel(form, text="Mode:", width=LABEL_WIDTH, anchor="w")
        mode_label.grid(row=2, column=0, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        self.mode_option = ctk.CTkOptionMenu(
            form,
            values=[mode.value for mode in AppMode],
            width=ENTRY_WIDTH,
        )
        self.mode_option.set(self.current_mode)
        self.mode_option.grid(row=2, column=1, padx=FIELD_PADX, pady=FIELD_PADY, sticky="w")

        apply_button = ctk.CTkButton(
            form,
            text="Apply Settings",
            height=40,
            command=self._apply_settings_from_gui,
        )
        apply_button.grid(
            row=3,
            column=0,
            columnspan=2,
            padx=FIELD_PADX,
            pady=20,
            sticky="w",
        )

        self.settings_message_label = ctk.CTkLabel(
            form,
            text="Viewer and Tester can use Test mode only.",
            font=ctk.CTkFont(size=13),
        )
        self.settings_message_label.grid(
            row=4,
            column=0,
            columnspan=2,
            padx=FIELD_PADX,
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

        # Запоминаем выбор на диск — при следующем запуске не спрашиваем
        # роль/режим заново (см. load_session_state в MainWindow.__init__).
        save_session_state(SESSION_FILE, role, mode)

        if self.settings_message_label is not None:
            self.settings_message_label.configure(
                text=f"Applied: {self.current_role} / {self.current_mode}"
            )
