"""
UI helper functions for launcher
Contains functions for icons, colors, and other UI utilities
"""
import os
import ctypes
import tkinter as tk
from typing import Optional

try:
    from PIL import Image  # type: ignore
except ImportError:
    Image = None

# Import config with fallback
try:
    from .config import BASE_DIR, DIR_TEMP, COLORS
except (ImportError, ValueError):
    from config import BASE_DIR, DIR_TEMP, COLORS


def get_app_icon_path() -> Optional[str]:
    """Returns path to application icon"""
    icon_path = os.path.join(BASE_DIR, "modules", "Images", "Launcher.ico")
    
    if os.path.exists(icon_path):
        return icon_path
    
    return None


def load_app_icon(window):
    """Loads and sets application icon with improved quality"""
    try:
        icon_path = get_app_icon_path()
        if not icon_path or not os.path.exists(icon_path):
            return
        
        # Try using PIL for conversion to PNG and loading via iconphoto
        if Image is not None:
            try:
                from io import BytesIO
                
                # Load icon through PIL
                img = Image.open(icon_path)
                
                # Convert to RGBA if needed
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Create large version for better quality (256x256)
                large_size = 256
                resized = img.resize((large_size, large_size), Image.Resampling.LANCZOS)
                
                # Save to temporary PNG file
                temp_png = os.path.join(DIR_TEMP, "launcher_icon_temp.png")
                os.makedirs(DIR_TEMP, exist_ok=True)
                resized.save(temp_png, format='PNG')
                
                # Load as PhotoImage
                photo = tk.PhotoImage(file=temp_png)
                window.iconphoto(True, photo)
                # Save reference so image doesn't get garbage collected
                window._icon_photo = photo
                
                # Also set via iconbitmap for compatibility
                window.iconbitmap(icon_path)
                return
            except Exception:
                # If PIL doesn't work, use standard method
                pass
        
        # Standard method via iconbitmap
        window.iconbitmap(icon_path)
        
        # Additionally try to set via Windows API for better quality
        # Delay this until after full window initialization to avoid hanging
        def set_icon_via_api():
            try:
                # Check if window is ready
                try:
                    window.update_idletasks()
                    hwnd = window.winfo_id()
                except:
                    # Window not ready yet, skip
                    return
                
                # Load icon through Windows API
                hicon = ctypes.windll.shell32.ExtractIconW(
                    ctypes.windll.kernel32.GetModuleHandleW(None),
                    icon_path,
                    0
                )
                if hicon:
                    # Set window icon via Windows API
                    ctypes.windll.user32.SendMessageW(
                        hwnd,
                        0x0080,  # WM_SETICON
                        0,  # ICON_SMALL
                        hicon
                    )
                    ctypes.windll.user32.SendMessageW(
                        hwnd,
                        0x0080,  # WM_SETICON
                        1,  # ICON_BIG
                        hicon
                    )
            except:
                pass
        
        # Delay API setting until after initialization
        try:
            window.after(100, set_icon_via_api)
        except:
            pass
            
    except Exception:
        # If nothing worked, just ignore the error
        pass


def show_error(title: str, msg: str):
    """Shows error message dialog"""
    try:
        ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10)
    except:
        print(f"[ERROR] {title}: {msg}", flush=True)



