#!/usr/bin/env python3
"""
Autoclicker Ultimate - Windows Edition
With Firebase Key System
"""

import threading
import time
import json
import random
import os
import re
import hashlib
import uuid
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
import urllib.request
import urllib.error

from pynput.mouse import Button, Controller as MouseController, Listener as MouseListener
from pynput.keyboard import Key, Controller as KeyboardController, Listener as KeyboardListener

# Optional: System tray support
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

# ============== FIREBASE CONFIGURATION ==============
# IMPORTANT: Replace these with your Firebase project details
FIREBASE_CONFIG = {
    'project_id': 'enm-tech-34ef4',  # e.g., 'autoclicker-keys'
    'database_url': 'https://enm-tech-34ef4-default-rtdb.europe-west1.firebasedatabase.app/',  # Your Realtime Database URL
    'api_key': 'YOUR_API_KEY'  # Optional: for additional security
}

# ============== KEY SYSTEM ==============
class KeySystem:
    def __init__(self):
        self.hwid = self.get_hwid()
        self.config_path = os.path.join(os.path.expanduser('~'), '.autoclicker_license.json')
        self.saved_key = self.load_saved_key()
        
    def get_hwid(self):
        """Generate a unique hardware ID"""
        try:
            # Combine multiple system identifiers
            import platform
            system_info = f"{platform.node()}-{platform.machine()}-{platform.processor()}"
            
            # Try to get MAC address
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                          for elements in range(0, 48, 8)][::-1])
            
            combined = f"{system_info}-{mac}"
            return hashlib.sha256(combined.encode()).hexdigest()[:32]
        except:
            # Fallback
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:32]
            
    def load_saved_key(self):
        """Load saved license key from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    return data.get('key')
        except:
            pass
        return None
        
    def save_key(self, key):
        """Save license key to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump({'key': key, 'hwid': self.hwid}, f)
        except:
            pass
            
    def clear_saved_key(self):
        """Remove saved license"""
        try:
            if os.path.exists(self.config_path):
                os.remove(self.config_path)
            self.saved_key = None
        except:
            pass
            
    def firebase_request(self, path, method='GET', data=None):
        """Make a request to Firebase Realtime Database"""
        url = f"{FIREBASE_CONFIG['database_url']}/{path}.json"
        
        try:
            if data is not None:
                data = json.dumps(data).encode('utf-8')
                
            request = urllib.request.Request(url, data=data, method=method)
            request.add_header('Content-Type', 'application/json')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(f"HTTP Error: {e.code}")
            return None
        except urllib.error.URLError as e:
            print(f"URL Error: {e.reason}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
            
    def validate_key(self, key):
        """
        Validate a license key against Firebase
        Returns: (success, message)
        """
        key = key.strip().upper()
        
        if not key:
            return False, "Please enter a license key"
            
        # Check if Firebase is configured
        if 'YOUR_PROJECT_ID' in FIREBASE_CONFIG['database_url']:
            return False, "Firebase not configured. See instructions."
            
        # Get key data from Firebase
        key_data = self.firebase_request(f"keys/{key}")
        
        if key_data is None:
            return False, "Invalid license key"
            
        # Check if key is active
        if not key_data.get('active', False):
            return False, "License key has been deactivated"
            
        # Check expiration
        expires = key_data.get('expires')
        if expires:
            try:
                exp_date = datetime.fromisoformat(expires)
                if datetime.now() > exp_date:
                    return False, "License key has expired"
            except:
                pass
                
        # Check HWID binding
        bound_hwid = key_data.get('hwid')
        
        if bound_hwid:
            # Key is already bound to a device
            if bound_hwid != self.hwid:
                return False, "License key is already used on another device"
        else:
            # Bind key to this device
            update_data = {
                'hwid': self.hwid,
                'activated_at': datetime.now().isoformat(),
                'used': True
            }
            self.firebase_request(f"keys/{key}", method='PATCH', data=update_data)
            
        # Save key locally
        self.save_key(key)
        self.saved_key = key
        
        return True, "License activated successfully!"
        
    def check_saved_key(self):
        """Check if saved key is still valid"""
        if not self.saved_key:
            return False, "No saved license"
        return self.validate_key(self.saved_key)


# ============== KEY GENERATION (ADMIN) ==============
class KeyGenerator:
    @staticmethod
    def generate_key():
        """Generate a random license key"""
        import string
        chars = string.ascii_uppercase + string.digits
        parts = [''.join(random.choices(chars, k=5)) for _ in range(4)]
        return '-'.join(parts)  # Format: XXXXX-XXXXX-XXXXX-XXXXX
        
    @staticmethod
    def add_key_to_firebase(key, expires=None, note=""):
        """Add a new key to Firebase (admin function)"""
        if 'YOUR_PROJECT_ID' in FIREBASE_CONFIG['database_url']:
            return False, "Firebase not configured"
            
        key_data = {
            'active': True,
            'used': False,
            'hwid': None,
            'created_at': datetime.now().isoformat(),
            'expires': expires,
            'note': note
        }
        
        url = f"{FIREBASE_CONFIG['database_url']}/keys/{key}.json"
        
        try:
            data = json.dumps(key_data).encode('utf-8')
            request = urllib.request.Request(url, data=data, method='PUT')
            request.add_header('Content-Type', 'application/json')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                return True, "Key added successfully"
        except Exception as e:
            return False, str(e)


# ============== LOGIN WINDOW ==============
class LoginWindow:
    def __init__(self, on_success):
        self.on_success = on_success
        self.key_system = KeySystem()
        
        # Check for saved valid key
        if self.key_system.saved_key:
            success, msg = self.key_system.check_saved_key()
            if success:
                self.on_success()
                return
                
        self.create_window()
        
    def create_window(self):
        self.root = tk.Tk()
        self.root.title("Autoclicker Ultimate - Activation")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        self.root.configure(bg='#1e1e1e')
        
        # Center window
        self.root.eval('tk::PlaceWindow . center')
        
        # Header
        header = tk.Frame(self.root, bg='#0078d4', height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(
            header, text="⚡ AUTOCLICKER ULTIMATE",
            font=('Segoe UI', 14, 'bold'),
            fg='#ffffff', bg='#0078d4'
        ).pack(pady=15)
        
        # Main content
        main = tk.Frame(self.root, bg='#1e1e1e', padx=40, pady=20)
        main.pack(fill='both', expand=True)
        
        tk.Label(
            main, text="Enter your license key to activate",
            font=('Segoe UI', 11),
            fg='#888888', bg='#1e1e1e'
        ).pack(pady=(10, 20))
        
        # Key entry
        self.key_var = tk.StringVar()
        self.key_entry = tk.Entry(
            main, textvariable=self.key_var,
            font=('Consolas', 12),
            bg='#2d2d2d', fg='#ffffff',
            insertbackground='#ffffff',
            relief='flat',
            justify='center',
            width=30
        )
        self.key_entry.pack(ipady=10)
        self.key_entry.bind('<Return>', lambda e: self.activate())
        
        # Status label
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            main, textvariable=self.status_var,
            font=('Segoe UI', 10),
            fg='#f44336', bg='#1e1e1e'
        )
        self.status_label.pack(pady=10)
        
        # Activate button
        self.activate_btn = tk.Button(
            main, text="ACTIVATE",
            font=('Segoe UI', 11, 'bold'),
            bg='#0078d4', fg='#ffffff',
            activebackground='#1a86d9',
            relief='flat',
            cursor='hand2',
            command=self.activate,
            width=20
        )
        self.activate_btn.pack(pady=10, ipady=8)
        
        # HWID display
        tk.Label(
            main, text=f"HWID: {self.key_system.hwid[:16]}...",
            font=('Segoe UI', 8),
            fg='#555555', bg='#1e1e1e'
        ).pack(pady=(20, 0))
        
        self.root.mainloop()
        
    def activate(self):
        key = self.key_var.get().strip()
        
        self.activate_btn.config(state='disabled', text='Checking...')
        self.status_var.set("")
        self.root.update()
        
        success, message = self.key_system.validate_key(key)
        
        if success:
            self.status_label.config(fg='#4ec959')
            self.status_var.set("✓ " + message)
            self.root.update()
            time.sleep(1)
            self.root.destroy()
            self.on_success()
        else:
            self.status_label.config(fg='#f44336')
            self.status_var.set("✗ " + message)
            self.activate_btn.config(state='normal', text='ACTIVATE')


# ============== CONFIGURATION ==============
DEFAULT_CONFIG = {
    'theme': 'dark',
    'hotkey_autoclicker': 'Key.f6',
    'hotkey_record': 'Key.f7',
    'hotkey_playback': 'Key.f8',
    'hotkey_hold': 'Key.f9',
    'hotkey_macro_record': 'Key.f10',
    'hotkey_macro_play': 'Key.f11',
    'always_on_top': False,
    'minimize_to_tray': True,
    'start_delay': 0,
    'interval': 0.1,
    'interval_random_min': 0.05,
    'interval_random_max': 0.15,
    'use_random_interval': False,
    'click_button': 'left',
    'click_type': 'single',
    'use_fixed_position': False,
    'fixed_x': 0,
    'fixed_y': 0,
    'click_limit': 0,
    'record_movements': False,
    'record_keyboard': False,
    'playback_repeat': 1,
    'playback_speed': 1.0,
    'playback_loop': False
}

THEMES = {
    'dark': {
        'bg': '#1e1e1e',
        'bg_light': '#2d2d2d',
        'bg_input': '#3c3c3c',
        'border': '#404040',
        'text': '#ffffff',
        'text_dim': '#888888',
        'accent': '#0078d4',
        'accent_hover': '#1a86d9',
        'success': '#4ec959',
        'warning': '#f9a825',
        'danger': '#f44336',
        'purple': '#9c27b0'
    },
    'light': {
        'bg': '#f0f0f0',
        'bg_light': '#ffffff',
        'bg_input': '#ffffff',
        'border': '#cccccc',
        'text': '#1e1e1e',
        'text_dim': '#666666',
        'accent': '#0078d4',
        'accent_hover': '#1a86d9',
        'success': '#2e7d32',
        'warning': '#f57c00',
        'danger': '#c62828',
        'purple': '#7b1fa2'
    }
}


# ============== MAIN APPLICATION ==============
class Autoclicker:
    def __init__(self):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        
        # States
        self.clicking = False
        self.recording = False
        self.playing = False
        self.hold_mode_active = False
        self.hold_key_pressed = False
        self.macro_recording = False
        self.macro_playing = False
        
        # Data
        self.recorded_actions = []
        self.record_start_time = 0
        self.profiles = {}
        self.macro_actions = []
        self.macro_start_time = 0
        self.saved_macros = {}
        
        # Statistics
        self.stats = {
            'total_clicks': 0,
            'session_clicks': 0,
            'session_start': None,
            'total_recordings_played': 0,
            'total_macros_played': 0
        }
        
        # Config
        self.config = DEFAULT_CONFIG.copy()
        self.load_config()
        self.colors = THEMES[self.config['theme']]
        
        self.setup_gui()
        self.setup_hotkeys()
        self.load_profiles()
        self.load_saved_macros()
        
        # System tray
        self.tray_icon = None
        if HAS_TRAY and self.config['minimize_to_tray']:
            self.setup_tray()
            
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Autoclicker Ultimate")
        self.root.geometry("520x650")
        self.root.resizable(False, False)
        self.root.configure(bg=self.colors['bg'])
        
        if self.config['always_on_top']:
            self.root.attributes('-topmost', True)
            
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Notebook style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        style.configure('TNotebook.Tab',
                       background=self.colors['bg_light'],
                       foreground=self.colors['text'],
                       padding=[10, 5],
                       font=('Segoe UI', 9))
        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['accent'])],
                 foreground=[('selected', '#ffffff')])
        
        # Header
        header = tk.Frame(self.root, bg=self.colors['accent'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(
            header, text="⚡ AUTOCLICKER ULTIMATE",
            font=('Segoe UI', 14, 'bold'),
            fg='#ffffff', bg=self.colors['accent']
        ).pack(side='left', padx=15, pady=12)
        
        self.header_status = tk.Label(
            header, text="● Idle",
            font=('Segoe UI', 10),
            fg='#ffffff', bg=self.colors['accent']
        )
        self.header_status.pack(side='right', padx=15)
        
        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_autoclicker_tab()
        self.create_recorder_tab()
        self.create_macro_tab()
        self.create_settings_tab()
        self.create_stats_tab()
        
    def create_checkbox(self, parent, text, var, command=None):
        cb = tk.Checkbutton(
            parent, text=text,
            variable=var,
            font=('Segoe UI', 10),
            fg=self.colors['text'],
            bg=self.colors['bg_light'],
            selectcolor=self.colors['bg_input'],
            activebackground=self.colors['bg_light'],
            activeforeground=self.colors['text'],
            command=command
        )
        cb.pack(anchor='w', pady=2)
        return cb
        
    def create_button(self, parent, text, command, style='default', width=15):
        colors = {
            'default': (self.colors['bg_input'], self.colors['text']),
            'primary': (self.colors['accent'], '#ffffff'),
            'success': (self.colors['success'], '#ffffff'),
            'danger': (self.colors['danger'], '#ffffff'),
            'warning': (self.colors['warning'], '#000000'),
            'purple': (self.colors['purple'], '#ffffff')
        }
        bg, fg = colors.get(style, colors['default'])
        
        btn = tk.Button(
            parent, text=text,
            font=('Segoe UI', 10, 'bold'),
            bg=bg, fg=fg,
            activebackground=self.colors['accent_hover'],
            activeforeground='#ffffff',
            relief='flat',
            cursor='hand2',
            command=command,
            width=width
        )
        return btn

    # ============== AUTOCLICKER TAB ==============
    def create_autoclicker_tab(self):
        tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(tab, text=" Autoclicker ")
        
        card = tk.Frame(tab, bg=self.colors['bg_light'], padx=20, pady=15)
        card.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Interval section
        tk.Label(card, text="CLICK INTERVAL", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        interval_frame = tk.Frame(card, bg=self.colors['bg_light'])
        interval_frame.pack(fill='x', pady=5)
        
        self.interval_var = tk.StringVar(value=str(self.config['interval']))
        tk.Label(interval_frame, text="Interval:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left')
        tk.Entry(interval_frame, textvariable=self.interval_var, width=8,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', padx=5, ipady=3)
        tk.Label(interval_frame, text="seconds", font=('Segoe UI', 10),
                fg=self.colors['text_dim'], bg=self.colors['bg_light']).pack(side='left')
        
        # Random interval
        self.use_random_var = tk.BooleanVar(value=self.config['use_random_interval'])
        self.create_checkbox(card, "Use random interval", self.use_random_var, self.toggle_random_interval)
        
        self.random_frame = tk.Frame(card, bg=self.colors['bg_light'])
        self.random_frame.pack(fill='x', pady=5)
        
        self.random_min_var = tk.StringVar(value=str(self.config['interval_random_min']))
        self.random_max_var = tk.StringVar(value=str(self.config['interval_random_max']))
        
        tk.Label(self.random_frame, text="Min:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left')
        tk.Entry(self.random_frame, textvariable=self.random_min_var, width=6,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', padx=5, ipady=3)
        tk.Label(self.random_frame, text="Max:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left', padx=(10, 0))
        tk.Entry(self.random_frame, textvariable=self.random_max_var, width=6,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', padx=5, ipady=3)
        self.toggle_random_interval()
        
        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill='x', pady=10)
        
        # Click Options
        tk.Label(card, text="CLICK OPTIONS", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        btn_frame = tk.Frame(card, bg=self.colors['bg_light'])
        btn_frame.pack(fill='x', pady=5)
        
        tk.Label(btn_frame, text="Button:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left')
        
        self.button_var = tk.StringVar(value=self.config['click_button'])
        for btn in ['left', 'right', 'middle']:
            rb = tk.Radiobutton(btn_frame, text=btn.capitalize(), variable=self.button_var, value=btn,
                               font=('Segoe UI', 10), fg=self.colors['text'], bg=self.colors['bg_light'],
                               selectcolor=self.colors['bg_input'], activebackground=self.colors['bg_light'])
            rb.pack(side='left', padx=5)
            
        type_frame = tk.Frame(card, bg=self.colors['bg_light'])
        type_frame.pack(fill='x', pady=5)
        
        tk.Label(type_frame, text="Type:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left')
        
        self.click_type_var = tk.StringVar(value=self.config['click_type'])
        for ctype in ['single', 'double', 'triple']:
            rb = tk.Radiobutton(type_frame, text=ctype.capitalize(), variable=self.click_type_var, value=ctype,
                               font=('Segoe UI', 10), fg=self.colors['text'], bg=self.colors['bg_light'],
                               selectcolor=self.colors['bg_input'], activebackground=self.colors['bg_light'])
            rb.pack(side='left', padx=5)
            
        limit_frame = tk.Frame(card, bg=self.colors['bg_light'])
        limit_frame.pack(fill='x', pady=5)
        
        self.click_limit_var = tk.StringVar(value=str(self.config['click_limit']))
        tk.Label(limit_frame, text="Click limit (0=infinite):", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left')
        tk.Entry(limit_frame, textvariable=self.click_limit_var, width=8,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='right', ipady=3)
        
        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill='x', pady=10)
        
        # Position
        tk.Label(card, text="CLICK POSITION", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        self.use_fixed_pos_var = tk.BooleanVar(value=self.config['use_fixed_position'])
        self.create_checkbox(card, "Click at fixed position", self.use_fixed_pos_var, self.toggle_fixed_pos)
        
        self.pos_frame = tk.Frame(card, bg=self.colors['bg_light'])
        self.pos_frame.pack(fill='x', pady=5)
        
        self.fixed_x_var = tk.StringVar(value=str(self.config['fixed_x']))
        self.fixed_y_var = tk.StringVar(value=str(self.config['fixed_y']))
        
        tk.Label(self.pos_frame, text="X:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left')
        tk.Entry(self.pos_frame, textvariable=self.fixed_x_var, width=6,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', padx=5, ipady=3)
        tk.Label(self.pos_frame, text="Y:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left', padx=(10, 0))
        tk.Entry(self.pos_frame, textvariable=self.fixed_y_var, width=6,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', padx=5, ipady=3)
        
        self.pick_pos_btn = self.create_button(self.pos_frame, "Pick", self.pick_position, 'default', 6)
        self.pick_pos_btn.pack(side='right', ipady=2)
        self.toggle_fixed_pos()
        
        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill='x', pady=10)
        
        # Options
        options_frame = tk.Frame(card, bg=self.colors['bg_light'])
        options_frame.pack(fill='x')
        
        self.hold_mode_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Hold mode (F9)", variable=self.hold_mode_var,
                      font=('Segoe UI', 10), fg=self.colors['text'], bg=self.colors['bg_light'],
                      selectcolor=self.colors['bg_input']).pack(side='left')
        
        tk.Label(options_frame, text="Delay:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left', padx=(20, 5))
        self.start_delay_var = tk.StringVar(value=str(self.config['start_delay']))
        tk.Entry(options_frame, textvariable=self.start_delay_var, width=4,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', ipady=3)
        tk.Label(options_frame, text="s", font=('Segoe UI', 10),
                fg=self.colors['text_dim'], bg=self.colors['bg_light']).pack(side='left')
        
        # Status
        status_frame = tk.Frame(card, bg=self.colors['bg_light'])
        status_frame.pack(fill='x', pady=(10, 5))
        
        self.auto_status_dot = tk.Label(status_frame, text="●", font=('Segoe UI', 16),
                                        fg=self.colors['text_dim'], bg=self.colors['bg_light'])
        self.auto_status_dot.pack(side='left')
        
        self.auto_status_var = tk.StringVar(value="Stopped")
        tk.Label(status_frame, textvariable=self.auto_status_var, font=('Segoe UI', 12, 'bold'),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left', padx=10)
        
        self.session_clicks_var = tk.StringVar(value="0 clicks")
        tk.Label(status_frame, textvariable=self.session_clicks_var, font=('Segoe UI', 10),
                fg=self.colors['text_dim'], bg=self.colors['bg_light']).pack(side='right')
        
        self.auto_toggle_btn = self.create_button(card, "▶ START (F6)", self.toggle_autoclicker, 'success', 20)
        self.auto_toggle_btn.pack(pady=8, ipady=6)
        
    def toggle_random_interval(self):
        state = 'normal' if self.use_random_var.get() else 'disabled'
        for child in self.random_frame.winfo_children():
            if isinstance(child, tk.Entry):
                child.config(state=state)
                
    def toggle_fixed_pos(self):
        state = 'normal' if self.use_fixed_pos_var.get() else 'disabled'
        for child in self.pos_frame.winfo_children():
            if isinstance(child, (tk.Entry, tk.Button)):
                child.config(state=state)
                
    def pick_position(self):
        self.root.iconify()
        time.sleep(0.3)
        messagebox.showinfo("Pick Position", "Click anywhere in 3 seconds...")
        def capture():
            time.sleep(3)
            x, y = self.mouse.position
            self.fixed_x_var.set(str(int(x)))
            self.fixed_y_var.set(str(int(y)))
            self.root.after(0, self.root.deiconify)
        threading.Thread(target=capture, daemon=True).start()

    # ============== RECORDER TAB ==============
    def create_recorder_tab(self):
        tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(tab, text=" Recorder ")
        
        card = tk.Frame(tab, bg=self.colors['bg_light'], padx=20, pady=15)
        card.pack(fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(card, text="RECORDING OPTIONS", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        self.record_movements_var = tk.BooleanVar(value=self.config['record_movements'])
        self.create_checkbox(card, "Record mouse movements", self.record_movements_var)
        
        self.record_keyboard_var = tk.BooleanVar(value=self.config['record_keyboard'])
        self.create_checkbox(card, "Record keyboard presses", self.record_keyboard_var)
        
        rec_status = tk.Frame(card, bg=self.colors['bg_light'])
        rec_status.pack(fill='x', pady=10)
        
        self.rec_status_dot = tk.Label(rec_status, text="●", font=('Segoe UI', 14),
                                       fg=self.colors['text_dim'], bg=self.colors['bg_light'])
        self.rec_status_dot.pack(side='left')
        
        self.record_status_var = tk.StringVar(value="Ready to record")
        tk.Label(rec_status, textvariable=self.record_status_var, font=('Segoe UI', 11),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left', padx=8)
        
        self.actions_var = tk.StringVar(value="0 actions")
        tk.Label(rec_status, textvariable=self.actions_var, font=('Segoe UI', 10),
                fg=self.colors['text_dim'], bg=self.colors['bg_light']).pack(side='right')
        
        rec_btns = tk.Frame(card, bg=self.colors['bg_light'])
        rec_btns.pack(fill='x', pady=5)
        
        self.record_btn = self.create_button(rec_btns, "⏺ RECORD (F7)", self.toggle_recording, 'danger', 14)
        self.record_btn.pack(side='left', ipady=5)
        self.create_button(rec_btns, "Clear", self.clear_recording, 'default', 7).pack(side='left', padx=10, ipady=5)
        
        delay_add = tk.Frame(card, bg=self.colors['bg_light'])
        delay_add.pack(fill='x', pady=8)
        
        self.manual_delay_var = tk.StringVar(value="1.0")
        tk.Label(delay_add, text="Add delay:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left')
        tk.Entry(delay_add, textvariable=self.manual_delay_var, width=5,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', padx=5, ipady=3)
        tk.Label(delay_add, text="s", font=('Segoe UI', 10),
                fg=self.colors['text_dim'], bg=self.colors['bg_light']).pack(side='left')
        self.create_button(delay_add, "+", self.add_manual_delay, 'default', 3).pack(side='left', padx=8, ipady=2)
        
        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill='x', pady=10)
        
        tk.Label(card, text="PLAYBACK OPTIONS", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        opt_frame = tk.Frame(card, bg=self.colors['bg_light'])
        opt_frame.pack(fill='x', pady=5)
        
        self.speed_var = tk.StringVar(value=str(self.config['playback_speed']))
        tk.Label(opt_frame, text="Speed:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left')
        tk.Entry(opt_frame, textvariable=self.speed_var, width=5,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', padx=5, ipady=3)
        tk.Label(opt_frame, text="×", font=('Segoe UI', 10),
                fg=self.colors['text_dim'], bg=self.colors['bg_light']).pack(side='left')
        
        self.repeat_var = tk.StringVar(value=str(self.config['playback_repeat']))
        tk.Label(opt_frame, text="Repeat:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left', padx=(15, 0))
        tk.Entry(opt_frame, textvariable=self.repeat_var, width=5,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', padx=5, ipady=3)
        
        self.loop_var = tk.BooleanVar(value=self.config['playback_loop'])
        tk.Checkbutton(opt_frame, text="Loop", variable=self.loop_var,
                      font=('Segoe UI', 10), fg=self.colors['text'],
                      bg=self.colors['bg_light'], selectcolor=self.colors['bg_input']).pack(side='left', padx=15)
        
        play_status = tk.Frame(card, bg=self.colors['bg_light'])
        play_status.pack(fill='x', pady=8)
        
        self.play_status_dot = tk.Label(play_status, text="●", font=('Segoe UI', 14),
                                        fg=self.colors['text_dim'], bg=self.colors['bg_light'])
        self.play_status_dot.pack(side='left')
        
        self.play_status_var = tk.StringVar(value="Stopped")
        tk.Label(play_status, textvariable=self.play_status_var, font=('Segoe UI', 11),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left', padx=8)
        
        self.play_progress_var = tk.StringVar(value="")
        tk.Label(play_status, textvariable=self.play_progress_var, font=('Segoe UI', 10),
                fg=self.colors['text_dim'], bg=self.colors['bg_light']).pack(side='right')
        
        self.play_btn = self.create_button(card, "▶ PLAY (F8)", self.toggle_playback, 'success', 14)
        self.play_btn.pack(anchor='w', ipady=5)
        
        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill='x', pady=10)
        
        file_frame = tk.Frame(card, bg=self.colors['bg_light'])
        file_frame.pack(fill='x')
        
        self.create_button(file_frame, "💾 Save", self.save_recording, 'default', 9).pack(side='left', ipady=4)
        self.create_button(file_frame, "📂 Load", self.load_recording, 'default', 9).pack(side='left', padx=10, ipady=4)
        
    def add_manual_delay(self):
        try:
            delay = float(self.manual_delay_var.get())
            if delay > 0:
                self.recorded_actions.append({'type': 'delay', 'time': delay})
                self.update_actions_count()
        except ValueError:
            pass

    # ============== MACRO TAB ==============
    def create_macro_tab(self):
        tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(tab, text=" Keyboard Macro ")
        
        card = tk.Frame(tab, bg=self.colors['bg_light'], padx=20, pady=15)
        card.pack(fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(card, text="KEYBOARD MACRO RECORDER", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['purple'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        macro_status = tk.Frame(card, bg=self.colors['bg_light'])
        macro_status.pack(fill='x', pady=5)
        
        self.macro_status_dot = tk.Label(macro_status, text="●", font=('Segoe UI', 14),
                                         fg=self.colors['text_dim'], bg=self.colors['bg_light'])
        self.macro_status_dot.pack(side='left')
        
        self.macro_status_var = tk.StringVar(value="Ready")
        tk.Label(macro_status, textvariable=self.macro_status_var, font=('Segoe UI', 11),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left', padx=8)
        
        self.macro_count_var = tk.StringVar(value="0 keys")
        tk.Label(macro_status, textvariable=self.macro_count_var, font=('Segoe UI', 10),
                fg=self.colors['text_dim'], bg=self.colors['bg_light']).pack(side='right')
        
        macro_btns = tk.Frame(card, bg=self.colors['bg_light'])
        macro_btns.pack(fill='x', pady=8)
        
        self.macro_record_btn = self.create_button(macro_btns, "⏺ RECORD (F10)", self.toggle_macro_recording, 'purple', 14)
        self.macro_record_btn.pack(side='left', ipady=5)
        
        self.macro_play_btn = self.create_button(macro_btns, "▶ PLAY (F11)", self.toggle_macro_playback, 'success', 12)
        self.macro_play_btn.pack(side='left', padx=10, ipady=5)
        
        self.create_button(macro_btns, "Clear", self.clear_macro, 'default', 7).pack(side='left', ipady=5)
        
        opt_frame = tk.Frame(card, bg=self.colors['bg_light'])
        opt_frame.pack(fill='x', pady=8)
        
        self.macro_speed_var = tk.StringVar(value="1.0")
        tk.Label(opt_frame, text="Speed:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left')
        tk.Entry(opt_frame, textvariable=self.macro_speed_var, width=5,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', padx=5, ipady=3)
        
        self.macro_repeat_var = tk.StringVar(value="1")
        tk.Label(opt_frame, text="Repeat:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left', padx=(15, 0))
        tk.Entry(opt_frame, textvariable=self.macro_repeat_var, width=5,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', padx=5, ipady=3)
        
        self.macro_loop_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_frame, text="Loop", variable=self.macro_loop_var,
                      font=('Segoe UI', 10), fg=self.colors['text'],
                      bg=self.colors['bg_light'], selectcolor=self.colors['bg_input']).pack(side='left', padx=15)
        
        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill='x', pady=10)
        
        tk.Label(card, text="MACRO EDITOR", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['purple'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        tk.Label(card, text="Commands: key(a), combo(ctrl+c), type(Hello), wait(0.5)",
                font=('Segoe UI', 9), fg=self.colors['text_dim'], bg=self.colors['bg_light']).pack(anchor='w')
        
        self.macro_editor = scrolledtext.ScrolledText(card, height=5, width=50,
                                                      font=('Consolas', 10), bg=self.colors['bg_input'],
                                                      fg=self.colors['text'], insertbackground=self.colors['text'], relief='flat')
        self.macro_editor.pack(fill='x', pady=5)
        
        editor_btns = tk.Frame(card, bg=self.colors['bg_light'])
        editor_btns.pack(fill='x', pady=5)
        
        self.create_button(editor_btns, "▶ Run Script", self.run_macro_script, 'success', 12).pack(side='left', ipady=4)
        self.create_button(editor_btns, "Import Recorded", self.import_recorded_to_editor, 'default', 13).pack(side='left', padx=10, ipady=4)
        
        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill='x', pady=10)
        
        tk.Label(card, text="SAVED MACROS", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['purple'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 5))
        
        save_frame = tk.Frame(card, bg=self.colors['bg_light'])
        save_frame.pack(fill='x', pady=5)
        
        self.macro_name_var = tk.StringVar()
        tk.Entry(save_frame, textvariable=self.macro_name_var, width=12,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', ipady=3)
        
        self.create_button(save_frame, "Save", self.save_macro, 'primary', 6).pack(side='left', padx=8, ipady=3)
        
        self.macro_list_var = tk.StringVar()
        self.macro_combo = ttk.Combobox(save_frame, textvariable=self.macro_list_var,
                                        values=list(self.saved_macros.keys()), state='readonly', width=10)
        self.macro_combo.pack(side='left', padx=(10, 0))
        
        self.create_button(save_frame, "Load", self.load_macro, 'default', 5).pack(side='left', padx=5, ipady=3)
        self.create_button(save_frame, "Del", self.delete_macro, 'danger', 4).pack(side='left', ipady=3)

    # ============== SETTINGS TAB ==============
    def create_settings_tab(self):
        tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(tab, text=" Settings ")
        
        canvas = tk.Canvas(tab, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient='vertical', command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=self.colors['bg'])
        
        scrollable.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scrollable, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        canvas.bind_all('<MouseWheel>', on_mousewheel)
        
        card = tk.Frame(scrollable, bg=self.colors['bg_light'], padx=20, pady=15)
        card.pack(fill='x', padx=10, pady=10)
        
        # Hotkeys
        tk.Label(card, text="HOTKEYS", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 10))
        
        self.hotkey_vars = {
            'autoclicker': tk.StringVar(value=self.config['hotkey_autoclicker']),
            'record': tk.StringVar(value=self.config['hotkey_record']),
            'playback': tk.StringVar(value=self.config['hotkey_playback']),
            'hold': tk.StringVar(value=self.config['hotkey_hold']),
            'macro_record': tk.StringVar(value=self.config['hotkey_macro_record']),
            'macro_play': tk.StringVar(value=self.config['hotkey_macro_play'])
        }
        
        self.hotkey_buttons = {}
        for name, label in [('autoclicker', 'Autoclicker'), ('record', 'Record Mouse'),
                           ('playback', 'Playback'), ('hold', 'Hold-to-click'),
                           ('macro_record', 'Record Macro'), ('macro_play', 'Play Macro')]:
            row = tk.Frame(card, bg=self.colors['bg_light'])
            row.pack(fill='x', pady=4)
            tk.Label(row, text=label, font=('Segoe UI', 10), fg=self.colors['text'],
                    bg=self.colors['bg_light'], width=14, anchor='w').pack(side='left')
            btn = tk.Button(row, text=self.format_key(self.hotkey_vars[name].get()),
                           font=('Segoe UI', 10), bg=self.colors['bg_input'], fg=self.colors['text'],
                           relief='flat', width=10, cursor='hand2', command=lambda n=name: self.capture_hotkey(n))
            btn.pack(side='right', ipady=2)
            self.hotkey_buttons[name] = btn
            
        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill='x', pady=15)
        
        # Appearance
        tk.Label(card, text="APPEARANCE", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 10))
        
        theme_frame = tk.Frame(card, bg=self.colors['bg_light'])
        theme_frame.pack(fill='x', pady=5)
        
        tk.Label(theme_frame, text="Theme:", font=('Segoe UI', 10),
                fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left')
        
        self.theme_var = tk.StringVar(value=self.config['theme'])
        for theme in ['dark', 'light']:
            rb = tk.Radiobutton(theme_frame, text=theme.capitalize(), variable=self.theme_var, value=theme,
                               font=('Segoe UI', 10), fg=self.colors['text'], bg=self.colors['bg_light'],
                               selectcolor=self.colors['bg_input'], command=self.change_theme)
            rb.pack(side='left', padx=10)
            
        self.always_on_top_var = tk.BooleanVar(value=self.config['always_on_top'])
        self.create_checkbox(card, "Always on top", self.always_on_top_var, self.toggle_always_on_top)
        
        if HAS_TRAY:
            self.minimize_tray_var = tk.BooleanVar(value=self.config['minimize_to_tray'])
            self.create_checkbox(card, "Minimize to system tray", self.minimize_tray_var)
            
        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill='x', pady=15)
        
        # License
        tk.Label(card, text="LICENSE", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 10))
        
        key_system = KeySystem()
        tk.Label(card, text=f"Key: {key_system.saved_key or 'Not activated'}",
                font=('Segoe UI', 10), fg=self.colors['text'], bg=self.colors['bg_light']).pack(anchor='w')
        tk.Label(card, text=f"HWID: {key_system.hwid[:20]}...",
                font=('Segoe UI', 9), fg=self.colors['text_dim'], bg=self.colors['bg_light']).pack(anchor='w')
        
        self.create_button(card, "Deactivate License", self.deactivate_license, 'danger', 16).pack(anchor='w', pady=10, ipady=4)
        
        tk.Frame(card, bg=self.colors['border'], height=1).pack(fill='x', pady=15)
        
        # Profiles
        tk.Label(card, text="PROFILES", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 10))
        
        profile_frame = tk.Frame(card, bg=self.colors['bg_light'])
        profile_frame.pack(fill='x', pady=5)
        
        self.profile_var = tk.StringVar(value="default")
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var,
                                          values=list(self.profiles.keys()) if self.profiles else ['default'],
                                          state='readonly', width=12)
        self.profile_combo.pack(side='left')
        
        self.create_button(profile_frame, "Load", self.load_profile, 'default', 6).pack(side='left', padx=5, ipady=2)
        self.create_button(profile_frame, "Save", self.save_profile, 'default', 6).pack(side='left', ipady=2)
        self.create_button(profile_frame, "Del", self.delete_profile, 'danger', 4).pack(side='left', padx=5, ipady=2)
        
        new_profile = tk.Frame(card, bg=self.colors['bg_light'])
        new_profile.pack(fill='x', pady=5)
        
        self.new_profile_var = tk.StringVar()
        tk.Entry(new_profile, textvariable=self.new_profile_var, width=12,
                font=('Segoe UI', 10), bg=self.colors['bg_input'],
                fg=self.colors['text'], relief='flat').pack(side='left', ipady=3)
        self.create_button(new_profile, "Create", self.create_profile, 'primary', 8).pack(side='left', padx=10, ipady=2)
        
    def deactivate_license(self):
        if messagebox.askyesno("Deactivate", "Remove license from this device?\nYou'll need to re-enter your key."):
            KeySystem().clear_saved_key()
            messagebox.showinfo("Done", "License removed. Restart the app.")
            self.root.destroy()

    # ============== STATS TAB ==============
    def create_stats_tab(self):
        tab = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(tab, text=" Stats ")
        
        card = tk.Frame(tab, bg=self.colors['bg_light'], padx=20, pady=20)
        card.pack(fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(card, text="SESSION STATISTICS", font=('Segoe UI', 9, 'bold'),
                fg=self.colors['accent'], bg=self.colors['bg_light']).pack(anchor='w', pady=(0, 15))
        
        self.stat_labels = {}
        for stat_id, label in [('session_clicks', 'Session Clicks'), ('total_clicks', 'Total Clicks'),
                               ('session_time', 'Session Duration'), ('recordings_played', 'Recordings Played'),
                               ('macros_played', 'Macros Played')]:
            row = tk.Frame(card, bg=self.colors['bg_light'])
            row.pack(fill='x', pady=8)
            tk.Label(row, text=label, font=('Segoe UI', 11), fg=self.colors['text'], bg=self.colors['bg_light']).pack(side='left')
            val_label = tk.Label(row, text="0", font=('Segoe UI', 11, 'bold'), fg=self.colors['accent'], bg=self.colors['bg_light'])
            val_label.pack(side='right')
            self.stat_labels[stat_id] = val_label
            
        self.create_button(card, "Reset Session", self.reset_session_stats, 'danger', 15).pack(pady=20, ipady=5)
        self.update_stats_display()
        
    def update_stats_display(self):
        self.stat_labels['session_clicks'].config(text=str(self.stats['session_clicks']))
        self.stat_labels['total_clicks'].config(text=str(self.stats['total_clicks']))
        self.stat_labels['recordings_played'].config(text=str(self.stats['total_recordings_played']))
        self.stat_labels['macros_played'].config(text=str(self.stats['total_macros_played']))
        
        if self.stats['session_start']:
            elapsed = time.time() - self.stats['session_start']
            hours, rem = divmod(int(elapsed), 3600)
            mins, secs = divmod(rem, 60)
            self.stat_labels['session_time'].config(text=f"{hours:02d}:{mins:02d}:{secs:02d}")
        self.root.after(1000, self.update_stats_display)
        
    def reset_session_stats(self):
        self.stats['session_clicks'] = 0
        self.stats['session_start'] = time.time()
        self.stats['total_recordings_played'] = 0
        self.stats['total_macros_played'] = 0

    # ============== HOTKEY HANDLING ==============
    def setup_hotkeys(self):
        self.update_hotkeys()
        
    def update_hotkeys(self):
        if hasattr(self, 'hotkey_listener'):
            self.hotkey_listener.stop()
            
        def on_press(key):
            key_str = str(key).replace("'", "")
            if self.hold_mode_var.get() and key_str == self.hotkey_vars['hold'].get():
                if not self.hold_key_pressed:
                    self.hold_key_pressed = True
                    self.root.after(0, self.start_hold_clicking)
            elif key_str == self.hotkey_vars['autoclicker'].get():
                self.root.after(0, self.toggle_autoclicker)
            elif key_str == self.hotkey_vars['record'].get():
                self.root.after(0, self.toggle_recording)
            elif key_str == self.hotkey_vars['playback'].get():
                self.root.after(0, self.toggle_playback)
            elif key_str == self.hotkey_vars['macro_record'].get():
                self.root.after(0, self.toggle_macro_recording)
            elif key_str == self.hotkey_vars['macro_play'].get():
                self.root.after(0, self.toggle_macro_playback)
                
        def on_release(key):
            key_str = str(key).replace("'", "")
            if self.hold_mode_var.get() and key_str == self.hotkey_vars['hold'].get():
                self.hold_key_pressed = False
                self.root.after(0, self.stop_hold_clicking)
                
        self.hotkey_listener = KeyboardListener(on_press=on_press, on_release=on_release)
        self.hotkey_listener.daemon = True
        self.hotkey_listener.start()
        
        if hasattr(self, 'auto_toggle_btn'):
            key = self.format_key(self.hotkey_vars['autoclicker'].get())
            self.auto_toggle_btn.config(text=f"▶ START ({key})")
            
    def format_key(self, key):
        return key.replace('Key.', '').upper() if key.startswith('Key.') else key.upper()
        
    def capture_hotkey(self, name):
        btn = self.hotkey_buttons[name]
        btn.config(text="Press...", bg=self.colors['accent'])
        def on_press(key):
            key_str = str(key).replace("'", "")
            self.hotkey_vars[name].set(key_str)
            self.root.after(0, lambda: btn.config(text=self.format_key(key_str), bg=self.colors['bg_input']))
            self.update_hotkeys()
            return False
        KeyboardListener(on_press=on_press).start()
        
    def toggle_always_on_top(self):
        self.root.attributes('-topmost', self.always_on_top_var.get())
        
    def change_theme(self):
        messagebox.showinfo("Theme", "Restart to apply.")
        self.config['theme'] = self.theme_var.get()
        self.save_config()
        
    def start_hold_clicking(self):
        if self.clicking: return
        self.clicking = True
        self.update_status("Hold clicking...", self.colors['warning'])
        threading.Thread(target=self._autoclicker_loop, daemon=True).start()
        
    def stop_hold_clicking(self):
        self.clicking = False
        self.update_status("Idle", self.colors['text_dim'])

    # ============== AUTOCLICKER LOGIC ==============
    def toggle_autoclicker(self):
        if self.hold_mode_var.get(): return
        if self.clicking: self.stop_autoclicker()
        else: self.start_autoclicker()
            
    def start_autoclicker(self):
        try: self.interval = max(0.001, float(self.interval_var.get()))
        except: self.interval = 0.1
        try: self.click_limit = int(self.click_limit_var.get())
        except: self.click_limit = 0
        try: self.start_delay = float(self.start_delay_var.get())
        except: self.start_delay = 0
            
        button_map = {"left": Button.left, "right": Button.right, "middle": Button.middle}
        self.click_button = button_map.get(self.button_var.get(), Button.left)
        self.clicks_per_action = {"single": 1, "double": 2, "triple": 3}.get(self.click_type_var.get(), 1)
        
        self.use_fixed_position = self.use_fixed_pos_var.get()
        try: self.fixed_pos = (int(self.fixed_x_var.get()), int(self.fixed_y_var.get()))
        except: self.fixed_pos = (0, 0)
            
        self.use_random = self.use_random_var.get()
        try: self.random_min, self.random_max = float(self.random_min_var.get()), float(self.random_max_var.get())
        except: self.random_min, self.random_max = 0.05, 0.15
            
        self.clicking = True
        self.stats['session_clicks'] = 0
        if not self.stats['session_start']: self.stats['session_start'] = time.time()
            
        key = self.format_key(self.hotkey_vars['autoclicker'].get())
        self.auto_toggle_btn.config(text=f"⏹ STOP ({key})", bg=self.colors['danger'])
        self.update_status("Running", self.colors['success'])
        self.auto_status_dot.config(fg=self.colors['success'])
        self.auto_status_var.set("Running")
        
        threading.Thread(target=self._autoclicker_with_delay, daemon=True).start()
        
    def _autoclicker_with_delay(self):
        if self.start_delay > 0:
            self.auto_status_var.set(f"Starting in {self.start_delay}s...")
            time.sleep(self.start_delay)
        if self.clicking: self._autoclicker_loop()
            
    def _autoclicker_loop(self):
        click_count = 0
        while self.clicking:
            if self.use_fixed_position: self.mouse.position = self.fixed_pos
            for _ in range(self.clicks_per_action): self.mouse.click(self.click_button)
            click_count += 1
            self.stats['session_clicks'] += 1
            self.stats['total_clicks'] += 1
            self.root.after(0, lambda c=click_count: self.session_clicks_var.set(f"{c} clicks"))
            if self.click_limit > 0 and click_count >= self.click_limit:
                self.root.after(0, self.stop_autoclicker)
                break
            time.sleep(random.uniform(self.random_min, self.random_max) if self.use_random else self.interval)
                
    def stop_autoclicker(self):
        self.clicking = False
        key = self.format_key(self.hotkey_vars['autoclicker'].get())
        self.auto_toggle_btn.config(text=f"▶ START ({key})", bg=self.colors['success'])
        self.update_status("Idle", self.colors['text_dim'])
        self.auto_status_dot.config(fg=self.colors['text_dim'])
        self.auto_status_var.set("Stopped")

    # ============== RECORDING LOGIC ==============
    def toggle_recording(self):
        if self.recording: self.stop_recording()
        else: self.start_recording()
            
    def start_recording(self):
        if self.playing: return
        self.recorded_actions = []
        self.recording = True
        self.record_start_time = time.time()
        self.last_action_time = 0
        
        self.record_status_var.set("Recording...")
        self.rec_status_dot.config(fg=self.colors['danger'])
        self.record_btn.config(text="⏹ STOP (F7)", bg=self.colors['warning'])
        self.update_status("Recording", self.colors['danger'])
        self.update_actions_count()
        
        self.mouse_rec_listener = MouseListener(on_click=self._on_click,
                                                 on_move=self._on_move if self.record_movements_var.get() else None)
        self.mouse_rec_listener.start()
        
        if self.record_keyboard_var.get():
            self.kb_rec_listener = KeyboardListener(on_press=self._on_key_press)
            self.kb_rec_listener.start()
            
    def _on_click(self, x, y, button, pressed):
        if not self.recording: return False
        if pressed:
            self.recorded_actions.append({'type': 'click', 'x': x, 'y': y, 'button': button.name, 'time': time.time() - self.record_start_time})
            self.root.after(0, self.update_actions_count)
            
    def _on_move(self, x, y):
        if not self.recording: return False
        current_time = time.time() - self.record_start_time
        if current_time - self.last_action_time > 0.05:
            self.recorded_actions.append({'type': 'move', 'x': x, 'y': y, 'time': current_time})
            self.last_action_time = current_time
            self.root.after(0, self.update_actions_count)
            
    def _on_key_press(self, key):
        if not self.recording: return False
        key_str = str(key).replace("'", "")
        if key_str in [self.hotkey_vars[k].get() for k in self.hotkey_vars]: return
        self.recorded_actions.append({'type': 'key', 'key': key_str, 'time': time.time() - self.record_start_time})
        self.root.after(0, self.update_actions_count)
        
    def stop_recording(self):
        self.recording = False
        self.record_status_var.set(f"Recorded {len(self.recorded_actions)} actions")
        self.rec_status_dot.config(fg=self.colors['text_dim'])
        self.record_btn.config(text="⏺ RECORD (F7)", bg=self.colors['danger'])
        self.update_status("Idle", self.colors['text_dim'])
        if hasattr(self, 'mouse_rec_listener'): self.mouse_rec_listener.stop()
        if hasattr(self, 'kb_rec_listener'): self.kb_rec_listener.stop()
            
    def clear_recording(self):
        if self.recording: self.stop_recording()
        self.recorded_actions = []
        self.record_status_var.set("Ready to record")
        self.update_actions_count()
        
    def update_actions_count(self):
        self.actions_var.set(f"{len(self.recorded_actions)} actions")

    # ============== PLAYBACK LOGIC ==============
    def toggle_playback(self):
        if self.playing: self.stop_playback()
        else: self.start_playback()
            
    def start_playback(self):
        if not self.recorded_actions:
            messagebox.showinfo("No Recording", "Record some actions first!")
            return
        if self.recording: self.stop_recording()
            
        try: self.playback_speed = max(0.1, float(self.speed_var.get()))
        except: self.playback_speed = 1.0
        try: self.playback_repeat = max(1, int(self.repeat_var.get()))
        except: self.playback_repeat = 1
            
        self.playback_loop = self.loop_var.get()
        self.playing = True
        
        self.play_status_var.set("Playing...")
        self.play_status_dot.config(fg=self.colors['success'])
        self.play_btn.config(text="⏹ STOP (F8)", bg=self.colors['danger'])
        self.update_status("Playing", self.colors['success'])
        
        threading.Thread(target=self._playback_loop, daemon=True).start()
        
    def _playback_loop(self):
        button_map = {'left': Button.left, 'right': Button.right, 'middle': Button.middle}
        repeat_count = 0
        
        while self.playing and (self.playback_loop or repeat_count < self.playback_repeat):
            repeat_count += 1
            self.root.after(0, lambda r=repeat_count: self.play_progress_var.set(f"Run {r}/{self.playback_repeat if not self.playback_loop else '∞'}"))
            last_time = 0
            
            for action in self.recorded_actions:
                if not self.playing: break
                delay = (action['time'] - last_time) / self.playback_speed
                if delay > 0: time.sleep(delay)
                last_time = action['time']
                if not self.playing: break
                    
                if action['type'] == 'click':
                    self.mouse.position = (action['x'], action['y'])
                    self.mouse.click(button_map.get(action['button'], Button.left))
                elif action['type'] == 'move':
                    self.mouse.position = (action['x'], action['y'])
                elif action['type'] == 'key':
                    key_str = action['key']
                    try:
                        if key_str.startswith('Key.'):
                            key = getattr(Key, key_str.replace('Key.', ''))
                            self.keyboard.press(key); self.keyboard.release(key)
                        else:
                            self.keyboard.press(key_str); self.keyboard.release(key_str)
                    except: pass
                elif action['type'] == 'delay':
                    time.sleep(action['time'] / self.playback_speed)
                    
            self.stats['total_recordings_played'] += 1
            
        self.playing = False
        self.root.after(0, self._playback_finished)
        
    def _playback_finished(self):
        self.play_status_var.set("Stopped")
        self.play_status_dot.config(fg=self.colors['text_dim'])
        self.play_btn.config(text="▶ PLAY (F8)", bg=self.colors['success'])
        self.play_progress_var.set("")
        self.update_status("Idle", self.colors['text_dim'])
        
    def stop_playback(self):
        self.playing = False

    # ============== MACRO LOGIC ==============
    def toggle_macro_recording(self):
        if self.macro_recording: self.stop_macro_recording()
        else: self.start_macro_recording()
            
    def start_macro_recording(self):
        if self.macro_playing: return
        self.macro_actions = []
        self.macro_recording = True
        self.macro_start_time = time.time()
        
        self.macro_status_var.set("Recording...")
        self.macro_status_dot.config(fg=self.colors['danger'])
        self.macro_record_btn.config(text="⏹ STOP (F10)", bg=self.colors['warning'])
        self.update_status("Recording Macro", self.colors['purple'])
        self.update_macro_count()
        
        self.macro_kb_listener = KeyboardListener(on_press=self._on_macro_key_press, on_release=self._on_macro_key_release)
        self.macro_kb_listener.start()
        
    def _on_macro_key_press(self, key):
        if not self.macro_recording: return False
        key_str = str(key).replace("'", "")
        if key_str == self.config.get('hotkey_macro_record', 'Key.f10'): return
        self.macro_actions.append({'type': 'key_press', 'key': key_str, 'time': time.time() - self.macro_start_time})
        self.root.after(0, self.update_macro_count)
        
    def _on_macro_key_release(self, key):
        if not self.macro_recording: return False
        key_str = str(key).replace("'", "")
        if key_str == self.config.get('hotkey_macro_record', 'Key.f10'): return
        self.macro_actions.append({'type': 'key_release', 'key': key_str, 'time': time.time() - self.macro_start_time})
        
    def stop_macro_recording(self):
        self.macro_recording = False
        if hasattr(self, 'macro_kb_listener'): self.macro_kb_listener.stop()
        self.macro_status_var.set(f"Recorded {len(self.macro_actions)} actions")
        self.macro_status_dot.config(fg=self.colors['text_dim'])
        self.macro_record_btn.config(text="⏺ RECORD (F10)", bg=self.colors['purple'])
        self.update_status("Idle", self.colors['text_dim'])
        
    def toggle_macro_playback(self):
        if self.macro_playing: self.stop_macro_playback()
        else: self.start_macro_playback()
            
    def start_macro_playback(self):
        if not self.macro_actions:
            messagebox.showinfo("No Macro", "Record a macro first!")
            return
        if self.macro_recording: self.stop_macro_recording()
            
        try: self.macro_speed = max(0.1, float(self.macro_speed_var.get()))
        except: self.macro_speed = 1.0
        try: self.macro_repeat = max(1, int(self.macro_repeat_var.get()))
        except: self.macro_repeat = 1
            
        self.macro_loop = self.macro_loop_var.get()
        self.macro_playing = True
        
        self.macro_status_var.set("Playing...")
        self.macro_status_dot.config(fg=self.colors['success'])
        self.macro_play_btn.config(text="⏹ STOP", bg=self.colors['danger'])
        self.update_status("Playing Macro", self.colors['success'])
        
        threading.Thread(target=self._macro_playback_loop, daemon=True).start()
        
    def _macro_playback_loop(self):
        repeat_count = 0
        while self.macro_playing and (self.macro_loop or repeat_count < self.macro_repeat):
            repeat_count += 1
            last_time = 0
            for action in self.macro_actions:
                if not self.macro_playing: break
                delay = (action['time'] - last_time) / self.macro_speed
                if delay > 0: time.sleep(delay)
                last_time = action['time']
                if not self.macro_playing: break
                    
                key_str = action['key']
                try:
                    key = getattr(Key, key_str.replace('Key.', '')) if key_str.startswith('Key.') else key_str
                    if action['type'] == 'key_press': self.keyboard.press(key)
                    elif action['type'] == 'key_release': self.keyboard.release(key)
                except: pass
                    
            self.stats['total_macros_played'] += 1
            
        self.macro_playing = False
        self.root.after(0, self._macro_playback_finished)
        
    def _macro_playback_finished(self):
        self.macro_status_var.set("Stopped")
        self.macro_status_dot.config(fg=self.colors['text_dim'])
        self.macro_play_btn.config(text="▶ PLAY (F11)", bg=self.colors['success'])
        self.update_status("Idle", self.colors['text_dim'])
        
    def stop_macro_playback(self):
        self.macro_playing = False
        
    def clear_macro(self):
        if self.macro_recording: self.stop_macro_recording()
        self.macro_actions = []
        self.macro_status_var.set("Ready")
        self.update_macro_count()
        
    def update_macro_count(self):
        self.macro_count_var.set(f"{len(self.macro_actions)} actions")
        
    def run_macro_script(self):
        script = self.macro_editor.get("1.0", tk.END).strip()
        if not script: return
        self.macro_playing = True
        self.update_status("Running Script", self.colors['success'])
        threading.Thread(target=self._run_script, args=(script,), daemon=True).start()
        
    def _run_script(self, script):
        for line in script.split('\n'):
            if not self.macro_playing: break
            line = line.strip()
            if not line or line.startswith('#'): continue
            try:
                if line.startswith('key(') and line.endswith(')'):
                    self._press_key(line[4:-1].strip().lower())
                elif line.startswith('combo(') and line.endswith(')'):
                    self._press_combo(line[6:-1].strip())
                elif line.startswith('type(') and line.endswith(')'):
                    self.keyboard.type(line[5:-1])
                elif line.startswith('wait(') and line.endswith(')'):
                    time.sleep(float(line[5:-1]))
            except: pass
        self.macro_playing = False
        self.root.after(0, lambda: self.update_status("Idle", self.colors['text_dim']))
        
    def _get_key(self, key_name):
        key_map = {'ctrl': Key.ctrl, 'alt': Key.alt, 'shift': Key.shift, 'win': Key.cmd,
                   'enter': Key.enter, 'space': Key.space, 'tab': Key.tab, 'backspace': Key.backspace,
                   'delete': Key.delete, 'esc': Key.esc, 'up': Key.up, 'down': Key.down,
                   'left': Key.left, 'right': Key.right}
        for i in range(1, 13): key_map[f'f{i}'] = getattr(Key, f'f{i}')
        return key_map.get(key_name.lower().strip(), key_name)
        
    def _press_key(self, key_name):
        key = self._get_key(key_name)
        self.keyboard.press(key); self.keyboard.release(key)
        
    def _press_combo(self, combo):
        keys = [self._get_key(k.strip()) for k in combo.split('+')]
        for key in keys: self.keyboard.press(key)
        time.sleep(0.05)
        for key in reversed(keys): self.keyboard.release(key)
        
    def import_recorded_to_editor(self):
        if not self.macro_actions:
            messagebox.showinfo("No Recording", "Record a macro first!")
            return
        script_lines = []
        last_time = 0
        for action in self.macro_actions:
            if action['type'] == 'key_press':
                delay = action['time'] - last_time
                if delay > 0.1: script_lines.append(f"wait({delay:.2f})")
                key = action['key'].replace('Key.', '') if action['key'].startswith('Key.') else action['key']
                script_lines.append(f"key({key})")
                last_time = action['time']
        self.macro_editor.delete("1.0", tk.END)
        self.macro_editor.insert("1.0", '\n'.join(script_lines))

    # ============== SAVED MACROS ==============
    def get_macros_path(self):
        return os.path.join(os.path.expanduser('~'), '.autoclicker_macros.json')
        
    def load_saved_macros(self):
        try:
            if os.path.exists(self.get_macros_path()):
                with open(self.get_macros_path(), 'r') as f: self.saved_macros = json.load(f)
        except: self.saved_macros = {}
            
    def save_macros_to_file(self):
        try:
            with open(self.get_macros_path(), 'w') as f: json.dump(self.saved_macros, f, indent=2)
        except: pass
            
    def save_macro(self):
        name = self.macro_name_var.get().strip()
        if not name: messagebox.showwarning("No Name", "Enter a name!"); return
        if not self.macro_actions: messagebox.showwarning("No Macro", "Record a macro first!"); return
        self.saved_macros[name] = self.macro_actions.copy()
        self.save_macros_to_file()
        self.macro_combo['values'] = list(self.saved_macros.keys())
        self.macro_list_var.set(name)
        self.macro_name_var.set("")
        
    def load_macro(self):
        name = self.macro_list_var.get()
        if name and name in self.saved_macros:
            self.macro_actions = self.saved_macros[name].copy()
            self.update_macro_count()
            self.macro_status_var.set(f"Loaded '{name}'")
            
    def delete_macro(self):
        name = self.macro_list_var.get()
        if name and name in self.saved_macros:
            del self.saved_macros[name]
            self.save_macros_to_file()
            self.macro_combo['values'] = list(self.saved_macros.keys())
            self.macro_list_var.set('')

    # ============== PROFILES ==============
    def get_profiles_path(self):
        return os.path.join(os.path.expanduser('~'), '.autoclicker_profiles.json')
        
    def load_profiles(self):
        try:
            if os.path.exists(self.get_profiles_path()):
                with open(self.get_profiles_path(), 'r') as f: self.profiles = json.load(f)
        except: self.profiles = {}
            
    def save_profiles(self):
        try:
            with open(self.get_profiles_path(), 'w') as f: json.dump(self.profiles, f, indent=2)
        except: pass
            
    def get_current_settings(self):
        return {k: getattr(self, f'{k}_var').get() for k in ['interval', 'button', 'click_type', 'click_limit', 'fixed_x', 'fixed_y', 'start_delay']}
        
    def apply_settings(self, settings):
        for k, v in settings.items():
            if hasattr(self, f'{k}_var'): getattr(self, f'{k}_var').set(v)
                
    def create_profile(self):
        name = self.new_profile_var.get().strip()
        if not name: return
        self.profiles[name] = self.get_current_settings()
        self.save_profiles()
        self.profile_combo['values'] = list(self.profiles.keys())
        self.profile_var.set(name)
        self.new_profile_var.set("")
        
    def save_profile(self):
        name = self.profile_var.get()
        if name: self.profiles[name] = self.get_current_settings(); self.save_profiles()
            
    def load_profile(self):
        name = self.profile_var.get()
        if name and name in self.profiles: self.apply_settings(self.profiles[name])
            
    def delete_profile(self):
        name = self.profile_var.get()
        if name and name in self.profiles:
            del self.profiles[name]
            self.save_profiles()
            self.profile_combo['values'] = list(self.profiles.keys()) if self.profiles else ['default']
            self.profile_var.set('')

    # ============== CONFIG ==============
    def get_config_path(self):
        return os.path.join(os.path.expanduser('~'), '.autoclicker_config.json')
        
    def load_config(self):
        try:
            if os.path.exists(self.get_config_path()):
                with open(self.get_config_path(), 'r') as f: self.config.update(json.load(f))
        except: pass
            
    def save_config(self):
        self.config['theme'] = self.theme_var.get() if hasattr(self, 'theme_var') else self.config['theme']
        self.config['always_on_top'] = self.always_on_top_var.get() if hasattr(self, 'always_on_top_var') else False
        if HAS_TRAY and hasattr(self, 'minimize_tray_var'): self.config['minimize_to_tray'] = self.minimize_tray_var.get()
        for k, v in self.hotkey_vars.items(): self.config[f'hotkey_{k}'] = v.get()
        try:
            with open(self.get_config_path(), 'w') as f: json.dump(self.config, f, indent=2)
        except: pass

    # ============== SYSTEM TRAY ==============
    def setup_tray(self):
        if not HAS_TRAY: return
        image = Image.new('RGB', (64, 64), color=self.colors['accent'])
        draw = ImageDraw.Draw(image)
        draw.ellipse([16, 16, 48, 48], fill='white')
        menu = pystray.Menu(pystray.MenuItem('Show', self.show_from_tray), pystray.MenuItem('Exit', self.quit_from_tray))
        self.tray_icon = pystray.Icon('Autoclicker', image, 'Autoclicker Ultimate', menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
    def show_from_tray(self):
        self.root.after(0, self.root.deiconify)
        
    def quit_from_tray(self):
        if self.tray_icon: self.tray_icon.stop()
        self.root.after(0, self.root.destroy)
        
    def minimize_to_tray(self):
        if HAS_TRAY and hasattr(self, 'minimize_tray_var') and self.minimize_tray_var.get(): self.root.withdraw()
        else: self.root.iconify()
            
    def update_status(self, text, color):
        self.header_status.config(text=f"● {text}")
        
    def on_close(self):
        self.save_config()
        if HAS_TRAY and hasattr(self, 'minimize_tray_var') and self.minimize_tray_var.get(): self.minimize_to_tray()
        else:
            if self.tray_icon: self.tray_icon.stop()
            self.root.destroy()
            
    def run(self):
        self.root.mainloop()


# ============== MAIN ==============
def main():
    def start_app():
        app = Autoclicker()
        app.run()
    
    # Check if Firebase is configured
    if 'YOUR_PROJECT_ID' in FIREBASE_CONFIG['database_url']:
        # Firebase not configured - run without key system
        print("NOTE: Firebase not configured. Running without license system.")
        print("To enable: Edit FIREBASE_CONFIG in the script with your Firebase details.")
        start_app()
    else:
        # Run with key system
        LoginWindow(start_app)

if __name__ == "__main__":
    main()