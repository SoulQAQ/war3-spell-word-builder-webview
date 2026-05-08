# WC3 Skill Text Generator - Technical Design

This document describes the technical implementation details of the WC3 Skill Text Generator.

---

## 1. Application Purpose

Generate Warcraft 3 skill description text with WC3 color codes (`|cffXXXXXX`) for use in map editing tools.

Key Features:
- Skill attribute editing with real-time WC3 tooltip preview
- Level-based value calculation with formula syntax
- Multi-layer category management (tree structure)
- Color configuration presets
- Batch import/export

---

## 2. Backend Implementation (gui.py)

### 2.1 Constants and Initialization

```python
# Data directories
DATA_DIR = APP_DIR / 'data'
SPELLS_DIR = DATA_DIR / 'spells'
COLORS_DIR = DATA_DIR / 'colors'
EXPORTS_DIR = DATA_DIR / 'exports'
SETTINGS_PATH = DATA_DIR / 'settings.json'

# Default configurations
DEFAULT_COLOR_CONFIG = {
    "learnLevel": "#33ccff",
    "property": "#33cc33",
    "hotKey": "#ffcc00",
    "learnUpdateLevel": "#ff9900",
    "nature": "#ffcccc"
}

DEFAULT_SPELL_DATA = {
    "id": "A000",
    "lv": 1,
    "name": "",
    "hotKey": "",
    "effect": "",
    "nature": "",
    "pros": [{"name": "法力消耗", "val": ""}],
    "updateWord": {"text": "", "vals": []},
    "normalWord": {"text": "", "vals": []}
}
```

### 2.2 Directory Tree Building

```python
def build_tree(path: Path, depth: int = 0) -> list:
    """Recursively build directory tree (max 3 levels)"""
    if depth > 3:
        return []
    
    items = []
    for item in sorted(path.iterdir()):
        if item.is_dir():
            children = build_tree(item, depth + 1)
            items.append({
                'type': 'category',
                'name': item.name,
                'path': str(item.relative_to(SPELLS_DIR)),
                'children': children,
                'expanded': False
            })
        elif item.is_file() and item.suffix == '.json':
            # Load skill name for display
            items.append({
                'type': 'spell',
                'name': data.get('name', item.stem),
                'filename': item.stem,
                'path': str(item.relative_to(SPELLS_DIR))
            })
    return items
```

### 2.3 Path Security

All path operations validate against directory traversal:

```python
if '..' in rel_path:
    return {'success': False, 'message': 'Invalid path'}

full_path = SPELLS_DIR / rel_path
```

---

## 3. Frontend Implementation (index.html)

### 3.1 Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│ Sidebar (200px) │ Main Area                                   │
│                 │ ┌─────────────────────────────────────────┐ │
│ Tree View       │ │ Tab Bar: [编辑文本] [色彩]              │ │
│                 │ ├─────────────────────────────────────────┤ │
│ [+ Category]    │ │ Edit Layout:                            │ │
│                 │ │  ┌─────────┐ ┌─────────────────────────┐│ │
│                 │ │  │ Preview │ │ Form: Name, Hotkey...   ││ │
│                 │ │  │ Mode    │ │ Properties List         ││ │
│                 │ │  │ Levels  │ │ Formula Inputs          ││ │
│                 │ │  └─────────┘ └─────────────────────────┘│ │
│                 │ ├─────────────────────────────────────────┤ │
│                 │ │ Bottom Bar: [Save] [Save As]            │ │
│                 │ └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 WC3 Tooltip Preview CSS

```css
.spell-preview {
    background: rgba(0, 0, 0, 0.75);
    border-radius: 6px;
    padding: 12px;
    color: #ffffff;
    font-size: 12px;
    font-weight: bold;
    line-height: 1.6;
}
```

### 3.3 Value Formula Parsing

```javascript
function conversion(str) {
    // Extract level count: [lv=N]
    const lvMatch = str.match(/\[lv=(\d+)\]/);
    if (!lvMatch) return [];
    const lv = parseInt(lvMatch[1]);
    
    // Extract parameters: [key=value]
    const pairs = [];
    const regex = /\[([a-z])=([^\]]+)\]/g;
    let match;
    while ((match = regex.exec(str)) !== null) {
        pairs.push({key: match[1], val: match[2]});
    }
    
    // Generate values for each level
    const result = [];
    for (let i = 0; i < lv; i++) {
        const obj = {};
        pairs.forEach(({key, val}) => {
            if (val.includes('+')) {
                // Formula: base + increment
                const [base, plus] = val.split('+').map(Number);
                obj[key] = base + plus * i;
            } else {
                // List: explicit values
                const vals = val.split(',').map(Number);
                obj[key] = vals[i];
            }
        });
        result.push(obj);
    }
    return result;
}
```

### 3.4 WC3 Color Code Generation

