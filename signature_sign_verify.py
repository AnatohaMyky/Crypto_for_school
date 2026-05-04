import customtkinter as ctk
from tkinter import filedialog

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


class SignatureSignVerifyApp(ctk.CTk):
    """Програма для підписування файлів і перевірки цифрового підпису."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Підписування та перевірка підпису")
        self.geometry("1040x700")
        self.minsize(900, 620)

        self.sign_file_path: str = ""
        self.private_key_path: str = ""
        self.verify_file_path: str = ""
        self.public_key_path: str = ""
        self.signature_path: str = ""

        self.private_key_data: bytes | None = None
        self.public_key_data: bytes | None = None

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

        self.main_frame = ctk.CTkFrame(self, corner_radius=12)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 8))
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure((0, 1), weight=1)

        self.sign_frame = self._create_section_frame("1) Підписування файлу", 0)
        self.verify_frame = self._create_section_frame("2) Перевірка підпису", 1)

        self._build_sign_section()
        self._build_verify_section()

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

    def _create_section_frame(self, title: str, row: int) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        frame.grid(row=row, column=0, sticky="nsew", padx=12, pady=8)
        frame.grid_columnconfigure((0, 1, 2), weight=1)

        title_label = ctk.CTkLabel(frame, text=title, anchor="w", font=self.title_font)
        title_label.grid(row=0, column=0, columnspan=3, sticky="ew", padx=14, pady=(12, 10))
        return frame

    def _build_sign_section(self) -> None:
        self.select_sign_file_button = ctk.CTkButton(
            self.sign_frame,
            text="Обрати файл для підпису",
            command=self.select_sign_file,
            font=self.body_font,
            height=38,
        )
        self.select_sign_file_button.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.select_private_key_button = ctk.CTkButton(
            self.sign_frame,
            text="Обрати приватний ключ",
            command=self.select_private_key,
            font=self.body_font,
            height=38,
        )
        self.select_private_key_button.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 10))

        self.sign_button = ctk.CTkButton(
            self.sign_frame,
            text="Підписати файл",
            command=self.sign_file,
            font=self.body_font,
            height=38,
        )
        self.sign_button.grid(row=1, column=2, sticky="ew", padx=14, pady=(0, 10))

        self.sign_file_label = ctk.CTkLabel(
            self.sign_frame,
            text="Файл для підпису: не обрано",
            anchor="w",
            font=self.body_font,
            wraplength=900,
        )
        self.sign_file_label.grid(row=2, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 8))

        self.private_key_label = ctk.CTkLabel(
            self.sign_frame,
            text="Приватний ключ: не обрано",
            anchor="w",
            font=self.body_font,
            wraplength=900,
        )
        self.private_key_label.grid(row=3, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 12))

    def _build_verify_section(self) -> None:
        self.select_verify_file_button = ctk.CTkButton(
            self.verify_frame,
            text="Обрати файл для перевірки",
            command=self.select_verify_file,
            font=self.body_font,
            height=38,
        )
        self.select_verify_file_button.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.select_public_key_button = ctk.CTkButton(
            self.verify_frame,
            text="Обрати публічний ключ",
            command=self.select_public_key,
            font=self.body_font,
            height=38,
        )
        self.select_public_key_button.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 10))

        self.select_signature_button = ctk.CTkButton(
            self.verify_frame,
            text="Обрати файл підпису (.sig)",
            command=self.select_signature_file,
            font=self.body_font,
            height=38,
        )
        self.select_signature_button.grid(row=1, column=2, sticky="ew", padx=14, pady=(0, 10))

        self.verify_button = ctk.CTkButton(
            self.verify_frame,
            text="Перевірити підпис",
            command=self.verify_signature,
            font=self.body_font,
            height=38,
        )
        self.verify_button.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.verify_file_label = ctk.CTkLabel(
            self.verify_frame,
            text="Файл для перевірки: не обрано",
            anchor="w",
            font=self.body_font,
            wraplength=900,
        )
        self.verify_file_label.grid(row=3, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 8))

        self.public_key_label = ctk.CTkLabel(
            self.verify_frame,
            text="Публічний ключ: не обрано",
            anchor="w",
            font=self.body_font,
            wraplength=900,
        )
        self.public_key_label.grid(row=4, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 8))

        self.signature_label = ctk.CTkLabel(
            self.verify_frame,
            text="Файл підпису: не обрано",
            anchor="w",
            font=self.body_font,
            wraplength=900,
        )
        self.signature_label.grid(row=5, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 12))

    def _set_status(self, message: str, color: str) -> None:
        self.status_label.configure(text=message, text_color=color)

    def _on_window_resize(self, _event: object) -> None:
        self._apply_responsive_layout(self.winfo_width())

    def _apply_responsive_layout(self, width: int) -> None:
        self._apply_dynamic_sizing(width)
        compact = width < 980
        if compact == self._compact_layout:
            self._update_wrap_lengths(width)
            return

        self._compact_layout = compact
        if compact:
            self.select_sign_file_button.grid_configure(row=1, column=0, columnspan=3)
            self.select_private_key_button.grid_configure(row=2, column=0, columnspan=3)
            self.sign_button.grid_configure(row=3, column=0, columnspan=3)
            self.sign_file_label.grid_configure(row=4, column=0, columnspan=3)
            self.private_key_label.grid_configure(row=5, column=0, columnspan=3)

            self.select_verify_file_button.grid_configure(row=1, column=0, columnspan=3)
            self.select_public_key_button.grid_configure(row=2, column=0, columnspan=3)
            self.select_signature_button.grid_configure(row=3, column=0, columnspan=3)
            self.verify_button.grid_configure(row=4, column=0, columnspan=3)
            self.verify_file_label.grid_configure(row=5, column=0, columnspan=3)
            self.public_key_label.grid_configure(row=6, column=0, columnspan=3)
            self.signature_label.grid_configure(row=7, column=0, columnspan=3)
        else:
            self.select_sign_file_button.grid_configure(row=1, column=0, columnspan=1)
            self.select_private_key_button.grid_configure(row=1, column=1, columnspan=1)
            self.sign_button.grid_configure(row=1, column=2, columnspan=1)
            self.sign_file_label.grid_configure(row=2, column=0, columnspan=3)
            self.private_key_label.grid_configure(row=3, column=0, columnspan=3)

            self.select_verify_file_button.grid_configure(row=1, column=0, columnspan=1)
            self.select_public_key_button.grid_configure(row=1, column=1, columnspan=1)
            self.select_signature_button.grid_configure(row=1, column=2, columnspan=1)
            self.verify_button.grid_configure(row=2, column=0, columnspan=1)
            self.verify_file_label.grid_configure(row=3, column=0, columnspan=3)
            self.public_key_label.grid_configure(row=4, column=0, columnspan=3)
            self.signature_label.grid_configure(row=5, column=0, columnspan=3)

        self._update_wrap_lengths(width)

    def _update_wrap_lengths(self, width: int) -> None:
        wrap = max(280, width - 140)
        self.sign_file_label.configure(wraplength=wrap)
        self.private_key_label.configure(wraplength=wrap)
        self.verify_file_label.configure(wraplength=wrap)
        self.public_key_label.configure(wraplength=wrap)
        self.signature_label.configure(wraplength=wrap)

    def _apply_dynamic_sizing(self, width: int) -> None:
        if width < 900:
            new_mode = "small"
            title_size, body_size, status_size = 15, 12, 13
            button_h = 34
        elif width > 1400:
            new_mode = "large"
            title_size, body_size, status_size = 21, 16, 17
            button_h = 46
        else:
            new_mode = "medium"
            title_size, body_size, status_size = 18, 14, 15
            button_h = 38

        if new_mode == self._size_mode:
            return

        self._size_mode = new_mode
        self.title_font.configure(size=title_size)
        self.body_font.configure(size=body_size)
        self.status_font.configure(size=status_size)

        for button in (
            self.select_sign_file_button,
            self.select_private_key_button,
            self.sign_button,
            self.select_verify_file_button,
            self.select_public_key_button,
            self.select_signature_button,
            self.verify_button,
        ):
            button.configure(height=button_h)

    def _read_file_bytes(self, path: str) -> bytes | None:
        try:
            with open(path, "rb") as file:
                return file.read()
        except OSError:
            return None

    
    def select_sign_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Оберіть файл для підпису",
            filetypes=[("All files", "*.*")],
        )
        if not path:
            return

        self.sign_file_path = path
        self.sign_file_label.configure(text=f"Файл для підпису: {path}")
        self._set_status("Файл для підпису обрано", "#60a5fa")

    def select_private_key(self) -> None:
        path = filedialog.askopenfilename(
            title="Оберіть приватний ключ",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )
        if not path:
            return

        key_bytes = self._read_file_bytes(path)
        if key_bytes is None:
            self._set_status("❌ Помилка: Не вдалося прочитати приватний ключ", "#ef4444")
            return

        try:
            serialization.load_pem_private_key(key_bytes, password=None)
            self.private_key_data = key_bytes
            self.private_key_path = path
            self.private_key_label.configure(text=f"Приватний ключ: {path}")
            self._set_status("✅ Приватний ключ завантажено", "#22c55e")
        except ValueError:
            self._set_status("❌ Помилка: Невірний формат приватного ключа", "#ef4444")

    def sign_file(self) -> None:
        if not self.sign_file_path:
            self._set_status("⚠️ Спочатку оберіть файл для підпису!", "#f59e0b")
            return
        if not self.private_key_data:
            self._set_status("⚠️ Спочатку оберіть приватний ключ!", "#f59e0b")
            return

        file_data = self._read_file_bytes(self.sign_file_path)
        if file_data is None:
            self._set_status("❌ Помилка: Не вдалося прочитати файл для підпису", "#ef4444")
            return

        try:
            private_key = serialization.load_pem_private_key(self.private_key_data, password=None)
            signature = private_key.sign(
                file_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
        except ValueError:
            self._set_status("❌ Помилка: Невірний приватний ключ", "#ef4444")
            return

        signature_path = f"{self.sign_file_path}.sig"
        try:
            with open(signature_path, "wb") as signature_file:
                signature_file.write(signature)
            self._set_status("✅ Підпис створено та збережено (.sig)", "#22c55e")
        except OSError:
            self._set_status("❌ Помилка: Не вдалося зберегти файл підпису", "#ef4444")

    def select_verify_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Оберіть файл для перевірки",
            filetypes=[("All files", "*.*")],
        )
        if not path:
            return

        self.verify_file_path = path
        self.verify_file_label.configure(text=f"Файл для перевірки: {path}")
        self._set_status("Файл для перевірки обрано", "#60a5fa")

    def select_public_key(self) -> None:
        path = filedialog.askopenfilename(
            title="Оберіть публічний ключ",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )
        if not path:
            return

        key_bytes = self._read_file_bytes(path)
        if key_bytes is None:
            self._set_status("❌ Помилка: Не вдалося прочитати публічний ключ", "#ef4444")
            return

        try:
            serialization.load_pem_public_key(key_bytes)
            self.public_key_data = key_bytes
            self.public_key_path = path
            self.public_key_label.configure(text=f"Публічний ключ: {path}")
            self._set_status("✅ Публічний ключ завантажено", "#22c55e")
        except ValueError:
            self._set_status("❌ Помилка: Невірний формат публічного ключа", "#ef4444")

    def select_signature_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Оберіть файл підпису",
            filetypes=[("Signature files", "*.sig"), ("All files", "*.*")],
        )
        if not path:
            return

        self.signature_path = path
        self.signature_label.configure(text=f"Файл підпису: {path}")
        self._set_status("Файл підпису обрано", "#60a5fa")

    def verify_signature(self) -> None:
        if not self.verify_file_path:
            self._set_status("⚠️ Спочатку оберіть файл для перевірки!", "#f59e0b")
            return
        if not self.public_key_data:
            self._set_status("⚠️ Спочатку оберіть публічний ключ!", "#f59e0b")
            return
        if not self.signature_path:
            self._set_status("⚠️ Спочатку оберіть файл підпису (.sig)!", "#f59e0b")
            return

        file_data = self._read_file_bytes(self.verify_file_path)
        signature_data = self._read_file_bytes(self.signature_path)
        if file_data is None or signature_data is None:
            self._set_status("❌ Помилка: Не вдалося прочитати файл або підпис", "#ef4444")
            return

        try:
            public_key = serialization.load_pem_public_key(self.public_key_data)
            public_key.verify(
                signature_data,
                file_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            self._set_status("✅ Підпис дійсний", "#22c55e")
        except InvalidSignature:
            self._set_status("❌ Підпис недійсний: файл або ключ не відповідає", "#ef4444")
        except ValueError:
            self._set_status("❌ Помилка: Невірний публічний ключ", "#ef4444")


def main() -> None:
    app = SignatureSignVerifyApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.destroy()


if __name__ == "__main__":
    main()
