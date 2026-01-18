#!/usr/bin/env python3
"""
Autoclicker Ultimate - GitHub Bootstrapper/Installer
Downloads and installs from GitHub repository
"""

import os
import sys
import json
import time
import shutil
import platform
import threading
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ============== CONFIGURATION ==============
APP_NAME = "Autoclicker Ultimate"
APP_VERSION = "0.0.2"
APP_DESCRIPTION = "Advanced Autoclicker with Recording, Macros & License System"

# ============== GITHUB CONFIGURATION ==============
# CHANGE THESE TO YOUR REPOSITORY
GITHUB_USER = "EmergencyNeuMuensterOfficial"  # Change to your GitHub username
GITHUB_REPO = "Autoclicker"      # Change to your repository name
GITHUB_BRANCH = "main"         # Branch to download from

# Files to download from the repository
GITHUB_FILES = [
    "autoclicker.py",      # Main application (REQUIRED)
    "README.md",           # Documentation (optional)
    "LICENSE",             # License file (optional)
]

# Required files (installation will fail if these are missing)
REQUIRED_FILES = [
    "autoclicker.py",
]

# ============== COLORS ==============
PRIMARY_COLOR = "#0078d4"
PRIMARY_DARK = "#005a9e"
SUCCESS_COLOR = "#4caf50"
SUCCESS_DARK = "#388e3c"
DANGER_COLOR = "#f44336"
DANGER_DARK = "#d32f2f"
WARNING_COLOR = "#ff9800"
WARNING_DARK = "#f57c00"
BACKGROUND = "#f5f5f5"
DARK_BG = "#1e1e1e"
TEXT_COLOR = "#333333"
TEXT_LIGHT = "#666666"
TEXT_LIGHTER = "#999999"
WHITE_SEMI = "#e6e6e6"

# ============== PATHS ==============
BASE_DIR = Path(__file__).parent.absolute()
INSTALL_DIR = BASE_DIR / "Autoclicker_Ultimate"
VENV_DIR = INSTALL_DIR / "venv"
CONFIG_DIR = INSTALL_DIR / "config"
BACKUP_DIR = INSTALL_DIR / "backups"
LOG_FILE = BASE_DIR / "installer.log"

# ============== DEPENDENCIES ==============
DEPENDENCIES = [
    "pynput>=1.7.6",
    "Pillow>=9.0.0",
    "pystray>=0.19.0",
    "psutil>=5.9.0"
]


# ============== LOGGER ==============
class Logger:
    def __init__(self, log_file: Path):
        self.log_file = log_file
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(f"[{level}] {message}")
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + "\n")
        except:
            pass
            
    def error(self, message: str):
        self.log(message, "ERROR")
        
    def warn(self, message: str):
        self.log(message, "WARN")
        
    def info(self, message: str):
        self.log(message, "INFO")

logger = Logger(LOG_FILE)