```javascript
// Convert hex color to WC3 format
function dyeing(str, color) {
    if (!color) return str;
    return '|cff' + color.replace('#', '') + str + '|r';
}

// Example: dyeing("Storm Bolt", "#ffcc00") = "|cffffcc00Storm Bolt|r"
```

### 3.5 String Template Filling

```javascript
String.prototype.format = function(obj) {
    let str = this;
    for (const key in obj) {
        str = str.replace(new RegExp('\\{' + key + '\\}', 'g'), obj[key]);
    }
    return str;
};

// Example: "{d} damage".format({d: 100}) = "100 damage"
```

---

## 4. Data File Format

### 4.1 Skill JSON Schema

```json
{
  "id": "A000",
  "lv": 1,
  "name": "Storm Bolt",
  "hotKey": "T",
  "effect": "A magical hammer that deals damage and stuns the target.",
  "nature": "",
  "pros": [
    {"name": "Mana Cost", "val": "75"},
    {"name": "Cast Range", "val": "800"},
    {"name": "Cooldown", "val": "6"}
  ],
  "updateWord": {
    "text": "{d} damage, {t} sec stun duration",
    "vals": [
      {"d": 100, "t": 3},
      {"d": 210, "t": 4},
      {"d": 320, "t": 5}
    ]
  },
  "normalWord": {
    "text": "Deals {d} damage and stuns for {t} seconds.",
    "vals": [
      {"d": 100, "t": 3},
      {"d": 210, "t": 4},
      {"d": 320, "t": 5}
    ]
  }
}
```

### 4.2 Color Config Schema

```json
{
  "learnLevel": "#33ccff",
  "property": "#33cc33",
  "hotKey": "#ffcc00",
  "learnUpdateLevel": "#ff9900",
  "nature": "#ffcccc"
}
```

---

## 5. Import/Export Format

### Export JSON Structure

```json
{
  "category": "Heroes/Paladin",
  "exportTime": "20260101_120000",
  "spells": [
    {
      "relativePath": "Holy Light",
      "data": { /* skill data */ }
    },
    {
      "relativePath": "Divine Shield",
      "data": { /* skill data */ }
    }
  ]
}
```

---

## 6. Generate Output Examples

### Learning Mode Title

```
学习 |cff33ccff%d 级|r 风暴之锤(|cffffcc00T|r)
```

### Learning Mode Extended

```
向目标投掷一巨大的魔法锤，对其造成一定伤害并使其陷入眩晕。

|cff33cc33法力消耗：|r75
|cff33cc33施法距离：|r800

|cffff99001级|r - 100点伤害，3秒晕眩时间。
|cffff99002级|r - 210点伤害，4秒晕眩时间。
```

### Normal Mode Title

```
风暴之锤(|cffffcc00T|r) - [|cff33ccff1 级|r]
```

---

## 7. API Reference

### wc3_get_spell_tree

Returns hierarchical category tree:

```javascript
{
  success: true,
  data: {
    tree: [
      {
        type: 'category',
        name: 'Heroes',
        path: 'Heroes',
        expanded: false,
        children: [
          {
            type: 'category',
            name: 'Paladin',
            path: 'Heroes/Paladin',
            children: [
              {type: 'spell', name: 'Holy Light', path: 'Heroes/Paladin/Holy Light.json'}
            ]
          }
        ]
      }
    ]
  }
}
```

### wc3_save_spell

Parameters:
```javascript
{
  path: 'Heroes/Paladin',  // Category path
  filename: 'Holy Light',  // File name (without .json)
  data: { /* skill object */ }
}
```

### wc3_load_spell

Parameters:
```javascript
{ path: 'Heroes/Paladin/Holy Light.json' }
```

Returns full skill data object.

---

## 8. Error Handling

### Backend Pattern

```python
def wc3_save_spell(self, payload: dict) -> dict:
    try:
        if not payload or 'data' not in payload:
            return {'success': False, 'message': 'Missing data parameter'}
        
        # ... business logic
        
        return {'success': True, 'message': 'Skill saved'}
    except Exception as e:
        return {'success': False, 'message': f'Save failed: {str(e)}'}
```

### Frontend Pattern

```javascript
async function saveSpell() {
    try {
        const result = await callApi('wc3_save_spell', payload);
        if (result.success) {
            showToast('Saved successfully', 'success');
        } else {
            showToast(result.message || 'Save failed', 'error');
        }
    } catch (e) {
        showToast('API error: ' + e.message, 'error');
    }
}
```

---

## 9. Environment Requirements

| Requirement | Version | Reason |
|-------------|---------|--------|
| Python | 3.13 | pythonnet ABI compatibility (3.14 not supported) |
| pywebview | 6.x | WebView embedding |
| pythonnet | 3.0.x | .NET runtime for Windows WebView |
| PyYAML | 6.x | Configuration parsing |

---

## 10. Future Improvements

- Drag-and-drop skill reordering
- INI file export (war3map.ini format)
- Skill template system
- Multi-language support
- Keyboard shortcuts

---

This document provides implementation details for developers working on or extending the WC3 Skill Text Generator.