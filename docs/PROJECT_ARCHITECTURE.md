# WC3 Skill Text Generator - Project Architecture

This document describes the technical architecture of the WC3 Skill Text Generator desktop application.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Desktop Application                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐     pywebview API      ┌────────────────────┐    │
│  │  Frontend    │ ◄──────────────────────► │   Python Backend   │    │
│  │  (HTML/JS)   │      JSON serialization  │    (gui.py)        │    │
│  └──────────────┘                          └────────────────────┘    │
│        │                                             │               │
│        ▼                                             ▼               │
│  ┌──────────────┐                          ┌────────────────────┐    │
│  │ State        │                          │ Data Storage       │    │
│  │ Management   │                          │ (JSON Files)       │    │
│  └──────────────┘                          └────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Description |
|-------|------------|-------------|
| Frontend | HTML + CSS + Vanilla JS | No framework dependencies, lightweight |
| Backend | Python 3.13 | Requires Python 3.13 (pythonnet compatibility) |
| GUI Framework | pywebview | Embedded WebView, cross-platform |
| Data Storage | JSON | Local file storage in `/data/` |
| Config | PyYAML | YAML configuration file |

---

## 2. Project Structure

```
project-root/
├── script/
│   └── gui.py              # Backend: API + Entry point
├── webui/
│   └── index.html          # Frontend: UI + Logic (single file)
├── data/
│   ├── spells/             # Skill data (hierarchical folders)
│   ├── colors/             # Color configuration presets
│   ├── exports/            # Exported JSON files
│   └── settings.json       # Application settings
├── config/
│   └── setting.yaml        # Legacy configuration
├── docs/
│   ├── PROJECT_ARCHITECTURE.md
│   └── TECHNICAL_DESIGN.md
├── .venv/                  # Virtual environment (created by start-uv.bat)
├── requirements.txt
├── start-uv.bat            # UV launcher script
└── README.md
```

---

## 3. Backend API Design

### AppApi Class Methods

The backend exposes an `AppApi` class via pywebview's `js_api` parameter:

```python
class AppApi:
    # Initialization
    def wc3_get_initial_state(self) -> dict
    
    # Skill Tree Management
    def wc3_get_spell_tree(self) -> dict
    def wc3_create_category(self, payload: dict) -> dict
    def wc3_delete_category(self, payload: dict) -> dict
    def wc3_rename_category(self, payload: dict) -> dict
    
    # Skill CRUD
    def wc3_save_spell(self, payload: dict) -> dict
    def wc3_load_spell(self, payload: dict) -> dict
    def wc3_delete_spell(self, payload: dict) -> dict
    def wc3_rename_spell(self, payload: dict) -> dict
    
    # Import/Export
    def wc3_export_category(self, payload: dict) -> dict
    def wc3_import_file(self, payload: dict) -> dict
    
    # Color Configuration
    def wc3_get_color_configs(self) -> dict
    def wc3_save_color_config(self, payload: dict) -> dict
    def wc3_delete_color_config(self, payload: dict) -> dict
    
    # Settings
    def wc3_get_settings(self) -> dict
    def wc3_save_settings(self, payload: dict) -> dict
```

### Return Format Convention

All API methods return:

```javascript
// Success
{ "success": true, "data": {...}, "message": null }

// Failure
{ "success": false, "data": null, "message": "Error description" }
```

---

## 4. Data Storage Structure

### Skill Storage (`/data/spells/`)

Skills are stored as JSON files with 2-3 level folder nesting:

```
data/spells/
├── Heroes/
│   ├── Paladin/
│   │   ├── Holy Light.json
│   │   └── Divine Shield.json
│   └── Archmage/
│       └── Blizzard.json
└── Items/
    └── Scroll.json
```

### Skill Data Schema

```json
{
  "id": "A000",
  "lv": 1,
  "name": "Storm Bolt",
  "hotKey": "T",
  "effect": "Description text",
  "nature": "Requires channeling",
  "pros": [
    {"name": "Mana Cost", "val": "75"},
    {"name": "Cooldown", "val": "6"}
  ],
  "updateWord": {
    "text": "{d} damage, {t} sec stun",
    "vals": [{"d": 100, "t": 3}, {"d": 210, "t": 4}]
  },
  "normalWord": {
    "text": "Deals {d} damage...",
    "vals": [{"d": 100, "t": 3}]
  }
}
```

