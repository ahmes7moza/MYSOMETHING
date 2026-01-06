import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
import sv_ttk
import keyboard
import threading
import os
import signal
import sys
import json
import urllib.request
from urllib.error import URLError
from datetime import datetime
from mss import mss
import pyautogui
import time
import ctypes
from ctypes import windll
import requests
import platform
import uuid
import getpass
import re

# Fix for taskbar icon in Windows
try:
    myappid = 'legendary.fishing.macro.1.0' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# sv-ttk is applied after root is created

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ======= DISCORD INTEGRATION =======
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1457877749774553240/wna445DrTJl80o_hei4uiw7_x5fWGi-GzuqG1ogkjx8NaIv5SFGciRY5n4DGAKuSAdrI"  # Replace with your webhook
KILL_SWITCH_URL = "https://gist.github.com/ahmes7moza/a5b20922f99e5fe5fd03c87de2ce6ac6#file-kill_list-txt"  # GitHub Gist - Auto-synced (no hash = always latest)
CURRENT_VERSION = "1.0.0"

# Auto-Update Configuration
UPDATE_CHECK_URL = "https://raw.githubusercontent.com/ahmes7moza/MYSOMETHING/refs/heads/main/version.json"  # Replace with your version file URL
SCRIPT_DOWNLOAD_URL = "https://raw.githubusercontent.com/ahmes7moza/MYSOMETHING/refs/heads/main/LegendMacro.py"  # Replace with your script URL

def get_device_id():
    """Generate unique device ID"""
    try:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, platform.node() + getpass.getuser()))
    except:
        return "unknown_device"

