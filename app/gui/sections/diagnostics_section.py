import customtkinter as ctk

from app.gui.layout import CONTENT_PADX
from app.core.diagnostics import format_diagnostics, run_diagnostics


class DiagnosticsSectionMixin:
    def _show_diagnostics_section(self) -> None:
        content = self._create_content_frame()
        content.grid_rowconfigure(1, weight=1)

        # Заголовок раздела уже есть в topbar — второй раз тем же текстом
        # его здесь не повторяем.
        run_button = ctk.CTkButton(
            content,
            text="Run Diagnostics",
            height=40,
            command=self._run_diagnostics,
        )
        run_button.grid(row=0, column=0, padx=CONTENT_PADX, pady=(30, 10), sticky="w")

        self.diagnostics_output = ctk.CTkTextbox(content)
        self.diagnostics_output.grid(
            row=1,
            column=0,
            padx=CONTENT_PADX,
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
