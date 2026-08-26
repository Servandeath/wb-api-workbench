import asyncio
import json

import customtkinter as ctk
import httpx

from app.core.api_tester import parse_json_body, send_wb_request
from app.core.marketplace import Marketplace
from app.core.wb_token import get_scope_hosts
from app.core.permissions import has_permission
from app.core.settings import AppMode, UserRole
from app.db.database import SessionLocal
from app.db.key_repository import list_api_keys
from app.db.request_log_repository import add_request_log


class ApiTesterSectionMixin:
    def _show_api_tester_section(self) -> None:
        current_role = UserRole(self.current_role)
        current_mode = AppMode(self.current_mode)

        content = self._create_content_frame()
        content.grid_rowconfigure(0, weight=1)

        # Форма может быть длиннее окна (метод/путь/тело/ключ/кнопки) —
        # тот же паттерн, что и в Users: скроллим всю секцию одним
        # контейнером, ничего не закреплено отдельно.
        scroll = ctk.CTkScrollableFrame(content, corner_radius=0, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            scroll,
            text="API Tester",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")

        description = ctk.CTkLabel(
            scroll,
            text=f"Test Wildberries API methods here. Current mode: {current_mode.value}.",
            font=ctk.CTkFont(size=16),
            justify="left",
        )
        description.grid(row=1, column=0, padx=30, pady=10, sticky="w")

        # Раньше это была одна узкая колонка на всю ширину окна — слева
        # поля, справа пусто. Делим на два блока: слева — что за запрос
        # (Section/Method/Path/JSON body), справа — откуда ключ и кнопки
        # отправки. Так используется вся ширина, а не половина.
        top_row = ctk.CTkFrame(scroll, fg_color="transparent")
        top_row.grid(row=2, column=0, padx=30, pady=20, sticky="new")
        top_row.grid_columnconfigure(0, weight=1)
        top_row.grid_columnconfigure(1, weight=1)

        request_panel = ctk.CTkFrame(top_row, corner_radius=12)
        request_panel.grid(row=0, column=0, padx=(0, 10), sticky="new")
        request_panel.grid_columnconfigure(1, weight=1)

        row = 0

        # У WB нет единого домена для всех методов — каждый раздел API
        # живёт на своём хосте (те же имена и хосты, что в Keys при
        # декодировании токена, см. wb_token.WB_SCOPES). Раздел определяет
        # base_url запроса, поле Path — только сам путь метода внутри него.
        self._api_tester_scope_hosts = dict(get_scope_hosts())

        section_label = ctk.CTkLabel(request_panel, text="Section:")
        section_label.grid(row=row, column=0, padx=20, pady=15, sticky="w")

        self.api_tester_section_option = ctk.CTkOptionMenu(
            request_panel, values=list(self._api_tester_scope_hosts.keys())
        )
        self.api_tester_section_option.grid(row=row, column=1, padx=20, pady=15, sticky="w")
        row += 1

        method_label = ctk.CTkLabel(request_panel, text="Method:")
        method_label.grid(row=row, column=0, padx=20, pady=15, sticky="w")

        self.api_tester_method_option = ctk.CTkOptionMenu(request_panel, values=["GET", "POST"])
        self.api_tester_method_option.grid(row=row, column=1, padx=20, pady=15, sticky="w")
        row += 1

        path_label = ctk.CTkLabel(request_panel, text="Path:")
        path_label.grid(row=row, column=0, padx=20, pady=15, sticky="w")

        self.api_tester_path_entry = ctk.CTkEntry(
            request_panel, width=280, placeholder_text="/api/v1/supplier/orders"
        )
        self.api_tester_path_entry.grid(row=row, column=1, padx=20, pady=15, sticky="w")
        row += 1

        body_label = ctk.CTkLabel(request_panel, text="JSON body\n(POST only):")
        body_label.grid(row=row, column=0, padx=20, pady=(15, 20), sticky="nw")

        self.api_tester_body_textbox = ctk.CTkTextbox(request_panel, width=280, height=100)
        self.api_tester_body_textbox.grid(row=row, column=1, padx=20, pady=(15, 20), sticky="w")
        row += 1

        send_panel = ctk.CTkFrame(top_row, corner_radius=12)
        send_panel.grid(row=0, column=1, padx=(10, 0), sticky="new")
        send_panel.grid_columnconfigure(1, weight=1)

        row = 0

        # Источник ключа зависит от режима: Test -> временный ключ
        # (session_key_storage, только в памяти), Real -> один из уже
        # сохранённых WB-ключей из Keys. Право на отправку — тоже
        # разное (run_test_request / run_real_request), см. docs/permissions.md.
        required_permission = (
            "run_test_request" if current_mode == AppMode.TEST else "run_real_request"
        )
        can_send = has_permission(current_role, required_permission)

        self.api_tester_temp_key_entry = None
        self.api_tester_key_option = None
        self.api_tester_save_checkbox = None

        if not can_send:
            note = ctk.CTkLabel(
                send_panel,
                text=(
                    f"Role {current_role.value} cannot send requests in "
                    f"{current_mode.value} mode."
                ),
                font=ctk.CTkFont(size=13),
                justify="left",
                wraplength=280,
            )
            note.grid(row=row, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")
            row += 1
        elif current_mode == AppMode.TEST:
            key_label = ctk.CTkLabel(send_panel, text="Temporary WB key:")
            key_label.grid(row=row, column=0, padx=20, pady=(20, 15), sticky="w")

            self.api_tester_temp_key_entry = ctk.CTkEntry(send_panel, width=240, show="*")
            self.api_tester_temp_key_entry.grid(row=row, column=1, padx=20, pady=(20, 15), sticky="w")
            row += 1
        else:
            wb_key_names = self._list_wb_key_names()

            key_label = ctk.CTkLabel(send_panel, text="Saved WB key:")
            key_label.grid(row=row, column=0, padx=20, pady=(20, 15), sticky="w")

            self.api_tester_key_option = ctk.CTkOptionMenu(
                send_panel, values=wb_key_names or ["No WB keys saved"]
            )
            self.api_tester_key_option.grid(row=row, column=1, padx=20, pady=(20, 15), sticky="w")
            row += 1

        if can_send:
            send_button = ctk.CTkButton(
                send_panel,
                text="Send",
                height=40,
                command=self._send_api_request_from_gui,
            )
            send_button.grid(row=row, column=0, padx=20, pady=(10, 20), sticky="w")

            save_permission = (
                "save_test_response" if current_mode == AppMode.TEST else "save_response"
            )
            if has_permission(current_role, save_permission):
                self.api_tester_save_checkbox = ctk.CTkCheckBox(send_panel, text="Save response")
                self.api_tester_save_checkbox.grid(
                    row=row, column=1, padx=20, pady=(10, 20), sticky="w"
                )
            row += 1

        self.api_tester_message_label = ctk.CTkLabel(
            scroll, text="", font=ctk.CTkFont(size=13), justify="left"
        )
        self.api_tester_message_label.grid(
            row=3, column=0, padx=30, pady=(0, 10), sticky="w"
        )

        response_title = ctk.CTkLabel(
            scroll, text="Response", font=ctk.CTkFont(size=18, weight="bold")
        )
        response_title.grid(row=4, column=0, padx=30, pady=(10, 5), sticky="w")

        self.api_tester_output = ctk.CTkTextbox(scroll, height=280)
        self.api_tester_output.grid(row=5, column=0, padx=30, pady=(0, 30), sticky="ew")

    def _list_wb_key_names(self) -> list[str]:
        session = SessionLocal()
        try:
            keys = list_api_keys(session)
        finally:
            session.close()

        return [key.name for key in keys if key.marketplace == Marketplace.WB.value]

    def _resolve_wb_token(self, current_mode: AppMode) -> str:
        if current_mode == AppMode.TEST:
            if self.api_tester_temp_key_entry is None:
                raise ValueError("Temporary key field is not available.")

            token = self.api_tester_temp_key_entry.get().strip()
            if not token:
                raise ValueError("Enter a temporary WB key.")

            # Не персистентно — только в памяти сессии, как и задумано
            # для Test mode (см. session_key_storage.py).
            self.session_key_storage.save_token("api_tester_temp", token)
            return token

        if self.api_tester_key_option is None:
            raise ValueError("No saved WB key selected.")

        name = self.api_tester_key_option.get()
        token = self.key_storage.get_token(name)
        if token is None:
            raise ValueError(f"Secret not found in storage for: {name}")

        return token

    def _send_api_request_from_gui(self) -> None:
        current_mode = AppMode(self.current_mode)

        try:
            method = self.api_tester_method_option.get()
            section = self.api_tester_section_option.get()
            base_url = self._api_tester_scope_hosts[section]
            path = self.api_tester_path_entry.get()
            json_body = parse_json_body(self.api_tester_body_textbox.get("1.0", "end"))
            token = self._resolve_wb_token(current_mode)
        except ValueError as error:
            self._set_api_tester_message(str(error))
            return

        try:
            result = asyncio.run(self._run_request(token, method, base_url, path, json_body))
        except httpx.RequestError as error:
            self._set_api_tester_message(f"Network error: {error}")
            return
        except ValueError as error:
            self._set_api_tester_message(str(error))
            return

        self._render_api_response(result)

        if self.api_tester_save_checkbox is not None and self.api_tester_save_checkbox.get() == 1:
            self._save_api_response(method, path, json_body, result, current_mode)

    async def _run_request(
        self, token: str, method: str, base_url: str, path: str, json_body: dict | None
    ) -> dict:
        async with httpx.AsyncClient() as client:
            return await send_wb_request(
                client, token, method, path, json_body, base_url=base_url
            )

    def _render_api_response(self, result: dict) -> None:
        if self.api_tester_output is None:
            return

        body = result["body"]
        if isinstance(body, (dict, list)):
            body_text = json.dumps(body, ensure_ascii=False, indent=2)
        else:
            body_text = str(body)

        output = f"Status: {result['status_code']}\n\n{body_text}"

        self.api_tester_output.delete("1.0", "end")
        self.api_tester_output.insert("1.0", output)
        self._set_api_tester_message(f"Request sent: {result['status_code']}")

    def _save_api_response(
        self,
        method: str,
        path: str,
        json_body: dict | None,
        result: dict,
        current_mode: AppMode,
    ) -> None:
        body = result["body"]
        response_text = (
            json.dumps(body, ensure_ascii=False)
            if isinstance(body, (dict, list))
            else str(body)
        )

        session = SessionLocal()
        try:
            add_request_log(
                session,
                method_name=method,
                endpoint=path,
                mode=current_mode.value.lower(),
                request_json=json.dumps(json_body, ensure_ascii=False) if json_body else None,
                response_json=response_text,
                status_code=result["status_code"],
            )
        finally:
            session.close()

    def _set_api_tester_message(self, text: str) -> None:
        if self.api_tester_message_label is not None:
            self.api_tester_message_label.configure(text=text)
