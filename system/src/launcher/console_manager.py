"""
Console management module for launcher
Handles console operations, context menus, and clipboard operations
"""
import tkinter as tk
from typing import Optional

try:
    from .i18n import t
except (ImportError, ValueError):
    try:
        from i18n import t
    except ImportError:
        def t(key, default=None, **kwargs):
            return default or key

# Import config with fallback
try:
    from .config import COLORS
except (ImportError, ValueError):
    from config import COLORS


class ConsoleManager:
    """Manages console operations and context menus"""
    
    def __init__(self, parent_window):
        self.parent = parent_window
    
    def setup_console_context_menu(self, textbox):
        """Adds context menu for copying text like in Windows"""
        def show_context_menu(event):
            try:
                # Get selected text
                try:
                    if textbox.tag_ranges("sel"):
                        selected = textbox.get("sel.first", "sel.last")
                    else:
                        selected = None
                except:
                    selected = None
                
                # Create menu
                menu = tk.Menu(
                    self.parent,
                    tearoff=0,
                    bg=COLORS['surface_light'],
                    fg=COLORS['text'],
                    activebackground=COLORS['primary'],
                    activeforeground='white',
                    font=("Segoe UI", 10)
                )
                
                if selected:
                    menu.add_command(
                        label=t("ui.launcher.console.copy", default="Копировать"),
                        command=lambda: self.copy_selected(textbox)
                    )
                else:
                    menu.add_command(
                        label=t("ui.launcher.console.copy_all", default="Копировать всё"),
                        command=lambda: self.copy_all_to_clipboard(textbox)
                    )
                
                menu.add_separator()
                menu.add_command(
                    label=t("ui.launcher.console.select_all", default="Выделить всё"),
                    command=lambda: self.select_all(textbox)
                )
                menu.add_separator()
                menu.add_command(
                    label=t("ui.launcher.console.clear", default="Очистить"),
                    command=lambda: self.clear_single_console(textbox)
                )
                
                # Show menu
                menu.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass
        
        # Bind right mouse button
        textbox.bind("<Button-3>", show_context_menu)
        # Standard Windows keyboard shortcuts
        textbox.bind("<Control-c>", lambda e: (self.copy_selected(textbox), "break"))
        textbox.bind("<Control-a>", lambda e: (self.select_all(textbox), "break"))
        textbox.bind("<Control-x>", lambda e: (self.cut_selected(textbox), "break"))
        textbox.bind("<Control-v>", lambda e: (self.paste_to_console(textbox), "break"))
        
        # Enable standard text selection with mouse
        textbox.bind("<Button-1>", lambda e: textbox.focus_set())
    
    def copy_to_clipboard(self, text: str):
        """Copies text to clipboard"""
        try:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(text)
        except:
            pass
    
    def copy_all_to_clipboard(self, textbox):
        """Copies all text from console"""
        try:
            text = textbox.get("1.0", "end-1c")
            self.parent.clipboard_clear()
            self.parent.clipboard_append(text)
        except:
            pass
    
    def copy_selected(self, textbox) -> bool:
        """Copies selected text"""
        try:
            if textbox.tag_ranges("sel"):
                selected = textbox.get("sel.first", "sel.last")
                if selected:
                    self.parent.clipboard_clear()
                    self.parent.clipboard_append(selected)
                    return True
        except:
            pass
        return False
    
    def cut_selected(self, textbox) -> bool:
        """Cuts selected text"""
        try:
            if textbox.tag_ranges("sel"):
                selected = textbox.get("sel.first", "sel.last")
                if selected:
                    self.parent.clipboard_clear()
                    self.parent.clipboard_append(selected)
                    textbox.configure(state="normal")
                    textbox.delete("sel.first", "sel.last")
                    textbox.configure(state="normal")
                    return True
        except:
            pass
        return False
    
    def paste_to_console(self, textbox) -> bool:
        """Pastes text from clipboard"""
        try:
            textbox.configure(state="normal")
            clipboard_text = self.parent.clipboard_get()
            if clipboard_text:
                textbox.insert("insert", clipboard_text)
            textbox.configure(state="normal")
            return True
        except:
            pass
        return False
    
    def select_all(self, textbox):
        """Selects all text"""
        try:
            textbox.configure(state="normal")
            textbox.tag_add("sel", "1.0", "end")
            textbox.mark_set("insert", "1.0")
            textbox.see("1.0")
            textbox.configure(state="normal")
        except:
            pass
    
    def clear_single_console(self, textbox):
        """Clears a single console"""
        try:
            textbox.configure(state="normal")
            textbox.delete("1.0", "end")
            textbox.configure(state="normal")  # Keep normal for text selection
        except:
            pass



