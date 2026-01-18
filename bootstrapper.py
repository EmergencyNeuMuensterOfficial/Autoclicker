#!/usr/bin/env python3
"""
Autoclicker Ultimate - Bootstrapper & Updater
Handles installation, updates, and launch of the application
"""

import os
import sys
import json
import time
import shutil
import hashlib
import zipfile
import tarfile
import platform
import tempfile
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import urllib.request
import urllib.error

# ============== CONFIGURATION ==============
APP_NAME = "ENM CLICKER"
APP_VERSION = "0.0.1"
REPO_URL = "https://github.com/EmergencyNeuMuensterOfficial/Autoclicker.git"  # Update with your repo
RELEASE_URL = f"{REPO_URL}/releases/latest/download"
CONFIG_DIR = Path.home() / f".{APP_NAME.lower().replace(' ', '_')}"
INSTALL_DIR = CONFIG_DIR / "app"
BACKUP_DIR = CONFIG_DIR / "backups"
LOG_FILE = CONFIG_DIR / "bootstrapper.log"

# ============== LOGGING ==============
class Logger:
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        print(log_entry.strip())
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
    def error(self, message: str):
        self.log(message, "ERROR")
        
    def warn(self, message: str):
        self.log(message, "WARN")
        
    def info(self, message: str):
        self.log(message, "INFO")

logger = Logger(LOG_FILE)

