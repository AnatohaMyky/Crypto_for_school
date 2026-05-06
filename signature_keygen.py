from __future__ import annotations

import customtkinter as ctk
from tkinter import filedialog
import threading
import os
import sys
from typing import Callable
from PIL import Image
import datetime
import time

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519


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
        self._selected_algorithm: str = "RSA"
        self._generation_thread: threading.Thread | None = None
        
        # Metrics storage
        self._generation_time_ms: float = 0.0
        self._private_key_size_bytes: int = 0
        self._public_key_size_bytes: int = 0

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
        self.metric_font = ctk.CTkFont(size=16, weight="bold")
        
        # Завантажуємо іконки
        self._load_icons()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Створюємо контейнер для фреймів
        self.container_frame = ctk.CTkFrame(self, corner_radius=12)
        self.container_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 8))
        self.container_frame.grid_columnconfigure(0, weight=1)

        # Створюємо обидва фрейми
        self._create_setup_frame()
        self._create_result_frame()

        # Показуємо setup_frame за замовчуванням
        self.setup_frame.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)

        # Статус та елементи керування
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

    def _create_setup_frame(self) -> None:
        """Створює фрейм налаштувань."""
        self.setup_frame = ctk.CTkFrame(self.container_frame, corner_radius=8)
        self.setup_frame.grid_columnconfigure((0, 1), weight=1)

        title_label = ctk.CTkLabel(
            self.setup_frame,
            text="Налаштування генерації ключів",
            font=self.title_font,
            anchor="w",
        )
        title_label.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 20))

        # Вибір алгоритму
        self.algorithm_label = ctk.CTkLabel(
            self.setup_frame,
            text="Алгоритм:",
            font=self.body_font,
            anchor="w",
        )
        self.algorithm_label.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.algorithm_menu = ctk.CTkOptionMenu(
            self.setup_frame,
            values=["RSA", "ECDSA (SECP256R1)", "Ed25519"],
            command=self._on_algorithm_change,
            font=self.body_font,
        )
        self.algorithm_menu.set("RSA")
        self.algorithm_menu.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 10))

        # Вибір розміру ключа (активний тільки для RSA)
        self.key_size_label = ctk.CTkLabel(
            self.setup_frame,
            text="Розмір ключа:",
            font=self.body_font,
            anchor="w",
        )
        self.key_size_label.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.key_size_menu = ctk.CTkOptionMenu(
            self.setup_frame,
            values=["2048", "3072", "4096"],
            command=self._on_key_size_change,
            font=self.body_font,
        )
        self.key_size_menu.set("2048")
        self.key_size_menu.grid(row=2, column=1, sticky="ew", padx=14, pady=(0, 10))

        # Кнопка генерації
        self.generate_button = ctk.CTkButton(
            self.setup_frame,
            text="Створити пару ключів",
            command=self.generate_key_pair,
            font=self.body_font,
            height=40,
        )
        self.generate_button.grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(20, 0))

    def _create_result_frame(self) -> None:
        """Створює фрейм результатів."""
        self.result_frame = ctk.CTkFrame(self.container_frame, corner_radius=8)
        self.result_frame.grid_columnconfigure((0, 1), weight=1)

        title_label = ctk.CTkLabel(
            self.result_frame,
            text="Результати генерації",
            font=self.title_font,
            anchor="w",
        )
        title_label.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 20))

        # Метрики
        self.time_label = ctk.CTkLabel(
            self.result_frame,
            text="Час генерації: -- мс",
            font=self.metric_font,
            anchor="w",
            text_color=("#22c55e", "#86efac"),
        )
        self.time_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 10))

        self.private_size_label = ctk.CTkLabel(
            self.result_frame,
            text="Розмір приватного ключа: -- байт",
            font=self.metric_font,
            anchor="w",
            text_color=("#3b82f6", "#60a5fa"),
        )
        self.private_size_label.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 10))

        self.public_size_label = ctk.CTkLabel(
            self.result_frame,
            text="Розмір публічного сертифіката: -- байт",
            font=self.metric_font,
            anchor="w",
            text_color=("#f59e0b", "#fbbf24"),
        )
        self.public_size_label.grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 20))

        # Кнопки
        self.save_private_button = ctk.CTkButton(
            self.result_frame,
            text="Зберегти приватний ключ",
            command=self.save_private_key,
            font=self.body_font,
            height=40,
        )
        self.save_private_button.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.save_public_button = ctk.CTkButton(
            self.result_frame,
            text="Зберегти публічний ключ",
            command=self.save_public_key,
            font=self.body_font,
            height=40,
        )
        self.save_public_button.grid(row=4, column=1, sticky="ew", padx=14, pady=(0, 10))

        self.back_button = ctk.CTkButton(
            self.result_frame,
            text="Повернутися назад",
            command=self.show_setup_frame,
            font=self.body_font,
            height=40,
        )
        self.back_button.grid(row=5, column=0, columnspan=2, sticky="ew", padx=14, pady=(10, 0))

    def show_setup_frame(self) -> None:
        """Показує фрейм налаштувань."""
        self.result_frame.grid_forget()
        self.setup_frame.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        self._set_status("Статус: Очікування дії...", ("gray10", "#DCE4EE"))

    def show_result_frame(self) -> None:
        """Показує фрейм результатів."""
        self.setup_frame.grid_forget()
        self.result_frame.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)

    def _on_algorithm_change(self, choice: str) -> None:
        """Обробляє зміну алгоритму."""
        self._selected_algorithm = choice
        
        # Активуємо/деактивуємо вибір розміру ключа
        if choice == "RSA":
            self.key_size_menu.configure(state="normal")
        else:
            self.key_size_menu.configure(state="disabled")

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
            return

        self._compact_layout = compact
        if compact:
            # Setup frame compact layout
            self.algorithm_label.grid_configure(row=1, column=0, columnspan=2)
            self.algorithm_menu.grid_configure(row=2, column=0, columnspan=2)
            self.key_size_label.grid_configure(row=3, column=0, columnspan=2)
            self.key_size_menu.grid_configure(row=4, column=0, columnspan=2)
            self.generate_button.grid_configure(row=5, column=0, columnspan=2)
            
            # Result frame compact layout
            self.time_label.grid_configure(row=1, column=0, columnspan=2)
            self.private_size_label.grid_configure(row=2, column=0, columnspan=2)
            self.public_size_label.grid_configure(row=3, column=0, columnspan=2)
            self.save_private_button.grid_configure(row=4, column=0, columnspan=2)
            self.save_public_button.grid_configure(row=5, column=0, columnspan=2)
            self.back_button.grid_configure(row=6, column=0, columnspan=2)
        else:
            # Setup frame normal layout
            self.algorithm_label.grid_configure(row=1, column=0, columnspan=1)
            self.algorithm_menu.grid_configure(row=1, column=1, columnspan=1)
            self.key_size_label.grid_configure(row=2, column=0, columnspan=1)
            self.key_size_menu.grid_configure(row=2, column=1, columnspan=1)
            self.generate_button.grid_configure(row=3, column=0, columnspan=2)
            
            # Result frame normal layout
            self.time_label.grid_configure(row=1, column=0, columnspan=2)
            self.private_size_label.grid_configure(row=2, column=0, columnspan=2)
            self.public_size_label.grid_configure(row=3, column=0, columnspan=2)
            self.save_private_button.grid_configure(row=4, column=0, columnspan=1)
            self.save_public_button.grid_configure(row=4, column=1, columnspan=1)
            self.back_button.grid_configure(row=5, column=0, columnspan=2)

    def _on_key_size_change(self, choice: str) -> None:
        self._key_size = int(choice)

    def _update_wrap_lengths(self, width: int) -> None:
        wrap = max(280, width - 140)
        # Update wrap lengths for metric labels in result frame
        self.time_label.configure(wraplength=wrap)
        self.private_size_label.configure(wraplength=wrap)
        self.public_size_label.configure(wraplength=wrap)

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

        # Update all buttons in both frames
        for button in (self.generate_button, self.save_private_button, self.save_public_button, self.back_button):
            button.configure(height=button_h)
        
        # Update option menus
        self.algorithm_menu.configure(height=button_h if button_h > 34 else 32)
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
        """Генерація ключів та сертифіката в окремому потоці з підтримкою кількох алгоритмів."""
        start_time = time.perf_counter()
        
        try:
            private_key = None
            public_key = None
            encryption_info = ""
            
            if self._selected_algorithm == "RSA":
                private_key = rsa.generate_private_key(public_exponent=65537, key_size=self._key_size)
                public_key = private_key.public_key()
                encryption_info = f"RSA {self._key_size}, PEM (Термін: 1 рік)"
                
            elif self._selected_algorithm == "ECDSA (SECP256R1)":
                private_key = ec.generate_private_key(ec.SECP256R1())
                public_key = private_key.public_key()
                encryption_info = "ECDSA SECP256R1, PEM (Термін: 1 рік)"
                
            elif self._selected_algorithm == "Ed25519":
                private_key = ed25519.Ed25519PrivateKey.generate()
                public_key = private_key.public_key()
                encryption_info = "Ed25519, PEM (Термін: 1 рік)"
            
            encryption_algorithm = serialization.NoEncryption()
            
            # Зберігаємо приватний ключ
            self.private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=encryption_algorithm,
            )

            # Створення сертифіката X.509
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, u"School Digital Signature User"),
            ])

            valid_from = datetime.datetime.now(datetime.timezone.utc)
            valid_to = valid_from + datetime.timedelta(days=365)

            # Будуємо сертифікат з правильним алгоритмом підпису
            cert_builder = x509.CertificateBuilder().subject_name(
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
            )
            
            # Критичний нюанс: для Ed25519 використовуємо None, для інших - SHA256
            if self._selected_algorithm == "Ed25519":
                cert = cert_builder.sign(private_key, None)
            else:
                cert = cert_builder.sign(private_key, hashes.SHA256())

            # Зберігаємо сертифікат у форматі PEM
            self.public_key_pem = cert.public_bytes(serialization.Encoding.PEM)

            # Обчислюємо метрики
            end_time = time.perf_counter()
            self._generation_time_ms = (end_time - start_time) * 1000
            self._private_key_size_bytes = len(self.private_key_pem)
            self._public_key_size_bytes = len(self.public_key_pem)

            # Оновлюємо UI в головному потоці
            self.after(0, lambda: self._on_keys_generated(encryption_info))
            
        except Exception as e:
            self.after(0, lambda: self._on_generation_error(str(e)))

    def _on_keys_generated(self, encryption_info: str) -> None:
        """Обробка успішної генерації ключів з метриками."""
        # Оновлюємо мітки з метриками
        self.time_label.configure(text=f"Час генерації: {self._generation_time_ms:.2f} мс")
        self.private_size_label.configure(text=f"Розмір приватного ключа: {self._private_key_size_bytes} байт")
        self.public_size_label.configure(text=f"Розмір публічного сертифіката: {self._public_key_size_bytes} байт")
        
        # Перемикаємося на фрейм результатів
        self.show_result_frame()
        
        self._set_status(f"✅ {self._selected_algorithm} ключі успішно згенеровано", "#22c55e")
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
