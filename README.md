# Watermark-Deksmo

**Open Source Batch Watermarking Tool for Comics & Manga**

![Logo](logo-open.png)

A modern, feature-rich desktop application for applying PNG watermarks to large collections of comic/manga pages with flexible placement controls and real-time preview.

## ✨ Features

- **Modern Dark UI** - Sleek glassmorphism design with purple/cyan accents
- **Click-to-Position** - Click anywhere on the preview to set watermark location manually
- **Real-time Preview** - See your watermark applied before processing
- **Batch Processing** - Apply watermarks to thousands of pages at once
- **Chapter Browser** - Navigate chapters and pages easily
- **Flexible Placement** - Anchor points, offsets, margins, scale, opacity
- **JSON Overrides** - Per-file settings for complex layouts
- **Standalone Executable** - Single .exe file, no Python needed

## 📁 Files

| File | Description |
|------|-------------|
| `main.py` | Application entry point |
| `watermark_bulk.py` | Core watermarking logic & CLI |
| `app/gui.py` | Modern CustomTkinter GUI |
| `app/theme.py` | Color palette & fonts |
| `app/components/` | UI components |
| `Watermark-Deksmo.spec` | PyInstaller build config |

## 🚀 Quick Start

### Option 1: Run Executable
```
dist/Watermark-Deksmo.exe
```

### Option 2: Run with Python
```bash
pip install customtkinter pillow
python main.py
```

## 🔧 Building the Executable

```bash
pip install pyinstaller
python -m PyInstaller --clean Watermark-Deksmo.spec
```

Output: `dist/Watermark-Deksmo.exe`

## 🎯 Click-to-Position (New!)

1. Enable "Click to Position" toggle in the preview panel
2. Click anywhere on the image
3. A crosshair marks your chosen position
4. Run to apply watermark at that exact location

## ⌨️ CLI Usage

```bash
python watermark_bulk.py -w watermark.png -i input_folder -o output_folder \
  --anchor bottom-right --scale 0.25 --opacity 0.6 --margin 16
```

## 📋 Requirements

- Python 3.9+
- CustomTkinter
- Pillow

## 📄 License

Open Source - Free to use and modify.
