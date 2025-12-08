"""
Compact chapter and page browser - minimal height.
"""

import customtkinter as ctk
from pathlib import Path
from typing import Callable, List, Optional

from app.theme import COLORS, RADIUS, SPACING, get_font


class BrowserPanel(ctk.CTkFrame):
    """Compact horizontal browser for chapters and pages."""
    
    EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    
    def __init__(
        self,
        master,
        on_page_select: Optional[Callable[[Path], None]] = None,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=COLORS["bg_card"],
            corner_radius=RADIUS["md"],
            height=120,  # Fixed compact height
            **kwargs
        )
        self.pack_propagate(False)  # Maintain fixed height
        
        self.on_page_select = on_page_select
        self.chapters: List[Path] = []
        self.pages: List[Path] = []
        self.root_path: Optional[Path] = None
        self.current_page_index = 0
        self.current_chapter_index = 0
        self.chapter_buttons: List[ctk.CTkButton] = []
        self.page_buttons: List[ctk.CTkButton] = []
        
        self._build_ui()
    
    def _build_ui(self):
        # Horizontal layout - chapters on left, pages on right
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)  # Pages get more space
        self.rowconfigure(0, weight=1)
        
        # === LEFT: Chapters ===
        chapter_section = ctk.CTkFrame(self, fg_color="transparent")
        chapter_section.grid(row=0, column=0, sticky="nsew", padx=(SPACING["md"], SPACING["sm"]), pady=SPACING["sm"])
        chapter_section.rowconfigure(1, weight=1)
        chapter_section.columnconfigure(0, weight=1)
        
        # Header
        ch_header = ctk.CTkFrame(chapter_section, fg_color="transparent", height=24)
        ch_header.grid(row=0, column=0, sticky="ew")
        ch_header.pack_propagate(False)
        
        ctk.CTkLabel(
            ch_header, text="📁 Chapters", font=get_font("xs", bold=True),
            text_color=COLORS["text_secondary"]
        ).pack(side="left")
        
        self.chapter_count = ctk.CTkLabel(
            ch_header, text="0", font=get_font("xs"), text_color=COLORS["text_muted"]
        )
        self.chapter_count.pack(side="right")
        
        # Scrollable chapter list
        self.chapter_frame = ctk.CTkScrollableFrame(
            chapter_section, fg_color=COLORS["bg_dark"], corner_radius=RADIUS["sm"],
            scrollbar_button_color=COLORS["bg_hover"], height=60
        )
        self.chapter_frame.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        
        # === RIGHT: Pages ===
        page_section = ctk.CTkFrame(self, fg_color="transparent")
        page_section.grid(row=0, column=1, sticky="nsew", padx=(SPACING["sm"], SPACING["md"]), pady=SPACING["sm"])
        page_section.rowconfigure(1, weight=1)
        page_section.columnconfigure(0, weight=1)
        
        # Header with nav buttons
        pg_header = ctk.CTkFrame(page_section, fg_color="transparent", height=24)
        pg_header.grid(row=0, column=0, sticky="ew")
        pg_header.pack_propagate(False)
        
        ctk.CTkLabel(
            pg_header, text="🖼️ Pages", font=get_font("xs", bold=True),
            text_color=COLORS["text_secondary"]
        ).pack(side="left")
        
        # Navigation on the right
        nav = ctk.CTkFrame(pg_header, fg_color="transparent")
        nav.pack(side="right")
        
        self.prev_btn = ctk.CTkButton(
            nav, text="◀", width=24, height=20, corner_radius=4,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["primary"],
            font=get_font("xs"), command=lambda: self._shift_page(-1)
        )
        self.prev_btn.pack(side="left", padx=1)
        
        self.page_label = ctk.CTkLabel(
            nav, text="0/0", font=get_font("xs"), text_color=COLORS["text_muted"], width=50
        )
        self.page_label.pack(side="left", padx=2)
        
        self.next_btn = ctk.CTkButton(
            nav, text="▶", width=24, height=20, corner_radius=4,
            fg_color=COLORS["bg_hover"], hover_color=COLORS["primary"],
            font=get_font("xs"), command=lambda: self._shift_page(1)
        )
        self.next_btn.pack(side="left", padx=1)
        
        # Scrollable page list
        self.page_frame = ctk.CTkScrollableFrame(
            page_section, fg_color=COLORS["bg_dark"], corner_radius=RADIUS["sm"],
            scrollbar_button_color=COLORS["bg_hover"], height=60
        )
        self.page_frame.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
    
    def set_input_folder(self, folder: str):
        """Load chapters from input folder."""
        if not folder:
            return
        
        path = Path(folder)
        if not path.is_dir():
            return
        
        self.root_path = path
        
        # Clear existing
        for btn in self.chapter_buttons:
            btn.destroy()
        for btn in self.page_buttons:
            btn.destroy()
        
        self.chapter_buttons = []
        self.page_buttons = []
        self.chapters = []
        self.pages = []
        
        # Build chapter list:
        # 1. If root has images, add root as "(All Images)"
        # 2. Add subfolders that contain images (direct or nested)
        entries = []
        
        # Check if root has images directly
        root_images = [p for p in path.iterdir() 
                       if p.is_file() and p.suffix.lower() in self.EXTENSIONS]
        if root_images:
            entries.append(("(All Images)", path, False))  # name, path, is_subfolder
        
        # Find subfolders with images inside
        for sub in sorted([p for p in path.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
            # Check if this folder or any nested folder has images
            has_images = any(
                f.suffix.lower() in self.EXTENSIONS 
                for f in sub.rglob("*") if f.is_file()
            )
            if has_images:
                entries.append((sub.name, sub, True))
        
        # Store just the paths for chapters
        self.chapters = [e[1] for e in entries]
        self.chapter_count.configure(text=str(len(entries)))
        
        # Create chapter buttons
        for i, (name, chapter_path, is_sub) in enumerate(entries):
            btn = ctk.CTkButton(
                self.chapter_frame, text=name, anchor="w", height=22,
                corner_radius=4, fg_color="transparent", hover_color=COLORS["bg_hover"],
                text_color=COLORS["text_primary"], font=get_font("xs"),
                command=lambda idx=i: self._select_chapter_by_index(idx)
            )
            btn.pack(fill="x", pady=1)
            self.chapter_buttons.append(btn)
        
        if entries:
            self._select_chapter_by_index(0)
        else:
            self.page_label.configure(text="0/0")
    
    def _select_chapter_by_index(self, index: int):
        """Select chapter and load its pages."""
        if index < 0 or index >= len(self.chapters):
            return
        
        self.current_chapter_index = index
        chapter = self.chapters[index]
        
        # Highlight selected chapter
        for i, btn in enumerate(self.chapter_buttons):
            btn.configure(fg_color=COLORS["primary"] if i == index else "transparent")
        
        # Clear pages
        for btn in self.page_buttons:
            btn.destroy()
        self.page_buttons = []
        
        # Find images - check if this is the root "(All Images)" entry
        if chapter == self.root_path:
            # Only direct images in root, not recursive
            self.pages = sorted(
                [p for p in chapter.iterdir() 
                 if p.is_file() and p.suffix.lower() in self.EXTENSIONS],
                key=lambda p: p.name.lower()
            )
        else:
            # For subfolders, search recursively
            self.pages = sorted(
                [p for p in chapter.rglob("*") 
                 if p.is_file() and p.suffix.lower() in self.EXTENSIONS],
                key=lambda p: p.name.lower()
            )
        
        # Create page buttons
        for i, page in enumerate(self.pages):
            btn = ctk.CTkButton(
                self.page_frame, text=page.name, anchor="w", height=20,
                corner_radius=3, fg_color="transparent", hover_color=COLORS["bg_hover"],
                text_color=COLORS["text_secondary"], font=get_font("xs"),
                command=lambda idx=i: self._select_page_by_index(idx)
            )
            btn.pack(fill="x", pady=0)
            self.page_buttons.append(btn)
        
        if self.pages:
            self._select_page_by_index(0)
        else:
            self.page_label.configure(text="0/0")
    
    def _select_page_by_index(self, index: int):
        """Select a page."""
        if index < 0 or index >= len(self.pages):
            return
        
        self.current_page_index = index
        
        # Highlight selected page
        for i, btn in enumerate(self.page_buttons):
            if i == index:
                btn.configure(fg_color=COLORS["secondary"], text_color=COLORS["text_primary"])
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["text_secondary"])
        
        self.page_label.configure(text=f"{index+1}/{len(self.pages)}")
        
        if self.on_page_select:
            self.on_page_select(self.pages[index])
    
    def _shift_page(self, delta: int):
        """Navigate pages."""
        if not self.pages:
            return
        new_idx = max(0, min(len(self.pages) - 1, self.current_page_index + delta))
        if new_idx != self.current_page_index:
            self._select_page_by_index(new_idx)
    
    def get_selected_chapter(self) -> Optional[Path]:
        if self.chapters and 0 <= self.current_chapter_index < len(self.chapters):
            return self.chapters[self.current_chapter_index]
        return None
    
    def get_selected_page(self) -> Optional[Path]:
        if self.pages and 0 <= self.current_page_index < len(self.pages):
            return self.pages[self.current_page_index]
        return None
