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
        
        # v1.2: Setup workspace folders
        self.workspace_dir = Path(__file__).parent.parent / "workspace"
        self.default_input = self.workspace_dir / "input"
        self.default_output = self.workspace_dir / "output"
        self._ensure_workspace()
        
        # State
        self.running = False
        self.watermark_image: Optional[Image.Image] = None
        self.chapters: List[Path] = []
        self.pages: List[Path] = []
        self.current_chapter_idx = 0
        self.current_page_idx = 0
        self.chapter_buttons: List[ctk.CTkButton] = []
        self.chapter_checkboxes: List[ctk.CTkCheckBox] = []  # v1.1: Chapter selection
        self.chapter_check_vars: List[ctk.BooleanVar] = []   # v1.1: Checkbox states
        self.page_buttons: List[ctk.CTkButton] = []
        self.manual_position: Optional[Tuple[int, int]] = None  # For click-to-position
        self.page_positions: dict = {}  # v1.1: {filename: (x, y)} per-page positions
        self.page_settings: dict = {}   # v1.2: {filename: {scale, opacity}} per-page settings
        self.show_popup_var = ctk.BooleanVar(value=True)  # v1.2: Show completion popup
        self.processing_start_time = 0  # v1.2: Track processing time
        
        self._build_ui()
        self._setup_bindings()
        self._apply_workspace_defaults()
    
    def _ensure_workspace(self):
        """Create workspace folders if they don't exist."""
        self.default_input.mkdir(parents=True, exist_ok=True)
        self.default_output.mkdir(parents=True, exist_ok=True)
    
    def _apply_workspace_defaults(self):
        """Apply default workspace folders."""
        # Set default input/output if not already set
        self.input_selector.set(str(self.default_input))
        self.output_selector.set(str(self.default_output))
    
    def _setup_bindings(self):
        """Setup keyboard shortcuts."""
        # Arrow keys for page navigation
        self.bind("<Left>", lambda e: self._shift_page(-1))
        self.bind("<Right>", lambda e: self._shift_page(1))
        # Ctrl+S to save position
        self.bind("<Control-s>", lambda e: self._save_page_position())
    
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
        
        # ===== PREVIEW WITH CONTROLS =====
        preview_container = ctk.CTkFrame(main, fg_color="transparent")
        preview_container.grid(row=1, column=1, sticky="nsew")
        preview_container.rowconfigure(0, weight=1)  # Preview expands
        preview_container.rowconfigure(1, weight=0)  # Controls fixed
        preview_container.columnconfigure(0, weight=1)
        
        # Preview panel
        self.preview_panel = PreviewPanel(preview_container, on_position_click=self._on_position_click)
        self.preview_panel.grid(row=0, column=0, sticky="nsew")
        
        # v1.2: Expandable position controls - collapsed by default, expands on hover
        self.controls_expanded = False
        self.pos_controls = ctk.CTkFrame(preview_container, fg_color=COLORS["bg_dark"], 
                                          corner_radius=RADIUS["md"], height=50,
                                          border_width=1, border_color=COLORS["border"])
        self.pos_controls.grid(row=1, column=0, sticky="ew", pady=(SPACING["sm"], 0))
        self.pos_controls.pack_propagate(False)
        
        # --- TOP ROW (always visible): Navigation ---
        top_row = ctk.CTkFrame(self.pos_controls, fg_color="transparent")
        top_row.pack(fill="x", pady=(SPACING["xs"], 0))
        
        # Page navigation arrows
        self.prev_page_btn = ctk.CTkButton(
            top_row, text="◀", width=36, height=32,
            corner_radius=RADIUS["md"], fg_color=COLORS["bg_hover"], 
            hover_color=COLORS["primary"], font=get_font("lg"),
            command=lambda: self._shift_page(-1)
        )
        self.prev_page_btn.pack(side="left", padx=(SPACING["sm"], 4))
        
        self.preview_page_label = ctk.CTkLabel(
            top_row, text="1/1", font=get_font("sm", bold=True),
            text_color=COLORS["text_primary"], width=50
        )
        self.preview_page_label.pack(side="left", padx=4)
        
        self.next_page_btn = ctk.CTkButton(
            top_row, text="▶", width=36, height=32,
            corner_radius=RADIUS["md"], fg_color=COLORS["bg_hover"], 
            hover_color=COLORS["primary"], font=get_font("lg"),
            command=lambda: self._shift_page(1)
        )
        self.next_page_btn.pack(side="left", padx=(4, SPACING["md"]))
        
        # Hint text (collapsed state)
        self.expand_hint = ctk.CTkLabel(
            top_row, text="▲ Hover for controls", font=get_font("xs"),
            text_color=COLORS["text_muted"]
        )
        self.expand_hint.pack(side="left", padx=SPACING["md"])
        
        # Position count (right side of top row)
        self.pos_count_label = ctk.CTkLabel(
            top_row, text="📍 0 saved", font=get_font("xs"),
            text_color=COLORS["text_muted"]
        )
        self.pos_count_label.pack(side="right", padx=SPACING["md"])
        
        # --- BOTTOM ROW (hidden until hover): Settings Grid ---
        self.bottom_row = ctk.CTkFrame(self.pos_controls, fg_color="transparent")
        # Initially hidden - will pack on hover
        
        sep = ctk.CTkFrame(self.bottom_row, height=1, fg_color=COLORS["border"])
        sep.pack(fill="x", padx=SPACING["md"], pady=(4, 4))
        
        # Grid container for settings
        grid_frame = ctk.CTkFrame(self.bottom_row, fg_color="transparent")
        grid_frame.pack(fill="x", padx=SPACING["sm"], pady=(0, 4))
        
        # Left Column: Buttons (Save/Clear)
        col1 = ctk.CTkFrame(grid_frame, fg_color="transparent")
        col1.pack(side="left", fill="y", padx=(0, SPACING["md"]))
        
        self.save_pos_btn = ctk.CTkButton(
            col1, text="💾 Save Page Settings", height=32, width=160,
            corner_radius=6, fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"],
            font=get_font("sm", bold=True), command=self._save_page_position
        )
        self.save_pos_btn.pack(fill="x", pady=(0, 4))
        
        row_clear = ctk.CTkFrame(col1, fg_color="transparent")
        row_clear.pack(fill="x")
        
        self.clear_pos_btn = ctk.CTkButton(
            row_clear, text="🗑️ Clear Page", height=28, width=100,
            corner_radius=4, fg_color=COLORS["bg_hover"], hover_color=COLORS["error"],
            font=get_font("xs"), command=self._clear_page_position
        )
        self.clear_pos_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        self.clear_all_btn = ctk.CTkButton(
            row_clear, text="Clear All", height=28, width=70,
            corner_radius=4, fg_color=COLORS["bg_hover"], hover_color=COLORS["error"],
            font=get_font("xs"), command=self._clear_all_positions
        )
        self.clear_all_btn.pack(side="left")

        # Middle Column: Position (Anchor + Margin)
        col2 = ctk.CTkFrame(grid_frame, fg_color="transparent")
        col2.pack(side="left", fill="y", padx=(0, SPACING["md"]))
        
        ctk.CTkLabel(col2, text="📍 POSITION", font=get_font("xs", bold=True),
                     text_color=COLORS["primary"]).pack(anchor="w")
        
        self.anchor_selector = AnchorSelector(col2, default="bottom-right", on_change=self._on_setting_change)
        self.anchor_selector.pack(anchor="w", pady=(0, 4))
        
        self.margin_slider = SettingsSlider(
            col2, label="Margin", from_=0, to=100, default=16, width=140,
            step=1, format_str="{:.0f}", suffix="px", on_change=self._on_setting_change
        )
        self.margin_slider.pack(anchor="w")

        # Right Column: Appearance (Scale, Opacity, Quality)
        col3 = ctk.CTkFrame(grid_frame, fg_color="transparent")
        col3.pack(side="left", fill="both", expand=True)
        
        ctk.CTkLabel(col3, text="🎨 APPEARANCE", font=get_font("xs", bold=True),
                     text_color=COLORS["primary"]).pack(anchor="w")
        
        self.scale_slider = SettingsSlider(
            col3, label="Scale", from_=0.05, to=0.75, default=0.25, width=180,
            step=0.01, format_str="{:.2f}", on_change=self._on_setting_change
        )
        self.scale_slider.pack(fill="x", pady=(0, 2))
        
        self.opacity_slider = SettingsSlider(
            col3, label="Opacity", from_=0.1, to=1.0, default=0.6, width=180,
            step=0.05, format_str="{:.0%}", on_change=self._on_setting_change
        )
        self.opacity_slider.pack(fill="x", pady=(0, 2))
        
        self.quality_slider = SettingsSlider(
            col3, label="Quality", from_=50, to=100, default=92, width=180,
            step=1, format_str="{:.0f}", suffix="%", on_change=self._on_setting_change
        )
        self.quality_slider.pack(fill="x", pady=(0, 2))
        
        # Hover effect - expand/collapse
        def on_controls_enter(e):
            if not self.controls_expanded:
                self.controls_expanded = True
                self.pos_controls.configure(height=240, fg_color=COLORS["bg_card"], 
                                             border_color=COLORS["secondary"])
                self.bottom_row.pack(fill="x")
                self.expand_hint.pack_forget()
        
        def on_controls_leave(e):
            # Check if mouse is still inside
            x, y = self.pos_controls.winfo_pointerxy()
            widget_x = self.pos_controls.winfo_rootx()
            widget_y = self.pos_controls.winfo_rooty()
            widget_w = self.pos_controls.winfo_width()
            widget_h = self.pos_controls.winfo_height()
            
            # Add lighter tolerance for smoother exit
            if not (widget_x <= x <= widget_x + widget_w and widget_y <= y <= widget_y + widget_h):
                self.controls_expanded = False
                self.pos_controls.configure(height=50, fg_color=COLORS["bg_dark"], 
                                             border_color=COLORS["border"])
                self.bottom_row.pack_forget()
                self.expand_hint.pack(side="left", padx=SPACING["md"])
        
        self.pos_controls.bind("<Enter>", on_controls_enter)
        self.pos_controls.bind("<Leave>", on_controls_leave)
        
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
            header, text="v1.2", font=get_font("xs"),
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
        self.output_selector.pack(fill="x", pady=(0, SPACING["sm"]))
        
        # v1.2: Workspace buttons
        workspace_btns = ctk.CTkFrame(scroll, fg_color="transparent")
        workspace_btns.pack(fill="x", pady=(0, SPACING["md"]))
        
        self.open_workspace_btn = ctk.CTkButton(
            workspace_btns, text="📂 Open Folder", height=28, corner_radius=6,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["bg_active"],
            font=get_font("xs"), command=self._open_workspace
        )
        self.open_workspace_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        self.refresh_btn = ctk.CTkButton(
            workspace_btns, text="🔄 Refresh", height=28, corner_radius=6,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["primary"],
            font=get_font("xs"), command=self._refresh_input
        )
        self.refresh_btn.pack(side="left", fill="x", expand=True)
        
        # === CHAPTERS SECTION ===
        chapters_header = ctk.CTkFrame(scroll, fg_color="transparent")
        chapters_header.pack(fill="x", pady=(SPACING["sm"], 4))
        
        ctk.CTkLabel(chapters_header, text="📚 CHAPTERS", font=get_font("xs", bold=True),
                     text_color=COLORS["primary"]).pack(side="left")
        
        # v1.1: Select All/None buttons
        ch_btns = ctk.CTkFrame(chapters_header, fg_color="transparent")
        ch_btns.pack(side="right")
        
        ctk.CTkButton(
            ch_btns, text="All", width=32, height=18, corner_radius=3,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["primary"],
            font=get_font("xs"), command=self._select_all_chapters
        ).pack(side="left", padx=1)
        
        ctk.CTkButton(
            ch_btns, text="None", width=36, height=18, corner_radius=3,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["secondary"],
            font=get_font("xs"), command=self._deselect_all_chapters
        ).pack(side="left", padx=1)
        
        self.chapter_select_label = ctk.CTkLabel(
            ch_btns, text="0/0", font=get_font("xs"), text_color=COLORS["text_muted"], width=35
        )
        self.chapter_select_label.pack(side="left", padx=(4, 0))
        
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
            scroll, fg_color=COLORS["bg_dark"], corner_radius=RADIUS["sm"], height=80
        )
        self.page_frame.pack(fill="x", pady=(0, SPACING["md"]))
        
        # Note: PAGE POSITION controls moved to preview area in v1.2
        
        # Note: POSITION and APPEARANCE settings moved to preview drawer in v1.2
        
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
        
        # v1.2: Show popup when done
        ctk.CTkCheckBox(
            scroll, text="Show popup when done", variable=self.show_popup_var,
            font=get_font("xs"), text_color=COLORS["text_secondary"],
            fg_color=COLORS["tertiary"], height=20
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
        
        # Clear existing - destroy row frames for chapters (since they contain checkbox + button)
        for btn in self.chapter_buttons:
            try:
                btn.master.destroy()  # Destroy the row frame containing checkbox + button
            except Exception:
                pass
        for btn in self.page_buttons:
            try:
                btn.destroy()
            except Exception:
                pass
        self.chapter_buttons = []
        self.chapter_checkboxes = []
        self.chapter_check_vars = []
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
        
        # v1.1: Reset checkbox variables
        self.chapter_check_vars = []
        self.chapter_checkboxes = []
        
        # Create chapter rows with checkboxes
        for i, (name, _) in enumerate(entries):
            row = ctk.CTkFrame(self.chapter_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            
            # Checkbox
            var = ctk.BooleanVar(value=True)  # Default: selected
            self.chapter_check_vars.append(var)
            
            cb = ctk.CTkCheckBox(
                row, text="", variable=var, width=20, height=20,
                checkbox_width=16, checkbox_height=16,
                fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                command=self._update_chapter_count
            )
            cb.pack(side="left", padx=(2, 4))
            self.chapter_checkboxes.append(cb)
            
            # Button
            btn = ctk.CTkButton(
                row, text=name, anchor="w", height=20, corner_radius=4,
                fg_color="transparent", hover_color=COLORS["bg_hover"],
                text_color=COLORS["text_primary"], font=get_font("xs"),
                command=lambda idx=i: self._select_chapter(idx)
            )
            btn.pack(side="left", fill="x", expand=True)
            self.chapter_buttons.append(btn)
        
        self._update_chapter_count()
        
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
        page = self.pages[index]
        
        # Highlight button
        for i, btn in enumerate(self.page_buttons):
            if i == index:
                btn.configure(fg_color=COLORS["secondary"], text_color=COLORS["text_primary"])
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["text_secondary"])
        
        self.page_label.configure(text=f"{index+1}/{len(self.pages)}")
        # Also update preview page label
        if hasattr(self, 'preview_page_label'):
            self.preview_page_label.configure(text=f"{index+1}/{len(self.pages)}")
        
        # v1.1: Load saved position for this page (if any)
        saved_pos = self.page_positions.get(page.name)
        if saved_pos:
            # Set the preview panel's crosshair to saved position
            self.preview_panel.set_manual_position(saved_pos)
        else:
            # Clear any previous position
            self.preview_panel.clear_manual_position()
        
        # v1.2: Load saved settings for this page (if any)
        saved_settings = self.page_settings.get(page.name)
        if saved_settings:
            self.scale_slider.set(saved_settings.get('scale', 0.25))
            self.opacity_slider.set(saved_settings.get('opacity', 0.6))
        
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
            args = self._build_args(for_page=page.name)
            canvas, info = compose_watermarked_image(page, self.watermark_image, args, {})
            self.preview_panel.show_image(canvas, info)
        except Exception as e:
            self.preview_panel.show_placeholder(f"Error: {e}")
    
    def _build_args(self, for_page: str = None) -> Namespace:
        """Build args from current settings. for_page is the filename to check for saved position."""
        # v1.1: Check saved page position first, then preview crosshair
        manual_pos = None
        
        if for_page and for_page in self.page_positions:
            # Use saved position for this specific page
            manual_pos = self.page_positions[for_page]
        elif hasattr(self, 'preview_panel'):
            # Fall back to current preview panel position
            manual_pos = self.preview_panel.get_manual_position()
        
        # If manual position is set, use top-left anchor with offsets
        if manual_pos:
            anchor = "top-left"
            offset_x = manual_pos[0]
            offset_y = manual_pos[1]
        else:
            anchor = self.anchor_selector.get()
            offset_x = 0
            offset_y = 0
        
        # v1.2: Get per-page settings if available
        page_settings = self.page_settings.get(for_page, {}) if for_page else {}
        scale = page_settings.get('scale', self.scale_slider.get())
        opacity = page_settings.get('opacity', self.opacity_slider.get())
        
        return Namespace(
            watermark=Path(self.watermark_selector.get()),
            input=Path(self.input_selector.get()) if self.input_selector.get() else Path("."),
            output=Path(self.output_selector.get()) if self.output_selector.get() else Path("."),
            extensions=[".jpg", ".jpeg", ".png"],
            anchor=anchor,
            offset_x=offset_x,
            offset_y=offset_y,
            margin=0 if manual_pos else int(self.margin_slider.get()),
            scale=scale,
            opacity=opacity,
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
        """Start batch processing with v1.1 features."""
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
        
        # v1.1: Get selected chapters
        selected_chapters = self.get_selected_chapters()
        if not selected_chapters:
            self.status_label.configure(text="⚠️ No chapters selected")
            return
        
        self.running = True
        self.run_btn.configure(state="disabled", text="⏳...")
        self.progress_bar.set(0)
        
        # v1.2: Track processing time
        import time
        self.processing_start_time = time.time()
        
        # v1.1: Copy page positions for thread safety
        page_positions = dict(self.page_positions)
        
        def worker():
            try:
                # Process each selected chapter
                total_pages = 0
                processed = 0
                
                # Count total pages first
                for chapter in selected_chapters:
                    if chapter == Path(inp):
                        pages = [p for p in chapter.iterdir() if p.is_file() and p.suffix.lower() in self.EXTENSIONS]
                    else:
                        pages = list(chapter.rglob("*"))
                        pages = [p for p in pages if p.is_file() and p.suffix.lower() in self.EXTENSIONS]
                    total_pages += len(pages)
                
                if total_pages == 0:
                    self.after(0, lambda: self._finish(False, "No images found"))
                    return
                
                # Process each page
                watermark = Image.open(wm).convert("RGBA")
                
                for chapter in selected_chapters:
                    if chapter == Path(inp):
                        pages = sorted([p for p in chapter.iterdir() if p.is_file() and p.suffix.lower() in self.EXTENSIONS], key=lambda p: p.name.lower())
                    else:
                        pages = sorted([p for p in chapter.rglob("*") if p.is_file() and p.suffix.lower() in self.EXTENSIONS], key=lambda p: p.name.lower())
                    
                    for page_path in pages:
                        # Build args for this specific page (with its saved position if any)
                        args = self._build_args(for_page=page_path.name)
                        args.output = Path(out)
                        args.input = Path(inp)
                        
                        # Process file
                        try:
                            from watermark_bulk import process_file, load_overrides
                            overrides = load_overrides(None)
                            process_file(page_path, watermark, args, overrides, Path(inp), log=lambda m: None)
                            processed += 1
                            progress = processed / total_pages
                            self.after(0, lambda p=progress, n=page_path.name: (
                                self.progress_bar.set(p),
                                self.status_label.configure(text=f"Processing: {n}")
                            ))
                        except Exception as e:
                            self.after(0, lambda e=e, n=page_path.name: self.status_label.configure(text=f"Error on {n}: {e}"))
                
                self.after(0, lambda: self._finish(True))
            except Exception as e:
                self.after(0, lambda: self._finish(False, str(e)))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _finish(self, success: bool, error: str = ""):
        """Handle completion with v1.2 time display and popup."""
        import time
        import tkinter.messagebox as messagebox
        
        self.running = False
        self.run_btn.configure(state="normal", text="🚀 Run")
        self.progress_bar.set(1 if success else 0)
        
        # v1.2: Calculate processing time
        elapsed = time.time() - self.processing_start_time
        if elapsed < 1:
            time_str = f"{int(elapsed * 1000)}ms"
        else:
            time_str = f"{elapsed:.1f}s"
        
        if success:
            self.status_label.configure(text=f"✅ Done in {time_str}!")
            
            # v1.2: Show popup if enabled
            if self.show_popup_var.get():
                messagebox.showinfo(
                    "Watermark-Deksmo",
                    f"✅ Processing complete!\n\nTime: {time_str}"
                )
        else:
            self.status_label.configure(text=f"❌ {error}")
    
    # ===== v1.1 HANDLER METHODS =====
    
    def _select_all_chapters(self):
        """Select all chapters for processing."""
        for var in self.chapter_check_vars:
            var.set(True)
        self._update_chapter_count()
    
    def _deselect_all_chapters(self):
        """Deselect all chapters."""
        for var in self.chapter_check_vars:
            var.set(False)
        self._update_chapter_count()
    
    def _update_chapter_count(self):
        """Update the chapter selection count label."""
        selected = sum(1 for var in self.chapter_check_vars if var.get())
        total = len(self.chapter_check_vars)
        self.chapter_select_label.configure(text=f"{selected}/{total}")
    
    def _save_page_position(self):
        """Save current manual position AND settings for the selected page."""
        if not self.pages or self.current_page_idx >= len(self.pages):
            self.status_label.configure(text="⚠️ No page selected")
            return
        
        pos = self.preview_panel.get_manual_position()
        if not pos:
            self.status_label.configure(text="⚠️ Click on preview to set position first")
            return
        
        page = self.pages[self.current_page_idx]
        
        # Save position
        self.page_positions[page.name] = pos
        
        # v1.2: Also save scale and opacity
        self.page_settings[page.name] = {
            'scale': self.scale_slider.get(),
            'opacity': self.opacity_slider.get()
        }
        
        self._update_position_count()
        self._update_page_button_indicator(self.current_page_idx)
        self.status_label.configure(text=f"💾 Saved position + settings for {page.name}")
    
    def _clear_page_position(self):
        """Clear saved position for the selected page."""
        if not self.pages or self.current_page_idx >= len(self.pages):
            return
        
        page = self.pages[self.current_page_idx]
        if page.name in self.page_positions:
            del self.page_positions[page.name]
            self._update_position_count()
            self._update_page_button_indicator(self.current_page_idx)
            self.status_label.configure(text=f"🗑️ Cleared position for {page.name}")
        
        # Also clear the preview crosshair
        self.preview_panel.clear_manual_position()
    
    def _update_position_count(self):
        """Update the position count label."""
        count = len(self.page_positions)
        self.pos_count_label.configure(text=f"📍 {count} saved")
    
    def _clear_all_positions(self):
        """Clear all saved page positions."""
        if self.page_positions:
            self.page_positions.clear()
            # Update all button indicators
            for i in range(len(self.page_buttons)):
                self._update_page_button_indicator(i)
            self._update_position_count()
            self.preview_panel.clear_manual_position()
            self.status_label.configure(text="🗑️ Cleared all saved positions")
    
    def _update_page_button_indicator(self, index: int):
        """Update button text to show indicator if page has custom position."""
        if index < 0 or index >= len(self.page_buttons):
            return
        
        page = self.pages[index]
        has_pos = page.name in self.page_positions
        btn = self.page_buttons[index]
        
        # Add/remove indicator
        base_name = page.name
        if has_pos:
            btn.configure(text=f"📍 {base_name}")
        else:
            btn.configure(text=base_name)
    
    def get_selected_chapters(self) -> List[Path]:
        """Get list of selected chapters for processing."""
        selected = []
        for i, var in enumerate(self.chapter_check_vars):
            if var.get() and i < len(self.chapters):
                selected.append(self.chapters[i])
        return selected
    
    # ===== v1.2 WORKSPACE METHODS =====
    
    def _open_workspace(self):
        """Show menu to choose which folder to open."""
        import tkinter as tk
        
        menu = tk.Menu(self, tearoff=0)
        menu.configure(bg=COLORS["bg_card"], fg=COLORS["text_primary"], 
                       activebackground=COLORS["primary"], activeforeground="white")
        
        menu.add_command(label="📥 Open Input Folder", command=self._open_input_folder)
        menu.add_command(label="📤 Open Output Folder", command=self._open_output_folder)
        
        # Show menu at button position
        try:
            x = self.open_workspace_btn.winfo_rootx()
            y = self.open_workspace_btn.winfo_rooty() + self.open_workspace_btn.winfo_height()
            menu.tk_popup(x, y)
        except Exception:
            pass
    
    def _open_input_folder(self):
        """Open input folder in Explorer."""
        import subprocess
        import os
        
        input_path = self.input_selector.get()
        folder = input_path if input_path and Path(input_path).is_dir() else str(self.default_input)
        
        if os.name == 'nt':
            subprocess.run(['explorer', folder], check=False)
        self.status_label.configure(text=f"📂 Opened input folder")
    
    def _open_output_folder(self):
        """Open output folder in Explorer."""
        import subprocess
        import os
        
        output_path = self.output_selector.get()
        folder = output_path if output_path and Path(output_path).is_dir() else str(self.default_output)
        
        if os.name == 'nt':
            subprocess.run(['explorer', folder], check=False)
        self.status_label.configure(text=f"📂 Opened output folder")
    
    def _refresh_input(self):
        """Refresh the chapters and pages from the input folder."""
        input_path = self.input_selector.get()
        if not input_path:
            input_path = str(self.default_input)
            self.input_selector.set(input_path)
        
        folder = Path(input_path)
        if folder.is_dir():
            # Just call the normal change handler which properly reloads
            self._on_input_change(input_path)
            self.status_label.configure(text=f"🔄 Refreshed!")
        else:
            self.status_label.configure(text="⚠️ No valid input folder")


def main():
    """Entry point."""
    app = WatermarkApp()
    app.mainloop()


if __name__ == "__main__":
    main()