# ============== SYSTEM CHECKS ==============
class SystemChecker:
    @staticmethod
    def check_python_version():
        """Check Python version compatibility"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 6):
            return False, f"Python 3.6+ required (you have {version.major}.{version.minor}.{version.micro})"
        return True, "Python version OK"
    
    @staticmethod
    def check_os():
        """Check operating system compatibility"""
        system = platform.system()
        if system == "Windows":
            return True, f"Windows {platform.release()}"
        elif system == "Linux":
            return True, f"Linux {platform.release()}"
        elif system == "Darwin":
            return True, f"macOS {platform.mac_ver()[0]}"
        else:
            return False, f"Unsupported OS: {system}"
    
    @staticmethod
    def check_dependencies():
        """Check required dependencies"""
        missing = []
        try:
            import tkinter
        except ImportError:
            missing.append("tkinter")
            
        try:
            import PIL
        except ImportError:
            missing.append("Pillow")
            
        return missing
    
    @staticmethod
    def get_system_info():
        """Get comprehensive system information"""
        info = {
            "platform": platform.platform(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "install_dir": str(INSTALL_DIR),
            "config_dir": str(CONFIG_DIR),
            "available_disk": shutil.disk_usage(INSTALL_DIR).free // (1024**3) if INSTALL_DIR.exists() else 0
        }
        return info

# ============== UPDATE SYSTEM ==============
class Updater:
    def __init__(self):
        self.current_version = APP_VERSION
        self.update_url = f"{REPO_URL}/releases/latest"
        self.manifest_url = f"{RELEASE_URL}/manifest.json"
        
    def check_for_updates(self) -> Dict:
        """Check for available updates"""
        try:
            # Try to get latest release info
            with urllib.request.urlopen(self.update_url, timeout=10) as response:
                import json
                import re
                html = response.read().decode('utf-8')
                
                # Try to extract version from release page
                version_pattern = r'releases/tag/v?([\d\.]+)'
                matches = re.findall(version_pattern, html)
                if matches:
                    latest_version = matches[0]
                    return {
                        "available": latest_version != self.current_version,
                        "latest_version": latest_version,
                        "current_version": self.current_version,
                        "url": f"{RELEASE_URL}/autoclicker-ultimate-v{latest_version}.zip"
                    }
        except Exception as e:
            logger.error(f"Failed to check updates: {e}")
            
        # Fallback: check manifest
        try:
            with urllib.request.urlopen(self.manifest_url, timeout=10) as response:
                manifest = json.loads(response.read())
                return {
                    "available": manifest.get("version", "0.0.0") != self.current_version,
                    "latest_version": manifest.get("version", "0.0.0"),
                    "current_version": self.current_version,
                    "changelog": manifest.get("changelog", []),
                    "url": manifest.get("download_url", "")
                }
        except Exception as e:
            logger.error(f"Failed to get manifest: {e}")
            
        return {"available": False, "error": "Cannot check updates"}
    
    def download_update(self, url: str, progress_callback=None) -> Optional[Path]:
        """Download update package"""
        try:
            temp_dir = Path(tempfile.mkdtemp())
            download_path = temp_dir / "update.zip"
            
            logger.info(f"Downloading update from {url}")
            
            with urllib.request.urlopen(url) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                block_size = 8192
                
                with open(download_path, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        f.write(buffer)
                        downloaded += len(buffer)
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
                            
            logger.info(f"Update downloaded: {download_path}")
            return download_path
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    def verify_update(self, update_path: Path, expected_hash: str = None) -> bool:
        """Verify update integrity"""
        try:
            if expected_hash:
                # Calculate file hash
                sha256 = hashlib.sha256()
                with open(update_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b''):
                        sha256.update(chunk)
                actual_hash = sha256.hexdigest()
                
                if actual_hash != expected_hash:
                    logger.error(f"Hash mismatch: {actual_hash} != {expected_hash}")
                    return False
                    
            # Verify archive integrity
            if update_path.suffix == '.zip':
                with zipfile.ZipFile(update_path, 'r') as zipf:
                    if zipf.testzip() is not None:
                        return False
            elif update_path.suffix in ['.tar', '.tar.gz', '.tgz']:
                with tarfile.open(update_path, 'r:*') as tarf:
                    # Just try to read members
                    tarf.getmembers()
                    
            return True
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
    
    def apply_update(self, update_path: Path, rollback_on_error: bool = True) -> bool:
        """Apply the downloaded update"""
        logger.info(f"Applying update from {update_path}")
        
        # Create backup
        backup_path = None
        if rollback_on_error and INSTALL_DIR.exists():
            backup_path = self._create_backup()
            if not backup_path:
                logger.error("Failed to create backup!")
                return False
        
        try:
            # Extract update
            temp_extract = Path(tempfile.mkdtemp())
            
            if update_path.suffix == '.zip':
                with zipfile.ZipFile(update_path, 'r') as zipf:
                    zipf.extractall(temp_extract)
            elif update_path.suffix in ['.tar', '.tar.gz', '.tgz']:
                with tarfile.open(update_path, 'r:*') as tarf:
                    tarf.extractall(temp_extract)
            else:
                logger.error(f"Unsupported archive format: {update_path.suffix}")
                return False
            
            # Stop any running instances
            self._stop_running_instances()
            
            # Remove old installation (keep configs)
            if INSTALL_DIR.exists():
                # Keep important files
                keep_files = ['config.json', 'profiles.json', 'macros.json', 'license.json']
                for file in keep_files:
                    config_file = INSTALL_DIR / file
                    if config_file.exists():
                        shutil.copy2(config_file, CONFIG_DIR / file)
                
                shutil.rmtree(INSTALL_DIR)
            
            # Copy new files
            extracted_app = None
            for item in temp_extract.iterdir():
                if item.is_dir() and 'autoclicker' in item.name.lower():
                    extracted_app = item
                    break
            
            if extracted_app:
                shutil.copytree(extracted_app, INSTALL_DIR)
            else:
                # If no clear app dir, copy everything
                for item in temp_extract.iterdir():
                    dest = INSTALL_DIR / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
            
            # Restore configs
            for file in ['config.json', 'profiles.json', 'macros.json', 'license.json']:
                config_file = CONFIG_DIR / file
                if config_file.exists():
                    shutil.copy2(config_file, INSTALL_DIR / file)
            
            # Update version
            version_file = INSTALL_DIR / "version.txt"
            with open(version_file, 'w') as f:
                f.write(self.current_version)
            
            # Cleanup
            shutil.rmtree(temp_extract)
            update_path.unlink()
            
            logger.info("Update applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Update failed: {e}")
            
            # Rollback if enabled
            if rollback_on_error and backup_path:
                logger.info("Rolling back to previous version...")
                self._restore_backup(backup_path)
                
            return False
    
    def _create_backup(self) -> Optional[Path]:
        """Create backup of current installation"""
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = BACKUP_DIR / f"backup_{timestamp}.zip"
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(INSTALL_DIR):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(INSTALL_DIR)
                        zipf.write(file_path, arcname)
            
            # Keep only last 5 backups
            backups = sorted(BACKUP_DIR.glob("backup_*.zip"))
            for old_backup in backups[:-5]:
                old_backup.unlink()
                
            return backup_path
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None
    
    def _restore_backup(self, backup_path: Path) -> bool:
        """Restore from backup"""
        try:
            if INSTALL_DIR.exists():
                shutil.rmtree(INSTALL_DIR)
            
            INSTALL_DIR.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(INSTALL_DIR)
            
            logger.info(f"Restored from backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def _stop_running_instances(self):
        """Stop any running instances of the app"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and 'autoclicker.py' in ' '.join(cmdline):
                        proc.terminate()
                        proc.wait(timeout=5)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            # psutil not available, try basic method
            pass

