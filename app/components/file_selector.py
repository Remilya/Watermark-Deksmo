"""
File/folder selector component with modern styling and drag-drop support.
"""

import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Optional, List

from app.theme import COLORS, RADIUS, SPACING, get_font


class FileSelector(ctk.CTkFrame):
    """Modern file selector with browse button and path display."""
    
    def __init__(
        self,
        master,
        label: str,
        is_folder: bool = False,
        filetypes: Optional[List[tuple]] = None,
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.is_folder = is_folder
        self.filetypes = filetypes or [("All files", "*.*")]
        self.on_change = on_change
        self.path_var = ctk.StringVar()
        
        self._build_ui(label)
    
    def _build_ui(self, label: str):
        # Label
        self.label = ctk.CTkLabel(
            self,
            text=label,
            font=get_font("sm", bold=True),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.label.pack(fill="x", pady=(0, SPACING["xs"]))
        
        # Container for entry and button
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="x")
        container.columnconfigure(0, weight=1)
        
        # Entry field
        self.entry = ctk.CTkEntry(
            container,
            textvariable=self.path_var,
            height=40,
            corner_radius=RADIUS["md"],
            border_width=2,
            border_color=COLORS["border"],
            fg_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
            placeholder_text="Click Browse or drag file here...",
            placeholder_text_color=COLORS["text_muted"],
            font=get_font("sm")
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        
        # Browse button
        icon = "📂" if self.is_folder else "📄"
        self.browse_btn = ctk.CTkButton(
            container,
            text=f"{icon} Browse",
            width=100,
            height=40,
            corner_radius=RADIUS["md"],
            fg_color=COLORS["bg_hover"],
            hover_color=COLORS["bg_active"],
            text_color=COLORS["text_primary"],
            font=get_font("sm"),
            command=self._browse
        )
        self.browse_btn.grid(row=0, column=1)
        
        # Bind path changes
        self.path_var.trace_add("write", self._on_path_change)
    
    def _browse(self):
        if self.is_folder:
            path = filedialog.askdirectory()
        else:
            path = filedialog.askopenfilename(filetypes=self.filetypes)
        
        if path:
            self.path_var.set(path)
    
    def _on_path_change(self, *args):
        path = self.path_var.get()
        
        # Visual validation
        if path:
            p = Path(path)
            is_valid = p.is_dir() if self.is_folder else p.is_file()
            color = COLORS["success"] if is_valid else COLORS["error"]
            self.entry.configure(border_color=color)
        else:
            self.entry.configure(border_color=COLORS["border"])
        
        # Callback
        if self.on_change:
            self.on_change(path)
    
    def get(self) -> str:
        return self.path_var.get()
    
    def set(self, path: str):
        self.path_var.set(path)


class SettingsSlider(ctk.CTkFrame):
    """Modern slider with label and value display."""
    
    def __init__(
        self,
        master,
        label: str,
        from_: float,
        to: float,
        default: float,
        step: float = 0.01,
        format_str: str = "{:.2f}",
        suffix: str = "",
        on_change: Optional[Callable[[float], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.format_str = format_str
        self.suffix = suffix
        self.on_change = on_change
        self.step = step
        
        self._build_ui(label, from_, to, default)
    
    def _build_ui(self, label: str, from_: float, to: float, default: float):
        # Header with label and value
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x")
        
        self.label = ctk.CTkLabel(
            header,
            text=label,
            font=get_font("sm"),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.label.pack(side="left")
        
        self.value_label = ctk.CTkLabel(
            header,
            text=self._format_value(default),
            font=get_font("sm", bold=True),
            text_color=COLORS["primary"],
            anchor="e"
        )
        self.value_label.pack(side="right")
        
        # Slider
        self.slider = ctk.CTkSlider(
            self,
            from_=from_,
            to=to,
            number_of_steps=int((to - from_) / self.step),
            height=16,
            corner_radius=RADIUS["full"],
            button_corner_radius=RADIUS["full"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            progress_color=COLORS["primary"],
            fg_color=COLORS["bg_hover"],
            command=self._on_slide
        )
        self.slider.set(default)
        self.slider.pack(fill="x", pady=(SPACING["xs"], 0))
    
    def _format_value(self, value: float) -> str:
        return self.format_str.format(value) + self.suffix
    
    def _on_slide(self, value: float):
        self.value_label.configure(text=self._format_value(value))
        if self.on_change:
            self.on_change(value)
    
    def get(self) -> float:
        return self.slider.get()
    
    def set(self, value: float):
        self.slider.set(value)
        self.value_label.configure(text=self._format_value(value))


class AnchorSelector(ctk.CTkFrame):
    """Visual anchor position selector grid."""
    
    POSITIONS = [
        ("top-left", "↖"),
        ("top-right", "↗"),
        ("center", "◎"),
        ("bottom-left", "↙"),
        ("bottom-right", "↘"),
    ]
    
    def __init__(
        self,
        master,
        default: str = "bottom-right",
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.on_change = on_change
        self.selected = ctk.StringVar(value=default)
        self.buttons = {}
        
        self._build_ui()
    
    def _build_ui(self):
        # Label
        label = ctk.CTkLabel(
            self,
            text="Anchor Position",
            font=get_font("sm", bold=True),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        label.pack(fill="x", pady=(0, SPACING["sm"]))
        
        # Grid container
        grid = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=RADIUS["lg"])
        grid.pack()
        
        # Layout: 3x3 grid with corners and center
        positions = {
            (0, 0): ("top-left", "↖"),
            (0, 2): ("top-right", "↗"),
            (1, 1): ("center", "◎"),
            (2, 0): ("bottom-left", "↙"),
            (2, 2): ("bottom-right", "↘"),
        }
        
        for (row, col), (anchor, icon) in positions.items():
            btn = ctk.CTkButton(
                grid,
                text=icon,
                width=44,
                height=44,
                corner_radius=RADIUS["sm"],
                font=get_font("lg"),
                fg_color=COLORS["primary"] if anchor == self.selected.get() else COLORS["bg_hover"],
                hover_color=COLORS["primary_hover"],
                text_color=COLORS["text_primary"],
                command=lambda a=anchor: self._select(a)
            )
            btn.grid(row=row, column=col, padx=2, pady=2)
            self.buttons[anchor] = btn
        
        # Fill empty cells
        for row in range(3):
            for col in range(3):
                if (row, col) not in positions:
                    spacer = ctk.CTkFrame(grid, width=44, height=44, fg_color="transparent")
                    spacer.grid(row=row, column=col, padx=2, pady=2)
    
    def _select(self, anchor: str):
        # Update visuals
        for a, btn in self.buttons.items():
            if a == anchor:
                btn.configure(fg_color=COLORS["primary"])
            else:
                btn.configure(fg_color=COLORS["bg_hover"])
        
        self.selected.set(anchor)
        if self.on_change:
            self.on_change(anchor)
    
    def get(self) -> str:
        return self.selected.get()
    
    def set(self, anchor: str):
        self._select(anchor)
