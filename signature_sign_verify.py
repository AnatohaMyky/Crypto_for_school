import customtkinter as ctk
from tkinter import filedialog
import threading
import os
import sys
from typing import Callable
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, utils

class CTkWithDND(ctk.CTk, TkinterDnD.DnDWrapper):
    """Гібридний клас для поєднання CustomTkinter та Drag-and-Drop."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

class SignatureSignVerifyApp(CTkWithDND):
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
        self._operation_thread: threading.Thread | None = None
        
        # Константи для chunking
        self.CHUNK_SIZE = 65536  # 64 KB

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

        # Створюємо tabview замість main_frame
        self.tabview = ctk.CTkTabview(self, corner_radius=12)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 8))
        
        # Додаємо вкладки
        self.sign_tab = self.tabview.add("Підписування файлу")
        self.verify_tab = self.tabview.add("Перевірка підпису")
        
        # Налаштовуємо grid для обох вкладок
        self.sign_tab.grid_columnconfigure((0, 1, 2), weight=1)
        self.verify_tab.grid_columnconfigure((0, 1, 2), weight=1)

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
            fg_color="#374151",
            border_width=1,
            border_color="#4b5563",
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

    def _load_icons(self) -> None:
        """Завантажує іконки для drag-and-drop зон."""
        try:
            # Визначаємо шлях до папки з іконками
            icons_dir = self._get_resource_path(os.path.join("assets", "icons"))
            
            # Шлях до іконки стрілки
            icon_path = os.path.join(icons_dir, "arrow-down-from-line.png")
            
            # Завантажуємо іконки, якщо файл існує
            if os.path.exists(icon_path):
                # Велика іконка для порожньої зони
                self.icon_upload_large = ctk.CTkImage(
                    Image.open(icon_path),
                    size=(40, 40)
                )
                # Малі іконки для заповненої зони
                self.icon_file_small = ctk.CTkImage(
                    Image.open(icon_path),
                    size=(20, 20)
                )
                self.icon_key_small = ctk.CTkImage(
                    Image.open(icon_path),
                    size=(20, 20)
                )
                # Іконка інформації
                info_icon_path = os.path.join(icons_dir, "info.png")
                if os.path.exists(info_icon_path):
                    self.icon_info = ctk.CTkImage(
                        Image.open(info_icon_path),
                        size=(24, 24)
                    )
                else:
                    self.icon_info = None
                    print(f"Попередження: іконку info не знайдено за шляхом: {info_icon_path}")
            else:
                # Якщо іконка не знайдена, використовуємо None
                self.icon_upload_large = None
                self.icon_file_small = None
                self.icon_key_small = None
                self.icon_info = None
                print(f"Попередження: іконку не знайдено за шляхом: {icon_path}")
        except Exception as e:
            # Якщо виникла помилка при завантаженні іконки
            self.icon_upload_large = None
            self.icon_file_small = None
            self.icon_key_small = None
            self.icon_info = None
            print(f"Помилка завантаження іконки: {e}")

    
    def _build_sign_section(self) -> None:
        # Заголовок секції
        title_label = ctk.CTkLabel(
            self.sign_tab,
            text="1) Підписування файлу",
            anchor="w",
            font=self.title_font,
        )
        title_label.grid(row=0, column=0, columnspan=3, sticky="ew", padx=14, pady=(12, 20))

        self.select_sign_file_button = ctk.CTkButton(
            self.sign_tab,
            text="Обрати файл для підпису",
            command=self.select_sign_file,
            font=self.body_font,
            height=38,
        )
        self.select_sign_file_button.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 20))

        self.select_private_key_button = ctk.CTkButton(
            self.sign_tab,
            text="Обрати приватний ключ",
            command=self.select_private_key,
            font=self.body_font,
            height=38,
        )
        self.select_private_key_button.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 20))

        self.sign_button = ctk.CTkButton(
            self.sign_tab,
            text="Підписати файл",
            command=self.sign_file,
            font=self.body_font,
            height=38,
        )
        self.sign_button.grid(row=1, column=2, sticky="ew", padx=14, pady=(0, 20))

        # Drop Zone для файлу для підпису
        self.sign_file_drop_frame = ctk.CTkFrame(
            self.sign_tab,
            border_width=2,
            border_color="#374151",
            fg_color="#1f2937",
            corner_radius=8,
        )
        self.sign_file_drop_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 20))
        self.sign_file_drop_frame.drop_target_register(DND_FILES)
        self.sign_file_drop_frame.dnd_bind('<<Drop>>', self._on_drop_sign_file)
        self.sign_file_drop_frame.dnd_bind('<<DragEnter>>', lambda e: self._on_drag_enter(e, self.sign_file_drop_frame))
        self.sign_file_drop_frame.dnd_bind('<<DragLeave>>', lambda e: self._on_drag_leave(e, self.sign_file_drop_frame))

        self.sign_file_label = ctk.CTkLabel(
            self.sign_file_drop_frame,
            text="Перетягніть файл сюди\nабо скористайтеся кнопкою вище",
            anchor="center",
            font=self.body_font,
            wraplength=900,
            image=self.icon_upload_large if self.icon_upload_large else None,
            compound="top" if self.icon_upload_large else None,
            justify="center",
            text_color="#9ca3af",
        )
        self.sign_file_label.pack(padx=20, pady=16, fill="x")
        self.sign_file_label.drop_target_register(DND_FILES)
        self.sign_file_label.dnd_bind('<<Drop>>', self._on_drop_sign_file)

        # Drop Zone для приватного ключа
        self.private_key_drop_frame = ctk.CTkFrame(
            self.sign_tab,
            border_width=2,
            border_color="#374151",
            fg_color="#1f2937",
            corner_radius=8,
        )
        self.private_key_drop_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 20))
        self.private_key_drop_frame.drop_target_register(DND_FILES)
        self.private_key_drop_frame.dnd_bind('<<Drop>>', self._on_drop_private_key)
        self.private_key_drop_frame.dnd_bind('<<DragEnter>>', lambda e: self._on_drag_enter(e, self.private_key_drop_frame))
        self.private_key_drop_frame.dnd_bind('<<DragLeave>>', lambda e: self._on_drag_leave(e, self.private_key_drop_frame))

        self.private_key_label = ctk.CTkLabel(
            self.private_key_drop_frame,
            text="Перетягніть приватний ключ сюди\nабо скористайтеся кнопкою вище",
            anchor="center",
            font=self.body_font,
            wraplength=900,
            image=self.icon_upload_large if self.icon_upload_large else None,
            compound="top" if self.icon_upload_large else None,
            justify="center",
            text_color="#9ca3af",
        )
        self.private_key_label.pack(padx=20, pady=16, fill="x")
        self.private_key_label.drop_target_register(DND_FILES)
        self.private_key_label.dnd_bind('<<Drop>>', self._on_drop_private_key)

    def _build_verify_section(self) -> None:
        # Заголовок секції
        title_label = ctk.CTkLabel(
            self.verify_tab,
            text="2) Перевірка підпису",
            anchor="w",
            font=self.title_font,
        )
        title_label.grid(row=0, column=0, columnspan=3, sticky="ew", padx=14, pady=(12, 20))

        self.select_verify_file_button = ctk.CTkButton(
            self.verify_tab,
            text="Обрати файл для перевірки",
            command=self.select_verify_file,
            font=self.body_font,
            height=38,
        )
        self.select_verify_file_button.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 20))

        self.select_public_key_button = ctk.CTkButton(
            self.verify_tab,
            text="Обрати публічний ключ",
            command=self.select_public_key,
            font=self.body_font,
            height=38,
        )
        self.select_public_key_button.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 20))

        self.select_signature_button = ctk.CTkButton(
            self.verify_tab,
            text="Обрати файл підпису (.sig)",
            command=self.select_signature_file,
            font=self.body_font,
            height=38,
        )
        self.select_signature_button.grid(row=1, column=2, sticky="ew", padx=14, pady=(0, 20))

        self.verify_button = ctk.CTkButton(
            self.verify_tab,
            text="Перевірити підпис",
            command=self.verify_signature,
            font=self.body_font,
            height=38,
        )
        self.verify_button.grid(row=2, column=1, sticky="ew", padx=14, pady=(0, 20))

        # Drop Zone для файлу для перевірки
        self.verify_file_drop_frame = ctk.CTkFrame(
            self.verify_tab,
            border_width=2,
            border_color="#374151",
            fg_color="#1f2937",
            corner_radius=8,
        )
        self.verify_file_drop_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 20))
        self.verify_file_drop_frame.drop_target_register(DND_FILES)
        self.verify_file_drop_frame.dnd_bind('<<Drop>>', self._on_drop_verify_file)
        self.verify_file_drop_frame.dnd_bind('<<DragEnter>>', lambda e: self._on_drag_enter(e, self.verify_file_drop_frame))
        self.verify_file_drop_frame.dnd_bind('<<DragLeave>>', lambda e: self._on_drag_leave(e, self.verify_file_drop_frame))

        self.verify_file_label = ctk.CTkLabel(
            self.verify_file_drop_frame,
            text="Перетягніть файл сюди\nабо скористайтеся кнопкою вище",
            anchor="center",
            font=self.body_font,
            wraplength=900,
            image=self.icon_upload_large if self.icon_upload_large else None,
            compound="top" if self.icon_upload_large else None,
            justify="center",
            text_color="#9ca3af",
        )
        self.verify_file_label.pack(padx=20, pady=16, fill="x")
        self.verify_file_label.drop_target_register(DND_FILES)
        self.verify_file_label.dnd_bind('<<Drop>>', self._on_drop_verify_file)

        # Drop Zone для публічного ключа
        self.public_key_drop_frame = ctk.CTkFrame(
            self.verify_tab,
            border_width=2,
            border_color="#374151",
            fg_color="#1f2937",
            corner_radius=8,
        )
        self.public_key_drop_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 20))
        self.public_key_drop_frame.drop_target_register(DND_FILES)
        self.public_key_drop_frame.dnd_bind('<<Drop>>', self._on_drop_public_key)
        self.public_key_drop_frame.dnd_bind('<<DragEnter>>', lambda e: self._on_drag_enter(e, self.public_key_drop_frame))
        self.public_key_drop_frame.dnd_bind('<<DragLeave>>', lambda e: self._on_drag_leave(e, self.public_key_drop_frame))

        self.public_key_label = ctk.CTkLabel(
            self.public_key_drop_frame,
            text="Перетягніть публічний ключ сюди\nабо скористайтеся кнопкою вище",
            anchor="center",
            font=self.body_font,
            wraplength=900,
            image=self.icon_upload_large if self.icon_upload_large else None,
            compound="top" if self.icon_upload_large else None,
            justify="center",
            text_color="#9ca3af",
        )
        self.public_key_label.pack(padx=20, pady=16, fill="x")
        self.public_key_label.drop_target_register(DND_FILES)
        self.public_key_label.dnd_bind('<<Drop>>', self._on_drop_public_key)

        # Drop Zone для файлу підпису
        self.signature_drop_frame = ctk.CTkFrame(
            self.verify_tab,
            border_width=2,
            border_color="#374151",
            fg_color="#1f2937",
            corner_radius=8,
        )
        self.signature_drop_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 20))
        self.signature_drop_frame.drop_target_register(DND_FILES)
        self.signature_drop_frame.dnd_bind('<<Drop>>', self._on_drop_signature_file)
        self.signature_drop_frame.dnd_bind('<<DragEnter>>', lambda e: self._on_drag_enter(e, self.signature_drop_frame))
        self.signature_drop_frame.dnd_bind('<<DragLeave>>', lambda e: self._on_drag_leave(e, self.signature_drop_frame))

        self.signature_label = ctk.CTkLabel(
            self.signature_drop_frame,
            text="Перетягніть файл підпису сюди\nабо скористайтеся кнопкою вище",
            anchor="center",
            font=self.body_font,
            wraplength=900,
            image=self.icon_upload_large if self.icon_upload_large else None,
            compound="top" if self.icon_upload_large else None,
            justify="center",
            text_color="#9ca3af",
        )
        self.signature_label.pack(padx=20, pady=16, fill="x")
        self.signature_label.drop_target_register(DND_FILES)
        self.signature_label.dnd_bind('<<Drop>>', self._on_drop_signature_file)

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
            # Підписування файлу - compact режим
            self.select_sign_file_button.grid_configure(row=1, column=0, columnspan=3)
            self.select_private_key_button.grid_configure(row=2, column=0, columnspan=3)
            self.sign_button.grid_configure(row=3, column=0, columnspan=3)
            self.sign_file_drop_frame.grid_configure(row=4, column=0, columnspan=3)
            self.private_key_drop_frame.grid_configure(row=5, column=0, columnspan=3)

            # Перевірка підпису - compact режим
            self.select_verify_file_button.grid_configure(row=1, column=0, columnspan=3)
            self.select_public_key_button.grid_configure(row=2, column=0, columnspan=3)
            self.select_signature_button.grid_configure(row=3, column=0, columnspan=3)
            self.verify_button.grid_configure(row=4, column=0, columnspan=3)
            self.verify_file_drop_frame.grid_configure(row=5, column=0, columnspan=3)
            self.public_key_drop_frame.grid_configure(row=6, column=0, columnspan=3)
            self.signature_drop_frame.grid_configure(row=7, column=0, columnspan=3)
        else:
            # Підписування файлу - звичайний режим
            self.select_sign_file_button.grid_configure(row=1, column=0, columnspan=1)
            self.select_private_key_button.grid_configure(row=1, column=1, columnspan=1)
            self.sign_button.grid_configure(row=1, column=2, columnspan=1)
            self.sign_file_drop_frame.grid_configure(row=2, column=0, columnspan=3)
            self.private_key_drop_frame.grid_configure(row=3, column=0, columnspan=3)

            # Перевірка підпису - звичайний режим
            self.select_verify_file_button.grid_configure(row=1, column=0, columnspan=1)
            self.select_public_key_button.grid_configure(row=1, column=1, columnspan=1)
            self.select_signature_button.grid_configure(row=1, column=2, columnspan=1)
            self.verify_button.grid_configure(row=2, column=0, columnspan=1)
            self.verify_file_drop_frame.grid_configure(row=3, column=0, columnspan=3)
            self.public_key_drop_frame.grid_configure(row=4, column=0, columnspan=3)
            self.signature_drop_frame.grid_configure(row=5, column=0, columnspan=3)

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

    def _clean_drop_path(self, path: str) -> str:
        """Очищує шлях файлу від фігурних дужок."""
        return path.strip('{}')

    def _read_file_bytes(self, path: str) -> bytes | None:
        """Читає файл повністю для ключів (не для великих файлів)."""
        try:
            with open(path, "rb") as file:
                return file.read()
        except OSError:
            return None

    def _hash_file_chunks(self, file_path: str) -> hashes.Hash:
        """Обчислює хеш файлу шматками для економії пам'яті."""
        hasher = hashes.Hash(hashes.SHA256())
        try:
            with open(file_path, "rb") as file:
                while chunk := file.read(self.CHUNK_SIZE):
                    hasher.update(chunk)
        except OSError:
            raise
        return hasher

    def _on_drop_sign_file(self, event) -> None:
        """Обробник перетягування файлу для підпису."""
        path = self._clean_drop_path(event.data)
        self.sign_file_path = path
        # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
        self.sign_file_label.configure(
            text=f"Обрано файл:\n{os.path.basename(path)}",
            image="",
            compound="none",
            justify="center",
            text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
        )
        self._set_status("Файл для підпису обрано (drag-and-drop)", "#60a5fa")
        # Повертаємо колір рамки до стандартного після успішного drop
        self.sign_file_drop_frame.configure(border_color="#374151")

    def _on_drop_private_key(self, event) -> None:
        """Обробник перетягування приватного ключа."""
        path = self._clean_drop_path(event.data)
        key_bytes = self._read_file_bytes(path)
        if key_bytes is None:
            self._set_status("❌ Помилка: Не вдалося прочитати приватний ключ", "#ef4444")
            self.private_key_drop_frame.configure(border_color="#374151")
            return

        # Спроба завантажити ключ без пароля
        try:
            serialization.load_pem_private_key(key_bytes, password=None)
            self.private_key_data = key_bytes
            self.private_key_path = path
            # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
            self.private_key_label.configure(
                text=f"Обрано ключ:\n{os.path.basename(path)}",
                image="",
                
            justify="center",
                text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
            )
            self._set_status("✅ Приватний ключ завантажено (drag-and-drop)", "#22c55e")
        except ValueError as e:
            # Якщо ключ зашифровано, запитуємо пароль
            if "password" in str(e).lower() or "decryption" in str(e).lower():
                password = self._prompt_for_password()
                if password is not None:
                    try:
                        password_bytes = password.encode('utf-8')
                        serialization.load_pem_private_key(key_bytes, password=password_bytes)
                        self.private_key_data = key_bytes
                        self.private_key_path = path
                        # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
                        self.private_key_label.configure(
                            text=f"Обрано ключ:\n{os.path.basename(path)}",
                            image="",
                            compound="none",
            justify="center",
                            text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
                        )
                        self._set_status("✅ Приватний ключ завантажено (з паролем)", "#22c55e")
                    except ValueError:
                        self._set_status("❌ Помилка: Невірний пароль або формат ключа", "#ef4444")
                else:
                    self._set_status("❌ Скасовано: потрібен пароль для ключа", "#f59e0b")
            else:
                self._set_status("❌ Помилка: Невірний формат приватного ключа", "#ef4444")
        # Повертаємо колір рамки до стандартного після обробки
        self.private_key_drop_frame.configure(border_color="#374151")

    def _on_drop_verify_file(self, event) -> None:
        """Обробник перетягування файлу для перевірки."""
        path = self._clean_drop_path(event.data)
        self.verify_file_path = path
        # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
        self.verify_file_label.configure(
            text=f"Обрано файл:\n{os.path.basename(path)}",
            image="",
            compound="none",
                        justify="center",
            text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
        )
        self._set_status("Файл для перевірки обрано (drag-and-drop)", "#60a5fa")
        # Повертаємо колір рамки до стандартного після успішного drop
        self.verify_file_drop_frame.configure(border_color="#374151")

    def _on_drop_public_key(self, event) -> None:
        """Обробник перетягування публічного ключа."""
        path = self._clean_drop_path(event.data)
        key_bytes = self._read_file_bytes(path)
        if key_bytes is None:
            self._set_status("❌ Помилка: Не вдалося прочитати публічний ключ", "#ef4444")
            self.public_key_drop_frame.configure(border_color="#374151")
            return

        try:
            serialization.load_pem_public_key(key_bytes)
            self.public_key_data = key_bytes
            self.public_key_path = path
            # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
            self.public_key_label.configure(
                text=f"Обрано ключ:\n{os.path.basename(path)}",
                image="",
                compound="none",
            justify="center",
                text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
            )
            self._set_status("✅ Публічний ключ завантажено (drag-and-drop)", "#22c55e")
        except ValueError:
            self._set_status("❌ Помилка: Невірний формат публічного ключа", "#ef4444")
        # Повертаємо колір рамки до стандартного після обробки
        self.public_key_drop_frame.configure(border_color="#374151")

    def _on_drop_signature_file(self, event) -> None:
        """Обробник перетягування файлу підпису."""
        path = self._clean_drop_path(event.data)
        self.signature_path = path
        # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
        self.signature_label.configure(
            text=f"Обрано файл:\n{os.path.basename(path)}",
            image="",
            compound="none",
                        justify="center",
            text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
        )
        self._set_status("Файл підпису обрано (drag-and-drop)", "#60a5fa")
        # Повертаємо колір рамки до стандартного після успішного drop
        self.signature_drop_frame.configure(border_color="#374151")

    def _on_drag_enter(self, event, frame: ctk.CTkFrame) -> None:
        """Обробник входу файлу в зону перетягування."""
        frame.configure(border_color="#3b82f6")

    def _on_drag_leave(self, event, frame: ctk.CTkFrame) -> None:
        """Обробник виходу файлу з зони перетягування."""
        frame.configure(border_color="#374151")

    def _show_popup(self, event) -> None:
        """Показує спливаюче вікно з інформацією про розробника."""
        self.popup_frame.place(relx=0.95, rely=0.92, anchor="se")

    def _hide_popup(self, event) -> None:
        """Ховає спливаюче вікно з інформацією про розробника."""
        self.popup_frame.place_forget()

    def _prompt_for_password(self) -> str | None:
        """Запитує пароль у користувача через діалогове вікно."""
        dialog = ctk.CTkInputDialog(
            text="Введіть пароль для зашифрованого приватного ключа:",
            title="Пароль ключа"
        )
        return dialog.get_input()

    def _prompt_for_overwrite(self, file_path: str) -> bool:
        """Запитує підтвердження на перезапис файлу через модальне вікно."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Підтвердження")
        dialog.geometry("420x160")
        dialog.resizable(False, False)
        dialog.transient(self) # Keep on top of main window
        
        result = ctk.BooleanVar(value=False)
        
        def on_yes():
            result.set(True)
            dialog.grab_release()
            dialog.destroy()
            
        def on_no():
            result.set(False)
            dialog.grab_release()
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_no)

        label = ctk.CTkLabel(
            dialog, 
            text=f"Файл '{os.path.basename(file_path)}' вже існує.\nБажаєте перезаписати його?",
            font=ctk.CTkFont(size=14)
        )
        label.pack(pady=(25, 20), padx=20)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        
        btn_no = ctk.CTkButton(btn_frame, text="Скасувати", width=120, command=on_no)
        btn_no.pack(side="left", padx=10, expand=True)

        btn_yes = ctk.CTkButton(
            btn_frame, 
            text="Перезаписати", 
            width=120, 
            fg_color="#ef4444", 
            hover_color="#dc2626", 
            command=on_yes
        )
        btn_yes.pack(side="right", padx=10, expand=True)

        # CRITICAL: Wait for window to be drawn before grabbing focus to avoid TclError
        dialog.wait_visibility()
        dialog.grab_set()
        
        self.wait_window(dialog)
        return result.get()

    def _ensure_sign_button_enabled(self) -> None:
        """Гарантує, що кнопка підписування увімкнена."""
        self.after(0, lambda: self.sign_button.configure(state="normal"))

    def _ensure_verify_button_enabled(self) -> None:
        """Гарантує, що кнопка перевірки увімкнена."""
        self.after(0, lambda: self.verify_button.configure(state="normal"))

    
    def select_sign_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Оберіть файл для підпису",
            filetypes=[("All files", "*.*")],
        )
        if not path:
            return

        self.sign_file_path = path
        # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
        self.sign_file_label.configure(
            text=f"Обрано файл:\n{os.path.basename(path)}",
            image="",
            compound="none",
                        justify="center",
            text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
        )
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

        # Спроба завантажити ключ без пароля
        try:
            serialization.load_pem_private_key(key_bytes, password=None)
            self.private_key_data = key_bytes
            self.private_key_path = path
            # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
            self.private_key_label.configure(
                text=f"Обрано ключ:\n{os.path.basename(path)}",
                image="",
                compound="none",
            justify="center",
                text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
            )
            self._set_status("✅ Приватний ключ завантажено", "#22c55e")
        except ValueError as e:
            # Якщо ключ зашифровано, запитуємо пароль
            if "password" in str(e).lower() or "decryption" in str(e).lower():
                password = self._prompt_for_password()
                if password is not None:
                    try:
                        password_bytes = password.encode('utf-8')
                        serialization.load_pem_private_key(key_bytes, password=password_bytes)
                        self.private_key_data = key_bytes
                        self.private_key_path = path
                        # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
                        self.private_key_label.configure(
                            text=f"Обрано ключ:\n{os.path.basename(path)}",
                            image="",
                            compound="none",
            justify="center",
                            text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
                        )
                        self._set_status("✅ Приватний ключ завантажено (з паролем)", "#22c55e")
                    except ValueError:
                        self._set_status("❌ Помилка: Невірний пароль або формат ключа", "#ef4444")
                else:
                    self._set_status("❌ Скасовано: потрібен пароль для ключа", "#f59e0b")
            else:
                self._set_status("❌ Помилка: Невірний формат приватного ключа", "#ef4444")

    def sign_file(self) -> None:
        if not self.sign_file_path:
            self._set_status("⚠️ Спочатку оберіть файл для підпису!", "#f59e0b")
            return
        if not self.private_key_data:
            self._set_status("⚠️ Спочатку оберіть приватний ключ!", "#f59e0b")
            return
        if self._operation_thread and self._operation_thread.is_alive():
            return

        # Блокуємо кнопки та показуємо статус
        self.sign_button.configure(state="disabled")
        self._set_status("⏳ Підписування файлу, зачекайте...", "#f59e0b")
        
        # Запускаємо підписування в окремому потоці
        self._operation_thread = threading.Thread(
            target=self._sign_file_thread,
            daemon=True
        )
        self._operation_thread.start()

    def _sign_file_thread(self) -> None:
        """Підписування файлу в окремому потоці."""
        try:
            try:
                # Обчислюємо хеш файлу шматками
                file_hash = self._hash_file_chunks(self.sign_file_path)
                digest = file_hash.finalize()
            except OSError as e:
                self.after(0, lambda: self._on_sign_error(f"Помилка читання файлу: {str(e)}"))
                return
            
            # Спроба завантажити ключ без пароля
            try:
                private_key = serialization.load_pem_private_key(self.private_key_data, password=None)
            except ValueError as e:
                # Якщо ключ зашифровано, запитуємо пароль
                if "password" in str(e).lower() or "decryption" in str(e).lower():
                    password = self._prompt_for_password()
                    if password is None:
                        self.after(0, lambda: self._on_sign_error("Скасовано: потрібен пароль для ключа"))
                        return
                    try:
                        password_bytes = password.encode('utf-8')
                        private_key = serialization.load_pem_private_key(self.private_key_data, password=password_bytes)
                    except ValueError:
                        self.after(0, lambda: self._on_sign_error("Невірний пароль або формат ключа"))
                        return
                else:
                    self.after(0, lambda: self._on_sign_error(f"Помилка приватного ключа: {str(e)}"))
                    return
            
            try:
                signature = private_key.sign(
                    digest,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH,
                    ),
                    utils.Prehashed(hashes.SHA256()),
                )
            except ValueError as e:
                self.after(0, lambda: self._on_sign_error(f"Помилка створення підпису: {str(e)}"))
                return

            # Перевіряємо, чи існує файл підпису
            signature_path = f"{self.sign_file_path}.sig"
            if os.path.exists(signature_path):
                # Запитуємо підтвердження в головному потоці
                self.after(0, lambda: self._check_overwrite_confirmation(signature_path, signature))
                return

            # Зберігаємо підпис
            try:
                with open(signature_path, "wb") as signature_file:
                    signature_file.write(signature)
            except OSError as e:
                self.after(0, lambda: self._on_sign_error(f"Помилка збереження підпису: {str(e)}"))
                return
            
            # Оновлюємо UI в головному потоці
            self.after(0, lambda: self._on_sign_completed(signature_path))
            
        except Exception as e:
            self.after(0, lambda: self._on_sign_error(f"Неочікувана помилка підписування: {type(e).__name__}: {str(e)}"))
        finally:
            self._ensure_sign_button_enabled()

    def _check_overwrite_confirmation(self, signature_path: str, signature: bytes) -> None:
        """Перевіряє підтвердження перезапису в головному потоці."""
        if self._prompt_for_overwrite(signature_path):
            # Користувач підтвердив перезапис
            self._operation_thread = threading.Thread(
                target=self._save_signature_after_confirmation,
                args=(signature_path, signature),
                daemon=True
            )
            self._operation_thread.start()
        else:
            # Користувач скасував
            self._set_status("Скасовано користувачем", "#f59e0b")
            self.sign_button.configure(state="normal")

    def _save_signature_after_confirmation(self, signature_path: str, signature: bytes) -> None:
        """Зберігає підпис після підтвердження перезапису."""
        try:
            with open(signature_path, "wb") as signature_file:
                signature_file.write(signature)
            self.after(0, lambda: self._on_sign_completed(signature_path))
        except OSError as e:
            self.after(0, lambda: self._on_sign_error(f"Помилка збереження підпису: {str(e)}"))
        except Exception as e:
            self.after(0, lambda: self._on_sign_error(f"Неочікувана помилка збереження: {type(e).__name__}: {str(e)}"))
        finally:
            self._ensure_sign_button_enabled()

    def _on_sign_completed(self, signature_path: str) -> None:
        """Обробка успішного підписування."""
        self._set_status("✅ Підпис створено та збережено (.sig)", "#22c55e")
        self.sign_button.configure(state="normal")

    def _on_sign_error(self, error_msg: str) -> None:
        """Обробка помилки підписування."""
        self._set_status(f"❌ {error_msg}", "#ef4444")
        self.sign_button.configure(state="normal")

    def select_verify_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Оберіть файл для перевірки",
            filetypes=[("All files", "*.*")],
        )
        if not path:
            return

        self.verify_file_path = path
        # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
        self.verify_file_label.configure(
            text=f"Обрано файл:\n{os.path.basename(path)}",
            image="",
            compound="none",
                        justify="center",
            text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
        )
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
            # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
            self.public_key_label.configure(
                text=f"Обрано ключ:\n{os.path.basename(path)}",
                image="",
            compound="none",
            justify="center",
                text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
            )
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
        # Оновлюємо мітку до стану "Заповнено" - повністю приховуємо іконку
        self.signature_label.configure(
            text=f"Обрано файл:\n{os.path.basename(path)}",
            image="",
            compound="none",
                        justify="center",
            text_color=("gray10", "#DCE4EE"),  # Стандартний колір тексту CustomTkinter
        )
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
        if self._operation_thread and self._operation_thread.is_alive():
            return

        # Блокуємо кнопки та показуємо статус
        self.verify_button.configure(state="disabled")
        self._set_status("⏳ Перевірка підпису, зачекайте...", "#f59e0b")
        
        # Запускаємо перевірку в окремому потоці
        self._operation_thread = threading.Thread(
            target=self._verify_signature_thread,
            daemon=True
        )
        self._operation_thread.start()

    def _verify_signature_thread(self) -> None:
        """Перевірка підпису в окремому потоці."""
        try:
            try:
                # Обчислюємо хеш файлу шматками
                file_hash = self._hash_file_chunks(self.verify_file_path)
                digest = file_hash.finalize()
            except OSError as e:
                self.after(0, lambda: self._on_verify_error(f"Помилка читання файлу: {str(e)}"))
                return
            
            # Читаємо підпис
            try:
                with open(self.signature_path, "rb") as signature_file:
                    signature_data = signature_file.read()
            except OSError as e:
                self.after(0, lambda: self._on_verify_error(f"Не вдалося прочитати файл підпису: {str(e)}"))
                return
            
            try:
                public_key = serialization.load_pem_public_key(self.public_key_data)
            except ValueError as e:
                self.after(0, lambda: self._on_verify_error(f"Помилка публічного ключа: {str(e)}"))
                return
            
            try:
                public_key.verify(
                    signature_data,
                    digest,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH,
                    ),
                    utils.Prehashed(hashes.SHA256()),
                )
            except InvalidSignature:
                self.after(0, lambda: self._on_verify_completed(False))
                return
            except ValueError as e:
                self.after(0, lambda: self._on_verify_error(f"Помилка перевірки підпису: {str(e)}"))
                return
            
            # Оновлюємо UI в головному потоці
            self.after(0, lambda: self._on_verify_completed(True))
            
        except Exception as e:
            self.after(0, lambda: self._on_verify_error(f"Неочікувана помилка перевірки: {type(e).__name__}: {str(e)}"))
        finally:
            self._ensure_verify_button_enabled()

    def _on_verify_completed(self, is_valid: bool) -> None:
        """Обробка результату перевірки."""
        if is_valid:
            self._set_status("✅ Підпис дійсний", "#22c55e")
        else:
            self._set_status("❌ Підпис недійсний: файл або ключ не відповідає", "#ef4444")
        self.verify_button.configure(state="normal")

    def _on_verify_error(self, error_msg: str) -> None:
        """Обробка помилки перевірки."""
        self._set_status(f"❌ {error_msg}", "#ef4444")
        self.verify_button.configure(state="normal")


def main() -> None:
    app = SignatureSignVerifyApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.destroy()


if __name__ == "__main__":
    main()
