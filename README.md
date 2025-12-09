# Watermark-Deksmo

**Open Source Batch Watermarking Tool for Comics & Manga**

![Version](https://img.shields.io/badge/version-v1.2-blue.svg) ![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg) ![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

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

## ✨ v1.2 Detailed Features

### 🎨 Interaction & UI
- **Expandable Preview Drawer** - Settings (Anchor, Margin, Scale, Opacity, Quality) are now hidden in a sleek drawer at the bottom of the preview. Hover to reveal them!
- **Keyboard Navigation** - Use **Left/Right Arrow** keys to flip through pages quickly.
- **Hover Effects** - Interactive elements now have satisfying glow and color shifts.

### ⚙️ Page-Level Control
- **Per-Page Settings** - Moving a watermark isn't enough? Now you can set specific **Scale** and **Opacity** for individual pages too.
- **Shortcuts** - Press `Ctrl+S` to instantly save current page settings.
- **Feedback** - New processing timer tells you exactly how fast your batch finished.

## 🚀 Usage Guide

1. **Launch**: Run `dist\Watermark-Deksmo.exe`
2. **Load**: Select your image folder using the "Input" field browse button.
3. **Position**: 
   - Click anywhere on the preview to place the watermark.
   - Hover over the bottom bar to adjust **Anchor**, **Scale**, or **Opacity**.
   - Use `Ctrl+S` to lock these settings for the current page.
4. **Process**: Click "Start Batch" - watch the progress bar and timer!

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