# ============== GITHUB DOWNLOADER ==============
class GitHubDownloader:
    """Downloads files from GitHub repository"""
    
    def __init__(self, user: str, repo: str, branch: str = "main"):
        self.user = user
        self.repo = repo
        self.branch = branch
        self.base_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}"
    
    def get_file_url(self, filename: str) -> str:
        """Get raw URL for a file"""
        return f"{self.base_url}/{filename}"
    
    def download_file(self, filename: str, destination: Path, timeout: int = 30) -> bool:
        """Download a single file from GitHub"""
        url = self.get_file_url(filename)
        
        try:
            logger.info(f"Downloading: {filename}")
            logger.info(f"From: {url}")
            
            # Create request with headers
            request = urllib.request.Request(url)
            request.add_header('User-Agent', f'{APP_NAME} Installer/{APP_VERSION}')
            
            # Download file
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content = response.read()
                
                # Save to destination
                destination.parent.mkdir(parents=True, exist_ok=True)
                with open(destination, 'wb') as f:
                    f.write(content)
                
                logger.info(f"Downloaded: {filename} ({len(content)} bytes)")
                return True
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.warn(f"File not found on GitHub: {filename}")
            else:
                logger.error(f"HTTP Error {e.code} downloading {filename}: {e.reason}")
            return False
            
        except urllib.error.URLError as e:
            logger.error(f"URL Error downloading {filename}: {e.reason}")
            return False
            
        except Exception as e:
            logger.error(f"Error downloading {filename}: {str(e)}")
            return False
    
    def download_all(self, files: list, destination_dir: Path, 
                     progress_callback=None) -> tuple:
        """Download multiple files, returns (successful, failed) lists"""
        successful = []
        failed = []
        
        total = len(files)
        for i, filename in enumerate(files):
            dest = destination_dir / filename
            
            if progress_callback:
                progress = ((i + 1) / total) * 100
                progress_callback(progress, f"Downloading {filename}...")
            
            if self.download_file(filename, dest):
                successful.append(filename)
            else:
                failed.append(filename)
        
        return successful, failed
    
    def test_connection(self) -> bool:
        """Test if we can reach the repository"""
        try:
            # Try to access the repo
            test_url = f"https://api.github.com/repos/{self.user}/{self.repo}"
            request = urllib.request.Request(test_url)
            request.add_header('User-Agent', f'{APP_NAME} Installer')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status == 200
        except:
            return False


