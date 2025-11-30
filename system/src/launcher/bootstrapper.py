import os
import sys
import subprocess
import threading
import time
import json

try:
    import tkinter as tk
    from tkinter import ttk
    GUI_AVAILABLE = True
except ImportError as e:
    print(f"[ERROR] Failed to import Tkinter: {e}")
    print("This usually means the runtime setup failed to copy Tkinter files.")
    print("Please try deleting the 'system/runtime' folder and running Launch.bat again.")
    GUI_AVAILABLE = False
    input("Press Enter to exit...")
    sys.exit(1)

def check_cache_valid():
    """Check if dependency cache is valid (< 1 hour old)"""
    try:
        appdata = os.environ.get("APPDATA", "")
        cache_file = os.path.join(appdata, "TelegramBotData", "data", "configs", ".bootstrap_cache.json")
        
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            last_check = cache_data.get("last_check", 0)
            # Cache valid for 1 hour
            if time.time() - last_check < 3600:
                return True
    except:
        pass
    return False

def check_missing_packages():
    """Check which packages are missing"""
    required = [
        "customtkinter", 
        "pillow", 
        "requests", 
        "psutil", 
        "pyyaml", 
        "python-dotenv",
        "packaging",
        "cryptography"
    ]
    
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    
    return missing

def install_packages_silent(missing):
    """Install packages without GUI"""
    python_exe = sys.executable
    
    # Install pip if missing
    try:
        subprocess.check_call([python_exe, "-m", "ensurepip", "--default-pip"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

    # Upgrade pip
    subprocess.call([python_exe, "-m", "pip", "install", "--upgrade", "pip"],
                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Install packages
    for pkg in missing:
        subprocess.check_call(
            [python_exe, "-m", "pip", "install", pkg],
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
    
    # Update cache
    try:
        appdata = os.environ.get("APPDATA", "")
        cache_file = os.path.join(appdata, "TelegramBotData", "data", "configs", ".bootstrap_cache.json")
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump({"last_check": time.time()}, f)
    except:
        pass

def launch_launcher():
    """Launch the main launcher application"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        launcher_path = os.path.join(current_dir, "launcher.pyw")
        
        if os.path.exists(launcher_path):
            subprocess.Popen([sys.executable, launcher_path])
        else:
            print(f"Error: launcher.pyw not found at {launcher_path}")
    except Exception as e:
        print(f"Launch Error: {e}")

class Bootstrapper(tk.Tk):
    def __init__(self, missing_packages):
        super().__init__()
        
        self.missing = missing_packages
        
        # Setup window
        self.title("Launcher Bootstrapper")
        self.geometry("400x150")
        self.resizable(False, False)
        
        # Center window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 150) // 2
        self.geometry(f"400x150+{x}+{y}")
        
        # UI Elements
        self.label = tk.Label(self, text="Installing dependencies...", font=("Segoe UI", 10))
        self.label.pack(pady=20)
        
        self.progress = ttk.Progressbar(self, orient="horizontal", length=300, mode="indeterminate")
        self.progress.pack(pady=10)
        
        self.status = tk.Label(self, text="", font=("Segoe UI", 8), fg="gray")
        self.status.pack(pady=5)
        
        # Start installation in thread
        self.progress.start(10)
        threading.Thread(target=self.install_packages, daemon=True).start()

    def update_status(self, text):
        self.label.config(text=text)
    
    def install_packages(self):
        try:
            python_exe = sys.executable
            
            # Install pip if missing
            try:
                subprocess.check_call([python_exe, "-m", "ensurepip", "--default-pip"], 
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

            # Upgrade pip
            subprocess.call([python_exe, "-m", "pip", "install", "--upgrade", "pip"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Install packages
            for pkg in self.missing:
                self.update_status(f"Installing {pkg}...")
                subprocess.check_call(
                    [python_exe, "-m", "pip", "install", pkg],
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
            
            # Update cache
            try:
                appdata = os.environ.get("APPDATA", "")
                cache_file = os.path.join(appdata, "TelegramBotData", "data", "configs", ".bootstrap_cache.json")
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                with open(cache_file, 'w') as f:
                    json.dump({"last_check": time.time()}, f)
            except:
                pass
            
            self.update_status("Starting Launcher...")
            time.sleep(1)
            self.launch_main()
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            print(f"Bootstrapper Error: {e}")
            time.sleep(5)
            self.destroy()
    
    def launch_main(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            launcher_path = os.path.join(current_dir, "launcher.pyw")
            
            if os.path.exists(launcher_path):
                subprocess.Popen([sys.executable, launcher_path])
                self.quit()
            else:
                self.update_status(f"Error: launcher.pyw not found at {launcher_path}")
        except Exception as e:
            self.update_status(f"Launch Error: {e}")

if __name__ == "__main__":
    # Check cache first - if valid, skip GUI entirely
    if check_cache_valid():
        # Silent mode - launch directly
        launch_launcher()
    else:
        # Check what's missing
        missing = check_missing_packages()
        
        if not missing:
            # Nothing to install, update cache and launch
            try:
                appdata = os.environ.get("APPDATA", "")
                cache_file = os.path.join(appdata, "TelegramBotData", "data", "configs", ".bootstrap_cache.json")
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                with open(cache_file, 'w') as f:
                    json.dump({"last_check": time.time()}, f)
            except:
                pass
            launch_launcher()
        else:
            # Show GUI and install
            app = Bootstrapper(missing)
            app.mainloop()
