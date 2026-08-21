import customtkinter as ctk

from app.core.diagnostics import format_diagnostics, run_diagnostics


class DiagnosticsSectionMixin:
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
