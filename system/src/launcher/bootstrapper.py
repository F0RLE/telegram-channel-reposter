import os
import sys
import subprocess
import threading
import time

try:
    import tkinter as tk
    from tkinter import ttk
    GUI_AVAILABLE = True
except ImportError as e:
    print(f"[ERROR] Failed to import Tkinter: {e}")
    print("This usually means the runtime setup failed to copy Tkinter files.")
    print("Please try deleting the 'system/runtime' folder and running Launch.bat again.")
    GUI_AVAILABLE = False
    # We will try to continue in console mode or just exit
    input("Press Enter to exit...")
    sys.exit(1)

class Bootstrapper(tk.Tk):
    def __init__(self):
        super().__init__()
        
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
        self.label = tk.Label(self, text="Checking dependencies...", font=("Segoe UI", 10))
        self.label.pack(pady=20)
        
        self.progress = ttk.Progressbar(self, orient="horizontal", length=300, mode="indeterminate")
        self.progress.pack(pady=10)
        
        self.status = tk.Label(self, text="", font=("Segoe UI", 8), fg="gray")
        self.status.pack(pady=5)
        
        # Start installation in thread
        self.progress.start(10)
        threading.Thread(target=self.check_and_install, daemon=True).start()

    def check_and_install(self):
        try:
            # List of required packages
            required = [
                "customtkinter", 
                "pillow", 
                "requests", 
                "psutil", 
                "pyyaml", 
                "python-dotenv",
                "packaging"
            ]
            
            missing = []
            for pkg in required:
                try:
                    __import__(pkg.replace("-", "_"))
                except ImportError:
                    missing.append(pkg)
            
            if missing:
                self.update_status(f"Installing {len(missing)} packages...")
                python_exe = sys.executable
                
                # Install pip if missing (should be there)
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
                    self.update_status(f"Installing {pkg}...")
                    subprocess.check_call(
                        [python_exe, "-m", "pip", "install", pkg],
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL
                    )
            
            self.update_status("Starting Launcher...")
            time.sleep(1)
            self.launch_main()
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            print(f"Bootstrapper Error: {e}")
            time.sleep(5)
            self.destroy()

    def update_status(self, text):
        self.label.config(text=text)
    
    def launch_main(self):
        try:
            # Get path to launcher.pyw
            current_dir = os.path.dirname(os.path.abspath(__file__))
            launcher_path = os.path.join(current_dir, "launcher.pyw")
            
            if os.path.exists(launcher_path):
                # Run launcher
                subprocess.Popen([sys.executable, launcher_path])
                self.quit()
            else:
                self.update_status(f"Error: launcher.pyw not found at {launcher_path}")
        except Exception as e:
            self.update_status(f"Launch Error: {e}")

if __name__ == "__main__":
    app = Bootstrapper()
    app.mainloop()
