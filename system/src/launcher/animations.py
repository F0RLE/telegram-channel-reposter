"""
Animation utilities for launcher UI
"""
import customtkinter as ctk
from typing import Callable, Optional


def fade_in(widget, duration=300, steps=20, callback: Optional[Callable] = None):
    """
    Fade in animation for widget.
    
    Args:
        widget: Widget to animate
        duration: Animation duration in milliseconds
        steps: Number of animation steps
        callback: Optional callback function to call after animation
    """
    if not hasattr(widget, '_fade_alpha'):
        widget._fade_alpha = 0.0
    
    step_size = 1.0 / steps
    delay = duration // steps
    
    def animate():
        widget._fade_alpha += step_size
        if widget._fade_alpha >= 1.0:
            widget._fade_alpha = 1.0
            if callback:
                callback()
            return
        
        # Apply alpha (if widget supports it)
        try:
            if hasattr(widget, 'configure'):
                # For CTkFrame and similar
                current_color = widget.cget('fg_color')
                if isinstance(current_color, str) and current_color.startswith('#'):
                    # Extract RGB and apply alpha
                    r = int(current_color[1:3], 16)
                    g = int(current_color[3:5], 16)
                    b = int(current_color[5:7], 16)
                    # Simple fade effect by adjusting opacity
                    pass  # CustomTkinter doesn't support alpha directly
        except:
            pass
        
        widget.after(delay, animate)
    
    animate()


def slide_in(widget, direction='left', distance=50, duration=300, steps=20):
    """
    Slide in animation for widget.
    
    Args:
        widget: Widget to animate
        direction: 'left', 'right', 'up', 'down'
        distance: Distance to slide in pixels
        duration: Animation duration in milliseconds
        steps: Number of animation steps
    """
    if not hasattr(widget, '_slide_pos'):
        widget._slide_pos = 0.0
    
    step_size = distance / steps
    delay = duration // steps
    
    # Store original position
    if not hasattr(widget, '_original_pos'):
        widget._original_pos = {}
        try:
            info = widget.grid_info()
            if info:
                widget._original_pos = {
                    'row': info.get('row', 0),
                    'column': info.get('column', 0),
                    'rowspan': info.get('rowspan', 1),
                    'columnspan': info.get('columnspan', 1),
                    'sticky': info.get('sticky', ''),
                    'padx': info.get('padx', 0),
                    'pady': info.get('pady', 0)
                }
        except:
            pass
    
    def animate():
        widget._slide_pos += step_size
        if widget._slide_pos >= distance:
            widget._slide_pos = distance
            return
        
        # Apply slide effect
        try:
            if direction == 'left':
                offset = -distance + widget._slide_pos
            elif direction == 'right':
                offset = distance - widget._slide_pos
            elif direction == 'up':
                offset = -distance + widget._slide_pos
            else:  # down
                offset = distance - widget._slide_pos
            
            # CustomTkinter doesn't support direct position animation
            # This is a placeholder for future implementation
        except:
            pass
        
        widget.after(delay, animate)
    
    animate()


def pulse(widget, min_alpha=0.5, max_alpha=1.0, duration=1000, steps=30):
    """
    Pulse animation for widget (fade in/out).
    
    Args:
        widget: Widget to animate
        min_alpha: Minimum alpha value
        max_alpha: Maximum alpha value
        duration: Animation duration in milliseconds (one cycle)
        steps: Number of animation steps
    """
    if not hasattr(widget, '_pulse_alpha'):
        widget._pulse_alpha = min_alpha
        widget._pulse_direction = 1
    
    step_size = (max_alpha - min_alpha) / (steps / 2)
    delay = duration // steps
    
    def animate():
        widget._pulse_alpha += step_size * widget._pulse_direction
        
        if widget._pulse_alpha >= max_alpha:
            widget._pulse_alpha = max_alpha
            widget._pulse_direction = -1
        elif widget._pulse_alpha <= min_alpha:
            widget._pulse_alpha = min_alpha
            widget._pulse_direction = 1
        
        # Apply pulse effect
        try:
            # CustomTkinter doesn't support alpha directly
            # This is a placeholder
            pass
        except:
            pass
        
        widget.after(delay, animate)
    
    animate()


def button_hover_effect(button, hover_color=None, normal_color=None):
    """
    Enhanced hover effect for button.
    
    Args:
        button: Button widget
        hover_color: Color on hover
        normal_color: Normal color
    """
    if hover_color is None:
        hover_color = '#818cf8'
    if normal_color is None:
        normal_color = '#6366f1'
    
    def on_enter(e):
        button.configure(fg_color=hover_color)
    
    def on_leave(e):
        button.configure(fg_color=normal_color)
    
    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)


def smooth_transition(widget, property_name, start_value, end_value, duration=300, steps=20, callback=None):
    """
    Smooth transition for widget property.
    
    Args:
        widget: Widget to animate
        property_name: Property name to animate (e.g., 'fg_color')
        start_value: Start value
        end_value: End value
        duration: Animation duration in milliseconds
        steps: Number of animation steps
        callback: Optional callback function
    """
    if not hasattr(widget, '_transition_step'):
        widget._transition_step = 0
    
    delay = duration // steps
    step_size = 1.0 / steps
    
    def animate():
        widget._transition_step += step_size
        if widget._transition_step >= 1.0:
            widget._transition_step = 1.0
            try:
                widget.configure(**{property_name: end_value})
            except:
                pass
            if callback:
                callback()
            return
        
        # Interpolate value
        try:
            if isinstance(start_value, (int, float)) and isinstance(end_value, (int, float)):
                current_value = start_value + (end_value - start_value) * widget._transition_step
                widget.configure(**{property_name: current_value})
        except:
            pass
        
        widget.after(delay, animate)
    
    animate()