# ============== INSTALLER ==============
class GitHubInstaller:
    """Installer that downloads from GitHub"""
    
    def __init__(self):
        self.downloader = GitHubDownloader(GITHUB_USER, GITHUB_REPO, GITHUB_BRANCH)
        self.installation_successful = False
        self.python_exe = None
        self.pip_exe = None
        
        self.install_steps = [
            ("Checking system requirements", 5, self.check_system),
            ("Testing GitHub connection", 5, self.test_github),
            ("Creating directories", 5, self.create_dirs),
            ("Downloading application files", 20, self.download_files),
            ("Setting up virtual environment", 15, self.setup_venv),
            ("Installing dependencies", 25, self.install_deps),
            ("Creating launchers", 10, self.create_launchers),
            ("Creating uninstaller", 5, self.create_uninstaller),
            ("Finalizing installation", 5, self.finalize),
        ]
    
    def check_system(self):
        """Check system requirements"""
        if sys.version_info < (3, 6):
            raise Exception("Python 3.6+ required")
        
        try:
            import tkinter
        except ImportError:
            raise Exception("tkinter not installed")
        
        free_gb = shutil.disk_usage(BASE_DIR).free // (1024**3)
        if free_gb < 1:
            raise Exception(f"Low disk space: {free_gb}GB free")
    
    def test_github(self):
        """Test GitHub connection"""
        # Check if repo is configured
        if GITHUB_USER == "YOUR_USERNAME" or GITHUB_REPO == "YOUR_REPO":
            raise Exception(
                "GitHub repository not configured!\n"
                "Edit GITHUB_USER and GITHUB_REPO at the top of this file."
            )
        
        # Test connection
        if not self.downloader.test_connection():
            logger.warn("Could not verify GitHub repository, will try downloading anyway...")
    
    def create_dirs(self):
        """Create necessary directories"""
        for directory in [INSTALL_DIR, CONFIG_DIR, BACKUP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def download_files(self):
        """Download application files from GitHub"""
        successful, failed = self.downloader.download_all(GITHUB_FILES, INSTALL_DIR)
        
        # Check if required files were downloaded
        missing_required = [f for f in REQUIRED_FILES if f in failed]
        
        if missing_required:
            raise Exception(
                f"Failed to download required files: {', '.join(missing_required)}\n"
                "Check your internet connection and repository settings."
            )
        
        if failed:
            logger.warn(f"Some optional files failed to download: {', '.join(failed)}")
        
        logger.info(f"Downloaded {len(successful)} files successfully")
    
    def setup_venv(self):
        """Setup Python virtual environment"""
        if VENV_DIR.exists():
            shutil.rmtree(VENV_DIR)
        
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_DIR), "--copies"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Failed to create virtual environment: {result.stderr}")
        
        if platform.system() == "Windows":
            self.python_exe = VENV_DIR / "Scripts" / "python.exe"
            self.pip_exe = VENV_DIR / "Scripts" / "pip.exe"
        else:
            self.python_exe = VENV_DIR / "bin" / "python"
            self.pip_exe = VENV_DIR / "bin" / "pip"
    
    def install_deps(self):
        """Install Python dependencies"""
        # Upgrade pip
        subprocess.run(
            [str(self.pip_exe), "install", "--upgrade", "pip"],
            capture_output=True,
            text=True
        )
        
        # Install dependencies
        for dep in DEPENDENCIES:
            result = subprocess.run(
                [str(self.pip_exe), "install", dep],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to install {dep}: {result.stderr}")
    
    def create_launchers(self):
        """Create launcher scripts"""
        # Windows batch file
        bat_content = f"""@echo off
chcp 65001 >nul
echo ============================================
echo        AUTOCLICKER ULTIMATE
echo ============================================
echo.
echo Starting {APP_NAME}...
cd /d "{INSTALL_DIR}"
"{self.python_exe}" autoclicker.py
pause
"""
        bat_path = BASE_DIR / "run.bat"
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        
        # Desktop shortcut
        desktop_bat = BASE_DIR / f"Start_{APP_NAME.replace(' ', '_')}.bat"
        with open(desktop_bat, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        
        # Linux/Mac shell script
        sh_content = f"""#!/bin/bash
cd "{INSTALL_DIR}"
"{self.python_exe}" autoclicker.py
"""
        sh_path = BASE_DIR / "run.sh"
        with open(sh_path, 'w') as f:
            f.write(sh_content)
        
        if platform.system() != "Windows":
            os.chmod(sh_path, 0o755)
        
        # Python launcher
        py_content = f'''#!/usr/bin/env python3
"""
{APP_NAME} Launcher
"""
import os
import sys
import subprocess

def main():
    print("Starting {APP_NAME}...")
    os.chdir(r"{INSTALL_DIR}")
    
    try:
        if sys.platform == "win32":
            subprocess.Popen([r"{self.python_exe}", "autoclicker.py"], 
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.Popen([r"{self.python_exe}", "autoclicker.py"])
        
        print("Application started!")
    except Exception as e:
        print(f"Error: {{e}}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
'''
        py_path = BASE_DIR / "run.py"
        with open(py_path, 'w', encoding='utf-8') as f:
            f.write(py_content)
    
    def create_uninstaller(self):
        """Create uninstaller"""
        uninstaller_content = f'''#!/usr/bin/env python3
"""
{APP_NAME} Uninstaller
"""
import os
import sys
import shutil
from pathlib import Path

def main():
    print("=" * 50)
    print("{APP_NAME} - Uninstaller")
    print("=" * 50)
    print()
    
    install_dir = Path(r"{INSTALL_DIR}")
    base_dir = Path(__file__).parent
    
    if not install_dir.exists():
        print("Application is not installed.")
        return
    
    print(f"This will remove:")
    print(f"  - {{install_dir}}")
    print(f"  - Launcher files")
    print()
    
    response = input("Are you sure? (y/N): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        return
    
    print("Removing...")
    
    if install_dir.exists():
        shutil.rmtree(install_dir, ignore_errors=True)
        print(f"Removed: {{install_dir}}")
    
    launchers = ["run.bat", "run.sh", "run.py", "Start_Autoclicker_Ultimate.bat", "uninstall.py", "uninstall.bat"]
    for launcher in launchers:
        p = base_dir / launcher
        if p.exists():
            p.unlink()
            print(f"Removed: {{launcher}}")
    
    print()
    print("Uninstall complete!")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
'''
        
        with open(BASE_DIR / "uninstall.py", 'w', encoding='utf-8') as f:
            f.write(uninstaller_content)
        
        if platform.system() == "Windows":
            bat_content = f"""@echo off
echo Uninstalling {APP_NAME}...
python "{BASE_DIR / 'uninstall.py'}"
pause
"""
            with open(BASE_DIR / "uninstall.bat", 'w', encoding='utf-8') as f:
                f.write(bat_content)
    
    def finalize(self):
        """Finalize installation"""
        # Create version file
        version_file = INSTALL_DIR / "version.txt"
        with open(version_file, 'w') as f:
            f.write(f"{APP_NAME} v{APP_VERSION}\n")
            f.write(f"Installed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source: github.com/{GITHUB_USER}/{GITHUB_REPO}\n")
            f.write(f"Python: {sys.version}\n")
        
        # Create config
        config = {
            "app_name": APP_NAME,
            "version": APP_VERSION,
            "installed_at": datetime.now().isoformat(),
            "install_dir": str(INSTALL_DIR),
            "github_repo": f"{GITHUB_USER}/{GITHUB_REPO}",
            "github_branch": GITHUB_BRANCH
        }
        
        with open(INSTALL_DIR / "config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        # Create requirements.txt
        with open(INSTALL_DIR / "requirements.txt", 'w') as f:
            f.write("\n".join(DEPENDENCIES))
        
        self.installation_successful = True
    
    def is_installed(self) -> bool:
        """Check if already installed"""
        return (INSTALL_DIR / "autoclicker.py").exists()
    
    def install(self, progress_callback=None, log_callback=None) -> bool:
        """Run complete installation"""
        total_weight = sum(w for _, w, _ in self.install_steps)
        completed = 0
        
        try:
            for name, weight, func in self.install_steps:
                if log_callback:
                    log_callback(f"Starting: {name}")
                
                try:
                    func()
                    completed += weight
                    progress = (completed / total_weight) * 100
                    
                    if progress_callback:
                        progress_callback(progress, f"✓ {name}")
                    if log_callback:
                        log_callback(f"Completed: {name}")
                        
                except Exception as e:
                    if log_callback:
                        log_callback(f"FAILED: {name} - {str(e)}")
                    raise
            
            return True
            
        except Exception as e:
            logger.error(f"Installation failed: {str(e)}")
            return False


# ============== GUI ==============
class InstallerGUI:
    """Graphical installer interface"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - Installer")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        self.root.configure(bg=BACKGROUND)
        
        self.center_window()
        self.installer = GitHubInstaller()
        self.setup_ui()
    
    def center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')
    
    def setup_ui(self):
        """Setup UI"""
        # Header
        header = tk.Frame(self.root, bg=PRIMARY_COLOR, height=80)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        title_frame = tk.Frame(header, bg=PRIMARY_COLOR)
        title_frame.pack(expand=True, fill='both', padx=40, pady=20)
        
        tk.Label(
            title_frame, 
            text=APP_NAME,
            font=('Segoe UI', 20, 'bold'),
            fg='white',
            bg=PRIMARY_COLOR
        ).pack(side='left')
        
        tk.Label(
            title_frame,
            text=f"v{APP_VERSION}",
            font=('Segoe UI', 10),
            fg=WHITE_SEMI,
            bg=PRIMARY_COLOR
        ).pack(side='right')
        
        # Content
        self.content_frame = tk.Frame(self.root, bg=BACKGROUND)
        self.content_frame.pack(fill='both', expand=True, padx=30, pady=30)
        
        self.show_welcome()
    
    def show_welcome(self):
        """Show welcome screen"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Title
        tk.Label(
            self.content_frame,
            text="Welcome to Autoclicker Ultimate!",
            font=('Segoe UI', 18, 'bold'),
            bg=BACKGROUND,
            fg=TEXT_COLOR
        ).pack(pady=(0, 10))
        
        tk.Label(
            self.content_frame,
            text=APP_DESCRIPTION,
            font=('Segoe UI', 11),
            bg=BACKGROUND,
            fg=TEXT_LIGHT,
            wraplength=600
        ).pack(pady=(0, 20))
        
        # GitHub info
        github_frame = tk.Frame(self.content_frame, bg='white', relief='solid', bd=1)
        github_frame.pack(fill='x', pady=(0, 15), padx=50)
        
        tk.Label(
            github_frame,
            text="📦 Source Repository:",
            font=('Segoe UI', 10, 'bold'),
            bg='white',
            fg=TEXT_COLOR
        ).pack(anchor='w', padx=15, pady=(15, 5))
        
        repo_text = f"github.com/{GITHUB_USER}/{GITHUB_REPO}"
        if GITHUB_USER == "YOUR_USERNAME":
            repo_text = "⚠️ Not configured - Edit GITHUB_USER and GITHUB_REPO"
            repo_color = DANGER_COLOR
        else:
            repo_color = PRIMARY_COLOR
        
        tk.Label(
            github_frame,
            text=repo_text,
            font=('Consolas', 10),
            bg='white',
            fg=repo_color
        ).pack(anchor='w', padx=15, pady=(0, 10))
        
        tk.Label(
            github_frame,
            text="📁 Install Location:",
            font=('Segoe UI', 10, 'bold'),
            bg='white',
            fg=TEXT_COLOR
        ).pack(anchor='w', padx=15, pady=(5, 5))
        
        tk.Label(
            github_frame,
            text=str(INSTALL_DIR),
            font=('Consolas', 9),
            bg='white',
            fg=TEXT_LIGHT,
            wraplength=500
        ).pack(anchor='w', padx=15, pady=(0, 15))
        
        # Status
        if self.installer.is_installed():
            status_text = "✅ Already Installed"
            status_color = SUCCESS_COLOR
            btn_text = "Reinstall / Update"
            show_launch = True
        else:
            status_text = "⭕ Ready to Install"
            status_color = PRIMARY_COLOR
            btn_text = "Install Now"
            show_launch = False
        
        tk.Label(
            self.content_frame,
            text=status_text,
            font=('Segoe UI', 14, 'bold'),
            bg=BACKGROUND,
            fg=status_color
        ).pack(pady=(10, 20))
        
        # Install button
        install_btn = tk.Button(
            self.content_frame,
            text=btn_text,
            font=('Segoe UI', 14, 'bold'),
            bg=PRIMARY_COLOR,
            fg='white',
            activebackground=PRIMARY_DARK,
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            padx=40,
            pady=15,
            command=self.start_install
        )
        install_btn.pack(pady=(0, 20))
        
        # Other buttons
        btn_frame = tk.Frame(self.content_frame, bg=BACKGROUND)
        btn_frame.pack(pady=(0, 10))
        
        if show_launch:
            tk.Button(
                btn_frame,
                text="🚀 Launch App",
                font=('Segoe UI', 11, 'bold'),
                bg=SUCCESS_COLOR,
                fg='white',
                activebackground=SUCCESS_DARK,
                relief='flat',
                cursor='hand2',
                padx=25,
                pady=8,
                command=self.launch_app
            ).pack(side='left', padx=5)
        
        tk.Button(
            btn_frame,
            text="🗑️ Uninstall",
            font=('Segoe UI', 11),
            bg=DANGER_COLOR,
            fg='white',
            activebackground=DANGER_DARK,
            relief='flat',
            cursor='hand2',
            padx=25,
            pady=8,
            command=self.uninstall
        ).pack(side='left', padx=5)
        
        tk.Button(
            btn_frame,
            text="Exit",
            font=('Segoe UI', 11),
            bg=TEXT_LIGHTER,
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=25,
            pady=8,
            command=self.root.destroy
        ).pack(side='left', padx=5)
        
        # Footer
        tk.Label(
            self.content_frame,
            text="📡 Files will be downloaded from GitHub during installation.",
            font=('Segoe UI', 9),
            bg=BACKGROUND,
            fg=TEXT_LIGHTER
        ).pack(side='bottom', pady=(20, 0))
    
    def start_install(self):
        """Start installation"""
        # Check if GitHub is configured
        if GITHUB_USER == "YOUR_USERNAME" or GITHUB_REPO == "YOUR_REPO":
            messagebox.showerror(
                "Not Configured",
                "GitHub repository is not configured!\n\n"
                "Edit this file and set:\n"
                "  • GITHUB_USER = 'your_username'\n"
                "  • GITHUB_REPO = 'your_repo_name'\n\n"
                "Then run the installer again."
            )
            return
        
        # Show installation UI
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        tk.Label(
            self.content_frame,
            text="Installing Autoclicker Ultimate",
            font=('Segoe UI', 18, 'bold'),
            bg=BACKGROUND,
            fg=TEXT_COLOR
        ).pack(pady=(0, 10))
        
        tk.Label(
            self.content_frame,
            text="Downloading from GitHub and setting up...",
            font=('Segoe UI', 11),
            bg=BACKGROUND,
            fg=TEXT_LIGHT
        ).pack(pady=(0, 30))
        
        # Progress
        progress_frame = tk.Frame(self.content_frame, bg=BACKGROUND)
        progress_frame.pack(fill='x', pady=(0, 20), padx=50)
        
        self.progress_pct = tk.Label(
            progress_frame,
            text="0%",
            font=('Segoe UI', 28, 'bold'),
            bg=BACKGROUND,
            fg=PRIMARY_COLOR
        )
        self.progress_pct.pack()
        
        self.progress_bar = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.progress_bar.pack(fill='x', pady=(10, 5))
        
        self.status_text = tk.Label(
            progress_frame,
            text="Preparing...",
            font=('Segoe UI', 10),
            bg=BACKGROUND,
            fg=TEXT_LIGHT
        )
        self.status_text.pack()
        
        # Log
        tk.Label(
            self.content_frame,
            text="Installation Log:",
            font=('Segoe UI', 11, 'bold'),
            bg=BACKGROUND,
            fg=TEXT_COLOR
        ).pack(anchor='w', pady=(20, 5), padx=50)
        
        log_frame = tk.Frame(self.content_frame, bg='#333')
        log_frame.pack(fill='both', expand=True, padx=50, pady=(0, 20))
        
        self.log_output = scrolledtext.ScrolledText(
            log_frame,
            font=('Consolas', 9),
            bg=DARK_BG,
            fg='#ccc',
            height=8,
            wrap='word'
        )
        self.log_output.pack(fill='both', expand=True, padx=1, pady=1)
        
        # Run installation
        threading.Thread(target=self.run_install, daemon=True).start()
    
    def run_install(self):
        """Run installation in background"""
        try:
            def update_progress(pct, msg):
                self.root.after(0, lambda: self._update_progress(pct, msg))
            
            def log_msg(msg):
                self.root.after(0, lambda: self._add_log(msg))
            
            success = self.installer.install(update_progress, log_msg)
            
            if success:
                self.root.after(0, self._install_complete)
            else:
                self.root.after(0, lambda: self._install_failed("Installation failed"))
                
        except Exception as e:
            self.root.after(0, lambda: self._install_failed(str(e)))
    
    def _update_progress(self, pct, msg):
        self.progress_bar['value'] = pct
        self.progress_pct.config(text=f"{int(pct)}%")
        self.status_text.config(text=msg)
        self._add_log(msg)
    
    def _add_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_output.insert('end', f"[{ts}] {msg}\n")
        self.log_output.see('end')
    
    def _install_complete(self):
        self.progress_bar['value'] = 100
        self.progress_pct.config(text="100%")
        self.status_text.config(text="Installation complete!")
        self._add_log("✅ Installation completed successfully!")
        
        tk.Button(
            self.content_frame,
            text="Continue",
            font=('Segoe UI', 12, 'bold'),
            bg=SUCCESS_COLOR,
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=30,
            pady=10,
            command=self.show_welcome
        ).pack(pady=10)
        
        self.root.after(1000, lambda: messagebox.showinfo(
            "Success",
            f"{APP_NAME} installed successfully!\n\n"
            f"Location: {INSTALL_DIR}"
        ))
    
    def _install_failed(self, error):
        self.status_text.config(text="Installation failed!", fg=DANGER_COLOR)
        self._add_log(f"❌ ERROR: {error}")
        
        tk.Button(
            self.content_frame,
            text="Retry",
            font=('Segoe UI', 12, 'bold'),
            bg=WARNING_COLOR,
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=30,
            pady=10,
            command=self.show_welcome
        ).pack(pady=10)
        
        self.root.after(500, lambda: messagebox.showerror("Failed", f"Installation failed:\n\n{error}"))
    
    def launch_app(self):
        """Launch application"""
        launchers = [BASE_DIR / "run.bat", BASE_DIR / "run.py"]
        
        for launcher in launchers:
            if launcher.exists():
                try:
                    if platform.system() == "Windows":
                        os.startfile(launcher)
                    else:
                        subprocess.Popen([str(launcher)])
                    self.root.after(1000, self.root.destroy)
                    return
                except Exception as e:
                    logger.error(f"Launch failed: {e}")
        
        # Fallback
        app = INSTALL_DIR / "autoclicker.py"
        if app.exists():
            try:
                os.chdir(INSTALL_DIR)
                subprocess.Popen([sys.executable, "autoclicker.py"])
                self.root.after(1000, self.root.destroy)
            except Exception as e:
                messagebox.showerror("Error", f"Launch failed: {e}")
        else:
            messagebox.showerror("Error", "Application not found!")
    
    def uninstall(self):
        """Uninstall application"""
        if not INSTALL_DIR.exists():
            messagebox.showinfo("Info", "Not installed!")
            return
        
        if not messagebox.askyesno("Confirm", f"Uninstall {APP_NAME}?"):
            return
        
        try:
            if INSTALL_DIR.exists():
                shutil.rmtree(INSTALL_DIR, ignore_errors=True)
            
            for name in ["run.bat", "run.py", "run.sh", "Start_Autoclicker_Ultimate.bat", "uninstall.py", "uninstall.bat"]:
                p = BASE_DIR / name
                if p.exists():
                    p.unlink()
            
            messagebox.showinfo("Success", "Uninstall complete!")
            self.show_welcome()
            
        except Exception as e:
            messagebox.showerror("Error", f"Uninstall failed: {e}")
    
    def run(self):
        self.root.mainloop()


# ============== CLI ==============
def cli_install():
    """Command line installation"""
    print(f"\n{APP_NAME} Installer (GitHub)")
    print("=" * 50)
    
    if GITHUB_USER == "YOUR_USERNAME" or GITHUB_REPO == "YOUR_REPO":
        print("\nERROR: GitHub repository not configured!")
        print("Edit GITHUB_USER and GITHUB_REPO in this file.")
        sys.exit(1)
    
    print(f"\nSource: github.com/{GITHUB_USER}/{GITHUB_REPO}")
    print(f"Install to: {INSTALL_DIR}")
    print()
    
    installer = GitHubInstaller()
    
    if installer.is_installed():
        print("Already installed!")
        response = input("Reinstall? (y/N): ").strip().lower()
        if response != 'y':
            return
    
    print("\nStarting installation...\n")
    
    def progress(pct, msg):
        print(f"[{int(pct):3d}%] {msg}")
    
    def log(msg):
        print(f"  {msg}")
    
    success = installer.install(progress, log)
    
    if success:
        print("\n" + "=" * 50)
        print("Installation complete!")
        print(f"Location: {INSTALL_DIR}")
        print("\nRun: python run.py  or  run.bat")
    else:
        print("\nInstallation failed!")
        sys.exit(1)


# ============== MAIN ==============
def main():
    print(f"{APP_NAME} Installer")
    
    if len(sys.argv) > 1 and sys.argv[1] in ["--cli", "-c", "cli"]:
        cli_install()
        return
    
    try:
        app = InstallerGUI()
        app.run()
    except Exception as e:
        print(f"GUI failed: {e}")
        print("Using CLI mode...")
        cli_install()


if __name__ == "__main__":
    main()