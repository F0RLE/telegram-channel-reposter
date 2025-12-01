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
    
    def _get_widget(self, textbox):
        """Gets underlying Tkinter widget from CTkTextbox if needed"""
        return textbox._textbox if hasattr(textbox, '_textbox') else textbox

    def setup_console_context_menu(self, textbox):
        """Adds context menu for copying text like in Windows"""
        widget = self._get_widget(textbox)
        
        def show_context_menu(event):
            try:
                # Get selected text
                try:
                    if widget.tag_ranges("sel"):
                        selected = widget.get("sel.first", "sel.last")
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
        widget.bind("<Button-3>", show_context_menu)
        # Standard Windows keyboard shortcuts
        widget.bind("<Control-c>", lambda e: (self.copy_selected(textbox), "break"))
        widget.bind("<Control-a>", lambda e: (self.select_all(textbox), "break"))
        widget.bind("<Control-x>", lambda e: (self.cut_selected(textbox), "break"))
        widget.bind("<Control-v>", lambda e: (self.paste_to_console(textbox), "break"))
        
        # Enable standard text selection with mouse
        widget.bind("<Button-1>", lambda e: widget.focus_set())
    
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
            widget = self._get_widget(textbox)
            text = widget.get("1.0", "end-1c")
            self.parent.clipboard_clear()
            self.parent.clipboard_append(text)
        except:
            pass
    
    def copy_selected(self, textbox) -> bool:
        """Copies selected text"""
        try:
            widget = self._get_widget(textbox)
            if widget.tag_ranges("sel"):
                selected = widget.get("sel.first", "sel.last")
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
            widget = self._get_widget(textbox)
            if widget.tag_ranges("sel"):
                selected = widget.get("sel.first", "sel.last")
                if selected:
                    self.parent.clipboard_clear()
                    self.parent.clipboard_append(selected)
                    widget.configure(state="normal")
                    widget.delete("sel.first", "sel.last")
                    widget.configure(state="normal")
                    return True
        except:
            pass
        return False
    
    def paste_to_console(self, textbox) -> bool:
        """Pastes text from clipboard"""
        try:
            widget = self._get_widget(textbox)
            widget.configure(state="normal")
            clipboard_text = self.parent.clipboard_get()
            if clipboard_text:
                widget.insert("insert", clipboard_text)
            widget.configure(state="normal")
            return True
        except:
            pass
        return False
    
    def select_all(self, textbox):
        """Selects all text"""
        try:
            widget = self._get_widget(textbox)
            widget.focus_set()
            widget.configure(state="normal")
            widget.tag_add("sel", "1.0", "end")
            widget.mark_set("insert", "1.0")
            widget.see("1.0")
            # Keep disabled but selected
            widget.configure(state="disabled") 
        except:
            pass
    
    def clear_single_console(self, textbox):
        """Clears a single console"""
        try:
            widget = self._get_widget(textbox)
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.configure(state="normal")  # Keep normal for text selection
        except:
            pass



