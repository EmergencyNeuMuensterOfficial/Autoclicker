#!/usr/bin/env python3
"""
Autoclicker Ultimate - Complete Installer
"""

import os
import sys
import json
import time
import shutil
import platform
import threading
import subprocess
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font

# ============== CONFIGURATION ==============
APP_NAME = "Autoclicker Ultimate"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Advanced Autoclicker with Recording, Macros & License System"

# Colors (Fixed: removed RGBA, only use hex colors)
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
WHITE_SEMI_TRANSPARENT = "#e6e6e6"

# Paths
BASE_DIR = Path(__file__).parent.absolute()
INSTALL_DIR = BASE_DIR / "Autoclicker_Ultimate"
VENV_DIR = INSTALL_DIR / "venv"
CONFIG_DIR = INSTALL_DIR / "config"
BACKUP_DIR = INSTALL_DIR / "backups"
LOG_FILE = BASE_DIR / "installer.log"

# Dependencies
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
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")
            
    def error(self, message: str):
        self.log(message, "ERROR")
        
    def warn(self, message: str):
        self.log(message, "WARN")
        
    def info(self, message: str):
        self.log(message, "INFO")

logger = Logger(LOG_FILE)

# ============== SIMPLE INSTALLER ==============
class SimpleInstaller:
    def __init__(self):
        self.install_steps = [
            ("Checking system requirements", 5, self.check_system),
            ("Creating directories", 5, self.create_dirs),
            ("Setting up virtual environment", 15, self.setup_venv),
            ("Installing dependencies", 25, self.install_deps),
            ("Copying application files", 15, self.copy_files),
            ("Creating launchers", 15, self.create_launchers),
            ("Creating uninstaller", 5, self.create_uninstaller),
            ("Finalizing installation", 5, self.finalize),
        ]
        self.installation_successful = False
    
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
            raise Exception(f"Low disk space: {free_gb}GB free (need at least 1GB)")
    
    def create_dirs(self):
        """Create necessary directories"""
        for directory in [INSTALL_DIR, CONFIG_DIR, BACKUP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
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
        # First upgrade pip
        pip_upgrade_result = subprocess.run(
            [str(self.pip_exe), "install", "--upgrade", "pip"],
            capture_output=True,
            text=True
        )
        
        if pip_upgrade_result.returncode != 0:
            # Try without upgrade if upgrade fails
            logger.warn(f"Pip upgrade failed: {pip_upgrade_result.stderr}")
        
        # Install each dependency
        for dep in DEPENDENCIES:
            result = subprocess.run(
                [str(self.pip_exe), "install", dep],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to install {dep}: {result.stderr}")
    
    def copy_files(self):
        """Copy application files"""
        files_to_copy = []
        
        for filename in ["autoclicker.py", "key_manager.py", "README.md", "LICENSE"]:
            src = BASE_DIR / filename
            if src.exists():
                files_to_copy.append(src)
        
        if not files_to_copy:
            raise Exception("No application files found!")
        
        for src in files_to_copy:
            shutil.copy2(src, INSTALL_DIR / src.name)
        
        # Create requirements.txt
        with open(INSTALL_DIR / "requirements.txt", 'w') as f:
            f.write("\n".join(DEPENDENCIES))
        
        # Create config file
        config = {
            "app_name": APP_NAME,
            "version": APP_VERSION,
            "installed_at": datetime.now().isoformat(),
            "install_dir": str(INSTALL_DIR),
            "portable": True
        }
        
        with open(INSTALL_DIR / "config.json", 'w') as f:
            json.dump(config, f, indent=2)
    
    def create_launchers(self):
        """Create launcher scripts"""
        # Use safe ASCII characters for batch files
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
        
        try:
            bat_path = BASE_DIR / "run.bat"
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)
        except UnicodeEncodeError:
            # Fallback to ASCII only
            bat_content_ascii = f"""@echo off
echo ============================================
echo        AUTOCLICKER ULTIMATE
echo ============================================
echo.
echo Starting {APP_NAME}...
cd /d "{INSTALL_DIR}"
"{self.python_exe}" autoclicker.py
pause
"""
            with open(bat_path, 'w', encoding='ascii', errors='ignore') as f:
                f.write(bat_content_ascii)
        
        # Desktop shortcut for Windows
        desktop_bat = BASE_DIR / f"Start_{APP_NAME.replace(' ', '_')}.bat"
        try:
            with open(desktop_bat, 'w', encoding='utf-8') as f:
                f.write(bat_content)
        except UnicodeEncodeError:
            with open(desktop_bat, 'w', encoding='ascii', errors='ignore') as f:
                f.write(bat_content)
        
        # Linux/Mac shell script - no fancy characters needed
        sh_content = f"""#!/bin/bash
cd "{INSTALL_DIR}"
"{self.python_exe}" autoclicker.py
"""
        sh_path = BASE_DIR / "run.sh"
        with open(sh_path, 'w') as f:
            f.write(sh_content)
        
        if platform.system() != "Windows":
            os.chmod(sh_path, 0o755)
        
        # Python launcher (cross-platform)
        py_content = f'''#!/usr/bin/env python3
"""
{APP_NAME} Launcher
"""
import os
import sys
import subprocess

def main():
    print("Starting {APP_NAME}...")
    print(f"Version: {APP_VERSION}")
    print()
    
    # Change to install directory
    os.chdir(r"{INSTALL_DIR}")
    
    try:
        if sys.platform == "win32":
            subprocess.Popen([r"{self.python_exe}", "autoclicker.py"], 
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.Popen([r"{self.python_exe}", "autoclicker.py"])
        
        print("SUCCESS: Application started!")
    except Exception as e:
        print(f"ERROR: {{e}}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
'''
        py_path = BASE_DIR / "run.py"
        with open(py_path, 'w', encoding='utf-8') as f:
            f.write(py_content)
    
    def create_uninstaller(self):
        """Create uninstaller script"""
        # FIXED: Using double curly braces to escape in f-string
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
    print(f"{APP_NAME} - Uninstaller")
    print("=" * 50)
    print()
    
    install_dir = Path(r"{INSTALL_DIR}")
    base_dir = Path(__file__).parent
    
    if not install_dir.exists():
        print("ERROR: Application is not installed.")
        return
    
    print(f"This will remove:")
    print(f"  • {{install_dir}}")
    print(f"  • Launcher files")
    print()
    
    response = input("Are you sure? (y/N): ").strip().lower()
    if response != 'y':
        print("Uninstall cancelled.")
        return
    
    print()
    print("Removing application...")
    
    # Remove installation directory
    if install_dir.exists():
        shutil.rmtree(install_dir, ignore_errors=True)
        print(f"Removed: {{install_dir}}")
    
    # Remove launchers
    launchers = ["run.bat", "run.sh", "run.py", f"Start_{APP_NAME.replace(' ', '_')}.bat"]
    for launcher in launchers:
        launcher_path = base_dir / launcher
        if launcher_path.exists():
            launcher_path.unlink()
            print(f"Removed: {{launcher}}")
    
    print()
    print("SUCCESS: Uninstall complete!")
    print("Note: Your settings are preserved in the config folder.")
    print()
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
'''
        
        uninstaller_path = BASE_DIR / "uninstall.py"
        with open(uninstaller_path, 'w', encoding='utf-8') as f:
            f.write(uninstaller_content)
        
        # Windows uninstaller batch
        if platform.system() == "Windows":
            uninstaller_bat = BASE_DIR / "uninstall.bat"
            uninstaller_bat_content = f"""@echo off
echo Uninstalling {APP_NAME}...
echo.
python "{uninstaller_path}"
pause
"""
            try:
                with open(uninstaller_bat, 'w', encoding='utf-8') as f:
                    f.write(uninstaller_bat_content)
            except UnicodeEncodeError:
                with open(uninstaller_bat, 'w', encoding='ascii', errors='ignore') as f:
                    f.write(uninstaller_bat_content)
    
    def finalize(self):
        """Finalize installation"""
        version_file = INSTALL_DIR / "version.txt"
        with open(version_file, 'w') as f:
            f.write(f"{APP_NAME} v{APP_VERSION}\n")
            f.write(f"Installed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Portable: Yes\n")
            f.write(f"Python: {sys.version}\n")
        
        self.installation_successful = True
    
    def is_installed(self):
        """Check if already installed"""
        return (INSTALL_DIR / "autoclicker.py").exists()
    
    def install(self, progress_callback=None, log_callback=None):
        """Run complete installation"""
        total_weight = sum(weight for _, weight, _ in self.install_steps)
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
                        log_callback(f"Failed: {name} - {str(e)}")
                    raise
            
            return True
        except Exception as e:
            logger.error(f"Installation failed: {str(e)}")
            return False

# ============== SIMPLE GUI ==============
class SimpleInstallerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - Installer")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        self.root.configure(bg=BACKGROUND)
        
        # Center window
        self.center_window()
        
        self.installer = SimpleInstaller()
        self.setup_ui()
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Setup the user interface"""
        # Header
        header = tk.Frame(self.root, bg=PRIMARY_COLOR, height=80)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        # App title
        title_frame = tk.Frame(header, bg=PRIMARY_COLOR)
        title_frame.pack(expand=True, fill='both', padx=40, pady=20)
        
        tk.Label(
            title_frame, 
            text=f"{APP_NAME}",
            font=('Segoe UI', 20, 'bold'),
            fg='white',
            bg=PRIMARY_COLOR
        ).pack(side='left')
        
        tk.Label(
            title_frame,
            text=f"v{APP_VERSION}",
            font=('Segoe UI', 10),
            fg=WHITE_SEMI_TRANSPARENT,
            bg=PRIMARY_COLOR
        ).pack(side='right')
        
        # Main content area
        self.content_frame = tk.Frame(self.root, bg=BACKGROUND)
        self.content_frame.pack(fill='both', expand=True, padx=30, pady=30)
        
        self.show_welcome_screen()
    
    def show_welcome_screen(self):
        """Show welcome screen with install button"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Welcome message
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
        ).pack(pady=(0, 30))
        
        # Installation folder info
        folder_frame = tk.Frame(self.content_frame, bg='white', relief='solid', bd=1)
        folder_frame.pack(fill='x', pady=(0, 30), padx=50)
        
        tk.Label(
            folder_frame,
            text="Installation Folder:",
            font=('Segoe UI', 10, 'bold'),
            bg='white',
            fg=TEXT_COLOR
        ).pack(anchor='w', padx=15, pady=(15, 5))
        
        tk.Label(
            folder_frame,
            text=str(INSTALL_DIR),
            font=('Consolas', 9),
            bg='white',
            fg=PRIMARY_COLOR,
            wraplength=500
        ).pack(anchor='w', padx=15, pady=(0, 15))
        
        # Check installation status
        if self.installer.is_installed():
            status_icon = ""
            status_text = "Already Installed"
            status_color = SUCCESS_COLOR
            button_text = "Reinstall Application"
            show_launch = True
        else:
            status_icon = ""
            status_text = "Ready to Install"
            status_color = PRIMARY_COLOR
            button_text = "Install Now"
            show_launch = False
        
        # Status display
        status_frame = tk.Frame(self.content_frame, bg=BACKGROUND)
        status_frame.pack(pady=(0, 20))
        
        tk.Label(
            status_frame,
            text=status_icon,
            font=('Segoe UI', 24),
            bg=BACKGROUND,
            fg=status_color
        ).pack(side='left', padx=(0, 10))
        
        tk.Label(
            status_frame,
            text=status_text,
            font=('Segoe UI', 14, 'bold'),
            bg=BACKGROUND,
            fg=status_color
        ).pack(side='left')
        
        # Big install button
        self.install_button = tk.Button(
            self.content_frame,
            text=button_text,
            font=('Segoe UI', 14, 'bold'),
            bg=PRIMARY_COLOR,
            fg='white',
            activebackground=PRIMARY_DARK,
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            padx=40,
            pady=15,
            command=self.start_installation
        )
        self.install_button.pack(pady=(0, 20))
        
        # Secondary buttons
        button_frame = tk.Frame(self.content_frame, bg=BACKGROUND)
        button_frame.pack(pady=(0, 10))
        
        if show_launch:
            launch_btn = tk.Button(
                button_frame,
                text="Launch Application",
                font=('Segoe UI', 11, 'bold'),
                bg=SUCCESS_COLOR,
                fg='white',
                activebackground=SUCCESS_DARK,
                activeforeground='white',
                relief='flat',
                cursor='hand2',
                padx=25,
                pady=8,
                command=self.launch_app
            )
            launch_btn.pack(side='left', padx=5)
        
        uninstall_btn = tk.Button(
            button_frame,
            text="Uninstall",
            font=('Segoe UI', 11),
            bg=DANGER_COLOR,
            fg='white',
            activebackground=DANGER_DARK,
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            padx=25,
            pady=8,
            command=self.uninstall_app
        )
        uninstall_btn.pack(side='left', padx=5)
        
        exit_btn = tk.Button(
            button_frame,
            text="Exit",
            font=('Segoe UI', 11),
            bg=TEXT_LIGHTER,
            fg='white',
            activebackground=TEXT_LIGHT,
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            padx=25,
            pady=8,
            command=self.root.destroy
        )
        exit_btn.pack(side='left', padx=5)
        
        # Footer note
        tk.Label(
            self.content_frame,
            text="Note: This is a portable installation. You can move the entire folder anywhere.",
            font=('Segoe UI', 9),
            bg=BACKGROUND,
            fg=TEXT_LIGHTER
        ).pack(side='bottom', pady=(20, 0))
    
    def start_installation(self):
        """Start installation process"""
        # Show installation screen
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Installation title
        tk.Label(
            self.content_frame,
            text="Installing Autoclicker Ultimate",
            font=('Segoe UI', 18, 'bold'),
            bg=BACKGROUND,
            fg=TEXT_COLOR
        ).pack(pady=(0, 10))
        
        tk.Label(
            self.content_frame,
            text="Please wait while we set up everything...",
            font=('Segoe UI', 11),
            bg=BACKGROUND,
            fg=TEXT_LIGHT
        ).pack(pady=(0, 30))
        
        # Progress container
        progress_container = tk.Frame(self.content_frame, bg=BACKGROUND)
        progress_container.pack(fill='x', pady=(0, 20), padx=50)
        
        # Progress percentage
        self.progress_percent = tk.Label(
            progress_container,
            text="0%",
            font=('Segoe UI', 28, 'bold'),
            bg=BACKGROUND,
            fg=PRIMARY_COLOR
        )
        self.progress_percent.pack()
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_container,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(fill='x', pady=(10, 5))
        
        # Status text
        self.status_text = tk.Label(
            progress_container,
            text="Preparing installation...",
            font=('Segoe UI', 10),
            bg=BACKGROUND,
            fg=TEXT_LIGHT
        )
        self.status_text.pack()
        
        # Log area
        tk.Label(
            self.content_frame,
            text="Installation Log:",
            font=('Segoe UI', 11, 'bold'),
            bg=BACKGROUND,
            fg=TEXT_COLOR
        ).pack(anchor='w', pady=(20, 5), padx=50)
        
        log_container = tk.Frame(self.content_frame, bg='#cccccc')
        log_container.pack(fill='both', expand=True, padx=50, pady=(0, 20))
        
        self.log_output = scrolledtext.ScrolledText(
            log_container,
            font=('Consolas', 9),
            bg=DARK_BG,
            fg='#cccccc',
            height=8,
            wrap='word'
        )
        self.log_output.pack(fill='both', expand=True, padx=1, pady=1)
        self.log_output.config(state='normal')
        
        # Start installation in background thread
        threading.Thread(target=self.run_installation, daemon=True).start()
    
    def run_installation(self):
        """Run installation in background thread"""
        try:
            def update_progress(percent, message):
                self.root.after(0, lambda: self.update_progress_ui(percent, message))
            
            def log_message(message):
                self.root.after(0, lambda: self.add_log(message))
            
            success = self.installer.install(update_progress, log_message)
            
            if success:
                # Installation successful
                self.root.after(0, self.installation_complete)
            else:
                # Installation failed
                error_msg = "Installation failed - check the log for details"
                self.root.after(0, lambda: self.installation_failed(error_msg))
            
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            logger.error(error_msg)
            self.root.after(0, lambda: self.installation_failed(error_msg))
    
    def update_progress_ui(self, percent, message):
        """Update progress UI"""
        self.progress_bar['value'] = percent
        self.progress_percent.config(text=f"{int(percent)}%")
        self.status_text.config(text=message)
        self.add_log(message)
    
    def add_log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.insert('end', f"[{timestamp}] {message}\n")
        self.log_output.see('end')
        self.log_output.update()
    
    def installation_complete(self):
        """Handle installation completion"""
        self.progress_bar['value'] = 100
        self.progress_percent.config(text="100%")
        self.status_text.config(text="Installation complete!")
        self.add_log("Installation completed successfully!")
        self.add_log(f"Application installed in: {INSTALL_DIR}")
        
        # Add Continue button
        continue_btn = tk.Button(
            self.content_frame,
            text="Continue",
            font=('Segoe UI', 12, 'bold'),
            bg=SUCCESS_COLOR,
            fg='white',
            activebackground=SUCCESS_DARK,
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            padx=30,
            pady=10,
            command=self.show_welcome_screen
        )
        continue_btn.pack(pady=10)
        
        # Show success message
        self.root.after(1000, lambda: messagebox.showinfo(
            "Installation Complete",
            f"{APP_NAME} has been installed successfully!\n\n"
            f"Location: {INSTALL_DIR}\n\n"
            "You can now launch the application."
        ))
    
    def installation_failed(self, error_msg):
        """Handle installation failure"""
        self.status_text.config(text="Installation failed!", fg=DANGER_COLOR)
        self.add_log(f"ERROR: {error_msg}")
        
        # Add retry button
        retry_btn = tk.Button(
            self.content_frame,
            text="Retry Installation",
            font=('Segoe UI', 12, 'bold'),
            bg=WARNING_COLOR,
            fg='white',
            activebackground=WARNING_DARK,
            activeforeground='white',
            relief='flat',
            cursor='hand2',
            padx=30,
            pady=10,
            command=self.show_welcome_screen
        )
        retry_btn.pack(pady=10)
        
        # Show error message
        self.root.after(500, lambda: messagebox.showerror(
            "Installation Failed",
            f"Installation failed:\n\n{error_msg}"
        ))
    
    def launch_app(self):
        """Launch the application"""
        # Try to find launcher
        launchers = [
            BASE_DIR / "run.bat",
            BASE_DIR / "run.py",
            BASE_DIR / "run.sh"
        ]
        
        for launcher in launchers:
            if launcher.exists():
                try:
                    if platform.system() == "Windows":
                        os.startfile(launcher)
                    else:
                        subprocess.Popen([str(launcher)])
                    
                    # Close installer
                    self.root.after(1000, self.root.destroy)
                    return
                except Exception as e:
                    logger.error(f"Failed to launch {launcher}: {e}")
        
        # Fallback
        app_path = INSTALL_DIR / "autoclicker.py"
        if app_path.exists():
            try:
                os.chdir(INSTALL_DIR)
                subprocess.Popen([sys.executable, "autoclicker.py"])
                self.root.after(1000, self.root.destroy)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to launch: {str(e)}")
        else:
            messagebox.showerror("Error", "Application not found!")
    
    def uninstall_app(self):
        """Uninstall application"""
        if not INSTALL_DIR.exists():
            messagebox.showinfo("Not Installed", "Application is not installed!")
            return
        
        if not messagebox.askyesno("Confirm Uninstall",
            f"Uninstall {APP_NAME}?\n\n"
            "This will remove the application but keep your settings."
        ):
            return
        
        try:
            # Remove installation
            if INSTALL_DIR.exists():
                shutil.rmtree(INSTALL_DIR, ignore_errors=True)
            
            # Remove launchers
            launchers = [
                BASE_DIR / "run.bat",
                BASE_DIR / "run.py",
                BASE_DIR / "run.sh",
                BASE_DIR / f"Start_{APP_NAME.replace(' ', '_')}.bat",
                BASE_DIR / "uninstall.py",
                BASE_DIR / "uninstall.bat"
            ]
            
            for launcher in launchers:
                launcher_path = BASE_DIR / launcher
                if launcher_path.exists():
                    launcher_path.unlink()
            
            messagebox.showinfo("Success", "Uninstall complete!")
            self.show_welcome_screen()
            
        except Exception as e:
            messagebox.showerror("Error", f"Uninstall failed: {str(e)}")
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

# ============== COMMAND LINE INTERFACE ==============
def command_line_installer():
    """Command line installer"""
    print(f"\n{APP_NAME} Installer")
    print("=" * 50)
    print()
    
    installer = SimpleInstaller()
    
    if installer.is_installed():
        print("Already installed!")
        print(f"Location: {INSTALL_DIR}")
        print()
        response = input("Reinstall? (y/N): ").strip().lower()
        if response != 'y':
            print("Exiting...")
            return
    
    print("Starting installation...")
    print(f"Installing to: {INSTALL_DIR}")
    print()
    
    try:
        def show_progress(percent, message):
            print(f"[{int(percent):3d}%] {message}")
        
        def show_log(message):
            print(f"  {message}")
        
        success = installer.install(show_progress, show_log)
        
        if success:
            print("\n" + "=" * 50)
            print("Installation complete!")
            print(f"Location: {INSTALL_DIR}")
            print()
            print("Launchers created:")
            print("  • run.bat (Windows)")
            print("  • run.py (Cross-platform)")
            print("  • run.sh (Linux/Mac)")
            print()
            print("To launch: Double-click 'run.bat' or run 'python run.py'")
        else:
            print("\nInstallation failed!")
            print("Check installer.log for details.")
            sys.exit(1)
        
    except Exception as e:
        print(f"\nInstallation failed: {str(e)}")
        sys.exit(1)

# ============== MAIN ==============
def main():
    """Main entry point"""
    print(f"{APP_NAME} Installer")
    print("=" * 50)
    
    # Check if tkinter is available
    try:
        import tkinter
    except ImportError:
        print("tkinter not installed!")
        print("Please install tkinter to use the graphical installer.")
        print("Using command-line mode instead...")
        command_line_installer()
        return
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ["--cli", "-c", "cli", "--console"]:
        command_line_installer()
        return
    
    # Launch GUI installer
    try:
        app = SimpleInstallerGUI()
        app.run()
    except Exception as e:
        print(f"GUI failed: {str(e)}")
        print("Falling back to command-line mode...")
        command_line_installer()

if __name__ == "__main__":
    main()