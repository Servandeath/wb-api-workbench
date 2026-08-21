import customtkinter as ctk

from app.core.settings import AppMode, UserRole, apply_settings


class SettingsSectionMixin:
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
