"""
Main application GUI for the bulk watermarker.
Modern dark-themed interface with CustomTkinter.
Sidebar contains all controls, main area is full-width preview.
"""

import customtkinter as ctk
import threading
from pathlib import Path
from argparse import Namespace
from typing import Optional, List, Tuple
from PIL import Image

from app.theme import COLORS, RADIUS, SPACING, WINDOW, get_font
from app.components.file_selector import FileSelector, SettingsSlider, AnchorSelector
from app.components.preview_panel import PreviewPanel

# Import core logic
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from watermark_bulk import compose_watermarked_image, load_overrides, run_with_args


class WatermarkApp(ctk.CTk):
    """Main application window."""
    
    EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("Watermark-Deksmo")
        self.geometry(f"{WINDOW['default_width']}x{WINDOW['default_height']}")
        self.minsize(WINDOW['min_width'], WINDOW['min_height'])
        
        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Configure window colors
        self.configure(fg_color=COLORS["bg_main"])
        
        # Load logo
        self.logo_image = None
        try:
            logo_path = Path(__file__).parent.parent / "logo-open.png"
            if logo_path.is_file():
                pil_logo = Image.open(logo_path)
                # Resize for header
                pil_logo = pil_logo.resize((36, 36), Image.LANCZOS)
                self.logo_image = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(36, 36))
        except Exception:
            pass
        
        # State
        self.running = False
        self.watermark_image: Optional[Image.Image] = None
        self.chapters: List[Path] = []
        self.pages: List[Path] = []
        self.current_chapter_idx = 0
        self.current_page_idx = 0
        self.chapter_buttons: List[ctk.CTkButton] = []
        self.page_buttons: List[ctk.CTkButton] = []
        self.manual_position: Optional[Tuple[int, int]] = None  # For click-to-position
        
        self._build_ui()
        self._setup_bindings()
    
    def _build_ui(self):
        """Build the main application layout."""
        # Main container
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=SPACING["md"], pady=SPACING["md"])
        
        # Configure grid - sidebar on left, preview takes rest
        main.columnconfigure(0, weight=0, minsize=300)  # Sidebar fixed width
        main.columnconfigure(1, weight=1)                # Preview expands
        main.rowconfigure(0, weight=0)                   # Header
        main.rowconfigure(1, weight=1)                   # Content
        main.rowconfigure(2, weight=0)                   # Footer
        
        # ===== HEADER =====
        header = self._build_header(main)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, SPACING["md"]))
        
        # ===== SIDEBAR (all controls) =====
        sidebar = self._build_sidebar(main)
        sidebar.grid(row=1, column=0, sticky="nsew", padx=(0, SPACING["md"]))
        
        # ===== PREVIEW (full width) =====
        self.preview_panel = PreviewPanel(main, on_position_click=self._on_position_click)
        self.preview_panel.grid(row=1, column=1, sticky="nsew")
        
        # ===== FOOTER =====
        footer = self._build_footer(main)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(SPACING["md"], 0))
    
    def _build_header(self, parent) -> ctk.CTkFrame:
        """Build compact header with logo."""
        header = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=RADIUS["md"], height=56)
        header.pack_propagate(False)
        
        # Logo image
        if self.logo_image:
            logo_label = ctk.CTkLabel(header, image=self.logo_image, text="")
            logo_label.pack(side="left", padx=(SPACING["md"], SPACING["sm"]))
        else:
            # Fallback text logo
            logo = ctk.CTkLabel(header, text="💧", font=get_font("xl"), text_color=COLORS["primary"])
            logo.pack(side="left", padx=SPACING["md"])
        
        # Title
        title = ctk.CTkLabel(
            header, text="WATERMARK-DEKSMO", font=get_font("lg", bold=True),
            text_color=COLORS["text_primary"]
        )
        title.pack(side="left")
        
        # Subtitle
        subtitle = ctk.CTkLabel(
            header, text="Open Source Batch Watermarking", font=get_font("xs"),
            text_color=COLORS["text_muted"]
        )
        subtitle.pack(side="left", padx=(SPACING["sm"], 0))
        
        # Version
        version = ctk.CTkLabel(
            header, text="v1.0", font=get_font("xs"),
            text_color=COLORS["text_muted"], fg_color=COLORS["bg_hover"],
            corner_radius=4, padx=6, pady=2
        )
        version.pack(side="right", padx=SPACING["md"])
        
        return header
    
    def _build_sidebar(self, parent) -> ctk.CTkFrame:
        """Build sidebar with all controls including browser."""
        sidebar = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=RADIUS["md"])
        
        # Scrollable content
        scroll = ctk.CTkScrollableFrame(
            sidebar, fg_color="transparent",
            scrollbar_button_color=COLORS["bg_hover"],
            scrollbar_button_hover_color=COLORS["bg_active"]
        )
        scroll.pack(fill="both", expand=True, padx=SPACING["sm"], pady=SPACING["sm"])
        
        # === FILES SECTION ===
        self._add_section_header(scroll, "📁 FILES")
        
        self.watermark_selector = FileSelector(
            scroll, label="Watermark PNG",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            on_change=self._on_watermark_change
        )
        self.watermark_selector.pack(fill="x", pady=(0, SPACING["sm"]))
        
        self.input_selector = FileSelector(
            scroll, label="Input Folder", is_folder=True,
            on_change=self._on_input_change
        )
        self.input_selector.pack(fill="x", pady=(0, SPACING["sm"]))
        
        self.output_selector = FileSelector(
            scroll, label="Output Folder", is_folder=True
        )
        self.output_selector.pack(fill="x", pady=(0, SPACING["md"]))
        
        # === CHAPTERS SECTION ===
        self._add_section_header(scroll, "📚 CHAPTERS")
        
        self.chapter_frame = ctk.CTkScrollableFrame(
            scroll, fg_color=COLORS["bg_dark"], corner_radius=RADIUS["sm"], height=80
        )
        self.chapter_frame.pack(fill="x", pady=(0, SPACING["md"]))
        
        # === PAGES SECTION ===
        pages_header = ctk.CTkFrame(scroll, fg_color="transparent")
        pages_header.pack(fill="x", pady=(0, 4))
        
        ctk.CTkLabel(pages_header, text="🖼️ PAGES", font=get_font("xs", bold=True),
                     text_color=COLORS["primary"]).pack(side="left")
        
        # Navigation
        nav = ctk.CTkFrame(pages_header, fg_color="transparent")
        nav.pack(side="right")
        
        self.prev_btn = ctk.CTkButton(
            nav, text="◀", width=24, height=20, corner_radius=4,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["primary"],
            font=get_font("xs"), command=lambda: self._shift_page(-1)
        )
        self.prev_btn.pack(side="left", padx=1)
        
        self.page_label = ctk.CTkLabel(nav, text="0/0", font=get_font("xs"),
                                        text_color=COLORS["text_muted"], width=40)
        self.page_label.pack(side="left", padx=2)
        
        self.next_btn = ctk.CTkButton(
            nav, text="▶", width=24, height=20, corner_radius=4,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["primary"],
            font=get_font("xs"), command=lambda: self._shift_page(1)
        )
        self.next_btn.pack(side="left", padx=1)
        
        self.page_frame = ctk.CTkScrollableFrame(
            scroll, fg_color=COLORS["bg_dark"], corner_radius=RADIUS["sm"], height=100
        )
        self.page_frame.pack(fill="x", pady=(0, SPACING["md"]))
        
        # === POSITION SECTION ===
        self._add_section_header(scroll, "📍 POSITION")
        
        self.anchor_selector = AnchorSelector(scroll, default="bottom-right", on_change=self._on_setting_change)
        self.anchor_selector.pack(fill="x", pady=(0, SPACING["sm"]))
        
        self.margin_slider = SettingsSlider(
            scroll, label="Margin", from_=0, to=100, default=16,
            step=1, format_str="{:.0f}", suffix="px", on_change=self._on_setting_change
        )
        self.margin_slider.pack(fill="x", pady=(0, SPACING["md"]))
        
        # === APPEARANCE SECTION ===
        self._add_section_header(scroll, "🎨 APPEARANCE")
        
        self.scale_slider = SettingsSlider(
            scroll, label="Scale", from_=0.05, to=0.75, default=0.25,
            step=0.01, format_str="{:.2f}", on_change=self._on_setting_change
        )
        self.scale_slider.pack(fill="x", pady=(0, SPACING["sm"]))
        
        self.opacity_slider = SettingsSlider(
            scroll, label="Opacity", from_=0.1, to=1.0, default=0.6,
            step=0.05, format_str="{:.0%}", on_change=self._on_setting_change
        )
        self.opacity_slider.pack(fill="x", pady=(0, SPACING["sm"]))
        
        self.quality_slider = SettingsSlider(
            scroll, label="Quality", from_=50, to=100, default=92,
            step=1, format_str="{:.0f}", suffix="%", on_change=self._on_setting_change
        )
        self.quality_slider.pack(fill="x", pady=(0, SPACING["md"]))
        
        # === OPTIONS SECTION ===
        self._add_section_header(scroll, "⚙️ OPTIONS")
        
        # Format
        format_row = ctk.CTkFrame(scroll, fg_color="transparent")
        format_row.pack(fill="x", pady=(0, SPACING["sm"]))
        ctk.CTkLabel(format_row, text="Format", font=get_font("xs"),
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self.format_var = ctk.StringVar(value="jpeg")
        ctk.CTkOptionMenu(
            format_row, values=["jpeg", "png", "keep"], variable=self.format_var,
            width=80, height=24, corner_radius=4, fg_color=COLORS["bg_hover"],
            button_color=COLORS["bg_active"], font=get_font("xs")
        ).pack(side="right")
        
        # Checkboxes
        self.overwrite_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            scroll, text="Overwrite existing", variable=self.overwrite_var,
            font=get_font("xs"), text_color=COLORS["text_secondary"],
            fg_color=COLORS["primary"], height=20
        ).pack(fill="x", anchor="w", pady=2)
        
        self.recursive_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            scroll, text="Include subfolders", variable=self.recursive_var,
            font=get_font("xs"), text_color=COLORS["text_secondary"],
            fg_color=COLORS["primary"], height=20
        ).pack(fill="x", anchor="w", pady=2)
        
        self.selected_only_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            scroll, text="Selected chapter only", variable=self.selected_only_var,
            font=get_font("xs"), text_color=COLORS["text_secondary"],
            fg_color=COLORS["secondary"], height=20
        ).pack(fill="x", anchor="w", pady=2)
        
        return sidebar
    
    def _add_section_header(self, parent, text: str):
        """Add a section header."""
        ctk.CTkLabel(
            parent, text=text, font=get_font("xs", bold=True),
            text_color=COLORS["primary"], anchor="w"
        ).pack(fill="x", pady=(SPACING["sm"], 4))
    
    def _build_footer(self, parent) -> ctk.CTkFrame:
        """Build compact footer."""
        footer = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=RADIUS["md"], height=50)
        footer.pack_propagate(False)
        
        # Status and progress
        status_frame = ctk.CTkFrame(footer, fg_color="transparent")
        status_frame.pack(side="left", fill="both", expand=True, padx=SPACING["md"], pady=SPACING["sm"])
        
        self.status_label = ctk.CTkLabel(
            status_frame, text="Ready", font=get_font("xs"),
            text_color=COLORS["text_secondary"], anchor="w"
        )
        self.status_label.pack(fill="x")
        
        self.progress_bar = ctk.CTkProgressBar(
            status_frame, height=6, corner_radius=3,
            fg_color=COLORS["bg_hover"], progress_color=COLORS["primary"]
        )
        self.progress_bar.pack(fill="x", pady=(4, 0))
        self.progress_bar.set(0)
        
        # Buttons
        btn_frame = ctk.CTkFrame(footer, fg_color="transparent")
        btn_frame.pack(side="right", padx=SPACING["md"], pady=SPACING["sm"])
        
        self.run_btn = ctk.CTkButton(
            btn_frame, text="🚀 Run", width=100, height=32,
            corner_radius=RADIUS["sm"], fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"], font=get_font("sm", bold=True),
            command=self._start_processing
        )
        self.run_btn.pack(side="right")
        
        return footer
    
    def _setup_bindings(self):
        """Set up keyboard shortcuts."""
        self.bind("<F5>", lambda e: self._refresh_preview())
        self.bind("<Left>", lambda e: self._shift_page(-1))
        self.bind("<Right>", lambda e: self._shift_page(1))
    
    # ===== BROWSER METHODS =====
    
    def _on_input_change(self, path: str):
        """Load chapters when input folder changes."""
        if not path:
            return
        
        folder = Path(path)
        if not folder.is_dir():
            return
        
        # Clear existing
        for btn in self.chapter_buttons:
            btn.destroy()
        for btn in self.page_buttons:
            btn.destroy()
        self.chapter_buttons = []
        self.page_buttons = []
        self.chapters = []
        self.pages = []
        
        # Build chapters
        entries = []
        
        # Root images
        root_images = [p for p in folder.iterdir() 
                       if p.is_file() and p.suffix.lower() in self.EXTENSIONS]
        if root_images:
            entries.append(("(All)", folder))
        
        # Subfolders with images
        for sub in sorted([p for p in folder.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
            if any(f.suffix.lower() in self.EXTENSIONS for f in sub.rglob("*") if f.is_file()):
                entries.append((sub.name, sub))
        
        self.chapters = [e[1] for e in entries]
        
        # Create buttons
        for i, (name, _) in enumerate(entries):
            btn = ctk.CTkButton(
                self.chapter_frame, text=name, anchor="w", height=22, corner_radius=4,
                fg_color="transparent", hover_color=COLORS["bg_hover"],
                text_color=COLORS["text_primary"], font=get_font("xs"),
                command=lambda idx=i: self._select_chapter(idx)
            )
            btn.pack(fill="x", pady=1)
            self.chapter_buttons.append(btn)
        
        if entries:
            self._select_chapter(0)
    
    def _select_chapter(self, index: int):
        """Select a chapter and load its pages."""
        if index < 0 or index >= len(self.chapters):
            return
        
        self.current_chapter_idx = index
        chapter = self.chapters[index]
        
        # Highlight
        for i, btn in enumerate(self.chapter_buttons):
            btn.configure(fg_color=COLORS["primary"] if i == index else "transparent")
        
        # Clear pages
        for btn in self.page_buttons:
            btn.destroy()
        self.page_buttons = []
        
        # Load pages
        if chapter == Path(self.input_selector.get()):
            self.pages = sorted(
                [p for p in chapter.iterdir() if p.is_file() and p.suffix.lower() in self.EXTENSIONS],
                key=lambda p: p.name.lower()
            )
        else:
            self.pages = sorted(
                [p for p in chapter.rglob("*") if p.is_file() and p.suffix.lower() in self.EXTENSIONS],
                key=lambda p: p.name.lower()
            )
        
        # Create page buttons
        for i, page in enumerate(self.pages):
            btn = ctk.CTkButton(
                self.page_frame, text=page.name, anchor="w", height=20, corner_radius=3,
                fg_color="transparent", hover_color=COLORS["bg_hover"],
                text_color=COLORS["text_secondary"], font=get_font("xs"),
                command=lambda idx=i: self._select_page(idx)
            )
            btn.pack(fill="x", pady=0)
            self.page_buttons.append(btn)
        
        if self.pages:
            self._select_page(0)
        else:
            self.page_label.configure(text="0/0")
    
    def _select_page(self, index: int):
        """Select a page and update preview."""
        if index < 0 or index >= len(self.pages):
            return
        
        self.current_page_idx = index
        
        for i, btn in enumerate(self.page_buttons):
            if i == index:
                btn.configure(fg_color=COLORS["secondary"], text_color=COLORS["text_primary"])
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["text_secondary"])
        
        self.page_label.configure(text=f"{index+1}/{len(self.pages)}")
        self._refresh_preview()
    
    def _shift_page(self, delta: int):
        """Navigate pages."""
        if not self.pages:
            return
        new_idx = max(0, min(len(self.pages) - 1, self.current_page_idx + delta))
        if new_idx != self.current_page_idx:
            self._select_page(new_idx)
    
    # ===== PREVIEW & PROCESSING =====
    
    def _on_watermark_change(self, path: str):
        """Handle watermark change."""
        if path and Path(path).is_file():
            try:
                self.watermark_image = Image.open(path).convert("RGBA")
                self._refresh_preview()
            except Exception as e:
                self.watermark_image = None
                self.status_label.configure(text=f"Error: {e}")
        else:
            self.watermark_image = None
    
    def _on_setting_change(self, *args):
        """Handle setting change."""
        self._refresh_preview()
    
    def _on_position_click(self, x: int, y: int):
        """Handle click on preview to set manual watermark position."""
        self.manual_position = (x, y)
        self.status_label.configure(text=f"📍 Manual position: ({x}, {y})")
        # Refresh preview with new manual position
        self._refresh_preview()
    
    def _refresh_preview(self):
        """Generate preview."""
        if not self.watermark_image:
            self.preview_panel.show_placeholder("Select a watermark PNG")
            return
        
        if not self.pages or self.current_page_idx >= len(self.pages):
            self.preview_panel.show_placeholder("Select a page to preview")
            return
        
        page = self.pages[self.current_page_idx]
        if not page.is_file():
            return
        
        try:
            args = self._build_args()
            canvas, info = compose_watermarked_image(page, self.watermark_image, args, {})
            self.preview_panel.show_image(canvas, info)
        except Exception as e:
            self.preview_panel.show_placeholder(f"Error: {e}")
    
    def _build_args(self) -> Namespace:
        """Build args from current settings."""
        # Check for manual position from click-to-position
        manual_pos = self.preview_panel.get_manual_position() if hasattr(self, 'preview_panel') else None
        
        # If manual position is set, use it as center anchor with specific offsets
        if manual_pos:
            # Use center anchor and calculate offset from center
            anchor = "top-left"
            offset_x = manual_pos[0]
            offset_y = manual_pos[1]
        else:
            anchor = self.anchor_selector.get()
            offset_x = 0
            offset_y = 0
        
        return Namespace(
            watermark=Path(self.watermark_selector.get()),
            input=Path(self.input_selector.get()) if self.input_selector.get() else Path("."),
            output=Path(self.output_selector.get()) if self.output_selector.get() else Path("."),
            extensions=[".jpg", ".jpeg", ".png"],
            anchor=anchor,
            offset_x=offset_x,
            offset_y=offset_y,
            margin=0 if manual_pos else int(self.margin_slider.get()),
            scale=self.scale_slider.get(),
            opacity=self.opacity_slider.get(),
            quality=int(self.quality_slider.get()),
            format=self.format_var.get(),
            suffix="",
            overwrite=self.overwrite_var.get(),
            dry_run=False,
            sample=None,
            avoid_json=None,
            recursive=self.recursive_var.get(),
        )
    
    def _start_processing(self):
        """Start batch processing."""
        if self.running:
            return
        
        wm = self.watermark_selector.get()
        inp = self.input_selector.get()
        out = self.output_selector.get()
        
        if not wm or not Path(wm).is_file():
            self.status_label.configure(text="⚠️ Select watermark")
            return
        if not inp or not Path(inp).is_dir():
            self.status_label.configure(text="⚠️ Select input folder")
            return
        if not out:
            self.status_label.configure(text="⚠️ Select output folder")
            return
        
        self.running = True
        self.run_btn.configure(state="disabled", text="⏳...")
        self.progress_bar.set(0)
        
        limit_dir = None
        if self.selected_only_var.get() and self.chapters:
            limit_dir = self.chapters[self.current_chapter_idx]
        
        def worker():
            try:
                args = self._build_args()
                run_with_args(args, log=lambda m: self.after(0, lambda: self.status_label.configure(text=m)), limit_dir=limit_dir)
                self.after(0, lambda: self._finish(True))
            except Exception as e:
                self.after(0, lambda: self._finish(False, str(e)))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _finish(self, success: bool, error: str = ""):
        """Handle completion."""
        self.running = False
        self.run_btn.configure(state="normal", text="🚀 Run")
        self.progress_bar.set(1 if success else 0)
        self.status_label.configure(text="✅ Done!" if success else f"❌ {error}")


def main():
    """Entry point."""
    app = WatermarkApp()
    app.mainloop()


if __name__ == "__main__":
    main()
