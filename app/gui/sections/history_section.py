import customtkinter as ctk

from app.gui.layout import CONTENT_PADX
from app.core.permissions import has_permission
from app.core.settings import UserRole
from app.db.database import SessionLocal
from app.db.request_log_repository import list_request_logs


class HistorySectionMixin:
    def _show_history_section(self) -> None:
        current_role = UserRole(self.current_role)

        # История — это уже сохранённые в БД запросы/ответы (через
        # "Save response" в API Tester). Право просмотра то же, что и на
        # сами JSON-ответы, отдельного права заводить незачем.
        if not has_permission(current_role, "view_json_responses"):
            self._show_default_section(
                title="History",
                description="Access denied.",
            )
            return

        content = self._create_content_frame()
        content.grid_rowconfigure(1, weight=1)

        # Заголовок раздела уже есть в topbar — второй раз тем же текстом
        # его здесь не повторяем.
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=CONTENT_PADX, pady=(30, 10))
        header.grid_columnconfigure(0, weight=1)

        description = ctk.CTkLabel(
            header,
            text="Saved API requests, most recent first.",
            font=ctk.CTkFont(size=16),
            justify="left",
        )
        description.grid(row=0, column=0, sticky="w")

        refresh_button = ctk.CTkButton(
            header,
            text="Refresh",
            height=32,
            width=100,
            command=self._refresh_history_list,
        )
        refresh_button.grid(row=0, column=1, sticky="e", padx=(10, 0))

        self.history_output = ctk.CTkTextbox(content)
        self.history_output.grid(row=1, column=0, padx=CONTENT_PADX, pady=(0, 30), sticky="nsew")

        self._refresh_history_list()

    def _refresh_history_list(self) -> None:
        if self.history_output is None:
            return

        session = SessionLocal()
        try:
            logs = list_request_logs(session)
        finally:
            session.close()

        if not logs:
            output = "No saved requests yet."
        else:
            lines = [
                f"[{log.created_at:%Y-%m-%d %H:%M:%S}] {log.mode} | "
                f"{log.method_name} {log.endpoint} -> {log.status_code}"
                for log in logs
            ]
            output = "\n".join(lines)

        self.history_output.delete("1.0", "end")
        self.history_output.insert("1.0", output)