### Color Configuration (`/data/colors/`)

```json
{
  "learnLevel": "#33ccff",
  "property": "#33cc33",
  "hotKey": "#ffcc00",
  "learnUpdateLevel": "#ff9900",
  "nature": "#ffcccc"
}
```

### Settings (`/data/settings.json`)

```json
{
  "lastCategory": "Heroes/Paladin",
  "lastSpell": "Holy Light.json",
  "colorConfig": "default"
}
```

---

## 5. Frontend Architecture

### State Management

```javascript
const state = {
    tree: [],              // Category tree data
    currentSpell: null,    // Currently editing spell
    currentPath: '',       // Current file path
    colorConfig: {},       // Current color configuration
    colorConfigs: [],      // All color presets
    currentColorName: '',  // Current preset name
    mode: 'learn',         // Display mode: 'learn' | 'normal'
    level: 1,              // Current level
    maxLevel: 1,           // Max available levels
    settings: {}           // Application settings
};
```

### API Call Pattern

```javascript
async function callApi(method, payload = {}) {
    while (!window.pywebview?.api) {
        await new Promise(r => setTimeout(r, 50));
    }
    return window.pywebview.api[method](payload);
}

// Usage
const result = await callApi('wc3_load_spell', {path: 'Heroes/Paladin/Holy Light.json'});
```

### WC3 Color Code Generation

```javascript
function dyeing(str, color) {
    if (!color) return str;
    return '|cff' + color.replace('#', '') + str + '|r';
}
```

---

## 6. Value Parameters

The editor uses the skill level input as the level count. Description placeholders such as `{a}` are matched with value parameter rules. The UI stores both the legacy compact text form and structured rules for easier editing:

```json
{
  "valueParams": "a=100+10;b=3,4,5",
  "valueParamRules": [
    {"key": "a", "label": "Damage", "type": "linear", "base": "100", "step": "10"},
    {"key": "b", "label": "Stun", "type": "list", "values": "3,4,5"}
  ]
}
```

- `key=base+increment`: Each level adds `increment` to `base`
- `key=v1,v2,v3`: Explicit values per level
- Legacy `[lv=3][a=100+10]` data is still parsed, but `lv` is ignored after migration because level count now comes from the editor input

Usage in description text:
```
"Deals {a} damage and stuns for {b} seconds."
```

---

## 7. Runtime Environment

### Path Handling

```python
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    # PyInstaller packaged environment
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', APP_DIR)).resolve()
else:
    # Development environment
    APP_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_DIR = APP_DIR

DATA_DIR = APP_DIR / 'data'
SPELLS_DIR = DATA_DIR / 'spells'
COLORS_DIR = DATA_DIR / 'colors'
```

---

## 8. Launch Scripts

### start-uv.bat

Uses `uv` package manager with Python 3.13 constraint:

```batch
uv venv --python 3.13
uv pip install -r requirements.txt
.venv\Scripts\python.exe script\gui.py
```

**Note**: Python 3.14 is not supported due to pythonnet ABI compatibility.

---

## 9. Build to EXE

```batch
pyinstaller --noconfirm --onefile --windowed ^
  --add-data "webui;webui" ^
  --add-data "config;config" ^
  --icon "app.ico" ^
  script\gui.py
```

Key parameters:
- `--onefile`: Single EXE output
- `--windowed`: No console window
- `--add-data "src;dest"`: Include data files (Windows uses `;`)

---

## 10. Troubleshooting

### pythonnet Initialization Failure

**Error**: `Python ABI v3.14.3 is not supported`

**Solution**: Use Python 3.13 or earlier. The `pythonnet` package does not support Python 3.14 ABI yet.

### pywebview API Not Available

**Cause**: Calling API before pywebview is ready

**Solution**: Listen for `pywebviewready` event:
```javascript
window.addEventListener('pywebviewready', bootstrap);
```

### Resource Files Not Found (EXE)

**Cause**: Incorrect path handling in packaged environment

**Solution**: Use `sys.frozen` and `_MEIPASS` to detect runtime environment.

---

This architecture document provides a complete reference for the WC3 Skill Text Generator application.
