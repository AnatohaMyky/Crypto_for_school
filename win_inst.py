#!/usr/bin/env python3
"""
ФІНАЛЬНА ВЕРСІЯ: Гарантировано працює на Windows.
Використовує пряме звернення до pyinstaller.exe
"""

import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path

def find_pyinstaller_exe():
    """Знаходимо pyinstaller.exe в системі."""
    possible_paths = [
        # Python Scripts папка
        Path(sys.executable).parent / "Scripts" / "pyinstaller.exe",
        Path(sys.executable).parent / "Scripts" / "pyinstaller",
        # Глобальні шляхи
        Path(os.environ.get("APPDATA", "")) / "Python" / "Scripts" / "pyinstaller.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Python" / "Scripts" / "pyinstaller.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Python" / "Scripts" / "pyinstaller.exe",
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    # Шукаємо через where
    try:
        result = subprocess.run(["where", "pyinstaller"], capture_output=True, text=True)
        if result.returncode == 0:
            first_line = result.stdout.split('\n')[0].strip()
            if first_line and Path(first_line).exists():
                return first_line
    except:
        pass
    
    return None

def install_pyinstaller():
    """Встановлюємо PyInstaller."""
    print("📦 Встановлення PyInstaller...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                      check=True, capture_output=True)
        print("✅ PyInstaller встановлено")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Помилка встановлення PyInstaller: {e}")
        return False

def build_with_pyinstaller_exe(script_path, app_name):
    """Створюємо EXE використовуючи pyinstaller.exe."""
    # Знаходимо pyinstaller.exe
    pyinstaller_path = find_pyinstaller_exe()
    
    if not pyinstaller_path:
        print("❌ pyinstaller.exe не знайдено")
        print("🔄 Спробуємо встановити PyInstaller...")
        if install_pyinstaller():
            pyinstaller_path = find_pyinstaller_exe()
            if not pyinstaller_path:
                print("❌ Після встановлення pyinstaller.exe все ще не знайдено")
                return False
        else:
            return False
    
    print(f"✅ Знайдено PyInstaller: {pyinstaller_path}")
    
    # Створюємо EXE
    cmd = [
    pyinstaller_path, 
    "--onefile", 
    "--windowed", 
    "--collect-all", "tkinterdnd2",
    "--add-data", "assets;assets", 
    "--name", app_name, 
    script_path
]
    
    try:
        print(f"🔨 Створення {app_name}.exe...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {app_name}.exe створено успішно")
            return True
        else:
            print(f"❌ Помилка створення {app_name}.exe")
            if result.stderr:
                print(f"STDERR: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Таймаут створення {app_name}.exe")
        return False
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False

def create_windows_package():
    """Створюємо фінальний дистрибутив."""
    print("\n📦 Створення Windows дистрибутива...")
    
    dist_dir = Path("digital_signature_tools_windows")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()
    
    # Копіюємо EXE файли
    exe_files = []
    for exe_name in ["SignatureKeyGenerator.exe", "SignatureSignVerify.exe"]:
        src = Path("dist") / exe_name
        if src.exists():
            dst = dist_dir / exe_name
            shutil.copy2(src, dst)
            exe_files.append(exe_name)
            size_mb = dst.stat().st_size / (1024 * 1024)
            print(f"✅ Скопійовано: {exe_name} ({size_mb:.1f} MB)")
        else:
            print(f"❌ Не знайдено: {exe_name}")
    
    if not exe_files:
        print("❌ Не знайдено виконуваних файлів!")
        return False
    
    # Створюємо README
    readme_content = """# Digital Signature Tools для Windows

## 🚀 Запуск програм

1. SignatureKeyGenerator.exe - генератор ключів RSA
2. SignatureSignVerify.exe - підписування та перевірка файлів

## 💡 Важливі поради

- ✅ Програми не вимагають встановлення Python
- ✅ Працюють на Windows 7 та вище
- ⚠️ Якщо антивірус блокує - додайте до винятків
- 💡 Можна створити ярлики на робочому столі

## 🎯 Що роблять програми

**SignatureKeyGenerator:**
- Створює пару ключів (приватний + публічний)
- Підтримує розміри 2048, 3072, 4096 біт
- Можливість шифрування ключів паролем

**SignatureSignVerify:**
- Підписує будь-які файли
- Перевіряє справжність підписів
- Підтримує drag-and-drop

## 🔧 Вирішення проблем

**Програма не запускається:**
1. Клацніть правою кнопкою → "Запустити від імені адміністратора"
2. Вимкніть антивірус тимчасово
3. Перевірте версію Windows (потребує Windows 7+)

**"Не вдалося знайти DLL":**
1. Встановіть Microsoft Visual C++ Redistributable
2. Перезавантажте комп'ютер

---
Створено автоматично за допомогою PyInstaller
Розробник: Анатолій Микитюк
"""
    
    with open(dist_dir / "README_WINDOWS.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # Створюємо ZIP архів
    zip_path = "digital_signature_tools_windows.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in dist_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(dist_dir)
                zipf.write(file_path, arcname)
    
    # Показуємо розмір
    zip_size = Path(zip_path).stat().st_size / (1024 * 1024)
    print(f"\n✅ Windows пакет створено!")
    print(f"📦 {zip_path} ({zip_size:.1f} MB)")
    print(f"📁 Папка: {dist_dir}")
    
    return True

def cleanup():
    """Очищення тимчасових файлів."""
    print("\n🧹 Очищення тимчасових файлів...")
    
    cleanup_items = ["build", "__pycache__", "*.spec"]
    
    for item in cleanup_items:
        if "*" in item:
            for file in Path.cwd().glob(item):
                if file.is_file():
                    file.unlink()
                    print(f"  Видалено: {file}")
        else:
            dir_path = Path(item)
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"  Видалено: {dir_path}")

def main():
    """Головна функція."""
    print("🚀 ФІНАЛЬНА ВЕРСІЯ: Створення Windows EXE файлів")
    print("=" * 60)
    
    # Перевірка Windows
    if os.name != 'nt':
        print("❌ Цей скрипт тільки для Windows")
        return False
    
    print(f"✅ Python: {sys.version}")
    print(f"✅ Робоча папка: {Path.cwd()}")
    
    # Перевірка файлів
    required_files = ["signature_keygen.py", "signature_sign_verify.py"]
    missing_files = [f for f in required_files if not Path(f).exists()]
    if missing_files:
        print(f"❌ Відсутні файли: {missing_files}")
        return False
    
    print("✅ Вихідні файли знайдено")
    
    # Встановлення залежностей
    print("\n📦 Встановлення залежностей...")
    packages = ["customtkinter", "cryptography", "pillow", "tkinterdnd2"]
    
    for package in packages:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], 
                          check=True, capture_output=True)
            print(f"✅ Встановлено: {package}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Помилка встановлення {package}: {e}")
            return False
    
    # Створення EXE файлів
    apps = [
        ("signature_keygen.py", "SignatureKeyGenerator"),
        ("signature_sign_verify.py", "SignatureSignVerify")
    ]
    
    success_count = 0
    for script, name in apps:
        if build_with_pyinstaller_exe(script, name):
            success_count += 1
    
    if success_count == len(apps):
        # Створення дистрибутива
        if create_windows_package():
            cleanup()
            print("\n🎉 Готово! Windows дистрибутив створено успішно!")
            print("\n📦 Файли для розповсюдження:")
            print("  📦 digital_signature_tools_windows.zip")
            print("  📁 digital_signature_tools_windows/ (папка з програмами)")
            print("\n💡 Користувачам достатньо розпакувати ZIP та запускати .exe файли")
            return True
    
    print(f"\n❌ Помилка створення дистрибутива (успішно: {success_count}/{len(apps)})")
    print("\n💡 Можливі рішення:")
    print("  1. Перевстановіть Python (рекомендовано 3.11 або 3.12)")
    print("  2. Встановіть Visual Studio Build Tools")
    print("  3. Спробуйте запустити від імені адміністратора")
    return False

if __name__ == "__main__":
    try:
        success = main()
        print(f"\n{'='*60}")
        if success:
            print("✅ УСПІХ! Дистрибутив створено.")
        else:
            print("❌ ПОМИЛКА!")
        
        input("\nНатисніть Enter для виходу...")
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Перервано користувачем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критична помилка: {e}")
        input("\nНатисніть Enter для виходу...")
        sys.exit(1)
