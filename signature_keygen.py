import customtkinter as ctk
from tkinter import filedialog
import threading
import os
import sys
from typing import Callable
from PIL import Image
import datetime

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class SignatureKeyGeneratorApp(ctk.CTk):
    """Генератор приватного та публічного ключів для цифрового підпису."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title("Генератор ключів цифрового підпису")
        self.geometry("920x520")
        self.minsize(820, 460)

        self.private_key_pem: bytes | None = None
        self.public_key_pem: bytes | None = None

        self._compact_layout = False
        self._size_mode = "medium"
        self._key_size: int = 2048
        self._generation_thread: threading.Thread | None = None

        self._build_ui()
        self.bind("<Configure>", self._on_window_resize)

    def _get_resource_path(self, relative_path: str) -> str:
        """Отримує абсолютний шлях до ресурсу для PyInstaller та звичайного запуску."""
        try:
            # PyInstaller розпаковує дані у тимчасову папку _MEIPASS
            base_path = sys._MEIPASS
        except AttributeError:
            # Звичайний запуск з вихідного коду
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(base_path, relative_path)

    def _build_ui(self) -> None:
        self.title_font = ctk.CTkFont(size=18, weight="bold")
        self.body_font = ctk.CTkFont(size=14)
        self.status_font = ctk.CTkFont(size=15, weight="bold")
        
        # Завантажуємо іконки
        self._load_icons()

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

        # Рядок з вибором розміру ключа
        self.key_size_label = ctk.CTkLabel(
            main_frame,
            text="Розмір ключа:",
            font=self.body_font,
            anchor="w",
        )
        self.key_size_label.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.key_size_menu = ctk.CTkOptionMenu(
            main_frame,
            values=["2048", "3072", "4096"],
            command=self._on_key_size_change,
            font=self.body_font,
        )
        self.key_size_menu.set("2048")
        self.key_size_menu.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 10))

        # Поле для пароля
        # self.password_label = ctk.CTkLabel(
        #     main_frame,
        #     text="Пароль шифрування:",
        #     font=self.body_font,
        #     anchor="w",
        # )
        # self.password_label.grid(row=1, column=2, sticky="ew", padx=14, pady=(0, 10))

        # self.password_entry = ctk.CTkEntry(
        #     main_frame,
        #     placeholder_text="Залиште порожнім для без шифрування",
        #     show="*",
        #     font=self.body_font,
        # )
        # self.password_entry.grid(row=2, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 10))

        self.generate_button = ctk.CTkButton(
            main_frame,
            text="Створити пару ключів",
            command=self.generate_key_pair,
            font=self.body_font,
            height=40,
        )
        self.generate_button.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.save_private_button = ctk.CTkButton(
            main_frame,
            text="Зберегти приватний ключ",
            command=self.save_private_key,
            font=self.body_font,
            height=40,
        )
        self.save_private_button.grid(row=3, column=1, sticky="ew", padx=14, pady=(0, 10))

        self.save_public_button = ctk.CTkButton(
            main_frame,
            text="Зберегти публічний ключ",
            command=self.save_public_key,
            font=self.body_font,
            height=40,
        )
        self.save_public_button.grid(row=3, column=2, sticky="ew", padx=14, pady=(0, 10))

        self.private_label = ctk.CTkLabel(
            main_frame,
            text="Приватний ключ: ще не створено",
            font=self.body_font,
            anchor="w",
            wraplength=780,
        )
        self.private_label.grid(row=4, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 8))

        self.public_label = ctk.CTkLabel(
            main_frame,
            text="Публічний ключ: ще не створено",
            font=self.body_font,
            anchor="w",
            wraplength=780,
        )
        self.public_label.grid(row=5, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 12))

        self.status_label = ctk.CTkLabel(
            self,
            text="Статус: Очікування дії...",
            font=self.status_font,
            text_color=("gray10", "#DCE4EE"),
            anchor="w",
        )
        self.status_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))

        # Theme switch
        self.theme_switch = ctk.CTkSwitch(
            self,
            text="Змінити тему",
            command=self._toggle_theme,
            font=self.body_font
        )
        self.theme_switch.place(relx=0.85, rely=0.98, anchor="se")

        self.update_idletasks()
        self._apply_responsive_layout(self.winfo_width())

        # Створюємо іконку інформації
        self.info_label = ctk.CTkLabel(
            self,
            image=self.icon_info if self.icon_info else None,
            text="",
            cursor="hand2"
        )
        self.info_label.place(relx=0.98, rely=0.98, anchor="se")
        
        # Прив'язуємо hover events до іконки інформації
        self.info_label.bind("<Enter>", self._show_popup)
        self.info_label.bind("<Leave>", self._hide_popup)

        # Створюємо прихований popup фрейм з інформацією про розробника
        self.popup_frame = ctk.CTkFrame(
            self,
            fg_color=("#f3f4f6", "#374151"),
            border_width=1,
            border_color=("#d1d5db", "#4b5563"),
            corner_radius=8
        )
        
        info_text = "Розробник: Анатолій Микитюк\nСтудент 4-го курсу ЧНУ ім. Ю. Федьковича\nВчитель інформатики, Хотинський опорний академічний ліцей"
        
        info_popup_label = ctk.CTkLabel(
            self.popup_frame,
            text=info_text,
            justify="left",
            padx=15,
            pady=10
        )
        info_popup_label.pack()

        # Перевірка системної теми та ініціалізація інтерфейсу
        if ctk.get_appearance_mode() == "Light":
            self.theme_switch.select()
            if self.icon_info_light:
                self.info_label.configure(image=self.icon_info_light)
        else:
            if self.icon_info:
                self.info_label.configure(image=self.icon_info)

    def _load_icons(self) -> None:
        """Завантажує іконки для інтерфейсу."""
        try:
            # Визначаємо шлях до папки з іконками
            icons_dir = self._get_resource_path(os.path.join("assets", "icons"))
            
            # Шлях до іконок інформації
            info_icon_path = os.path.join(icons_dir, "info.png")
            light_info_icon_path = os.path.join(icons_dir, "light-info.png")
            
            # Завантажуємо іконки, якщо файли існують 
            if os.path.exists(info_icon_path):
                self.icon_info = ctk.CTkImage(
                    Image.open(info_icon_path),
                    size=(24, 24)
                )
            else:
                self.icon_info = None
                print(f"Попередження: іконку info не знайдено за шляхом: {info_icon_path}")
                
            if os.path.exists(light_info_icon_path):
                self.icon_info_light = ctk.CTkImage(
                    Image.open(light_info_icon_path),
                    size=(24, 24)
                )
            else:
                self.icon_info_light = None
                print(f"Попередження: іконку light-info не знайдено за шляхом: {light_info_icon_path}")
                
        except Exception as e:
            # Якщо виникла помилка при завантаженні іконки
            self.icon_info = None
            self.icon_info_light = None
            print(f"Помилка завантаження іконки: {e}")

    def _set_status(self, message: str, color: str) -> None:
        self.status_label.configure(text=message, text_color=color)

    def _show_popup(self, event) -> None:
        """Показує спливаюче вікно з інформацією про розробника."""
        self.popup_frame.place(relx=0.95, rely=0.92, anchor="se")

    def _hide_popup(self, event) -> None:
        """Ховає спливаюче вікно з інформацією про розробника."""
        self.popup_frame.place_forget()

    def _toggle_theme(self) -> None:
        """Перемикає між світлою та темною темою."""
        if self.theme_switch.get():
            ctk.set_appearance_mode("light")
            # Змінюємо іконку на світлу тему
            if self.icon_info_light:
                self.info_label.configure(image=self.icon_info_light)
        else:
            ctk.set_appearance_mode("dark")
            # Змінюємо іконку на темну тему
            if self.icon_info:
                self.info_label.configure(image=self.icon_info)

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
            self.key_size_label.grid_configure(row=1, column=0, columnspan=3)
            self.key_size_menu.grid_configure(row=2, column=0, columnspan=3)
            # self.password_label.grid_configure(row=3, column=0, columnspan=3)
            # self.password_entry.grid_configure(row=4, column=0, columnspan=3)
            self.generate_button.grid_configure(row=5, column=0, columnspan=3)
            self.save_private_button.grid_configure(row=6, column=0, columnspan=3)
            self.save_public_button.grid_configure(row=7, column=0, columnspan=3)
            self.private_label.grid_configure(row=8, column=0, columnspan=3)
            self.public_label.grid_configure(row=9, column=0, columnspan=3)
        else:
            self.key_size_label.grid_configure(row=1, column=0, columnspan=1)
            self.key_size_menu.grid_configure(row=1, column=1, columnspan=1)
            # self.password_label.grid_configure(row=1, column=2, columnspan=1)
            # self.password_entry.grid_configure(row=2, column=0, columnspan=3)
            self.generate_button.grid_configure(row=3, column=0, columnspan=1)
            self.save_private_button.grid_configure(row=3, column=1, columnspan=1)
            self.save_public_button.grid_configure(row=3, column=2, columnspan=1)
            self.private_label.grid_configure(row=4, column=0, columnspan=3)
            self.public_label.grid_configure(row=5, column=0, columnspan=3)

        self._update_wrap_lengths(width)

    def _on_key_size_change(self, choice: str) -> None:
        self._key_size = int(choice)

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
        
        # Оновлюємо висоту entry та option menu
        # self.password_entry.configure(height=button_h if button_h > 34 else 32)
        self.key_size_menu.configure(height=button_h if button_h > 34 else 32)

    def generate_key_pair(self) -> None:
        """Створюємо ключі RSA для підпису/перевірки."""
        if self._generation_thread and self._generation_thread.is_alive():
            return
        
        # Блокуємо кнопку та показуємо статус
        self.generate_button.configure(state="disabled")
        self._set_status("⏳ Генерація ключів, зачекайте...", "#f59e0b")
        
        # Запускаємо генерацію в окремому потоці
        self._generation_thread = threading.Thread(
            target=self._generate_keys_thread,
            daemon=True
        )
        self._generation_thread.start()

    def _generate_keys_thread(self) -> None:
        """Генерація ключів та сертифіката в окремому потоці."""
        try:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=self._key_size)
            public_key = private_key.public_key()

            encryption_algorithm = serialization.NoEncryption()
            encryption_info = f"RSA {self._key_size}, PEM (Термін: 1 рік)"
            
            # Зберігаємо приватний ключ як і раніше
            self.private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=encryption_algorithm,
            )

            # --- НОВА ЛОГІКА: Створення сертифіката X.509 замість голого ключа ---
            
            # Задаємо ім'я власника сертифіката (можна розширити в майбутньому)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, u"School Digital Signature User"),
            ])

            # Задаємо термін дії (від зараз і на 365 днів вперед)
            valid_from = datetime.datetime.now(datetime.timezone.utc)
            valid_to = valid_from + datetime.timedelta(days=365)

            # Будуємо сертифікат
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                public_key
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                valid_from
            ).not_valid_after(
                valid_to
            ).sign(private_key, hashes.SHA256()) # Підписуємо сертифікат нашим приватним ключем

            # Зберігаємо сертифікат у форматі PEM (це і буде наш "публічний ключ")
            self.public_key_pem = cert.public_bytes(serialization.Encoding.PEM)

            # Оновлюємо UI в головному потоці
            self.after(0, lambda: self._on_keys_generated(encryption_info))
            
        except Exception as e:
            self.after(0, lambda: self._on_generation_error(str(e)))

    def _on_keys_generated(self, encryption_info: str) -> None:
        """Обробка успішної генерації ключів."""
        self.private_label.configure(text=f"Приватний ключ: створено ({encryption_info})")
        self.public_label.configure(text=f"Публічний ключ: створено ({encryption_info})")
        self._set_status("✅ Пару ключів успішно згенеровано", "#22c55e")
        self.generate_button.configure(state="normal")

    def _on_generation_error(self, error_msg: str) -> None:
        """Обробка помилки генерації ключів."""
        self._set_status(f"❌ Помилка генерації ключів: {error_msg}", "#ef4444")
        self.generate_button.configure(state="normal")

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
            title="Зберегти сертифікат (публічний ключ)",
            defaultextension=".crt",
            initialfile="certificate.crt",
            filetypes=[("Certificate files", "*.crt"), ("PEM files", "*.pem"), ("All files", "*.*")],
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
