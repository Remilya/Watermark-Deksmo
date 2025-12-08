"""
Preview panel component with click-to-position watermark feature.
"""

import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
from typing import Optional, Callable, Tuple
import tkinter as tk

from app.theme import COLORS, RADIUS, SPACING, get_font


class PreviewPanel(ctk.CTkFrame):
    """Preview panel with click-to-position watermark support."""
    
    def __init__(
        self, 
        master, 
        on_position_click: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=COLORS["bg_card"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=COLORS["border"],
            **kwargs
        )
        
        self.current_image: Optional[Image.Image] = None
        self.original_size: Tuple[int, int] = (0, 0)
        self.photo_image: Optional[ImageTk.PhotoImage] = None
        self.zoom_level = 0  # 0 = fit to window
        self.on_position_click = on_position_click
        self.display_scale = 1.0
        self.image_offset = (0, 0)
        self.manual_mode = False
        self.crosshair_pos: Optional[Tuple[int, int]] = None  # Position in original image coords
        
        self._build_ui()
    
    def _build_ui(self):
        # Header with title and controls
        header = ctk.CTkFrame(self, fg_color="transparent", height=36)
        header.pack(fill="x", padx=SPACING["sm"], pady=(SPACING["sm"], 4))
        header.pack_propagate(False)
        
        title = ctk.CTkLabel(
            header, text="🖼️ Preview", font=get_font("base", bold=True),
            text_color=COLORS["text_primary"]
        )
        title.pack(side="left")
        
        # Manual mode toggle
        self.manual_var = ctk.BooleanVar(value=False)
        self.manual_toggle = ctk.CTkSwitch(
            header, text="Click to Position", variable=self.manual_var,
            font=get_font("xs"), text_color=COLORS["text_secondary"],
            progress_color=COLORS["secondary"], button_color=COLORS["primary"],
            command=self._toggle_manual_mode, width=40
        )
        self.manual_toggle.pack(side="right", padx=(SPACING["sm"], 0))
        
        # Zoom controls
        zoom_frame = ctk.CTkFrame(header, fg_color="transparent")
        zoom_frame.pack(side="right")
        
        self.zoom_out_btn = ctk.CTkButton(
            zoom_frame, text="−", width=26, height=26, corner_radius=4,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["primary"],
            font=get_font("base", bold=True), command=self._zoom_out
        )
        self.zoom_out_btn.pack(side="left", padx=1)
        
        self.zoom_label = ctk.CTkLabel(
            zoom_frame, text="Fit", font=get_font("xs"),
            text_color=COLORS["text_muted"], width=40
        )
        self.zoom_label.pack(side="left", padx=2)
        
        self.zoom_in_btn = ctk.CTkButton(
            zoom_frame, text="+", width=26, height=26, corner_radius=4,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["primary"],
            font=get_font("base", bold=True), command=self._zoom_in
        )
        self.zoom_in_btn.pack(side="left", padx=1)
        
        self.fit_btn = ctk.CTkButton(
            zoom_frame, text="⊞", width=26, height=26, corner_radius=4,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["primary"],
            font=get_font("base"), command=self._fit_to_window
        )
        self.fit_btn.pack(side="left", padx=(4, 8))
        
        # Info bar
        self.info_label = ctk.CTkLabel(
            self, text="Click to set watermark position when manual mode is ON",
            font=get_font("xs"), text_color=COLORS["text_muted"], anchor="w"
        )
        self.info_label.pack(fill="x", padx=SPACING["sm"], pady=(0, 4))
        
        # Canvas container
        self.canvas_frame = ctk.CTkFrame(
            self, fg_color=COLORS["bg_dark"], corner_radius=RADIUS["sm"],
            border_width=1, border_color=COLORS["border"]
        )
        self.canvas_frame.pack(fill="both", expand=True, padx=SPACING["sm"], pady=(0, SPACING["sm"]))
        
        # Canvas
        self.canvas = tk.Canvas(
            self.canvas_frame, bg=COLORS["bg_dark"], highlightthickness=0
        )
        
        # Scrollbars
        self.v_scroll = ctk.CTkScrollbar(self.canvas_frame, command=self.canvas.yview)
        self.h_scroll = ctk.CTkScrollbar(self.canvas_frame, orientation="horizontal", command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        
        self.canvas_frame.rowconfigure(0, weight=1)
        self.canvas_frame.columnconfigure(0, weight=1)
        
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.v_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 2), pady=2)
        self.h_scroll.grid(row=1, column=0, sticky="ew", padx=2, pady=(0, 2))
        
        # Bindings
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)
        
        self._draw_placeholder("Select a watermark and page to preview")
    
    def _toggle_manual_mode(self):
        """Toggle manual positioning mode."""
        self.manual_mode = self.manual_var.get()
        if self.manual_mode:
            self.canvas.configure(cursor="crosshair")
            self.info_label.configure(
                text="🎯 MANUAL MODE: Click anywhere to set watermark position",
                text_color=COLORS["secondary"]
            )
        else:
            self.canvas.configure(cursor="arrow")
            self.crosshair_pos = None
            self.info_label.configure(
                text="Toggle 'Click to Position' to manually place watermark",
                text_color=COLORS["text_muted"]
            )
            self._render_image()
    
    def _on_click(self, event):
        """Handle click to set position."""
        if not self.manual_mode or not self.current_image:
            return
        
        # Convert canvas click to original image coordinates
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Subtract image offset and scale to original coordinates
        img_x = int((canvas_x - self.image_offset[0]) / self.display_scale)
        img_y = int((canvas_y - self.image_offset[1]) / self.display_scale)
        
        # Clamp to image bounds
        img_x = max(0, min(self.original_size[0], img_x))
        img_y = max(0, min(self.original_size[1], img_y))
        
        self.crosshair_pos = (img_x, img_y)
        
        # Update info
        self.info_label.configure(
            text=f"🎯 Position set: ({img_x}, {img_y}) - Click 'Run' to apply",
            text_color=COLORS["success"]
        )
        
        # Redraw with crosshair
        self._render_image()
        
        # Callback
        if self.on_position_click:
            self.on_position_click(img_x, img_y)
    
    def _on_motion(self, event):
        """Show coordinates on hover in manual mode."""
        if not self.manual_mode or not self.current_image:
            return
        
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        img_x = int((canvas_x - self.image_offset[0]) / self.display_scale)
        img_y = int((canvas_y - self.image_offset[1]) / self.display_scale)
        
        if 0 <= img_x <= self.original_size[0] and 0 <= img_y <= self.original_size[1]:
            pos_text = f"({img_x}, {img_y})"
            if self.crosshair_pos:
                self.info_label.configure(
                    text=f"🎯 Current: {self.crosshair_pos} | Hover: {pos_text}",
                    text_color=COLORS["success"]
                )
            else:
                self.info_label.configure(
                    text=f"🎯 Click to set position: {pos_text}",
                    text_color=COLORS["secondary"]
                )
    
    def _draw_placeholder(self, text: str):
        """Draw placeholder text."""
        self.canvas.delete("all")
        self.canvas.update_idletasks()
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 300)
        
        self.canvas.create_text(
            w // 2, h // 2 - 20, text="🖼️", font=("Segoe UI", 48), fill=COLORS["text_muted"]
        )
        self.canvas.create_text(
            w // 2, h // 2 + 40, text=text, font=get_font("base"), fill=COLORS["text_muted"]
        )
    
    def show_image(self, image: Image.Image, info: str = ""):
        """Display image."""
        self.current_image = image
        self.original_size = image.size
        base_info = f"Size: {image.width}×{image.height}"
        if not self.manual_mode:
            self.info_label.configure(text=info or base_info, text_color=COLORS["text_muted"])
        self.zoom_level = 0
        self._render_image()
    
    def show_placeholder(self, text: str = "No preview"):
        """Show placeholder."""
        self.current_image = None
        self.info_label.configure(text=text, text_color=COLORS["text_muted"])
        self._draw_placeholder(text)
    
    def _render_image(self):
        """Render image with optional crosshair."""
        if not self.current_image:
            return
        
        self.canvas.update_idletasks()
        canvas_w = max(self.canvas.winfo_width(), 100)
        canvas_h = max(self.canvas.winfo_height(), 100)
        
        img_w, img_h = self.current_image.size
        
        if self.zoom_level == 0:
            scale_w = (canvas_w - 16) / img_w
            scale_h = (canvas_h - 16) / img_h
            scale = min(scale_w, scale_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            self.display_scale = scale
            self.zoom_label.configure(text=f"{int(scale * 100)}%")
        else:
            new_w = int(img_w * self.zoom_level)
            new_h = int(img_h * self.zoom_level)
            self.display_scale = self.zoom_level
            self.zoom_label.configure(text=f"{int(self.zoom_level * 100)}%")
        
        new_w = max(50, new_w)
        new_h = max(50, new_h)
        
        # Resize
        scaled = self.current_image.resize((new_w, new_h), Image.LANCZOS)
        
        # Draw crosshair if in manual mode
        if self.manual_mode and self.crosshair_pos:
            draw_img = scaled.copy()
            draw = ImageDraw.Draw(draw_img)
            
            # Convert original coords to scaled coords
            cx = int(self.crosshair_pos[0] * self.display_scale)
            cy = int(self.crosshair_pos[1] * self.display_scale)
            
            # Draw crosshair
            line_color = (0, 212, 255)  # Cyan
            draw.line([(cx - 20, cy), (cx + 20, cy)], fill=line_color, width=2)
            draw.line([(cx, cy - 20), (cx, cy + 20)], fill=line_color, width=2)
            draw.ellipse([(cx - 8, cy - 8), (cx + 8, cy + 8)], outline=line_color, width=2)
            
            scaled = draw_img
        
        self.photo_image = ImageTk.PhotoImage(scaled)
        
        self.canvas.delete("all")
        
        # Center image
        x = max(0, (canvas_w - new_w) // 2)
        y = max(0, (canvas_h - new_h) // 2)
        self.image_offset = (x, y)
        
        self.canvas.create_image(x, y, anchor="nw", image=self.photo_image)
        self.canvas.configure(scrollregion=(0, 0, max(canvas_w, new_w), max(canvas_h, new_h)))
    
    def _fit_to_window(self):
        self.zoom_level = 0
        self._render_image()
    
    def _zoom_in(self):
        if self.zoom_level == 0 and self.current_image:
            canvas_w = max(self.canvas.winfo_width(), 100)
            canvas_h = max(self.canvas.winfo_height(), 100)
            scale_w = canvas_w / self.current_image.width
            scale_h = canvas_h / self.current_image.height
            self.zoom_level = min(scale_w, scale_h)
        self.zoom_level = min(4.0, self.zoom_level * 1.25)
        self._render_image()
    
    def _zoom_out(self):
        if self.zoom_level == 0 and self.current_image:
            canvas_w = max(self.canvas.winfo_width(), 100)
            canvas_h = max(self.canvas.winfo_height(), 100)
            scale_w = canvas_w / self.current_image.width
            scale_h = canvas_h / self.current_image.height
            self.zoom_level = min(scale_w, scale_h)
        self.zoom_level = max(0.1, self.zoom_level / 1.25)
        self._render_image()
    
    def _on_canvas_resize(self, event):
        if self.zoom_level == 0 and self.current_image:
            self.after(50, self._render_image)
    
    def _on_mousewheel(self, event):
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()
    
    def get_manual_position(self) -> Optional[Tuple[int, int]]:
        """Get the manually set position, or None if not set."""
        return self.crosshair_pos if self.manual_mode else None
    
    def clear_manual_position(self):
        """Clear the manual position."""
        self.crosshair_pos = None
        if self.current_image:
            self._render_image()
