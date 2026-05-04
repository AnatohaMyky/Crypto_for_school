import customtkinter as ctk
from tkinter import filedialog

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class SignatureKeyGeneratorApp(ctk.CTk):
    """Генератор приватного та публічного ключів для цифрового підпису."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Генератор ключів цифрового підпису")
        self.geometry("920x520")
        self.minsize(820, 460)

        self.private_key_pem: bytes | None = None
        self.public_key_pem: bytes | None = None

        self._compact_layout = False
        self._size_mode = "medium"

        self._build_ui()
        self.bind("<Configure>", self._on_window_resize)

    def _build_ui(self) -> None:
        self.title_font = ctk.CTkFont(size=18, weight="bold")
        self.body_font = ctk.CTkFont(size=14)
        self.status_font = ctk.CTkFont(size=15, weight="bold")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        main_frame = ctk.CTkFrame(self, corner_radius=12)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 8))
        main_frame.grid_columnconfigure((0, 1, 2), weight=1)

        title_label = ctk.CTkLabel(
            main_frame,
            text="Генерація ключів (RSA) для цифрового підпису",
            font=self.title_font,
            anchor="w",
        )
        title_label.grid(row=0, column=0, columnspan=3, sticky="ew", padx=14, pady=(12, 10))

        self.generate_button = ctk.CTkButton(
            main_frame,
            text="Створити пару ключів",
            command=self.generate_key_pair,
            font=self.body_font,
            height=40,
        )
        self.generate_button.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.save_private_button = ctk.CTkButton(
            main_frame,
            text="Зберегти приватний ключ",
            command=self.save_private_key,
            font=self.body_font,
            height=40,
        )
        self.save_private_button.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 10))

        self.save_public_button = ctk.CTkButton(
            main_frame,
            text="Зберегти публічний ключ",
            command=self.save_public_key,
            font=self.body_font,
            height=40,
        )
        self.save_public_button.grid(row=1, column=2, sticky="ew", padx=14, pady=(0, 10))

        self.private_label = ctk.CTkLabel(
            main_frame,
            text="Приватний ключ: ще не створено",
            font=self.body_font,
            anchor="w",
            wraplength=780,
        )
        self.private_label.grid(row=2, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 8))

        self.public_label = ctk.CTkLabel(
            main_frame,
            text="Публічний ключ: ще не створено",
            font=self.body_font,
            anchor="w",
            wraplength=780,
        )
        self.public_label.grid(row=3, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 12))

        self.status_label = ctk.CTkLabel(
            self,
            text="Статус: Очікування дії...",
            font=self.status_font,
            text_color="#d1d5db",
            anchor="w",
        )
        self.status_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))

        self.update_idletasks()
        self._apply_responsive_layout(self.winfo_width())

    def _set_status(self, message: str, color: str) -> None:
        self.status_label.configure(text=message, text_color=color)

    def _on_window_resize(self, _event: object) -> None:
        self._apply_responsive_layout(self.winfo_width())

    def _apply_responsive_layout(self, width: int) -> None:
        self._apply_dynamic_sizing(width)
        compact = width < 900
        if compact == self._compact_layout:
            self._update_wrap_lengths(width)
            return

        self._compact_layout = compact
        if compact:
            self.generate_button.grid_configure(row=1, column=0, columnspan=3)
            self.save_private_button.grid_configure(row=2, column=0, columnspan=3)
            self.save_public_button.grid_configure(row=3, column=0, columnspan=3)
            self.private_label.grid_configure(row=4, column=0, columnspan=3)
            self.public_label.grid_configure(row=5, column=0, columnspan=3)
        else:
            self.generate_button.grid_configure(row=1, column=0, columnspan=1)
            self.save_private_button.grid_configure(row=1, column=1, columnspan=1)
            self.save_public_button.grid_configure(row=1, column=2, columnspan=1)
            self.private_label.grid_configure(row=2, column=0, columnspan=3)
            self.public_label.grid_configure(row=3, column=0, columnspan=3)

        self._update_wrap_lengths(width)

    def _update_wrap_lengths(self, width: int) -> None:
        wrap = max(280, width - 140)
        self.private_label.configure(wraplength=wrap)
        self.public_label.configure(wraplength=wrap)

    def _apply_dynamic_sizing(self, width: int) -> None:
        if width < 860:
            new_mode = "small"
            title_size, body_size, status_size = 15, 12, 13
            button_h = 34
        elif width > 1300:
            new_mode = "large"
            title_size, body_size, status_size = 21, 16, 17
            button_h = 46
        else:
            new_mode = "medium"
            title_size, body_size, status_size = 18, 14, 15
            button_h = 40

        if new_mode == self._size_mode:
            return

        self._size_mode = new_mode
        self.title_font.configure(size=title_size)
        self.body_font.configure(size=body_size)
        self.status_font.configure(size=status_size)

        for button in (self.generate_button, self.save_private_button, self.save_public_button):
            button.configure(height=button_h)

    def generate_key_pair(self) -> None:
        """Створюємо ключі RSA для підпису/перевірки."""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()

        self.private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        self.public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        self.private_label.configure(text="Приватний ключ: створено (RSA 2048, PEM)")
        self.public_label.configure(text="Публічний ключ: створено (RSA 2048, PEM)")
        self._set_status("✅ Пару ключів успішно згенеровано", "#22c55e")

    def save_private_key(self) -> None:
        if not self.private_key_pem:
            self._set_status("⚠️ Спочатку створіть пару ключів!", "#f59e0b")
            return

        file_path = filedialog.asksaveasfilename(
            title="Зберегти приватний ключ",
            defaultextension=".pem",
            initialfile="private_key.pem",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            with open(file_path, "wb") as private_file:
                private_file.write(self.private_key_pem)
            self.private_label.configure(text=f"Приватний ключ: {file_path}")
            self._set_status("✅ Приватний ключ збережено", "#22c55e")
        except OSError:
            self._set_status("❌ Помилка: Не вдалося зберегти приватний ключ", "#ef4444")

    def save_public_key(self) -> None:
        if not self.public_key_pem:
            self._set_status("⚠️ Спочатку створіть пару ключів!", "#f59e0b")
            return

        file_path = filedialog.asksaveasfilename(
            title="Зберегти публічний ключ",
            defaultextension=".pem",
            initialfile="public_key.pem",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            with open(file_path, "wb") as public_file:
                public_file.write(self.public_key_pem)
            self.public_label.configure(text=f"Публічний ключ: {file_path}")
            self._set_status("✅ Публічний ключ збережено", "#22c55e")
        except OSError:
            self._set_status("❌ Помилка: Не вдалося зберегти публічний ключ", "#ef4444")


def main() -> None:
    app = SignatureKeyGeneratorApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.destroy()


if __name__ == "__main__":
    main()
