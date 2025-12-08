"""
Theme configuration for the modern watermark GUI.
Enhanced dark theme with glassmorphism and vibrant accents.
"""

# Color Palette - Dark Mode with Glass Effects
COLORS = {
    # Background layers - deeper, richer darks
    "bg_dark": "#050508",       # Darkest - for preview canvas
    "bg_main": "#0d0d14",       # Main window background
    "bg_card": "#16161f",       # Card backgrounds
    "bg_hover": "#1f1f2e",      # Hover states
    "bg_active": "#2a2a40",     # Active/pressed states
    
    # Glass effect colors
    "glass": "#1a1a2855",       # Semi-transparent
    "glass_border": "#4a4a6a",  # Visible border
    
    # Primary accent - Vibrant purple gradient
    "primary": "#9333ea",       # Rich purple
    "primary_hover": "#a855f7", # Lighter purple
    "primary_dark": "#7c22ce",  # Darker purple
    
    # Secondary accent - Electric cyan
    "secondary": "#00d4ff",     # Bright cyan
    "secondary_hover": "#33e0ff", # Lighter
    "secondary_dark": "#00b8e6",  # Darker
    
    # Tertiary - Warm accent
    "tertiary": "#f97316",      # Orange
    
    # Text colors with better contrast
    "text_primary": "#ffffff",   # Pure white for headers
    "text_secondary": "#b0b0c8", # Soft lavender-gray
    "text_muted": "#6a6a8a",     # Muted for hints
    
    # Status colors
    "success": "#22c55e",        # Bright green
    "warning": "#eab308",        # Yellow
    "error": "#ef4444",          # Red
    "info": "#3b82f6",           # Blue
    
    # Border colors - subtle but visible
    "border": "#2a2a40",         # Default border
    "border_light": "#3d3d5c",   # Lighter variant
    "border_glow": "#9333ea55",  # Purple glow effect
}

# Font configuration
FONTS = {
    "family": "Segoe UI",
    "family_mono": "Cascadia Code",
    "size_xs": 10,
    "size_sm": 11,
    "size_base": 13,
    "size_lg": 15,
    "size_xl": 18,
    "size_2xl": 22,
    "size_3xl": 28,
    "weight_normal": "normal",
    "weight_bold": "bold",
}

# Border radius - more rounded for modern feel
RADIUS = {
    "sm": 6,
    "md": 10,
    "lg": 14,
    "xl": 18,
    "full": 9999,
}

# Spacing
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 14,
    "lg": 20,
    "xl": 28,
    "2xl": 40,
}

# Animation timings (ms)
ANIMATION = {
    "fast": 150,
    "normal": 250,
    "slow": 400,
}

# Window configuration
WINDOW = {
    "min_width": 1100,
    "min_height": 750,
    "default_width": 1300,
    "default_height": 850,
}


def get_font(size: str = "base", bold: bool = False) -> tuple:
    """Return font tuple for CustomTkinter."""
    font_size = FONTS.get(f"size_{size}", FONTS["size_base"])
    weight = FONTS["weight_bold"] if bold else FONTS["weight_normal"]
    return (FONTS["family"], font_size, weight)


def get_mono_font(size: str = "base") -> tuple:
    """Return monospace font tuple."""
    font_size = FONTS.get(f"size_{size}", FONTS["size_base"])
    return (FONTS["family_mono"], font_size)
