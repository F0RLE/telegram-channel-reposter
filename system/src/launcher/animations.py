"""
Animation utilities for launcher UI
Enhanced animations for CustomTkinter widgets
"""
import customtkinter as ctk
from typing import Callable, Optional, Tuple
import math


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex color"""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def interpolate_color(start_color: str, end_color: str, factor: float) -> str:
    """Interpolate between two hex colors"""
    start_rgb = hex_to_rgb(start_color)
    end_rgb = hex_to_rgb(end_color)
    r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * factor)
    g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * factor)
    b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * factor)
    return rgb_to_hex((r, g, b))


def fade_in(widget, duration=300, steps=20, callback: Optional[Callable] = None):
    """
    Fade in animation for widget using opacity effect.
    """
    if not hasattr(widget, '_fade_alpha'):
        widget._fade_alpha = 0.0
    
    step_size = 1.0 / steps
    delay = max(1, duration // steps)
    
    # Store original color if frame
    if isinstance(widget, (ctk.CTkFrame, ctk.CTkLabel)) and not hasattr(widget, '_original_fg_color'):
        try:
            widget._original_fg_color = widget.cget('fg_color')
        except:
            widget._original_fg_color = None
    
    def animate():
        widget._fade_alpha += step_size
        if widget._fade_alpha >= 1.0:
            widget._fade_alpha = 1.0
            if callback:
                callback()
            return
        
        # Apply fade effect by adjusting color brightness
        try:
            if hasattr(widget, '_original_fg_color') and widget._original_fg_color:
                if isinstance(widget._original_fg_color, str) and widget._original_fg_color.startswith('#'):
                    # Interpolate from black to original color
                    current_color = interpolate_color('#000000', widget._original_fg_color, widget._fade_alpha)
                    widget.configure(fg_color=current_color)
        except:
            pass
        
        widget.after(delay, animate)
    
    animate()


def fade_out(widget, duration=300, steps=20, callback: Optional[Callable] = None):
    """
    Fade out animation for widget.
    """
    if not hasattr(widget, '_fade_alpha'):
        widget._fade_alpha = 1.0
    
    step_size = 1.0 / steps
    delay = max(1, duration // steps)
    
    # Store original color
    if isinstance(widget, (ctk.CTkFrame, ctk.CTkLabel)) and not hasattr(widget, '_original_fg_color'):
        try:
            widget._original_fg_color = widget.cget('fg_color')
        except:
            widget._original_fg_color = None
    
    def animate():
        widget._fade_alpha -= step_size
        if widget._fade_alpha <= 0.0:
            widget._fade_alpha = 0.0
            if callback:
                callback()
            return
        
        # Apply fade effect
        try:
            if hasattr(widget, '_original_fg_color') and widget._original_fg_color:
                if isinstance(widget._original_fg_color, str) and widget._original_fg_color.startswith('#'):
                    current_color = interpolate_color('#000000', widget._original_fg_color, widget._fade_alpha)
                    widget.configure(fg_color=current_color)
        except:
            pass
        
        widget.after(delay, animate)
    
    animate()


def slide_in(widget, direction='left', distance=50, duration=300, steps=20, callback: Optional[Callable] = None):
    """
    Slide in animation for widget using position offset.
    """
    if not hasattr(widget, '_slide_pos'):
        widget._slide_pos = 0.0
    
    step_size = distance / steps
    delay = max(1, duration // steps)
    
    # Store original position
    if not hasattr(widget, '_original_pos'):
        try:
            info = widget.grid_info()
            if info:
                widget._original_pos = {
                    'row': info.get('row', 0),
                    'column': info.get('column', 0),
                    'sticky': info.get('sticky', ''),
                    'padx': info.get('padx', 0),
                    'pady': info.get('pady', 0)
                }
        except:
            widget._original_pos = {}
    
    def animate():
        widget._slide_pos += step_size
        if widget._slide_pos >= distance:
            widget._slide_pos = distance
            if callback:
                callback()
            return
        
        # Apply slide effect using padx/pady
        try:
            offset = int(distance - widget._slide_pos)
            if direction == 'left':
                widget.grid_configure(padx=(offset, 0))
            elif direction == 'right':
                widget.grid_configure(padx=(0, offset))
            elif direction == 'up':
                widget.grid_configure(pady=(offset, 0))
            elif direction == 'down':
                widget.grid_configure(pady=(0, offset))
        except:
            pass
        
        widget.after(delay, animate)
    
    animate()


def slide_out(widget, direction='left', distance=50, duration=300, steps=20, callback: Optional[Callable] = None):
    """
    Slide out animation for widget.
    """
    if not hasattr(widget, '_slide_pos'):
        widget._slide_pos = distance
    
    step_size = distance / steps
    delay = max(1, duration // steps)
    
    def animate():
        widget._slide_pos -= step_size
        if widget._slide_pos <= 0.0:
            widget._slide_pos = 0.0
            if callback:
                callback()
            return
        
        # Apply slide effect
        try:
            offset = int(widget._slide_pos)
            if direction == 'left':
                widget.grid_configure(padx=(offset, 0))
            elif direction == 'right':
                widget.grid_configure(padx=(0, offset))
            elif direction == 'up':
                widget.grid_configure(pady=(offset, 0))
            elif direction == 'down':
                widget.grid_configure(pady=(0, offset))
        except:
            pass
        
        widget.after(delay, animate)
    
    animate()


def scale_in(widget, start_scale=0.8, duration=300, steps=20, callback: Optional[Callable] = None):
    """
    Scale in animation for widget (zoom effect).
    """
    if not hasattr(widget, '_scale_factor'):
        widget._scale_factor = start_scale
    
    step_size = (1.0 - start_scale) / steps
    delay = max(1, duration // steps)
    
    def animate():
        widget._scale_factor += step_size
        if widget._scale_factor >= 1.0:
            widget._scale_factor = 1.0
            if callback:
                callback()
            return
        
        # Apply scale effect (using corner_radius as visual indicator)
        try:
            if isinstance(widget, ctk.CTkFrame):
                original_radius = getattr(widget, '_original_radius', 12)
                current_radius = int(original_radius * widget._scale_factor)
                widget.configure(corner_radius=current_radius)
        except:
            pass
        
        widget.after(delay, animate)
    
    # Store original corner radius
    if isinstance(widget, ctk.CTkFrame) and not hasattr(widget, '_original_radius'):
        try:
            widget._original_radius = widget.cget('corner_radius')
        except:
            widget._original_radius = 12
    
    animate()


def pulse(widget, min_alpha=0.7, max_alpha=1.0, duration=1000, steps=30):
    """
    Pulse animation for widget (breathing effect).
    """
    if not hasattr(widget, '_pulse_alpha'):
        widget._pulse_alpha = min_alpha
        widget._pulse_direction = 1
    
    step_size = (max_alpha - min_alpha) / (steps / 2)
    delay = max(1, duration // steps)
    
    # Store original color
    if not hasattr(widget, '_original_pulse_color'):
        try:
            widget._original_pulse_color = widget.cget('fg_color')
        except:
            widget._original_pulse_color = None
    
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
            if hasattr(widget, '_original_pulse_color') and widget._original_pulse_color:
                if isinstance(widget._original_pulse_color, str) and widget._original_pulse_color.startswith('#'):
                    # Interpolate between darker and original color
                    darker = interpolate_color('#000000', widget._original_pulse_color, min_alpha)
                    current_color = interpolate_color(darker, widget._original_pulse_color, widget._pulse_alpha)
                    widget.configure(fg_color=current_color)
        except:
            pass
        
        widget.after(delay, animate)
    
    animate()


def button_hover_effect(button, hover_color=None, normal_color=None, duration=150):
    """
    Enhanced hover effect for button with smooth transition.
    """
    if hover_color is None:
        hover_color = '#818cf8'
    if normal_color is None:
        try:
            normal_color = button.cget('fg_color')
        except:
            normal_color = '#6366f1'
    
    def on_enter(e):
        smooth_color_transition(button, 'fg_color', normal_color, hover_color, duration)
    
    def on_leave(e):
        smooth_color_transition(button, 'fg_color', hover_color, normal_color, duration)
    
    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)


def smooth_color_transition(widget, property_name, start_color, end_color, duration=200, steps=15, callback=None):
    """
    Smooth color transition for widget property.
    """
    if not hasattr(widget, '_transition_step'):
        widget._transition_step = 0.0
    
    delay = max(1, duration // steps)
    step_size = 1.0 / steps
    widget._transition_step = 0.0
    
    def animate():
        widget._transition_step += step_size
        if widget._transition_step >= 1.0:
            widget._transition_step = 1.0
            try:
                widget.configure(**{property_name: end_color})
            except:
                pass
            if callback:
                callback()
            return
        
        # Interpolate color
        try:
            if isinstance(start_color, str) and isinstance(end_color, str):
                if start_color.startswith('#') and end_color.startswith('#'):
                    current_color = interpolate_color(start_color, end_color, widget._transition_step)
                    widget.configure(**{property_name: current_color})
        except:
            pass
        
        widget.after(delay, animate)
    
    animate()


def shake(widget, intensity=10, duration=300, steps=10, callback=None):
    """
    Shake animation for widget (error feedback).
    """
    if not hasattr(widget, '_shake_pos'):
        widget._shake_pos = 0
    
    delay = max(1, duration // steps)
    original_x = 0
    
    def animate():
        widget._shake_pos += 1
        if widget._shake_pos >= steps:
            widget._shake_pos = 0
            try:
                widget.grid_configure(padx=(original_x, 0))
            except:
                pass
            if callback:
                callback()
            return
        
        # Apply shake effect
        try:
            offset = int(intensity * math.sin(widget._shake_pos * math.pi * 2 / steps))
            widget.grid_configure(padx=(original_x + offset, 0))
        except:
            pass
        
        widget.after(delay, animate)
    
    animate()


def bounce_in(widget, duration=400, steps=20, callback=None):
    """
    Bounce in animation with elastic effect.
    """
    if not hasattr(widget, '_bounce_step'):
        widget._bounce_step = 0.0
    
    delay = max(1, duration // steps)
    max_scale = 1.2  # Overshoot
    
    def animate():
        widget._bounce_step += 1.0 / steps
        
        if widget._bounce_step >= 1.0:
            widget._bounce_step = 1.0
            if callback:
                callback()
            return
        
        # Elastic easing function
        t = widget._bounce_step
        scale = 1.0 - math.pow(1.0 - t, 3) * (1.0 + max_scale * (1.0 - t))
        
        # Apply scale effect
        try:
            if isinstance(widget, ctk.CTkFrame):
                original_radius = getattr(widget, '_original_radius', 12)
                current_radius = int(original_radius * scale)
                widget.configure(corner_radius=current_radius)
        except:
            pass
        
        widget.after(delay, animate)
    
    # Store original corner radius
    if isinstance(widget, ctk.CTkFrame) and not hasattr(widget, '_original_radius'):
        try:
            widget._original_radius = widget.cget('corner_radius')
        except:
            widget._original_radius = 12
    
    animate()


def stagger_children(parent, animation_func, delay_between=50, **kwargs):
    """
    Apply animation to children widgets with stagger effect.
    """
    children = parent.winfo_children()
    for i, child in enumerate(children):
        def animate_child(w=child, idx=i):
            animation_func(w, **kwargs)
        parent.after(i * delay_between, animate_child)