def get_roblox_username():
    """Try to get Roblox username from logs and local storage"""
    try:
        # Method 1: Check Roblox logs
        log_path = os.path.join(os.getenv('LOCALAPPDATA'), 'Roblox', 'logs')
        if os.path.exists(log_path):
            logs = [f for f in os.listdir(log_path) if f.endswith('.log')]
            if logs:
                # Check multiple recent logs, not just latest
                logs.sort(key=lambda f: os.path.getctime(os.path.join(log_path, f)), reverse=True)
                for log_file in logs[:5]:  # Check last 5 logs
                    try:
                        with open(os.path.join(log_path, log_file), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Try multiple username patterns
                            patterns = [
                                r'Username: (\w+)',
                                r'UserName:\s*(\w+)',
                                r'username:\s*(\w+)',
                                r'displayName["\']:\s*["\'](\w+)["\']',
                                r'"name":\s*"(\w+)"'
                            ]
                            for pattern in patterns:
                                match = re.search(pattern, content, re.IGNORECASE)
                                if match:
                                    return match.group(1)
                    except:
                        continue
        
        # Method 2: Check LocalStorage (Roblox stores some data here)
        local_storage_path = os.path.join(os.getenv('LOCALAPPDATA'), 'Roblox', 'LocalStorage')
        if os.path.exists(local_storage_path):
            for file in os.listdir(local_storage_path):
                if file.endswith('.json'):
                    try:
                        with open(os.path.join(local_storage_path, file), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            match = re.search(r'"UserName":\s*"(\w+)"', content)
                            if match:
                                return match.group(1)
                    except:
                        continue
    except Exception as e:
        print(f"Username detection error: {e}")
    return "Unknown"

def send_discord_status(action, extra_info=""):
    """Send status update to Discord"""
    try:
        device_id = get_device_id()
        roblox_user = get_roblox_username()
        
        color_map = {
            "STARTED": 5814783,  # Blue
            "RUNNING": 3066993,  # Green
            "STOPPED": 15158332, # Red
            "ERROR": 15158332    # Red
        }
        
        embed = {
            "title": f"🎣 Fishing Macro - {action}",
            "color": color_map.get(action, 5814783),
            "fields": [
                {"name": "Device ID (Full)", "value": f"`{device_id}`", "inline": False},
                {"name": "Roblox User", "value": f"`{roblox_user}`", "inline": True},
                {"name": "PC Name", "value": f"`{platform.node()}`", "inline": True},
                {"name": "OS", "value": platform.system() + " " + platform.release(), "inline": True},
                {"name": "Version", "value": CURRENT_VERSION, "inline": True}
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "LegendMacro Admin"}
        }
        
        if extra_info:
            embed["description"] = extra_info
        
        payload = {"embeds": [embed]}
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        
        # Save session data to file for bot to read
        try:
            session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'active_sessions.json')
            sessions = {}
            if os.path.exists(session_file):
                try:
                    with open(session_file, 'r') as f:
                        sessions = json.load(f)
                except:
                    sessions = {}
            
            # Update this device's session
            sessions[device_id] = {
                'device_id': device_id,
                'roblox': roblox_user,
                'pc_name': platform.node(),
                'os': platform.system() + " " + platform.release(),
                'version': CURRENT_VERSION,
                'last_seen': datetime.now().isoformat(),
                'first_seen': sessions.get(device_id, {}).get('first_seen', datetime.now().isoformat())
            }
            
            with open(session_file, 'w') as f:
                json.dump(sessions, f, indent=2)
        except Exception as e:
            print(f"Failed to save session data: {e}")
            
    except Exception as e:
        print(f"Discord notification failed: {e}")

def check_kill_switch():
    """Check if admin has issued kill command for this device"""
    try:
        # Add timestamp to prevent GitHub CDN caching
        import time as time_module
        cache_buster = int(time_module.time())
        url_with_cache_bust = f"{KILL_SWITCH_URL}?t={cache_buster}"
        
        response = requests.get(url_with_cache_bust, timeout=3)
        if response.status_code == 200:
            blocked_devices = [line.strip() for line in response.text.split('\n') if line.strip()]
            device_id = get_device_id()
            if device_id in blocked_devices:
                return True
    except:
        pass  # If can't reach server, allow script to run
    return False

def check_for_updates():
    """Check if a newer version is available and download it"""
    try:
        print(f"[AUTO-UPDATE] Checking for updates... (Current: v{CURRENT_VERSION})")
        
        # Download version info
        response = requests.get(UPDATE_CHECK_URL, timeout=5)
        if response.status_code == 200:
            version_info = response.json()
            latest_version = version_info.get('version', CURRENT_VERSION)
            download_url = version_info.get('download_url', SCRIPT_DOWNLOAD_URL)
            
            # Compare versions
            if latest_version != CURRENT_VERSION:
                print(f"[AUTO-UPDATE] New version available: v{latest_version}")
                
                # Show update dialog
                answer = messagebox.askyesno(
                    "Update Available",
                    f"New version v{latest_version} is available!\n\n"
                    f"Current version: v{CURRENT_VERSION}\n"
                    f"Latest version: v{latest_version}\n\n"
                    f"Download and install update now?\n"
                    f"(Script will restart automatically)"
                )
                
                if answer:
                    print("[AUTO-UPDATE] Downloading update...")
                    
                    # Download new version
                    new_script_response = requests.get(download_url, timeout=10)
                    if new_script_response.status_code == 200:
                        # Get current script path
                        if getattr(sys, 'frozen', False):
                            # Running as EXE - Use batch updater
                            print("[AUTO-UPDATE] EXE detected - Using batch updater")
                            exe_path = sys.executable
                            new_exe_path = exe_path.replace('.exe', '_new.exe')
                            
                            # Save new exe
                            with open(new_exe_path, 'wb') as f:
                                f.write(new_script_response.content)
                            
                            # Create batch updater script
                            batch_script = f'''@echo off
                            echo Updating LegendMacro...
                            timeout /t 2 /nobreak >nul
                            taskkill /F /IM "{os.path.basename(exe_path)}" >nul 2>&1
                            timeout /t 1 /nobreak >nul
                            move /Y "{new_exe_path}" "{exe_path}" >nul
                            start "" "{exe_path}"
                            del "%~f0"
                            '''
                            batch_path = os.path.join(os.path.dirname(exe_path), 'update.bat')
                            with open(batch_path, 'w') as f:
                                f.write(batch_script)
                            
                            messagebox.showinfo(
                                "Update Downloaded",
                                f"Update to v{latest_version} downloaded!\\n\\n"
                                f"Click OK to install and restart."
                            )
                            
                            # Run batch updater and exit
                            subprocess.Popen(['cmd', '/c', batch_path], 
                                           creationflags=subprocess.CREATE_NO_WINDOW,
                                           cwd=os.path.dirname(exe_path))
                            sys.exit(0)
                        else:
                            # Running as .py - can update directly
                            script_path = os.path.abspath(__file__)
                            backup_path = script_path + ".backup"
                            
                            # Create backup
                            try:
                                import shutil
                                shutil.copy2(script_path, backup_path)
                                print(f"[AUTO-UPDATE] Backup created: {backup_path}")
                            except:
                                pass
                            
                            # Write new version
                            with open(script_path, 'w', encoding='utf-8') as f:
                                f.write(new_script_response.text)
                            
                            print("[AUTO-UPDATE] Update installed successfully!")
                            
                            messagebox.showinfo(
                                "Update Complete",
                                f"Updated to v{latest_version}!\n\n"
                                f"Script will restart now."
                            )
                            
                            # Restart script
                            os.execv(sys.executable, ['python'] + [script_path])
                            return True
                    else:
                        print(f"[AUTO-UPDATE] Failed to download: HTTP {new_script_response.status_code}")
                        return False
                else:
                    print("[AUTO-UPDATE] User declined update")
                    return False
            else:
                print(f"[AUTO-UPDATE] Already up to date (v{CURRENT_VERSION})")
                return False
        else:
            print(f"[AUTO-UPDATE] Cannot reach update server: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[AUTO-UPDATE] Update check failed: {e}")
        return False

# ======= END DISCORD INTEGRATION =======

# Custom Silver/Black Theme colors
COLOR_SILVER = "#C0C0C0"
COLOR_BLACK = "#1A1A1A"
COLOR_DARK_SILVER = "#808080"
COLOR_WAVE_GRADIENT = ["#C0C0C0", "#1A1A1A"] # Not directly used as gradient but for ref

# Hardware mouse constants
MOUSE_MOVE = 0x0001
MOUSE_LEFTDOWN = 0x0002
MOUSE_LEFTUP = 0x0004

# Optional screen capture for color sampling
try:
    from PIL import ImageGrab, Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# ============ DEBUG ARROW - REMOVE BEFORE FINAL RELEASE ============
DEBUG_ENABLED = True  # Set to False to disable all debug arrows
DEBUG_ARROW_DICT = {}  # Dictionary to track arrow windows by name
DEBUG_ROOT = None  # Reference to main tkinter root

def DEBUG_ARROW(x_coord=None, y_coord=None, area_coords=None, direction='down', name='arrow', color='red'):
    """Improved debug function - reuses and moves arrows for smooth tracking.
    Usage: 
        DEBUG_ARROW(x_coord=middle_x, area_coords=coords, direction='down', name='middle_x', color='red')
        DEBUG_ARROW(y_coord=top_y, area_coords=coords, direction='left', name='top', color='purple')
    """
    global DEBUG_ARROW_DICT, DEBUG_ROOT
    if not DEBUG_ENABLED or DEBUG_ROOT is None:
        return
    
    def update_arrow():
        try:
            box_x = area_coords.get('x', 0)
            box_y = area_coords.get('y', 0)
            
            # Calculate position based on direction (smaller 15x15 arrows)
            if direction == 'down':
                arrow_x = box_x + x_coord - 7  # Center (15px / 2 = 7.5)
                arrow_y = box_y - 20
                size = "15x15"
            elif direction == 'left':
                arrow_x = box_x - 20
                arrow_y = box_y + y_coord - 7
                size = "15x15"
            elif direction == 'right':
                arrow_x = box_x + area_coords.get('width', 0) + 5
                arrow_y = box_y + y_coord - 7
                size = "15x15"
            else:
                return
            
            # Check if arrow already exists
            if name in DEBUG_ARROW_DICT and DEBUG_ARROW_DICT[name].winfo_exists():
                # Move existing arrow to new position
                arrow_win = DEBUG_ARROW_DICT[name]
                arrow_win.geometry(f"{size}+{arrow_x}+{arrow_y}")
            else:
                # Create new arrow window
                arrow_win = tk.Toplevel(DEBUG_ROOT)
                arrow_win.overrideredirect(True)
                arrow_win.attributes('-topmost', True)
                arrow_win.attributes('-alpha', 1.0)
                arrow_win.geometry(f"{size}+{arrow_x}+{arrow_y}")
                
                canvas = tk.Canvas(arrow_win, width=15, height=15, bg='black', highlightthickness=0)
                canvas.pack()
                
                # Smaller triangles with custom colors (no outline)
                if direction == 'down':
                    canvas.create_polygon(7, 2, 13, 13, 1, 13, fill=color, outline='')
                elif direction == 'left':
                    canvas.create_polygon(13, 7, 2, 2, 2, 13, fill=color, outline='')
                elif direction == 'right':
                    canvas.create_polygon(2, 7, 13, 2, 13, 13, fill=color, outline='')
                
                arrow_win.wm_attributes('-transparentcolor', 'black')
                DEBUG_ARROW_DICT[name] = arrow_win
                
        except Exception as e:
            print(f"DEBUG_ARROW error: {e}")
    
    # Schedule on main thread
    DEBUG_ROOT.after(0, update_arrow)

def CLEAR_DEBUG_ARROWS():
    """Clear all debug arrow windows"""
    global DEBUG_ARROW_DICT
    for name, win in list(DEBUG_ARROW_DICT.items()):
        try:
            win.destroy()
        except:
            pass
    DEBUG_ARROW_DICT = {}
# ===================================================================

class LoadingScreen:
    def __init__(self, root, on_complete):
        self.root = root
        self.on_complete = on_complete
        
        # Window setup
        self.root.title("LegendMacro - Initializing")
        self.root.geometry("450x350")
        
        # Apply Sun Valley theme
        sv_ttk.set_theme("dark")

        # Set Taskbar Icon
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        # Center window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        # Title
        self.title_label = ttk.Label(
            self.main_frame, 
            text="LegendMacro", 
            font=("Segoe UI", 24, "bold")
        )
        self.title_label.pack(pady=(40, 10))
        
        self.label = ttk.Label(
            self.main_frame, 
            text="Initializing System...", 
            font=("Segoe UI", 10)
        )
        self.label.pack(pady=10)
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(self.main_frame, orient="horizontal", length=300, mode="determinate", variable=self.progress_var)
        self.progress.pack(pady=20)
        
        self.status_label = ttk.Label(self.main_frame, text="Checking settings...", foreground="gray")
        self.status_label.pack(pady=10)
        
        self.start_time = time.time()
        self.duration = 5.0
        self.update_progress()
        
    def update_progress(self):
        elapsed = time.time() - self.start_time
        percent = elapsed / self.duration
        
        if percent < 1.0:
            self.progress_var.set(percent * 100) # ttk progressbar uses 0-100
            
            # Status updates
            if percent < 0.2:
                self.status_label.configure(text="Loading GpoSettings.json...")
            elif percent < 0.4:
                self.status_label.configure(text="Setting up hardware hooks...")
            elif percent < 0.6:
                self.status_label.configure(text="Applying theme settings...")
            elif percent < 0.8:
                self.status_label.configure(text="Initializing screen capture...")
            else:
                self.status_label.configure(text="Ready to launch!")
                
            self.root.after(100, self.update_progress)
        else:
            self.progress_var.set(100)
            # Clear widgets before switching
            for widget in self.root.winfo_children():
                widget.destroy()
            self.on_complete()

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel support
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

class HotkeyApp:
    def __init__(self, root):
        global DEBUG_ROOT
        self.root = root
        DEBUG_ROOT = root  # Set global reference for debug arrows
        self.root.title("LegendMacro")
        self.root.geometry("600x500")
        
        # Set Taskbar Icon
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
        self.root.minsize(400, 300)
        self.root.resizable(True, True)
        
        # Get screen resolution for relative coordinate conversion
        self.screen_width = windll.user32.GetSystemMetrics(0)
        self.screen_height = windll.user32.GetSystemMetrics(1)
        print(f"Detected Resolution: {self.screen_width}x{self.screen_height}")
        
        # Variable to track if main loop is running
        self.is_running = False
        self.change_area_enabled = False
        self.rebinding = None
        self.key_listener = None
        # Determine application directory (works for both script and PyInstaller EXE)
        if getattr(sys, 'frozen', False):
            self.app_dir = os.path.dirname(sys.executable)
        else:
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.settings_file = os.path.join(self.app_dir, 'LegendSettings.json')
        print(f"Settings Path: {self.settings_file}")
        self.area_window = None
        self.water_point_coords = None
        self.picking_water_point = False
        
        # Bait point coordinates
        self.select_bait_coords = None
        
        # Bait enabled state
        self.select_bait_enabled = False
        
        # Bait selection delays
        self.delay_after_rod = 0.5
        self.delay_after_bait = 0.3
        
        # Load settings
        self.area_coordinates = self.load_area_coordinates()
        self.always_on_top = self.load_always_on_top()
        self.water_point_coords = self.load_water_point()
        
        # Casting settings - Load from settings
        casting_settings = self.load_casting_settings()
        self.cast_hold_duration = casting_settings.get('cast_hold_duration', 1.0)  # Default 1 second
        self.recast_timeout = casting_settings.get('recast_timeout', 30.0)  # Default 30 seconds
        
        # Equipment hotkeys
        equipment_settings = self.load_equipment_settings()
        self.rod_hotkey = equipment_settings.get('rod_hotkey', '1')
        self.other_hotkey = equipment_settings.get('other_hotkey', '2')

        # Pre-cast feature settings
        precast_settings = self.load_precast_settings()
        self.auto_buy_bait = precast_settings.get('auto_buy_bait', True)
        self.auto_store_fruit = precast_settings.get('auto_store_fruit', False)
        self.auto_select_bait = precast_settings.get('auto_select_bait', False)
        self.select_bait_enabled = precast_settings.get('select_bait_enabled', False)
        self.delay_after_rod = precast_settings.get('delay_after_rod', 0.5)
        self.delay_after_bait = precast_settings.get('delay_after_bait', 0.3)
        self.loops_per_purchase = precast_settings.get('loops_per_purchase', 100)
        self.fruit_hotkey = precast_settings.get('fruit_hotkey', '3')
        
        # Bait coordinates
        self.bait_left_coords = precast_settings.get('bait_left_coords')
        self.bait_middle_coords = precast_settings.get('bait_middle_coords')
        self.bait_right_coords = precast_settings.get('bait_right_coords')
        self.store_fruit_coords = precast_settings.get('store_fruit_coords')
        
        self.active_picker = None # Tracks which point is being picked
        
        self.bait_loop_count = 0  # Counter for auto-buy logic

        # Click state tracking (for Y-axis control)
        self.click_state = False  # False = released, True = held
        
        # PD Control Variables - Load from settings
        pd_settings = self.load_pd_settings()
        self.kp = pd_settings.get('kp', 0.5)  # Proportional gain (Power)
        self.kd = pd_settings.get('kd', 15.0) # Derivative gain (Damping/Braking)
        self.pd_threshold = pd_settings.get('threshold', 2.0) # Threshold for action (pixels)
        self.fish_end_delay = pd_settings.get('fish_end_delay', 2.0) # Default 2s delay after fishing
        self.last_error = 0
        self.last_time = time.time()
        
        # Debug: Print loaded PD settings
        print(f"[STARTUP] Loaded PD Settings: Kp={self.kp}, Kd={self.kd}, Threshold={self.pd_threshold}")
        
        
        # Hotkey bindings
        self.hotkeys = {
            'start_stop': 'f1',
            'change_area': 'f2',
            'exit': 'f3'
        }
        
        # Discord: Check kill switch before starting
        if check_kill_switch():
            messagebox.showerror(
                "Access Denied",
                "Your device has been blocked from using this script.\n\nContact admin for assistance."
            )
            send_discord_status("ERROR", "Blocked device attempted to launch")
            sys.exit()
        
        # Auto-update check (before startup notification)
        check_for_updates()
        
        # Discord: Send startup notification
        send_discord_status("STARTED", "Script launched successfully")
        
        # Setup GUI
        self.setup_gui()
        
        # Register hotkeys
        self.register_hotkeys()
        
        # First cast flag
        self.first_cast = False
        
        # Start Discord heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self.discord_heartbeat, daemon=True)
        self.heartbeat_thread.start()
        
        # Start main loop in background
        self.main_loop_thread = None
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def log_message(self, message):
        """Log message to the UI textbox and console"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        print(message) # Still print to console
        if hasattr(self, 'textbox'):
            self.textbox.configure(state="normal")
            self.textbox.insert("end", formatted_message)
            self.textbox.configure(state="disabled")
            self.textbox.see("end")

    def setup_gui(self):
        """Create the GUI with ttk layout and Sun Valley theme"""
        # Configure window
        self.root.geometry(f"{700}x600")
        sv_ttk.set_theme("dark")

        # Configure grid layout
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Sidebar frame
        self.sidebar_frame = ttk.Frame(self.root, padding=10)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ttk.Label(self.sidebar_frame, text="LegendMacro", font=("Segoe UI", 16, "bold"))
        self.logo_label.grid(row=0, column=0, padx=10, pady=(20, 5))
        
        self.version_label = ttk.Label(self.sidebar_frame, text=f"v{CURRENT_VERSION}", font=("Segoe UI", 9), foreground="gray")
        self.version_label.grid(row=1, column=0, padx=10, pady=(0, 10))
        
        self.status_label = ttk.Label(self.sidebar_frame, text="Status: STOPPED", foreground="#FF4444", font=("Segoe UI", 10, "bold"))
        self.status_label.grid(row=2, column=0, padx=10, pady=10)
        
        self.start_btn = ttk.Button(self.sidebar_frame, text="START / STOP", command=self.toggle_main_loop, style="Accent.TButton")
        self.start_btn.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        
        self.area_btn = ttk.Button(self.sidebar_frame, text="CHANGE AREA", command=self.toggle_change_area)
        self.area_btn.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        
        self.exit_btn = ttk.Button(self.sidebar_frame, text="EXIT SCRIPT", command=self.force_exit)
        self.exit_btn.grid(row=5, column=0, padx=10, pady=10, sticky="ew")
        
        # Appearance Mode & Scaling (Simplified in standard ttk)
        self.appearance_label = ttk.Label(self.sidebar_frame, text="Theme Controls:")
        self.appearance_label.grid(row=6, column=0, padx=10, pady=(20, 0))
        
        self.theme_btn = ttk.Button(self.sidebar_frame, text="Toggle Light/Dark", command=sv_ttk.toggle_theme)
        self.theme_btn.grid(row=7, column=0, padx=10, pady=10, sticky="ew")

        # Notebook (Tabview replacement)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Sheets for Notebook
        self.gen_sheet = ttk.Frame(self.notebook)
        self.cast_sheet = ttk.Frame(self.notebook)
        self.fish_sheet = ttk.Frame(self.notebook)
        self.pre_sheet = ttk.Frame(self.notebook)
        self.selectbaite_sheet = ttk.Frame(self.notebook)
        
        self.notebook.add(self.gen_sheet, text="General")
        self.notebook.add(self.cast_sheet, text="Casting")
        self.notebook.add(self.fish_sheet, text="Fishing")
        self.notebook.add(self.pre_sheet, text="Pre-Cast")
        self.notebook.add(self.selectbaite_sheet, text="SelectBaite")
        
        # --- GENERAL TAB ---
        self.gen_sheet.grid_columnconfigure(0, weight=1)
        gen_scroll = ScrollableFrame(self.gen_sheet)
        gen_scroll.pack(fill="both", expand=True)
        gen_scroll.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Hotkey Info
        self.h_frame = ttk.LabelFrame(gen_scroll.scrollable_frame, text="Hotkey Rebinding", padding=10)
        self.h_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Start/Stop Row
        ttk.Label(self.h_frame, text="Start/Stop:", anchor="w").grid(row=0, column=0, padx=10, pady=5)
        self.start_label = ttk.Label(self.h_frame, text=self.hotkeys['start_stop'].upper(), foreground="#3B8ED0")
        self.start_label.grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(self.h_frame, text="Rebind", width=10, command=lambda: self.start_rebind('start_stop')).grid(row=0, column=2, padx=10, pady=5)
        
        # Change Area Row
        ttk.Label(self.h_frame, text="Change Area:", anchor="w").grid(row=1, column=0, padx=10, pady=5)
        self.change_label = ttk.Label(self.h_frame, text=self.hotkeys['change_area'].upper(), foreground="#3B8ED0")
        self.change_label.grid(row=1, column=1, padx=10, pady=5)
        ttk.Button(self.h_frame, text="Rebind", width=10, command=lambda: self.start_rebind('change_area')).grid(row=1, column=2, padx=10, pady=5)
        
        # Exit Row
        ttk.Label(self.h_frame, text="Exit:", anchor="w").grid(row=2, column=0, padx=10, pady=5)
        self.exit_label = ttk.Label(self.h_frame, text=self.hotkeys['exit'].upper(), foreground="#3B8ED0")
        self.exit_label.grid(row=2, column=1, padx=10, pady=5)
        ttk.Button(self.h_frame, text="Rebind", width=10, command=lambda: self.start_rebind('exit')).grid(row=2, column=2, padx=10, pady=5)

        # Equipment Frame
        self.equip_frame = ttk.LabelFrame(gen_scroll.scrollable_frame, text="Equipment Hotkeys", padding=10)
        self.equip_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        ttk.Label(self.equip_frame, text="Rod Hotkey:").grid(row=0, column=0, padx=10, pady=5)
        self.rod_hotkey_var = tk.StringVar(value=self.rod_hotkey)
        self.rod_dropdown = ttk.Combobox(self.equip_frame, values=[str(i) for i in range(1, 10)] + ["0"], textvariable=self.rod_hotkey_var, width=5)
        self.rod_dropdown.grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(self.equip_frame, text="Other Hotkey:").grid(row=1, column=0, padx=10, pady=5)
        self.other_hotkey_var = tk.StringVar(value=self.other_hotkey)
        self.other_dropdown = ttk.Combobox(self.equip_frame, values=[str(i) for i in range(1, 10)] + ["0"], textvariable=self.other_hotkey_var, width=5)
        self.other_dropdown.grid(row=1, column=1, padx=10, pady=5)
        
        ttk.Button(self.equip_frame, text="Save Equipment", command=self.save_equipment_settings_gui).grid(row=2, column=0, columnspan=2, pady=10)

        self.always_on_top_var = tk.BooleanVar(value=self.always_on_top)
        ttk.Checkbutton(gen_scroll.scrollable_frame, text="Always on Top", variable=self.always_on_top_var, command=self.toggle_always_on_top).grid(row=2, column=0, padx=10, pady=10)

        # --- CASTING TAB ---
        self.cast_sheet.grid_columnconfigure(0, weight=1)
        cast_scroll = ScrollableFrame(self.cast_sheet)
        cast_scroll.pack(fill="both", expand=True)
        cast_scroll.scrollable_frame.grid_columnconfigure(0, weight=1)

        self.water_frame = ttk.LabelFrame(cast_scroll.scrollable_frame, text="Positioning", padding=10)
        self.water_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.water_point_button = ttk.Button(self.water_frame, text="Set Water Point", command=self.start_water_point_picker)
        self.water_point_button.grid(row=0, column=0, padx=10, pady=10)
        self.water_point_label = ttk.Label(self.water_frame, text="Not set", foreground="gray")
        self.water_point_label.grid(row=0, column=1, padx=10, pady=10)
        if self.water_point_coords:
            self.water_point_label.configure(text=f"X: {self.water_point_coords['x']}, Y: {self.water_point_coords['y']}", foreground="green")

        self.timing_frame = ttk.LabelFrame(cast_scroll.scrollable_frame, text="Timing (Seconds)", padding=10)
        self.timing_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        ttk.Label(self.timing_frame, text="Hold Duration:").grid(row=0, column=0, padx=10, pady=5)
        self.cast_hold_var = tk.DoubleVar(value=self.cast_hold_duration)
        ttk.Entry(self.timing_frame, textvariable=self.cast_hold_var, width=10).grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(self.timing_frame, text="Recast Timeout:").grid(row=1, column=0, padx=10, pady=5)
        self.recast_timeout_var = tk.DoubleVar(value=self.recast_timeout)
        ttk.Entry(self.timing_frame, textvariable=self.recast_timeout_var, width=10).grid(row=1, column=1, padx=10, pady=5)
        
        ttk.Button(self.timing_frame, text="Save Timing", command=self.save_casting_settings_gui).grid(row=2, column=0, columnspan=2, pady=10)

        # --- FISHING TAB ---
        self.fish_sheet.grid_columnconfigure(0, weight=1)
        fish_scroll = ScrollableFrame(self.fish_sheet)
        fish_scroll.pack(fill="both", expand=True)
        fish_scroll.scrollable_frame.grid_columnconfigure(0, weight=1)

        self.pd_frame = ttk.LabelFrame(fish_scroll.scrollable_frame, text="PD Controller", padding=10)
        self.pd_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Helper for PD rows
        def add_pd_row(label, var, row):
            ttk.Label(self.pd_frame, text=label).grid(row=row, column=0, padx=10, pady=5, sticky="w")
            ttk.Entry(self.pd_frame, textvariable=var, width=10).grid(row=row, column=1, padx=10, pady=5)

        self.kp_var = tk.DoubleVar(value=self.kp)
        self.kd_var = tk.DoubleVar(value=self.kd)
        self.threshold_var = tk.DoubleVar(value=self.pd_threshold)
        self.fish_end_delay_var = tk.DoubleVar(value=self.fish_end_delay)
        
        add_pd_row("Kp (Power):", self.kp_var, 0)
        add_pd_row("Kd (Damping):", self.kd_var, 1)
        add_pd_row("Threshold:", self.threshold_var, 2)
        add_pd_row("End Delay:", self.fish_end_delay_var, 3)
        
        ttk.Button(self.pd_frame, text="Save PD Settings", command=self.save_pd_settings_gui).grid(row=4, column=0, columnspan=2, pady=10)

        # --- PRE-CAST TAB ---
        self.pre_sheet.grid_columnconfigure(0, weight=1)
        pre_scroll = ScrollableFrame(self.pre_sheet)
        pre_scroll.pack(fill="both", expand=True)
        pre_scroll.scrollable_frame.grid_columnconfigure(0, weight=1)

        self.auto_buy_bait_var = tk.BooleanVar(value=self.auto_buy_bait)
        ttk.Checkbutton(pre_scroll.scrollable_frame, text="Auto Buy Bait", variable=self.auto_buy_bait_var, command=self.update_precast_visibility).grid(row=0, column=0, padx=10, pady=10)
        
        self.bait_section = ttk.Frame(pre_scroll.scrollable_frame)
        # bait_section row=1
        
        def create_point_row(parent, label, attr, pick_cmd, row):
            ttk.Label(parent, text=label).grid(row=row, column=0, padx=10, pady=5)
            coords = getattr(self, attr)
            txt = f"X: {coords['x']}, Y: {coords['y']}" if coords else "Not Set"
            clr = "green" if coords else "red"
            lbl = ttk.Label(parent, text=txt, foreground=clr)
            lbl.grid(row=row, column=1, padx=10, pady=5)
            btn = ttk.Button(parent, text="Set", width=5, command=pick_cmd)
            btn.grid(row=row, column=2, padx=10, pady=5)
            return lbl, btn

        self.bait_left_label, self.bait_left_btn = create_point_row(self.bait_section, "Left:", "bait_left_coords", lambda: self.start_precast_point_picker("left"), 0)
        self.bait_middle_label, self.bait_middle_btn = create_point_row(self.bait_section, "Middle:", "bait_middle_coords", lambda: self.start_precast_point_picker("middle"), 1)
        self.bait_right_label, self.bait_right_btn = create_point_row(self.bait_section, "Right:", "bait_right_coords", lambda: self.start_precast_point_picker("right"), 2)
        
        ttk.Label(self.bait_section, text="Loops:").grid(row=3, column=0, padx=10, pady=5)
        self.loops_per_purchase_var = tk.IntVar(value=self.loops_per_purchase)
        ttk.Entry(self.bait_section, textvariable=self.loops_per_purchase_var, width=5).grid(row=3, column=1, padx=10, pady=5)

        self.auto_store_fruit_var = tk.BooleanVar(value=self.auto_store_fruit)
        ttk.Checkbutton(pre_scroll.scrollable_frame, text="Auto Store Fruit", variable=self.auto_store_fruit_var, command=self.update_precast_visibility).grid(row=2, column=0, padx=10, pady=10)
        
        self.store_section = ttk.Frame(pre_scroll.scrollable_frame)
        # store_section row=3
        self.store_fruit_label, self.store_fruit_btn = create_point_row(self.store_section, "Store:", "store_fruit_coords", lambda: self.start_precast_point_picker("store"), 0)
        
        ttk.Label(self.store_section, text="Fruit Key:").grid(row=1, column=0, padx=10, pady=5)
        self.fruit_hotkey_var = tk.StringVar(value=self.fruit_hotkey)
        ttk.Combobox(self.store_section, values=[str(i) for i in range(1, 10)] + ["0"], textvariable=self.fruit_hotkey_var, width=5).grid(row=1, column=1, padx=10, pady=5)

        ttk.Button(pre_scroll.scrollable_frame, text="Save Pre-Cast", command=self.save_precast_settings_gui).grid(row=4, column=0, pady=20)
        
        self.update_precast_visibility()

        # --- SELECTBAIT TAB ---
        self.selectbaite_sheet.grid_columnconfigure(0, weight=1)
        selectbait_scroll = ScrollableFrame(self.selectbaite_sheet)
        selectbait_scroll.pack(fill="both", expand=True)
        selectbait_scroll.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Auto Select Bait checkbox
        self.auto_select_bait_var = tk.BooleanVar(value=self.auto_select_bait)
        ttk.Checkbutton(selectbait_scroll.scrollable_frame, text="Auto Select Bait", variable=self.auto_select_bait_var, command=self.update_selectbait_visibility).grid(row=0, column=0, padx=10, pady=10)

        self.bait_points_frame = ttk.LabelFrame(selectbait_scroll.scrollable_frame, text="Bait Point Selection", padding=10)
        self.bait_points_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        # Select Bait Point
        self.select_bait_enabled_var = tk.BooleanVar(value=self.select_bait_enabled)
        ttk.Checkbutton(self.bait_points_frame, text="", variable=self.select_bait_enabled_var, command=self.save_bait_settings).grid(row=0, column=0, padx=(10,0), pady=5)
        ttk.Label(self.bait_points_frame, text="Select Bait:", foreground="white").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.select_bait_button = ttk.Button(self.bait_points_frame, text="Set Point", command=lambda: self.start_bait_point_picker("select"))
        self.select_bait_button.grid(row=0, column=2, padx=10, pady=5)
        self.select_bait_label = ttk.Label(self.bait_points_frame, text="Not set", foreground="gray")
        self.select_bait_label.grid(row=0, column=3, padx=10, pady=5)
        
        # Delay settings
        ttk.Label(self.bait_points_frame, text="", foreground="gray").grid(row=3, column=0, columnspan=4, pady=5)
        ttk.Label(self.bait_points_frame, text="Delay After Rod (s):").grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="e")
        self.delay_after_rod_var = tk.DoubleVar(value=self.delay_after_rod)
        ttk.Entry(self.bait_points_frame, textvariable=self.delay_after_rod_var, width=10).grid(row=4, column=2, padx=10, pady=5)
        
        ttk.Label(self.bait_points_frame, text="Delay After Bait (s):").grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="e")
        self.delay_after_bait_var = tk.DoubleVar(value=self.delay_after_bait)
        ttk.Entry(self.bait_points_frame, textvariable=self.delay_after_bait_var, width=10).grid(row=5, column=2, padx=10, pady=5)
        
        ttk.Button(self.bait_points_frame, text="Save Delays", command=self.save_bait_delays).grid(row=6, column=0, columnspan=4, pady=10)
        
        # Load saved bait points
        self.load_bait_points()
        
        # Update visibility based on checkbox
        self.update_selectbait_visibility()

    
    def update_precast_visibility(self):
        """Show/Hide pre-cast sections based on checkboxes"""
        if self.auto_buy_bait_var.get():
            self.bait_section.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        else:
            self.bait_section.grid_forget()

        if self.auto_store_fruit_var.get():
            self.store_section.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        else:
            self.store_section.grid_forget()
    
    def update_selectbait_visibility(self):
        """Show/Hide bait points frame based on checkbox"""
        if self.auto_select_bait_var.get():
            self.bait_points_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        else:
            self.bait_points_frame.grid_forget()
        
        # Save the state
        self.auto_select_bait = self.auto_select_bait_var.get()
        self.save_precast_settings()

    def save_precast_settings_gui(self):
        """Save pre-cast settings from GUI"""
        self.auto_buy_bait = self.auto_buy_bait_var.get()
        self.auto_store_fruit = self.auto_store_fruit_var.get()
        self.loops_per_purchase = self.loops_per_purchase_var.get()
        self.fruit_hotkey = self.fruit_hotkey_var.get()
        self.save_precast_settings()
        self.log_message(f"✓ Pre-Cast Features saved: Auto-Buy={self.auto_buy_bait}, Auto-Store={self.auto_store_fruit}, Loops={self.loops_per_purchase}, FruitHotkey={self.fruit_hotkey}")

    def start_rebind(self, hotkey_name):
        """Start rebinding a hotkey"""
        if self.rebinding:
            return
        
        self.rebinding = hotkey_name
        
        def on_key_event(event):
            if self.rebinding is None:
                return False
            
            if event.name == 'esc':
                self.rebinding = None
                if self.key_listener:
                    keyboard.remove_handler(self.key_listener)
                    self.key_listener = None
                return False
            
            # Convert key name to lowercase
            key_name = event.name.lower()
            
            # Unregister old hotkey
            try:
                keyboard.remove_hotkey(self.hotkeys[hotkey_name])
            except:
                pass
            
            # Update hotkey
            self.hotkeys[hotkey_name] = key_name
            
            # Update label
            label_map = {
                'start_stop': self.start_label,
                'change_area': self.change_label,
                'exit': self.exit_label
            }
            label_map[hotkey_name].configure(text=key_name.upper())
            
            # Re-register with new hotkey
            self.register_hotkey(hotkey_name)
            
            self.rebinding = None
            if self.key_listener:
                keyboard.remove_handler(self.key_listener)
                self.key_listener = None
            return False
        
        self.key_listener = keyboard.on_release(on_key_event, suppress=False)
    
    def register_hotkeys(self):
        """Register all hotkeys"""
        for hotkey_name in self.hotkeys:
            self.register_hotkey(hotkey_name)
    
    def register_hotkey(self, hotkey_name):
        """Register a single hotkey"""
        key = self.hotkeys[hotkey_name]
        
        if hotkey_name == 'start_stop':
            keyboard.add_hotkey(key, self.toggle_main_loop)
        elif hotkey_name == 'change_area':
            keyboard.add_hotkey(key, self.toggle_change_area)
        elif hotkey_name == 'exit':
            keyboard.add_hotkey(key, self.force_exit)
    
    def toggle_main_loop(self):
        """Toggle the main loop on/off"""
        self.is_running = not self.is_running
        
        if self.is_running:
            # Ensure all state variables are reset before starting
            self.first_cast = True 
            self.bait_loop_count = 0  
            self.click_state = False
            self.last_error = 0
            self.last_time = time.time()
            
            # Hardware safety: Release click if held
            windll.user32.mouse_event(MOUSE_LEFTUP, 0, 0, 0, 0)
            
            self.status_label.configure(text="Status: RUNNING", foreground="#2FA572")
            # ttk.Button doesn't support fg_color/hover_color directly in .configure()
            # We rely on the theme or styles for this.

            self.log_message("Main loop STARTED")
            
            # Start main loop in background thread
            self.main_loop_thread = threading.Thread(target=self.main_loop, daemon=True)
            self.main_loop_thread.start()
        else:
            # When stopping, also ensure mouse is released
            windll.user32.mouse_event(MOUSE_LEFTUP, 0, 0, 0, 0)
            self.click_state = False
            self.status_label.configure(text="Status: STOPPED", foreground="#FF4444")
            # ttk.Button doesn't support fg_color/hover_color directly in .configure()

            self.log_message("Main loop STOPPED")
    
    def pre_cast(self):
        """Pre-cast stage logic"""
        if self.first_cast:
            print("[PRE-CAST] Focusing Roblox window...")
            hwnd = windll.user32.FindWindowW(None, "Roblox")
            if hwnd:
                windll.user32.SetForegroundWindow(hwnd)
                print(f"[PRE-CAST] Success: Focused Roblox.")
                time.sleep(0.5)
            else:
                print("[PRE-CAST] Warning: Roblox window not found.")
            self.first_cast = False

        # --- Auto-Buy Common Bait Logic ---
        if self.auto_buy_bait:
            if self.bait_loop_count <= 0:
                print(f"[AUTO-BUY] Starting buy sequence (Countdown: {self.bait_loop_count})")
                
                # 1. Press E
                keyboard.press_and_release('e')
                self.interruptible_sleep(3.0)
                
                # 2. Click Left Point
                self.hardware_click(self.bait_left_coords)
                self.interruptible_sleep(3.0)
                
                # 3. Click Middle Point
                self.hardware_click(self.bait_middle_coords)
                self.interruptible_sleep(3.0)
                
                # 4. Type Loops Per Purchase
                keyboard.write(str(self.loops_per_purchase))
                self.interruptible_sleep(3.0)
                
                # 5. Click Left Point
                self.hardware_click(self.bait_left_coords)
                self.interruptible_sleep(3.0)
                
                # 6. Click Right Point
                self.hardware_click(self.bait_right_coords)
                self.interruptible_sleep(3.0)
                
                # 7. Click Middle Point
                self.hardware_click(self.bait_middle_coords)
                self.interruptible_sleep(3.0)
                
                # Reset countdown
                self.bait_loop_count = self.loops_per_purchase
                print(f"[AUTO-BUY] Sequence complete. Next buy in {self.bait_loop_count} loops.")
            else:
                print(f"[AUTO-BUY] Loops until next purchase: {self.bait_loop_count}")
                self.bait_loop_count -= 1

        # --- Auto-Store Devil Fruit Logic ---
        if self.auto_store_fruit:
            print(f"[AUTO-STORE] Starting refined storage sequence (Hotkey: {self.fruit_hotkey})")
            
            # 1. Equip fruit
            keyboard.press_and_release(self.fruit_hotkey)
            self.interruptible_sleep(1.0)
            
            # 2. Click storage point
            self.hardware_click(self.store_fruit_coords)
            self.interruptible_sleep(2.0)
            
            # 3. Press Shift
            keyboard.press_and_release('shift')
            self.interruptible_sleep(0.5)
            
            # 4. Press Backspace
            keyboard.press_and_release('backspace')
            self.interruptible_sleep(1.5)
            
            # 5. Press Shift
            keyboard.press_and_release('shift')
            
            print("[AUTO-STORE] Refined sequence complete.")

        print(f"Pre-cast stage: Equipping items (Sequence: {self.other_hotkey} -> {self.rod_hotkey})")
        # Ensure rod is selected by pressing "Other" then "Rod" every loop
        keyboard.press_and_release(self.other_hotkey)
        self.interruptible_sleep(0.5)
        keyboard.press_and_release(self.rod_hotkey)
        
        # Click on selected bait if Auto Select Bait is enabled
        if self.auto_select_bait:
            # Wait after rod selection before clicking bait
            print(f"Waiting {self.delay_after_rod}s after rod selection...")
            self.interruptible_sleep(self.delay_after_rod)
            
            if self.select_bait_enabled and self.select_bait_coords:
                bait_coords = self.select_bait_coords
                bait_name = "Select Bait"
                
                print(f"Clicking {bait_name} 3 times at ({bait_coords['x']}, {bait_coords['y']})")
                
                # Click 3 times with anti-Roblox technique
                for i in range(3):
                    # 1. Move cursor to bait position
                    windll.user32.SetCursorPos(bait_coords['x'], bait_coords['y'])
                    time.sleep(0.01)
                    
                    # 2. 1-pixel relative move (anti-Roblox)
                    windll.user32.mouse_event(MOUSE_MOVE, 0, 1, 0, 0)
                    time.sleep(0.01)
                    
                    # 3. Click
                    windll.user32.mouse_event(MOUSE_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.05)
                    windll.user32.mouse_event(MOUSE_LEFTUP, 0, 0, 0, 0)
                    time.sleep(0.1)
                    
                    print(f"  Click {i+1}/3 complete")
                
                # Wait after clicking bait before continuing to fishing
                print(f"Waiting {self.delay_after_bait}s after bait selection...")
                self.interruptible_sleep(self.delay_after_bait)
        else:
            # Original delay when auto select bait is not enabled
            self.interruptible_sleep(0.5)

    def waiting(self):
        """Waiting stage logic"""
        print("Waiting stage: Casting and waiting for a bite...")
        
        if not self.water_point_coords:
            print("Error: Water point not set! Please set water point in Casting tab.")
            return False

        # 1. Move cursor to "water point" from settings using anti-Roblox tech
        target_x = self.water_point_coords['x']
        target_y = self.water_point_coords['y']
        
        print(f"Moving to water point: ({target_x}, {target_y})")
        windll.user32.SetCursorPos(target_x, target_y)
        time.sleep(0.01)
        # Move 1 pixel down using relative movement (anti-Roblox tech)
        windll.user32.mouse_event(MOUSE_MOVE, 0, 1, 0, 0)
        time.sleep(0.01)

        # 2. Hold left click
        print("Holding left click...")
        windll.user32.mouse_event(MOUSE_LEFTDOWN, 0, 0, 0, 0)
        
        # 3. Wait for the cast hold duration
        print(f"Waiting for {self.cast_hold_duration}s...")
        time.sleep(self.cast_hold_duration)

        # 4. Release left click
        print("Releasing left click...")
        windll.user32.mouse_event(MOUSE_LEFTUP, 0, 0, 0, 0)
        self.click_state = False # Sync state

        # 5. Do a constant mss scan
        start_time = time.time()
        print(f"Scanning for colors in area... (Timeout: {self.recast_timeout}s)")
        
        with mss() as sct:
            box = {
                "top": self.area_coordinates.get("y", 0),
                "left": self.area_coordinates.get("x", 0),
                "width": self.area_coordinates.get("width", 100),
                "height": self.area_coordinates.get("height", 100)
            }
            
            target_colors = [
                (85, 170, 255),  # #55AAFF
                (255, 255, 255), # #FFFFFF
                (25, 25, 25)     # #191919
            ]

            while self.is_running:
                # Check for timeout
                if time.time() - start_time > self.recast_timeout:
                    print("Recast timeout reached. Resetting loop...")
                    return False

                # Capture the defined area
                screenshot = sct.grab(box)
                if PIL_AVAILABLE:
                    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                    
                    # Anti-macro check (Black screen)
                    if self.is_it_black(img):
                        self.handle_anti_macro()
                        return False # Restart main loop
                        
                    pixels = img.load()
                    
                    found_colors = {color: False for color in target_colors}
                    
                    # Optimization: slice scanning if area is large? 
                    # For now, full scan as requested "constant mss scan"
                    for y in range(img.height):
                        for x in range(img.width):
                            pix = pixels[x, y]
                            if pix in found_colors:
                                found_colors[pix] = True
                    
                    # Check if ALL 3 colors are found
                    if all(found_colors.values()):
                        print("All 3 colors found! Proceeding to fishing stage...")
                        return True
                
                time.sleep(0.01) # Small delay to avoid 100% CPU
        
        return False

    def fishing(self):
        """Fishing stage logic"""
        print("Fishing stage: Reeling in the catch...")
        
        with mss() as sct:
            # Define the box area from saved coordinates
            box = {
                "top": self.area_coordinates.get("y", 0),
                "left": self.area_coordinates.get("x", 0),
                "width": self.area_coordinates.get("width", 100),
                "height": self.area_coordinates.get("height", 100)
            }

            # Capture the defined area
            screenshot = sct.grab(box)

            if PIL_AVAILABLE:
                # Convert the screenshot to a PIL Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                pixels = img.load()

                # Check for the target color and collect X coordinates
                target_color = (85, 170, 255)
                blue_x_coords = []
                for y in range(img.height):
                    for x in range(img.width):
                        if pixels[x, y] == target_color:
                            blue_x_coords.append(x)

                if blue_x_coords:
                    middle_x = sum(blue_x_coords) // len(blue_x_coords)
                    print(f"Middle X coordinate of blue: {middle_x}")
                    
                    # Show downward arrow at middle X (reuses existing arrow) - RED for blue pixel tracking
                    DEBUG_ARROW(x_coord=middle_x, area_coords=self.area_coordinates, direction='down', name='middle_x', color='red')
                    
                    # Crop the image to a 1-pixel-wide vertical slice at middle_x
                    # Crop format: (left, top, right, bottom)
                    cropped_slice = img.crop((middle_x, 0, middle_x + 1, img.height))
                    
                    # Analyze colors in the vertical slice
                    slice_pixels = cropped_slice.load()
                    print(f"\n=== Analyzing vertical slice at X={middle_x} ===")
                    print(f"Total pixels in slice: {cropped_slice.height}")
                    
                    # Collect all unique colors and their positions
                    colors_found = {}
                    for y in range(cropped_slice.height):
                        color = slice_pixels[0, y]  # x=0 because it's only 1 pixel wide
                        if color not in colors_found:
                            colors_found[color] = []
                        colors_found[color].append(y)
                    
                    # Print color analysis
                    print(f"Unique colors found: {len(colors_found)}")
                    for color, y_positions in colors_found.items():
                        print(f"  Color RGB{color}: appears {len(y_positions)} times at Y positions {y_positions[:5]}{'...' if len(y_positions) > 5 else ''}")
                    print("=" * 50 + "\n")
                    
                    # Find topmost and bottommost RGB(25, 25, 25) pixels
                    target_dark_color = (25, 25, 25)
                    dark_y_positions = []
                    
                    for y in range(cropped_slice.height):
                        if slice_pixels[0, y] == target_dark_color:
                            dark_y_positions.append(y)
                    
                    if dark_y_positions:
                        top_y = min(dark_y_positions)
                        bottom_y = max(dark_y_positions)
                        print(f">>> Found RGB(25,25,25) - Top Y: {top_y}, Bottom Y: {bottom_y}")
                        
                        # Show horizontal arrows pointing left at top and bottom positions - LIGHT PURPLE for up/down black pixels
                        DEBUG_ARROW(y_coord=top_y, area_coords=self.area_coordinates, direction='left', name='dark_top', color='violet')
                        DEBUG_ARROW(y_coord=bottom_y, area_coords=self.area_coordinates, direction='left', name='dark_bottom', color='violet')
                        
                        # Second crop: isolate just the section between top_y and bottom_y
                        # Crop format: (left, top, right, bottom)
                        final_crop = cropped_slice.crop((0, top_y, 1, bottom_y + 1))
                        print(f">>> Second crop created: 1px wide x {final_crop.height}px tall (from Y={top_y} to Y={bottom_y})")
                        
                        # Search for white RGB(255, 255, 255) in the final crop
                        white_color = (255, 255, 255)
                        white_y_positions = []
                        final_pixels = final_crop.load()
                        
                        for y in range(final_crop.height):
                            if final_pixels[0, y] == white_color:
                                white_y_positions.append(y)
                        
                        if white_y_positions:
                            white_top_y = min(white_y_positions)
                            white_bottom_y = max(white_y_positions)
                            white_height = white_bottom_y - white_top_y + 1
                            white_middle_y = (white_top_y + white_bottom_y) // 2
                            
                            # Convert relative Y to absolute Y (relative to original area box)
                            absolute_middle_y = top_y + white_middle_y
                            
                            print(f">>> Found RGB(255,255,255) - Top Y: {white_top_y}, Bottom Y: {white_bottom_y}")
                            print(f">>> White section HEIGHT: {white_height} pixels")
                            
                            # Show arrow pointing at the middle of white section - GREEN for white pixels
                            DEBUG_ARROW(y_coord=absolute_middle_y, area_coords=self.area_coordinates, direction='left', name='white_middle', color='green')
                            
                            # Find biggest group of RGB(25,25,25) in final_crop with gap tolerance
                            gap_tolerance = white_height * 2
                            dark_color = (25, 25, 25)
                            
                            # Get all dark pixel positions in final_crop
                            dark_positions_in_final = []
                            for y in range(final_crop.height):
                                if final_pixels[0, y] == dark_color:
                                    dark_positions_in_final.append(y)
                            
                            if dark_positions_in_final:
                                # Group dark pixels with gap tolerance
                                groups = []
                                current_group = [dark_positions_in_final[0]]
                                
                                for i in range(1, len(dark_positions_in_final)):
                                    gap = dark_positions_in_final[i] - dark_positions_in_final[i-1]
                                    if gap <= gap_tolerance:
                                        # Part of same group
                                        current_group.append(dark_positions_in_final[i])
                                    else:
                                        # New group
                                        groups.append(current_group)
                                        current_group = [dark_positions_in_final[i]]
                                
                                # Add last group
                                groups.append(current_group)
                                
                                # Find biggest group
                                biggest_group = max(groups, key=len)
                                group_top = min(biggest_group)
                                group_bottom = max(biggest_group)
                                group_middle = (group_top + group_bottom) // 2
                                
                                # Convert to absolute Y
                                absolute_group_middle = top_y + group_middle
                                
                                print(f">>> Biggest RGB(25,25,25) group: {len(biggest_group)} pixels (Y: {group_top} to {group_bottom})")
                                print(f">>> Gap tolerance: {gap_tolerance} pixels, Total groups found: {len(groups)}")
                                
                                # Show arrow at middle of biggest group - YELLOW for black group pixels, pointing RIGHT
                                DEBUG_ARROW(y_coord=absolute_group_middle, area_coords=self.area_coordinates, direction='right', name='biggest_group', color='yellow')
                                
                                # ===== Y-AXIS CONTROL LOGIC =====
                                # Gray middle = absolute_group_middle
                                # White middle = absolute_middle_y
                                gray_middle_y = absolute_group_middle
                                white_middle_y = absolute_middle_y
                                
                                print(f"\n*** CONTROL LOGIC ***")
                                print(f"Gray Middle Y: {gray_middle_y}")
                                print(f"White Middle Y: {white_middle_y}")
                                
                                # ===== Y-AXIS CONTROL LOGIC =====
                                # Gray middle = absolute_group_middle
                                # White middle = absolute_middle_y
                                gray_middle_y = absolute_group_middle
                                white_middle_y = absolute_middle_y
                                
                                print(f"\n*** CONTROL LOGIC ***")
                                print(f"Gray Middle Y: {gray_middle_y}")
                                print(f"White Middle Y: {white_middle_y}")
                                
                                # --- PD CONTROL LOGIC ---
                                current_time = time.time()
                                time_delta = current_time - self.last_time
                                if time_delta == 0: time_delta = 0.001 # Prevent zero division

                                # Error: Positive = White is BELOW Gray (Needs to go DOWN -> RELEASE)
                                #        Negative = White is ABOVE Gray (Needs to go UP -> HOLD)
                                # Note: Y-axis is inverted (0 is top). 
                                # If white_y > gray_y (white is lower), diff is positive.
                                # If white_y < gray_y (white is higher), diff is negative.
                                
                                error = white_middle_y - gray_middle_y
                                
                                # Derivative (Rate of change of error) -> "The Brake"
                                derivative = (error - self.last_error) / time_delta
                                
                                # Control Output
                                # PD Formula: Output = (Kp * Error) + (Kd * Derivative)
                                output = (self.kp * error) + (self.kd * derivative)
                                
                                # Debug info
                                print(f"[PD] Kp={self.kp} | Kd={self.kd} | Thresh={self.pd_threshold}")
                                print(f"Err: {error:.1f} | Deriv: {derivative:.1f} | Out: {output:.1f}")

                                # Update state for next loop
                                self.last_error = error
                                self.last_time = current_time
                                
                                # --- APPLY CONTROL ---
                                # Threshold check (Deadzone)
                                if abs(output) < self.pd_threshold:
                                    # In balance - do nothing (or maintain current state if you prefer spam)
                                    pass 
                                
                                elif output < 0: 
                                    # Negative Output -> Needs to go UP -> HOLD
                                    if not self.click_state:
                                        windll.user32.mouse_event(MOUSE_LEFTDOWN, 0, 0, 0, 0)
                                        self.click_state = True
                                        print("HARDWARE HOLD (PD)")
                                        
                                elif output > 0:
                                    # Positive Output -> Needs to go DOWN -> RELEASE
                                    if self.click_state:
                                        windll.user32.mouse_event(MOUSE_LEFTUP, 0, 0, 0, 0)
                                        self.click_state = False
                                        print("HARDWARE RELEASE (PD)")
                                
                                # Save state to settings
                                self.save_click_state()
                                print(f"Current click state: {'HELD' if self.click_state else 'RELEASED'}")
                                print("=" * 50)
                            else:
                                print(f">>> No RGB(25,25,25) found in final crop for grouping")
                        else:
                            print(f">>> RGB(255,255,255) not found in final crop")
                    else:
                        print(f">>> RGB(25,25,25) not found in vertical slice")
                    return True # Blue found, continue fishing
                else:
                    # Blue color not found - return False to stop fishing loop
                    print("Blue color RGB(85, 170, 255) not found - finishing fishing")
                    
                    # Safety release
                    if self.click_state:
                        windll.user32.mouse_event(MOUSE_LEFTUP, 0, 0, 0, 0)
                        self.click_state = False
                    
                    return False
            else:
                print("PIL not available for processing screenshots.")
                return
        
        # Force GUI update to show debug arrows in real-time
        try:
            self.root.update()
        except:
            pass


    def main_loop(self):
        """Main loop that runs when toggled on"""
        last_kill_check = time.time()
        kill_check_interval = 10  # Check every 10 seconds for blocks
        
        while self.is_running:
            # Check kill switch periodically for LIVE BLOCKING
            if time.time() - last_kill_check > kill_check_interval:
                print("[KILL-SWITCH] Checking if device is blocked...")
                if check_kill_switch():
                    self.is_running = False
                    self.status_label.configure(text="Status: BLOCKED", foreground="#FF0000")
                    send_discord_status("ERROR", "Device was blocked during execution")
                    messagebox.showerror(
                        "Access Denied",
                        "Your device has been BLOCKED by admin.\n\nScript will now close."
                    )
                    self.force_exit()
                    return
                last_kill_check = time.time()
            
            # 1. Hardware safety: Release any previous clicks before starting new cast
            if self.click_state:
                windll.user32.mouse_event(MOUSE_LEFTUP, 0, 0, 0, 0)
                self.click_state = False
                print("[MAIN LOOP] Safety: Click released at start of loop.")

            # 2. Pre-cast stage (Equipping)
            self.pre_cast()
            
            # 3. Waiting stage (Casting + Bite detection)
            # Recast timeout is reset every call because start_time is local in waiting()
            if self.waiting():
                # Bite detected! Enter fishing loop until finished
                print("[MAIN LOOP] Bite detected, entering fishing stage...")
                while self.is_running and self.fishing():
                    time.sleep(0.05)
                
                # 4. Guarantee mouse release after fishing finishes
                if self.click_state:
                    windll.user32.mouse_event(MOUSE_LEFTUP, 0, 0, 0, 0)
                    self.click_state = False
                    print("[MAIN LOOP] Safety: Click released after fishing.")
                
                print(f"[MAIN LOOP] Fishing stage finished. Delay: {self.fish_end_delay}s")
                
                # Check for anti-macro immediately after fishing ends
                self.handle_anti_macro()
                
                self.interruptible_sleep(self.fish_end_delay)
            else:
                # If waiting returns False, it means timeout or reset, loop again
                # Explicitly release here too just in case it timed out while holding
                if self.click_state:
                    windll.user32.mouse_event(MOUSE_LEFTUP, 0, 0, 0, 0)
                    self.click_state = False
                    print("[MAIN LOOP] Safety: Click released after timeout/reset.")
                print("[MAIN LOOP] Resetting to pre-cast...")
                
            time.sleep(0.05)  # Small delay to reduce CPU usage and overshoot
    
    def load_area_coordinates(self):
        """Load area coordinates as relative and convert to absolute"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    # Load click state if available
                    self.click_state = data.get('click_state', False)
                    rel = data.get('area_coordinates')
                    if rel:
                        abs_coords = {
                            'x': int(rel['rx'] * self.screen_width),
                            'y': int(rel['ry'] * self.screen_height),
                            'width': int(rel['rw'] * self.screen_width),
                            'height': int(rel['rh'] * self.screen_height),
                            'sample_color': rel.get('sample_color')
                        }
                        # Recalculate geometry string
                        abs_coords['geometry'] = f"{abs_coords['width']}x{abs_coords['height']}+{abs_coords['x']}+{abs_coords['y']}"
                        return abs_coords
        except Exception:
            pass
        
        # Default relative: X=0.5245, Y=0.3574, W=0.1109, H=0.3315
        d_x, d_y = int(0.5245 * self.screen_width), int(0.3574 * self.screen_height)
        d_w, d_h = int(0.1109 * self.screen_width), int(0.3315 * self.screen_height)
        return {
            'x': d_x, 'y': d_y, 'width': d_w, 'height': d_h,
            'geometry': f"{d_w}x{d_h}+{d_x}+{d_y}",
            'sample_color': {'r': 3, 'g': 66, 'b': 59}
        }
    
    def save_click_state(self):
        """Save click state to settings file"""
        try:
            data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
            
            data['click_state'] = self.click_state
            data['last_click_update'] = datetime.now().isoformat()
            
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving click state: {e}")

    def save_area_coordinates(self):
        """Save absolute area coordinates as relative to settings file"""
        try:
            data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}

            if self.area_coordinates:
                data['area_coordinates'] = {
                    'rx': round(self.area_coordinates['x'] / self.screen_width, 4),
                    'ry': round(self.area_coordinates['y'] / self.screen_height, 4),
                    'rw': round(self.area_coordinates['width'] / self.screen_width, 4),
                    'rh': round(self.area_coordinates['height'] / self.screen_height, 4),
                    'sample_color': self.area_coordinates.get('sample_color')
                }
            
            data['last_updated'] = datetime.now().isoformat()
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def create_area_window(self):
        """Create a green resizable/movable area selector"""
        if self.area_window is not None:
            return

        self.area_window = tk.Toplevel(self.root)
        self.area_window.title("Area Selector")
        # Restore last geometry if available
        geom = self.area_coordinates.get('geometry')
        if geom:
            try:
                self.area_window.geometry(geom)
            except Exception:
                self.area_window.geometry("300x200+100+100")
        else:
            self.area_window.geometry("300x200+100+100")

        self.area_window.attributes('-alpha', 0.4)
        self.area_window.attributes('-topmost', 1)
        self.area_window.overrideredirect(True)

        frame = tk.Frame(self.area_window, bg='green', bd=3, relief='solid')
        frame.pack(expand=True, fill='both')

        label = tk.Label(frame, text='AREA SELECTOR', bg='green', fg='white')
        label.pack(fill='x')

        # movement/resizing state
        self.area_window.moving = False
        self.area_window.resizing = False
        self.area_window.RESIZE_HANDLE_SIZE = 12

        def start_action(event):
            w = self.area_window.winfo_width()
            h = self.area_window.winfo_height()
            on_right = w - self.area_window.RESIZE_HANDLE_SIZE <= event.x <= w
            on_bottom = h - self.area_window.RESIZE_HANDLE_SIZE <= event.y <= h
            if on_right and on_bottom:
                self.area_window.resizing = True
                self.area_window.start_width = w
                self.area_window.start_height = h
                self.area_window.start_x = event.x_root
                self.area_window.start_y = event.y_root
            else:
                self.area_window.moving = True
                self.area_window.start_x = event.x_root
                self.area_window.start_y = event.y_root
                self.area_window.window_x = self.area_window.winfo_x()
                self.area_window.window_y = self.area_window.winfo_y()

        def do_action(event):
            if self.area_window.resizing:
                dx = event.x_root - self.area_window.start_x
                dy = event.y_root - self.area_window.start_y
                new_w = max(self.area_window.start_width + dx, 20)
                new_h = max(self.area_window.start_height + dy, 20)
                x = self.area_window.winfo_x()
                y = self.area_window.winfo_y()
                self.area_window.geometry(f"{new_w}x{new_h}+{x}+{y}")
            elif self.area_window.moving:
                dx = event.x_root - self.area_window.start_x
                dy = event.y_root - self.area_window.start_y
                new_x = self.area_window.window_x + dx
                new_y = self.area_window.window_y + dy
                self.area_window.geometry(f'+{new_x}+{new_y}')

        def stop_action(event):
            self.area_window.moving = False
            self.area_window.resizing = False

        # Bind events
        self.area_window.bind('<ButtonPress-1>', start_action)
        self.area_window.bind('<B1-Motion>', do_action)
        self.area_window.bind('<ButtonRelease-1>', stop_action)
        frame.bind('<ButtonPress-1>', start_action)
        frame.bind('<B1-Motion>', do_action)
        frame.bind('<ButtonRelease-1>', stop_action)

    def close_and_save_area(self):
        """Close area selector, sample color and save geometry"""
        if self.area_window is None:
            return

        x = self.area_window.winfo_x()
        y = self.area_window.winfo_y()
        w = self.area_window.winfo_width()
        h = self.area_window.winfo_height()

        geom = self.area_window.winfo_geometry()
        self.area_coordinates['geometry'] = geom
        self.area_coordinates['x'] = x
        self.area_coordinates['y'] = y
        self.area_coordinates['width'] = w
        self.area_coordinates['height'] = h

        # Try to sample average color inside the box (if PIL available)
        try:
            if PIL_AVAILABLE:
                # ImageGrab uses screen coordinates; box = (left, top, right, bottom)
                img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                # Resize small to speed up average
                thumb = img.resize((50, 50))
                pixels = thumb.getdata()
                r = sum([p[0] for p in pixels]) // len(pixels)
                g = sum([p[1] for p in pixels]) // len(pixels)
                b = sum([p[2] for p in pixels]) // len(pixels)
                self.area_coordinates['sample_color'] = {'r': r, 'g': g, 'b': b}
            else:
                self.area_coordinates['sample_color'] = None
        except Exception as e:
            print(f"Color sampling failed: {e}")
            self.area_coordinates['sample_color'] = None

        # Save to file and close
        self.save_area_coordinates()
        try:
            self.area_window.destroy()
        except Exception:
            pass
        self.area_window = None

    def toggle_change_area(self):
        """Toggle change area mode - show/hide area selector and save on hide"""
        self.change_area_enabled = not self.change_area_enabled
        if self.change_area_enabled:
            self.area_btn.configure(text="SAVE AREA")
            self.log_message("Area selector ENABLED")
            self.create_area_window()
        else:
            self.area_btn.configure(text="CHANGE AREA") # Default blue
            self.log_message("Area selector DISABLED and SAVED")
            self.close_and_save_area()
    
    def toggle_always_on_top(self):
        """Toggle always on top window attribute"""
        self.always_on_top = self.always_on_top_var.get()
        self.root.attributes('-topmost', self.always_on_top)
        self.save_always_on_top()
    
    def load_always_on_top(self):
        """Load always on top state from settings file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    return data.get('always_on_top', False)
        except Exception:
            pass
        return False
    
    def save_always_on_top(self):
        """Save always on top state to settings file"""
        try:
            data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
            
            data['always_on_top'] = self.always_on_top
            
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving always on top state: {e}")
    
    def load_pd_settings(self):
        """Load PD controller settings from settings file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    return data.get('pd_settings', {})
        except Exception:
            pass
        return {}
    
    def save_pd_settings(self):
        """Save PD controller settings to settings file"""
        try:
            data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
            
            data['pd_settings'] = {
                'kp': self.kp,
                'kd': self.kd,
                'threshold': self.pd_threshold,
                'fish_end_delay': self.fish_end_delay
            }
            
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving PD settings: {e}")
    
    def save_pd_settings_gui(self):
        """Save PD settings from GUI and update instance variables"""
        # Update instance variables from GUI
        self.kp = self.kp_var.get()
        self.kd = self.kd_var.get()
        self.pd_threshold = self.threshold_var.get()
        self.fish_end_delay = self.fish_end_delay_var.get()
        
        # Save to file
        self.save_pd_settings()
        
        # Show confirmation
        self.log_message(f"✓ PD Settings saved and applied: Kp={self.kp}, Kd={self.kd}, Threshold={self.pd_threshold}")

    def load_equipment_settings(self):
        """Load equipment hotkeys from settings file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    return data.get('equipment_settings', {})
        except Exception:
            pass
        return {}

    def save_equipment_settings(self):
        """Save equipment hotkeys to settings file"""
        try:
            data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
            
            data['equipment_settings'] = {
                'rod_hotkey': self.rod_hotkey,
                'other_hotkey': self.other_hotkey
            }
            
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving equipment settings: {e}")

    def save_equipment_settings_gui(self):
        """Save equipment settings from GUI and update instance variables"""
        self.rod_hotkey = self.rod_hotkey_var.get()
        self.other_hotkey = self.other_hotkey_var.get()
        self.save_equipment_settings()
        self.log_message(f"✓ Equipment Hotkeys saved: Rod={self.rod_hotkey}, Other={self.other_hotkey}")

    def load_precast_settings(self):
        """Load pre-cast settings and convert relative coordinates to absolute"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    precast = data.get('precast_features', {})
                    
                    # Convert coordinates if they exist
                    for key in ['bait_left_coords', 'bait_middle_coords', 'bait_right_coords', 'store_fruit_coords']:
                        rel = precast.get(key)
                        if rel:
                            precast[key] = self.rel_to_abs(rel['x'], rel['y'])
                    return precast
        except Exception:
            pass
        
        # Default relative values (based on 1920x1080 setup)
        return {
            'auto_buy_bait': True,
            'auto_store_fruit': True,
            'loops_per_purchase': 100,
            'fruit_hotkey': '3',
            'bait_left_coords': self.rel_to_abs(0.4193, 0.8713),
            'bait_middle_coords': self.rel_to_abs(0.5016, 0.8676),
            'bait_right_coords': self.rel_to_abs(0.5818, 0.8667),
            'store_fruit_coords': self.rel_to_abs(0.4990, 0.7657)
        }

    def save_precast_settings(self):
        """Save pre-cast settings with absolute coordinates converted to relative"""
        try:
            data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
            
            # Helper to convert to relative safely
            def to_rel(coords):
                return self.abs_to_rel(coords['x'], coords['y']) if coords else None

            data['precast_features'] = {
                'auto_buy_bait': self.auto_buy_bait,
                'auto_store_fruit': self.auto_store_fruit,
                'auto_select_bait': self.auto_select_bait,
                'select_bait_enabled': self.select_bait_enabled,
                'delay_after_rod': self.delay_after_rod,
                'delay_after_bait': self.delay_after_bait,
                'loops_per_purchase': self.loops_per_purchase,
                'fruit_hotkey': self.fruit_hotkey,
                'bait_left_coords': to_rel(self.bait_left_coords),
                'bait_middle_coords': to_rel(self.bait_middle_coords),
                'bait_right_coords': to_rel(self.bait_right_coords),
                'store_fruit_coords': to_rel(self.store_fruit_coords)
            }
            
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving pre-cast settings: {e}")
    
    def load_casting_settings(self):
        """Load casting settings from settings file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    return data.get('casting_settings', {})
        except Exception:
            pass
        return {}
    
    def save_casting_settings(self):
        """Save casting settings to settings file"""
        try:
            data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
            
            data['casting_settings'] = {
                'cast_hold_duration': self.cast_hold_duration,
                'recast_timeout': self.recast_timeout
            }
            
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving casting settings: {e}")
    
    def save_casting_settings_gui(self):
        """Save casting settings from GUI and update instance variables"""
        # Update instance variables from GUI
        self.cast_hold_duration = self.cast_hold_var.get()
        self.recast_timeout = self.recast_timeout_var.get()
        
        # Save to file
        self.save_casting_settings()
        
        # Show confirmation
        self.log_message(f"Casting Settings saved: Cast Hold={self.cast_hold_duration}s, Recast Timeout={self.recast_timeout}s")
    
    def load_water_point(self):
        """Load water point coordinates as relative and convert to absolute"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    rel = data.get('water_point_coords')
                    if rel:
                        return self.rel_to_abs(rel['x'], rel['y'])
        except Exception:
            pass
        # Default relative: X=0.4943, Y=0.2185
        return self.rel_to_abs(0.4943, 0.2185)
    
    def save_water_point(self):
        """Save absolute water point coordinates as relative to settings file"""
        try:
            data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
            
            if self.water_point_coords:
                data['water_point_coords'] = self.abs_to_rel(
                    self.water_point_coords['x'], 
                    self.water_point_coords['y']
                )
            
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving water point: {e}")
    
    def is_it_black(self, img):
        """Check if more than 50% of the image pixels are RGB(0,0,0)"""
        total_pixels = img.width * img.height
        colors = img.getcolors(total_pixels)
        if not colors: return False
        
        black_count = 0
        for count, color in colors:
            # Check for (0,0,0) or (0,0,0,255) depending on mode
            if color[:3] == (0, 0, 0):
                black_count += count
        
        return (black_count / total_pixels) >= 0.5

    def handle_anti_macro(self):
        """Monitor for black screen and spam hotkey if detected"""
        if not PIL_AVAILABLE or not self.area_coordinates:
            return False

        detected_macro = False
        with mss() as sct:
            while self.is_running:
                # Capture current area
                monitor = {
                    "top": self.area_coordinates['y'],
                    "left": self.area_coordinates['x'],
                    "width": self.area_coordinates['width'],
                    "height": self.area_coordinates['height']
                }
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                if self.is_it_black(img):
                    if not detected_macro:
                        print("[ANTI-MACRO] Anti-macro detected (50%+ black screen). Spamming hotkey...")
                        detected_macro = True
                    
                    # Spam hotkey
                    keyboard.press_and_release(self.other_hotkey)
                    self.interruptible_sleep(0.25)
                else:
                    if detected_macro:
                        print("[ANTI-MACRO] Screen cleared. Resuming.")
                    break # Not black, exit loop
        return detected_macro

    # --- COORDINATE HELPERS (Relative <-> Absolute) ---
    def abs_to_rel(self, x, y):
        """Convert absolute pixel coordinates to relative fractions (0.0 to 1.0)"""
        return {
            'x': round(x / self.screen_width, 4) if self.screen_width > 0 else 0,
            'y': round(y / self.screen_height, 4) if self.screen_height > 0 else 0
        }

    def rel_to_abs(self, rx, ry):
        """Convert relative fractions to absolute pixel coordinates"""
        return {
            'x': int(rx * self.screen_width),
            'y': int(ry * self.screen_height)
        }

    def start_water_point_picker(self):
        """Start picking water point coordinates"""
        if self.active_picker: return
        self.active_picker = "water"
        self.water_point_button.configure(text="Picking...", state="disabled")
        self.create_click_overlay("Click anywhere to set Water Point")

    def start_precast_point_picker(self, point_type):
        """Start picking coordinates for pre-cast features (bait or store fruit)"""
        if self.active_picker: return
        
        btn_map = {
            "left": self.bait_left_btn, 
            "middle": self.bait_middle_btn, 
            "right": self.bait_right_btn,
            "store": self.store_fruit_btn
        }
        
        if point_type == "store":
            self.active_picker = "store_fruit"
            instruction = "Store Fruit Point"
        else:
            self.active_picker = f"bait_{point_type}"
            instruction = f"{point_type.capitalize()} Bait Point"

        btn_map[point_type].configure(text="...", state="disabled")
        self.create_click_overlay(f"Click to set {instruction}")
    
    def create_click_overlay(self, instruction_text):
        """Create a transparent fullscreen overlay to capture clicks"""
        self.overlay = tk.Toplevel(self.root)
        self.overlay.attributes('-fullscreen', True)
        self.overlay.attributes('-topmost', True)
        self.overlay.attributes('-alpha', 0.1) # Slightly visible for feedback
        self.overlay.configure(bg='black')
        
        # Bind click event
        self.overlay.bind('<Button-1>', self.on_overlay_click)
        
        # Add instruction label
        instruction = tk.Label(
            self.overlay, 
            text=f"{instruction_text}\nPress ESC to cancel",
            font=("Arial", 16, "bold"),
            fg="white",
            bg="black"
        )
        instruction.place(relx=0.5, rely=0.5, anchor="center")
        
        # Bind ESC to cancel
        self.overlay.bind('<Escape>', self.cancel_point_pick)
    
    def on_overlay_click(self, event):
        """Handle click on overlay"""
        x, y = event.x_root, event.y_root
        picker_type = self.active_picker
        self.overlay.destroy()
        
        if picker_type == "water":
            self.save_water_point_coords(x, y)
        elif picker_type == "bait_select":
            self.save_bait_point("select", x, y)
        elif picker_type.startswith("bait_"):
            point = picker_type.replace("bait_", "")
            self.save_bait_point_coords(point, x, y)
        elif picker_type == "store_fruit":
            self.save_store_fruit_coords(x, y)
        
        self.active_picker = None
    
    def cancel_point_pick(self, event=None):
        """Cancel coordinate picking"""
        if hasattr(self, 'overlay'):
            self.overlay.destroy()
        
        # Reset UI states
        self.water_point_button.configure(text="Set Water Point", state="normal")
        self.bait_left_btn.configure(text="Set", state="normal")
        self.bait_middle_btn.configure(text="Set", state="normal")
        self.bait_right_btn.configure(text="Set", state="normal")
        self.store_fruit_btn.configure(text="Set", state="normal")
        
        # Reset SelectBait button
        if hasattr(self, 'select_bait_button'):
            self.select_bait_button.configure(text="Set Point", state="normal")
        
        self.active_picker = None
    
    def save_water_point_coords(self, x, y):
        """Save the water point coordinates"""
        self.water_point_coords = {'x': x, 'y': y}
        self.save_water_point()
        self.water_point_label.configure(text=f"X: {x}, Y: {y}", foreground="green")
        self.water_point_button.configure(text="Set Water Point", state="normal")

    def save_bait_point_coords(self, point, x, y):
        """Save bait point coordinates"""
        coords = {'x': x, 'y': y}
        if point == "left":
            self.bait_left_coords = coords
            self.bait_left_label.configure(text=f"X: {x}, Y: {y}", foreground="green")
            self.bait_left_btn.configure(text="Set", state="normal")
        elif point == "middle":
            self.bait_middle_coords = coords
            self.bait_middle_label.configure(text=f"X: {x}, Y: {y}", foreground="green")
            self.bait_middle_btn.configure(text="Set", state="normal")
        elif point == "right":
            self.bait_right_coords = coords
            self.bait_right_label.configure(text=f"X: {x}, Y: {y}", foreground="green")
            self.bait_right_btn.configure(text="Set", state="normal")
        
        self.save_precast_settings()
        print(f"✓ Bait Point ({point}) set to: {x}, {y}")

    def save_store_fruit_coords(self, x, y):
        """Save store fruit coordinates"""
        self.store_fruit_coords = {'x': x, 'y': y}
        self.save_precast_settings()
        self.store_fruit_label.configure(text=f"X: {x}, Y: {y}", foreground="green")
        self.store_fruit_btn.configure(text="Set", state="normal")
        print(f"✓ Store Fruit Point set to: {x}, {y}")
    
    def start_bait_point_picker(self, bait_type):
        """Start picking bait point coordinates"""
        self.active_picker = f"bait_{bait_type}"
        self.select_bait_button.configure(text="Click on screen...", state="disabled")
        self.create_click_overlay(f"Click on Bait position (ESC to cancel)")
    
    def save_bait_point(self, bait_type, x, y):
        """Save bait point coordinates"""
        self.select_bait_coords = {'x': x, 'y': y}
        self.select_bait_label.configure(text=f"X: {x}, Y: {y}", foreground="white")
        self.select_bait_button.configure(text="Set Point", state="normal")
        
        self.save_bait_points()
        self.log_message(f"Bait point saved: X={x}, Y={y}")
    
    def load_bait_points(self):
        """Load bait point coordinates from settings"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    
                    self.select_bait_coords = data.get('select_bait_coords')
                    
                    # Update label
                    if self.select_bait_coords:
                        self.select_bait_label.configure(
                            text=f"X: {self.select_bait_coords['x']}, Y: {self.select_bait_coords['y']}",
                            foreground="white"
                        )
        except Exception as e:
            print(f"Error loading bait points: {e}")
    
    def save_bait_points(self):
        """Save bait point coordinates to settings"""
        try:
            data = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
            
            if self.select_bait_coords:
                data['select_bait_coords'] = self.select_bait_coords
            
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving bait points: {e}")
    
    def save_bait_settings(self):
        """Save bait checkbox state"""
        self.select_bait_enabled = self.select_bait_enabled_var.get()
        self.save_precast_settings()
        print(f"Bait settings saved: Select Bait={self.select_bait_enabled}")
    
    def save_bait_delays(self):
        """Save bait delay settings"""
        try:
            self.delay_after_rod = self.delay_after_rod_var.get()
            self.delay_after_bait = self.delay_after_bait_var.get()
            self.save_precast_settings()
            self.log_message(f"✓ Bait delays saved: After Rod={self.delay_after_rod}s, After Bait={self.delay_after_bait}s")
        except Exception as e:
            self.log_message(f"Error saving delays: {e}")
    
    def discord_heartbeat(self):
        """Send periodic status updates to Discord"""
        while True:
            try:
                time.sleep(60)  # Check every 60 seconds
                
                # Check if device is blocked BEFORE sending heartbeat
                if check_kill_switch():
                    print("[HEARTBEAT] Device is BLOCKED! Shutting down...")
                    self.is_running = False
                    send_discord_status("ERROR", "Device blocked during execution")
                    self.root.after(0, lambda: messagebox.showerror(
                        "Access Denied",
                        "Your device has been BLOCKED by admin.\n\nScript will close now."
                    ))
                    self.root.after(100, self.force_exit)
                    break
                
                if self.is_running:
                    send_discord_status("RUNNING", "Active fishing session")
            except Exception as e:
                print(f"[HEARTBEAT] Error: {e}")
    
    def force_exit(self):
        """Force close the application"""
        print("Force exit requested.")
        try:
            send_discord_status("STOPPED", "Script closed by user")
            time.sleep(0.3)  # Give time for Discord message to send
        except:
            pass
        os.kill(os.getpid(), signal.SIGTERM)
    
    def on_closing(self):
        """Handle window close"""
        try:
            keyboard.clear_all_hotkeys()
            if self.key_listener:
                keyboard.remove_handler(self.key_listener)
        except:
            pass
        self.root.destroy()
        sys.exit(0)

    # --- HARDWARE HELPERS for Game Interaction ---
    def hardware_click(self, coords):
        """Perform a hardware-level click at the given coordinates with anti-Roblox tech"""
        if not coords or not self.is_running:
            return
        
        x, y = coords['x'], coords['y']
        
        print(f"[HARDWARE CLICK] Target: ({x}, {y})")
        # 1. Teleport mouse
        windll.user32.SetCursorPos(x, y)
        time.sleep(0.01)
        
        # 2. 1-pixel relative move (anti-Roblox)
        windll.user32.mouse_event(MOUSE_MOVE, 0, 1, 0, 0)
        time.sleep(0.01)
        
        # 3. Click
        windll.user32.mouse_event(MOUSE_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        windll.user32.mouse_event(MOUSE_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.01)

    def interruptible_sleep(self, seconds):
        """Sleep for a duration while checking self.is_running"""
        start = time.time()
        while time.time() - start < seconds:
            if not self.is_running:
                break
            time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    # Start loading screen which will then launch HotkeyApp
    LoadingScreen(root, lambda: HotkeyApp(root))
    root.mainloop()