# ============== INSTALLATION SYSTEM ==============
class Installer:
    def __init__(self):
        self.dependencies = [
            "pynput>=1.7.6",
            "Pillow>=9.0.0",
            "pystray>=0.19.0",  # Optional but recommended
        ]
        
    def check_installation(self) -> bool:
        """Check if application is properly installed"""
        required_files = [
            INSTALL_DIR / "autoclicker.py",
            INSTALL_DIR / "requirements.txt",
        ]
        
        return all(f.exists() for f in required_files)
    
    def install_dependencies(self, progress_callback=None) -> bool:
        """Install Python dependencies"""
        logger.info("Installing dependencies...")
        
        for i, dep in enumerate(self.dependencies):
            try:
                if progress_callback:
                    progress_callback((i / len(self.dependencies)) * 100, f"Installing {dep}")
                
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "--upgrade", dep
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                logger.info(f"Installed: {dep}")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install {dep}: {e}")
                return False
        
        if progress_callback:
            progress_callback(100, "Dependencies installed")
            
        return True
    
    def setup_environment(self) -> bool:
        """Setup application environment"""
        try:
            # Create directories
            INSTALL_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            
            # Create desktop shortcut (Windows)
            if platform.system() == "Windows":
                self._create_windows_shortcut()
            
            # Create launcher script
            self._create_launcher_script()
            
            # Create uninstaller
            self._create_uninstaller()
            
            logger.info("Environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Environment setup failed: {e}")
            return False
    
    def _create_windows_shortcut(self):
        """Create Windows desktop shortcut"""
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, f"{APP_NAME}.lnk")
            
            target = str(Path(sys.executable).parent / "pythonw.exe")
            wDir = str(INSTALL_DIR)
            icon = str(INSTALL_DIR / "icon.ico") if (INSTALL_DIR / "icon.ico").exists() else None
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = target
            shortcut.Arguments = f'"{INSTALL_DIR / "autoclicker.py"}"'
            shortcut.WorkingDirectory = wDir
            if icon:
                shortcut.IconLocation = icon
            shortcut.save()
            
            logger.info(f"Created desktop shortcut: {shortcut_path}")
            
        except Exception as e:
            logger.warn(f"Could not create Windows shortcut: {e}")
    
    def _create_launcher_script(self):
        """Create launcher script"""
        launcher_content = f'''#!/usr/bin/env python3
"""
{APP_NAME} Launcher
"""
import os
import sys
import subprocess

app_dir = r"{INSTALL_DIR}"
script_path = os.path.join(app_dir, "autoclicker.py")

if not os.path.exists(script_path):
    print("Error: Application not found!")
    print(f"Expected at: {{script_path}}")
    sys.exit(1)

os.chdir(app_dir)
subprocess.Popen([sys.executable, script_path])
'''
        
        launcher_path = CONFIG_DIR / "launcher.py"
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        
        # Make executable on Unix
        if platform.system() != "Windows":
            os.chmod(launcher_path, 0o755)
    
    def _create_uninstaller(self):
        """Create uninstaller script"""
        uninstaller_content = f'''#!/usr/bin/env python3
"""
{APP_NAME} Uninstaller
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    print("=== {APP_NAME} Uninstaller ===")
    print("This will remove the application and all its data.")
    
    response = input("Are you sure? (y/N): ").strip().lower()
    if response != 'y':
        print("Uninstall cancelled.")
        return
    
    # Remove installation
    install_dir = Path(r"{INSTALL_DIR}")
    config_dir = Path(r"{CONFIG_DIR}")
    
    if install_dir.exists():
        shutil.rmtree(install_dir, ignore_errors=True)
        print(f"Removed installation: {{install_dir}}")
    
    # Remove configs (optional)
    response = input("Remove all settings and configurations? (y/N): ").strip().lower()
    if response == 'y':
        if config_dir.exists():
            shutil.rmtree(config_dir, ignore_errors=True)
            print(f"Removed configurations: {{config_dir}}")
    
    # Remove desktop shortcut (Windows)
    if sys.platform == "win32":
        try:
            import winshell
            shortcut = os.path.join(winshell.desktop(), "{APP_NAME}.lnk")
            if os.path.exists(shortcut):
                os.remove(shortcut)
                print("Removed desktop shortcut")
        except:
            pass
    
    print("\\nUninstall complete!")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
'''
        
        uninstaller_path = CONFIG_DIR / "uninstaller.py"
        with open(uninstaller_path, 'w') as f:
            f.write(uninstaller_content)
        
        if platform.system() != "Windows":
            os.chmod(uninstaller_path, 0o755)

# ============== GUI FOR BOOTSTRAPPER ==============
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading

class BootstrapGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - Installer")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Center window
        self.root.eval('tk::PlaceWindow . center')
        
        # Variables
        self.installer = Installer()
        self.updater = Updater()
        self.system_checker = SystemChecker()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg='#0078d4', height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(
            header, text=f"⚡ {APP_NAME}",
            font=('Segoe UI', 16, 'bold'),
            fg='#ffffff', bg='#0078d4'
        ).pack(pady=15)
        
        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create tabs
        self.create_welcome_tab()
        self.create_install_tab()
        self.create_update_tab()
        self.create_system_tab()
        self.create_logs_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(self.root, textvariable=self.status_var, 
                            relief='sunken', anchor='w', padx=10)
        status_bar.pack(fill='x', side='bottom')
        
    def create_welcome_tab(self):
        tab = tk.Frame(self.notebook, bg='white')
        self.notebook.add(tab, text=" Welcome ")
        
        content = tk.Frame(tab, bg='white', padx=30, pady=30)
        content.pack(fill='both', expand=True)
        
        tk.Label(
            content, text=f"Welcome to {APP_NAME}!",
            font=('Segoe UI', 20, 'bold'),
            fg='#0078d4', bg='white'
        ).pack(pady=10)
        
        tk.Label(
            content, text="The ultimate autoclicker with advanced features",
            font=('Segoe UI', 12),
            fg='#666666', bg='white'
        ).pack(pady=5)
        
        features = [
            "✓ Advanced autoclicking with multiple modes",
            "✓ Mouse movement recording & playback",
            "✓ Keyboard macro system",
            "✓ Customizable hotkeys",
            "✓ System tray integration",
            "✓ License key system"
        ]
        
        for feature in features:
            tk.Label(
                content, text=feature,
                font=('Segoe UI', 10),
                fg='#333333', bg='white',
                anchor='w'
            ).pack(fill='x', pady=2)
        
        # Check if installed
        if self.installer.check_installation():
            tk.Label(
                content, text="✓ Application is installed and ready!",
                font=('Segoe UI', 11, 'bold'),
                fg='#4ec959', bg='white'
            ).pack(pady=20)
            
            tk.Button(
                content, text="🚀 Launch Application", 
                command=self.launch_app,
                font=('Segoe UI', 12, 'bold'),
                bg='#0078d4', fg='white',
                padx=20, pady=10,
                cursor='hand2'
            ).pack(pady=10)
        else:
            tk.Label(
                content, text="⚠ Application not installed",
                font=('Segoe UI', 11, 'bold'),
                fg='#f9a825', bg='white'
            ).pack(pady=20)
            
            tk.Button(
                content, text="🔧 Go to Installation", 
                command=lambda: self.notebook.select(1),
                font=('Segoe UI', 12),
                bg='#f9a825', fg='white',
                padx=20, pady=10,
                cursor='hand2'
            ).pack(pady=10)
    
    def create_install_tab(self):
        tab = tk.Frame(self.notebook, bg='#f0f0f0')
        self.notebook.add(tab, text=" Installation ")
        
        content = tk.Frame(tab, bg='#f0f0f0', padx=20, pady=20)
        content.pack(fill='both', expand=True)
        
        # System check results
        check_frame = tk.LabelFrame(content, text="System Check", 
                                   font=('Segoe UI', 11, 'bold'),
                                   bg='#f0f0f0', padx=10, pady=10)
        check_frame.pack(fill='x', pady=(0, 15))
        
        # Python version
        py_ok, py_msg = self.system_checker.check_python_version()
        py_color = '#4ec959' if py_ok else '#f44336'
        tk.Label(check_frame, text=f"Python: {py_msg}", 
                font=('Segoe UI', 10), fg=py_color, bg='#f0f0f0').pack(anchor='w')
        
        # OS
        os_ok, os_msg = self.system_checker.check_os()
        os_color = '#4ec959' if os_ok else '#f44336'
        tk.Label(check_frame, text=f"OS: {os_msg}", 
                font=('Segoe UI', 10), fg=os_color, bg='#f0f0f0').pack(anchor='w')
        
        # Dependencies
        missing_deps = self.system_checker.check_dependencies()
        if missing_deps:
            tk.Label(check_frame, text=f"Missing: {', '.join(missing_deps)}", 
                    font=('Segoe UI', 10), fg='#f9a825', bg='#f0f0f0').pack(anchor='w')
        else:
            tk.Label(check_frame, text="Dependencies: All available", 
                    font=('Segoe UI', 10), fg='#4ec959', bg='#f0f0f0').pack(anchor='w')
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(content, variable=self.progress_var, maximum=100)
        progress_bar.pack(fill='x', pady=10)
        
        self.progress_label = tk.Label(content, text="", bg='#f0f0f0')
        self.progress_label.pack()
        
        # Install button
        self.install_btn = tk.Button(
            content, text="🚀 Install Application",
            command=self.start_installation,
            font=('Segoe UI', 12, 'bold'),
            bg='#0078d4', fg='white',
            padx=20, pady=10,
            cursor='hand2'
        )
        self.install_btn.pack(pady=20)
        
        # Uninstall button (if installed)
        if self.installer.check_installation():
            tk.Button(
                content, text="🗑️ Uninstall",
                command=self.uninstall_app,
                font=('Segoe UI', 10),
                bg='#f44336', fg='white',
                padx=10, pady=5,
                cursor='hand2'
            ).pack()
    
    def create_update_tab(self):
        tab = tk.Frame(self.notebook, bg='#f0f0f0')
        self.notebook.add(tab, text=" Updates ")
        
        content = tk.Frame(tab, bg='#f0f0f0', padx=20, pady=20)
        content.pack(fill='both', expand=True)
        
        tk.Label(
            content, text="Update Check",
            font=('Segoe UI', 14, 'bold'),
            bg='#f0f0f0'
        ).pack(pady=(0, 10))
        
        self.update_status = tk.Label(
            content, text="Checking for updates...",
            font=('Segoe UI', 11),
            bg='#f0f0f0'
        )
        self.update_status.pack(pady=10)
        
        # Check for updates on load
        self.root.after(100, self.check_updates)
        
        # Update progress
        self.update_progress_var = tk.DoubleVar()
        update_progress = ttk.Progressbar(content, variable=self.update_progress_var, maximum=100)
        update_progress.pack(fill='x', pady=10)
        
        self.update_progress_label = tk.Label(content, text="", bg='#f0f0f0')
        self.update_progress_label.pack()
        
        # Update button
        self.update_btn = tk.Button(
            content, text="⬇️ Download Update",
            command=self.download_update,
            font=('Segoe UI', 11),
            bg='#0078d4', fg='white',
            state='disabled',
            padx=15, pady=8,
            cursor='hand2'
        )
        self.update_btn.pack(pady=10)
        
        # Manual update button
        tk.Button(
            content, text="📁 Install from File",
            command=self.manual_update,
            font=('Segoe UI', 10),
            bg='#9c27b0', fg='white',
            padx=10, pady=5,
            cursor='hand2'
        ).pack(pady=5)
    
    def create_system_tab(self):
        tab = tk.Frame(self.notebook, bg='#f0f0f0')
        self.notebook.add(tab, text=" System ")
        
        content = tk.Frame(tab, bg='#f0f0f0', padx=20, pady=20)
        content.pack(fill='both', expand=True)
        
        tk.Label(
            content, text="System Information",
            font=('Segoe UI', 14, 'bold'),
            bg='#f0f0f0'
        ).pack(pady=(0, 15))
        
        # System info display
        info_frame = tk.Frame(content, bg='#ffffff', relief='solid', borderwidth=1)
        info_frame.pack(fill='both', expand=True)
        
        info_text = scrolledtext.ScrolledText(info_frame, height=15, 
                                            font=('Consolas', 9))
        info_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Get system info
        system_info = self.system_checker.get_system_info()
        for key, value in system_info.items():
            info_text.insert('end', f"{key}: {value}\n")
        
        info_text.config(state='disabled')
        
        # Action buttons
        btn_frame = tk.Frame(content, bg='#f0f0f0')
        btn_frame.pack(fill='x', pady=10)
        
        tk.Button(
            btn_frame, text="📋 Copy Info",
            command=lambda: self.copy_to_clipboard(str(system_info)),
            font=('Segoe UI', 10),
            bg='#607d8b', fg='white',
            padx=10, pady=5,
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        tk.Button(
            btn_frame, text="🗑️ Clear Cache",
            command=self.clear_cache,
            font=('Segoe UI', 10),
            bg='#ff9800', fg='white',
            padx=10, pady=5,
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        tk.Button(
            btn_frame, text="🔄 Repair Installation",
            command=self.repair_installation,
            font=('Segoe UI', 10),
            bg='#4caf50', fg='white',
            padx=10, pady=5,
            cursor='hand2'
        ).pack(side='left', padx=5)
    
    def create_logs_tab(self):
        tab = tk.Frame(self.notebook, bg='#f0f0f0')
        self.notebook.add(tab, text=" Logs ")
        
        content = tk.Frame(tab, bg='#f0f0f0', padx=20, pady=20)
        content.pack(fill='both', expand=True)
        
        tk.Label(
            content, text="Application Logs",
            font=('Segoe UI', 14, 'bold'),
            bg='#f0f0f0'
        ).pack(pady=(0, 10))
        
        # Log display
        log_frame = tk.Frame(content, bg='#ffffff', relief='solid', borderwidth=1)
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, 
                                                font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Load logs
        self.load_logs()
        
        # Action buttons
        btn_frame = tk.Frame(content, bg='#f0f0f0')
        btn_frame.pack(fill='x', pady=10)
        
        tk.Button(
            btn_frame, text="🔄 Refresh",
            command=self.load_logs,
            font=('Segoe UI', 10),
            bg='#2196f3', fg='white',
            padx=10, pady=5,
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        tk.Button(
            btn_frame, text="🗑️ Clear Logs",
            command=self.clear_logs,
            font=('Segoe UI', 10),
            bg='#f44336', fg='white',
            padx=10, pady=5,
            cursor='hand2'
        ).pack(side='left', padx=5)
        
        tk.Button(
            btn_frame, text="📁 Open Log Folder",
            command=lambda: self.open_folder(LOG_FILE.parent),
            font=('Segoe UI', 10),
            bg='#9c27b0', fg='white',
            padx=10, pady=5,
            cursor='hand2'
        ).pack(side='left', padx=5)
    
    # ============== ACTIONS ==============
    def start_installation(self):
        """Start the installation process"""
        self.install_btn.config(state='disabled', text="Installing...")
        self.status_var.set("Starting installation...")
        
        threading.Thread(target=self._install_thread, daemon=True).start()
    
    def _install_thread(self):
        """Installation thread"""
        try:
            # Update progress
            def update_progress(value, message):
                self.progress_var.set(value)
                self.progress_label.config(text=message)
                self.status_var.set(message)
            
            # Step 1: Setup environment
            update_progress(10, "Setting up environment...")
            if not self.installer.setup_environment():
                messagebox.showerror("Error", "Failed to setup environment!")
                return
            
            # Step 2: Install dependencies
            update_progress(30, "Installing dependencies...")
            if not self.installer.install_dependencies(update_progress):
                messagebox.showerror("Error", "Failed to install dependencies!")
                return
            
            # Step 3: Copy application files
            update_progress(80, "Copying application files...")
            
            # Find and copy autoclicker.py
            current_dir = Path(__file__).parent
            source_files = [
                "autoclicker.py",
                "key_manager.py",
                "requirements.txt",
                "README.md",
                "LICENSE"
            ]
            
            for file in source_files:
                src = current_dir / file
                if src.exists():
                    shutil.copy2(src, INSTALL_DIR / file)
            
            # Create default config
            config = {
                "version": APP_VERSION,
                "installed_at": datetime.now().isoformat(),
                "install_dir": str(INSTALL_DIR)
            }
            
            with open(INSTALL_DIR / "config.json", 'w') as f:
                json.dump(config, f, indent=2)
            
            update_progress(100, "Installation complete!")
            
            # Success message
            self.root.after(0, lambda: messagebox.showinfo(
                "Success", 
                f"{APP_NAME} has been installed successfully!\n\n"
                f"Location: {INSTALL_DIR}\n"
                "You can now launch the application from the Welcome tab."
            ))
            
            # Update UI
            self.root.after(0, lambda: self.install_btn.config(
                state='normal', text="✅ Installation Complete"
            ))
            
            # Refresh welcome tab
            self.root.after(0, lambda: self.notebook.forget(0))
            self.root.after(0, self.create_welcome_tab)
            
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Error", f"Installation failed:\n{str(e)}"
            ))
            self.root.after(0, lambda: self.install_btn.config(
                state='normal', text="🚀 Install Application"
            ))
    
    def check_updates(self):
        """Check for available updates"""
        self.update_status.config(text="Checking for updates...")
        
        def check():
            try:
                update_info = self.updater.check_for_updates()
                
                self.root.after(0, lambda: self._update_check_callback(update_info))
                
            except Exception as e:
                logger.error(f"Update check failed: {e}")
                self.root.after(0, lambda: self.update_status.config(
                    text=f"Error checking updates: {str(e)}",
                    fg='#f44336'
                ))
        
        threading.Thread(target=check, daemon=True).start()
    
    def _update_check_callback(self, update_info):
        """Handle update check results"""
        if update_info.get('available'):
            self.update_status.config(
                text=f"Update available: v{update_info['latest_version']}",
                fg='#4ec959'
            )
            self.update_btn.config(state='normal')
        else:
            if update_info.get('error'):
                self.update_status.config(
                    text=f"Update check failed: {update_info['error']}",
                    fg='#f44336'
                )
            else:
                self.update_status.config(
                    text=f"You have the latest version: v{APP_VERSION}",
                    fg='#2196f3'
                )
    
    def download_update(self):
        """Download and apply update"""
        update_info = self.updater.check_for_updates()
        if not update_info.get('available'):
            return
        
        self.update_btn.config(state='disabled', text="Downloading...")
        
        def download():
            def progress_callback(percent):
                self.root.after(0, lambda: self.update_progress_var.set(percent))
                self.root.after(0, lambda: self.update_progress_label.config(
                    text=f"Downloading: {percent:.1f}%"
                ))
            
            # Download update
            update_path = self.updater.download_update(
                update_info.get('url'), 
                progress_callback
            )
            
            if not update_path:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", "Failed to download update"
                ))
                self.root.after(0, lambda: self.update_btn.config(
                    state='normal', text="⬇️ Download Update"
                ))
                return
            
            # Verify update
            self.root.after(0, lambda: self.update_progress_label.config(
                text="Verifying update..."
            ))
            
            if not self.updater.verify_update(update_path):
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", "Update verification failed"
                ))
                return
            
            # Apply update
            self.root.after(0, lambda: self.update_progress_label.config(
                text="Applying update..."
            ))
            
            if self.updater.apply_update(update_path):
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success", "Update applied successfully!"
                ))
                self.root.after(0, lambda: self.update_progress_label.config(
                    text="Update complete!"
                ))
            else:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", "Failed to apply update"
                ))
            
            self.root.after(0, lambda: self.update_btn.config(
                state='normal', text="⬇️ Download Update"
            ))
            self.root.after(0, self.check_updates)
        
        threading.Thread(target=download, daemon=True).start()
    
    def manual_update(self):
        """Install update from local file"""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Select Update Package",
            filetypes=[
                ("ZIP files", "*.zip"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        if messagebox.askyesno("Confirm", "Apply this update?"):
            update_path = Path(file_path)
            if self.updater.apply_update(update_path):
                messagebox.showinfo("Success", "Update applied successfully!")
                self.check_updates()
            else:
                messagebox.showerror("Error", "Failed to apply update")
    
    def launch_app(self):
        """Launch the main application"""
        app_path = INSTALL_DIR / "autoclicker.py"
        
        if not app_path.exists():
            messagebox.showerror("Error", "Application not found!")
            return
        
        try:
            # Change to app directory
            os.chdir(INSTALL_DIR)
            
            # Launch in background
            if platform.system() == "Windows":
                subprocess.Popen([
                    sys.executable, "autoclicker.py"
                ], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen([
                    sys.executable, "autoclicker.py"
                ])
            
            # Close bootstrapper
            self.root.after(1000, self.root.destroy)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch: {str(e)}")
    
    def uninstall_app(self):
        """Uninstall the application"""
        if not messagebox.askyesno("Confirm", 
            "Uninstall Autoclicker Ultimate?\n\n"
            "This will remove the application but keep your settings."
        ):
            return
        
        # Run uninstaller
        uninstaller_path = CONFIG_DIR / "uninstaller.py"
        if uninstaller_path.exists():
            subprocess.Popen([sys.executable, str(uninstaller_path)])
            self.root.destroy()
        else:
            # Manual uninstall
            try:
                if INSTALL_DIR.exists():
                    shutil.rmtree(INSTALL_DIR, ignore_errors=True)
                messagebox.showinfo("Success", "Uninstall complete!")
                self.notebook.forget(0)
                self.create_welcome_tab()
            except Exception as e:
                messagebox.showerror("Error", f"Uninstall failed: {str(e)}")
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Copied", "System info copied to clipboard!")
    
    def clear_cache(self):
        """Clear application cache"""
        cache_dirs = [
            CONFIG_DIR / "cache",
            INSTALL_DIR / "__pycache__" if INSTALL_DIR.exists() else None
        ]
        
        cleared = 0
        for cache_dir in cache_dirs:
            if cache_dir and cache_dir.exists():
                shutil.rmtree(cache_dir, ignore_errors=True)
                cleared += 1
        
        messagebox.showinfo("Cache Cleared", f"Cleared {cleared} cache directories")
    
    def repair_installation(self):
        """Repair installation"""
        if not INSTALL_DIR.exists():
            messagebox.showerror("Error", "Application not installed!")
            return
        
        if messagebox.askyesno("Repair", "Repair installation?\n\nThis will reinstall dependencies and fix missing files."):
            self.start_installation()
    
    def load_logs(self):
        """Load and display logs"""
        try:
            self.log_text.config(state='normal')
            self.log_text.delete(1.0, 'end')
            
            if LOG_FILE.exists():
                with open(LOG_FILE, 'r') as f:
                    logs = f.read()
                self.log_text.insert('end', logs)
            else:
                self.log_text.insert('end', "No logs found.")
            
            self.log_text.config(state='disabled')
            self.log_text.see('end')
            
        except Exception as e:
            logger.error(f"Failed to load logs: {e}")
    
    def clear_logs(self):
        """Clear log file"""
        if messagebox.askyesno("Clear Logs", "Clear all log files?"):
            if LOG_FILE.exists():
                LOG_FILE.unlink()
            self.load_logs()
    
    def open_folder(self, folder_path):
        """Open folder in file explorer"""
        try:
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":
                subprocess.Popen(['open', folder_path])
            else:
                subprocess.Popen(['xdg-open', folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open folder: {str(e)}")
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

# ============== COMMAND LINE INTERFACE ==============
class CLI:
    def __init__(self):
        self.installer = Installer()
        self.updater = Updater()
        self.system_checker = SystemChecker()
        
    def show_help(self):
        """Show help information"""
        help_text = f"""
{APP_NAME} Bootstrapper - Command Line Interface

Usage:
  python bootstrapper.py [command]

Commands:
  install     - Install the application
  update      - Check and install updates
  launch      - Launch the application
  uninstall   - Remove the application
  status      - Show installation status
  system      - Show system information
  repair      - Repair installation
  gui         - Launch graphical installer (default)
  help        - Show this help

Examples:
  python bootstrapper.py install
  python bootstrapper.py update
  python bootstrapper.py launch
        """
        print(help_text)
    
    def install(self):
        """Install via CLI"""
        print(f"\n=== Installing {APP_NAME} ===\n")
        
        # Check system
        print("1. Checking system...")
        py_ok, py_msg = self.system_checker.check_python_version()
        print(f"   Python: {py_msg}")
        
        if not py_ok:
            print("   ❌ Python version check failed!")
            return
        
        os_ok, os_msg = self.system_checker.check_os()
        print(f"   OS: {os_msg}")
        
        if not os_ok:
            print("   ❌ OS not supported!")
            return
        
        # Setup environment
        print("\n2. Setting up environment...")
        if not self.installer.setup_environment():
            print("   ❌ Failed to setup environment!")
            return
        print("   ✓ Environment ready")
        
        # Install dependencies
        print("\n3. Installing dependencies...")
        if not self.installer.install_dependencies():
            print("   ❌ Failed to install dependencies!")
            return
        print("   ✓ Dependencies installed")
        
        # Copy files
        print("\n4. Copying application files...")
        current_dir = Path(__file__).parent
        source_files = ["autoclicker.py", "key_manager.py", "requirements.txt"]
        
        for file in source_files:
            src = current_dir / file
            if src.exists():
                shutil.copy2(src, INSTALL_DIR / file)
                print(f"   ✓ Copied {file}")
        
        # Create config
        config = {
            "version": APP_VERSION,
            "installed_at": datetime.now().isoformat()
        }
        
        with open(INSTALL_DIR / "config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✅ Installation complete!")
        print(f"   Location: {INSTALL_DIR}")
        print(f"   Run 'python bootstrapper.py launch' to start the application")
    
    def update(self):
        """Update via CLI"""
        print(f"\n=== Checking for Updates ===\n")
        
        update_info = self.updater.check_for_updates()
        
        if update_info.get('available'):
            print(f"Update available: v{update_info['latest_version']}")
            print(f"Current version: v{APP_VERSION}")
            
            response = input("\nDownload and install update? (y/N): ").strip().lower()
            if response == 'y':
                print("\nDownloading update...")
                update_path = self.updater.download_update(update_info.get('url'))
                
                if update_path and self.updater.verify_update(update_path):
                    print("Applying update...")
                    if self.updater.apply_update(update_path):
                        print("✅ Update applied successfully!")
                    else:
                        print("❌ Failed to apply update")
                else:
                    print("❌ Update verification failed")
        else:
            print(f"You have the latest version: v{APP_VERSION}")
    
    def launch(self):
        """Launch via CLI"""
        app_path = INSTALL_DIR / "autoclicker.py"
        
        if not app_path.exists():
            print("❌ Application not installed!")
            print("Run 'python bootstrapper.py install' first")
            return
        
        print(f"Launching {APP_NAME}...")
        
        try:
            os.chdir(INSTALL_DIR)
            subprocess.Popen([sys.executable, "autoclicker.py"])
            print("✅ Application launched!")
        except Exception as e:
            print(f"❌ Failed to launch: {e}")
    
    def uninstall(self):
        """Uninstall via CLI"""
        print(f"\n=== Uninstall {APP_NAME} ===\n")
        
        if not INSTALL_DIR.exists():
            print("Application not installed!")
            return
        
        print(f"Installation location: {INSTALL_DIR}")
        print(f"Config location: {CONFIG_DIR}")
        
        response = input("\nRemove application? (y/N): ").strip().lower()
        if response != 'y':
            print("Uninstall cancelled.")
            return
        
        # Remove installation
        if INSTALL_DIR.exists():
            shutil.rmtree(INSTALL_DIR, ignore_errors=True)
            print("✓ Removed installation")
        
        response = input("Remove all settings and configurations? (y/N): ").strip().lower()
        if response == 'y':
            if CONFIG_DIR.exists():
                shutil.rmtree(CONFIG_DIR, ignore_errors=True)
                print("✓ Removed configurations")
        
        print("\n✅ Uninstall complete!")
    
    def status(self):
        """Show status via CLI"""
        print(f"\n=== {APP_NAME} Status ===\n")
        
        # Installation status
        installed = self.installer.check_installation()
        print(f"Installed: {'✅ Yes' if installed else '❌ No'}")
        
        if installed:
            config_file = INSTALL_DIR / "config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                print(f"Version: {config.get('version', 'Unknown')}")
                print(f"Installed at: {config.get('installed_at', 'Unknown')}")
            
            # Check for updates
            print("\nChecking for updates...")
            update_info = self.updater.check_for_updates()
            if update_info.get('available'):
                print(f"Update available: v{update_info['latest_version']}")
            else:
                print("You have the latest version")
        
        # System info
        print("\n=== System Information ===")
        system_info = self.system_checker.get_system_info()
        for key, value in system_info.items():
            print(f"{key}: {value}")
    
    def system_info(self):
        """Show system information"""
        system_info = self.system_checker.get_system_info()
        
        print(f"\n=== System Information ===\n")
        for key, value in system_info.items():
            print(f"{key}: {value}")
    
    def repair(self):
        """Repair installation via CLI"""
        print(f"\n=== Repair Installation ===\n")
        
        if not INSTALL_DIR.exists():
            print("❌ Application not installed!")
            return
        
        print("Reinstalling dependencies...")
        if self.installer.install_dependencies():
            print("✅ Repair complete!")
        else:
            print("❌ Repair failed!")

# ============== MAIN ==============
def main():
    """Main entry point"""
    logger.info(f"{APP_NAME} Bootstrapper started")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        cli = CLI()
        command = sys.argv[1].lower()
        
        if command == "install":
            cli.install()
        elif command == "update":
            cli.update()
        elif command == "launch":
            cli.launch()
        elif command == "uninstall":
            cli.uninstall()
        elif command == "status":
            cli.status()
        elif command == "system":
            cli.system_info()
        elif command == "repair":
            cli.repair()
        elif command == "help":
            cli.show_help()
        elif command == "gui":
            # Fall through to GUI
            pass
        else:
            print(f"Unknown command: {command}")
            cli.show_help()
            sys.exit(1)
    else:
        # No arguments, launch GUI
        try:
            gui = BootstrapGUI()
            gui.run()
        except Exception as e:
            logger.error(f"GUI failed: {e}")
            print(f"GUI error: {e}")
            print("\nYou can use command line mode:")
            print("  python bootstrapper.py help")

if __name__ == "__main__":
    main()