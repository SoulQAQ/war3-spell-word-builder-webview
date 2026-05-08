# WC3 Skill Text Generator

[English](README.md) | [中文](README.zh-CN.md)

A desktop application for generating Warcraft 3 skill description text with custom color codes.

## Features

- **Skill Editor**: Edit skill attributes (name, hotkey, effect, properties)
- **Real-time Preview**: WC3 tooltip-style preview with custom colors
- **Formula Parsing**: Support `[lv=3][a=100+10]` syntax for level-based values
- **Color Configuration**: Customize 5 color elements with save/load presets
- **Text Generation**: One-click copy with WC3 color codes (`|cffXXXXXX`)
- **Category Management**: Tree-style resource manager with 2-3 level nesting
- **Import/Export**: Batch JSON import and export

## Tech Stack

- **Backend**: Python 3.13 + pywebview
- **Frontend**: Vanilla HTML/CSS/JS (no framework)
- **Data Storage**: Local JSON files in `/data/`

## Requirements

- Python 3.13 (Python 3.14 not supported due to pythonnet compatibility)
- uv package manager (recommended) or pip

## Quick Start

### Using UV (Recommended)

```bash
# Install uv if not already installed
pip install uv

# Run the launcher script
start-uv.bat
```

### Using pip

```bash
# Run setup script (requires Python 3.13)
setup.bat

# Start application
start.bat
```

### Manual Setup

```bash
# Create virtual environment with Python 3.13
python -m venv .venv

# Activate and install dependencies
.venv\Scripts\activate
pip install -r requirements.txt

# Run the application
python script/gui.py
```

## Project Structure

```
project-root/
├── script/
│   └── gui.py              # Backend entry point & API
├── webui/
│   └── index.html          # Frontend page (HTML/CSS/JS)
├── data/
│   ├── spells/             # Skill JSON files (by category)
│   ├── colors/             # Color configuration presets
│   ├── exports/            # Exported files
│   └── settings.json       # Application settings
├── config/
│   └── setting.yaml        # Configuration file
├── docs/
│   ├── PROJECT_ARCHITECTURE.md
│   └── TECHNICAL_DESIGN.md
├── requirements.txt
├── setup.bat               # Environment setup script
├── start.bat               # Application launcher
├── start-uv.bat            # UV launcher script
├── build.bat               # Build to EXE
└── README.md
```

## Data Storage

Skills are stored as JSON files in the `/data/spells/` directory, organized by category:

```
data/spells/
├── Heroes/
│   ├── Paladin/
│   │   ├── Holy Light.json
│   │   └── Divine Shield.json
│   └── Archmage/
│       └── Blizzard.json
└── Items/
    └── Scroll of Teleportation.json
```

## Color Configuration

Customize these color elements:
- **Hotkey**: Skill hotkey color
- **Learn Level**: Level text in learning mode
- **Property**: Attribute names (Mana, Cooldown, etc.)
- **Learn Update Level**: Level prefix in upgrade descriptions
- **Nature**: Special description text (e.g., "Requires channeling")

Color presets are saved in `/data/colors/` as JSON files.

## Usage

1. **Create Category**: Click "+ Category" in the sidebar to create skill folders
2. **Edit Skill**: Fill in skill attributes in the right panel
3. **Parse Values**: Use `[lv=N][a=base+increment]` syntax for level-scaling values
4. **Preview**: Real-time WC3 tooltip preview in the left panel
5. **Generate**: Click "Generate" to copy text with WC3 color codes
6. **Save**: Save skills to the selected category

## Value Formula Syntax

```
[lv=3][a=100+10][b=3,4,5]
```

- `lv=N`: Number of levels
- `a=base+increment`: Formula (each level adds increment)
- `b=val1,val2,val3`: Explicit values per level

Reference: `{a}` in description text maps to the `a` parameter.

## Build to EXE

```bash
build.bat
```

Or manually:
```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --add-data "webui;webui" --add-data "config;config" --icon "app.ico" script/gui.py
```

## License

[GPL-3.0](LICENSE)
