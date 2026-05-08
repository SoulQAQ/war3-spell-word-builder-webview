"""
自动打包器 GUI入口和API桥接模块

提供pywebview API接口，连接前端UI和后端核心逻辑。
"""

import json
import subprocess
import sys
import webview
from pathlib import Path
import yaml
from webview.dom import DOMEventHandler

from core import (
    generate_password,
    process_packaging,
    delete_source_files
)


# ============================================================================
# 运行时路径处理
# ============================================================================
if getattr(sys, 'frozen', False):
    # PyInstaller打包后的运行环境
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', APP_DIR)).resolve()
else:
    # 开发环境
    APP_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_DIR = APP_DIR

CONFIG_PATH = APP_DIR / 'config' / 'setting.yaml'
WEBUI_INDEX = RESOURCE_DIR / 'webui' / 'index.html'
DEFAULT_SEVEN_ZIP_PATH = r'C:\Program Files\7-Zip\7z.exe'

# WC3技能生成器数据目录
DATA_DIR = APP_DIR / 'data'
SPELLS_DIR = DATA_DIR / 'spells'
COLORS_DIR = DATA_DIR / 'colors'
EXPORTS_DIR = DATA_DIR / 'exports'
SETTINGS_PATH = DATA_DIR / 'settings.json'


# ============================================================================
# 配置管理函数
# ============================================================================
def load_config() -> dict:
    """
    加载配置文件。

    返回:
        dict: 配置字典
    """
    default_config = get_default_config()

    try:
        # 配置文件应该已由 ensure_config_exists() 创建
        if not CONFIG_PATH.exists():
            return default_config

        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # 异常内容兜底
        if not isinstance(config, dict):
            return default_config

        # 补齐关键字段，避免旧配置缺项
        changed = False

        app_settings = config.get('app_settings')
        if not isinstance(app_settings, dict):
            app_settings = {}
            config['app_settings'] = app_settings
            changed = True

        if not app_settings.get('language'):
            app_settings['language'] = default_config['app_settings']['language']
            changed = True

        if not app_settings.get('seven_zip_path'):
            app_settings['seven_zip_path'] = default_config['app_settings']['seven_zip_path']
            changed = True

        if not isinstance(config.get('text_types'), list) or not config.get('text_types'):
            config['text_types'] = default_config['text_types']
            changed = True

        user_settings = config.get('user_settings')
        if not isinstance(user_settings, dict):
            config['user_settings'] = default_config['user_settings']
            changed = True
        else:
            if 'last_text_type' not in user_settings:
                user_settings['last_text_type'] = default_config['user_settings']['last_text_type']
                changed = True
            if 'auto_delete_source' not in user_settings:
                user_settings['auto_delete_source'] = default_config['user_settings']['auto_delete_source']
                changed = True

        if changed:
            save_config(config)

        return config
    except Exception as e:
        print(f"加载配置失败: {e}")
        return default_config


def save_config(config: dict):
    """
    保存配置文件
    
    参数:
        config: 配置字典
    """
    try:
        # 确保配置目录存在
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    except Exception as e:
        raise RuntimeError(f"保存配置失败: {e}")


def get_default_config() -> dict:
    """
    获取默认配置

    返回:
        dict: 默认配置字典
    """
    return {
        "app_settings": {
            "language": "zh-CN",
            "seven_zip_path": DEFAULT_SEVEN_ZIP_PATH
        },
        "text_types": [
            {"label": "说明文本", "value": "说明文本"},
            {"label": "游戏简介", "value": "游戏简介"}
        ],
        "user_settings": {
            "last_text_type": "说明文本",
            "auto_delete_source": False
        }
    }


# ============================================================================
# WC3技能生成器 - 默认配置
# ============================================================================
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


def ensure_data_dirs():
    """
    确保WC3生成器数据目录存在
    """
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SPELLS_DIR.mkdir(parents=True, exist_ok=True)
        COLORS_DIR.mkdir(parents=True, exist_ok=True)
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # 创建默认颜色配置
        default_color_path = COLORS_DIR / 'default.json'
        if not default_color_path.exists():
            import json
            with open(default_color_path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_COLOR_CONFIG, f, ensure_ascii=False, indent=2)

        # 创建默认设置文件
        if not SETTINGS_PATH.exists():
            import json
            default_settings = {
                "lastCategory": "",
                "lastSpell": "",
                "colorConfig": "default"
            }
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"初始化数据目录失败: {e}")


# ============================================================================
# AppApi 类 - 前端API接口
# ============================================================================
class AppApi:
    """
    前端API接口类
    
    所有方法返回dict，包含success字段表示操作是否成功。
    """
    
    def __init__(self):
        self.window = None
        self._drop_bound = False

    def _handle_native_drop(self, event: dict):
        """
        处理 pywebview 原生 drop 事件，并将完整路径回传给前端。
        """
        try:
            files = event.get('dataTransfer', {}).get('files', [])
            paths = []
            for f in files:
                full_path = f.get('pywebviewFullPath') or f.get('path')
                if full_path:
                    paths.append(str(full_path))

            if paths:
                payload = json.dumps(paths, ensure_ascii=False)
                # 调用前端函数，避免浏览器层无法拿到本地路径
                self.window.evaluate_js(f'window.handleNativeDrop({payload});')
        except Exception as e:
            print(f'处理拖拽事件失败: {e}')
    
    def get_initial_state(self, payload=None) -> dict:
        """
        返回初始状态

        返回:
            dict: {
                'success': bool,
                'data': {
                    'text_types': list[str],
                    'selected_text_type': str,
                    'source_files': list,
                    'archive_name': str,
                    'output_dir': str,
                    'seven_zip_path': str,
                    'seven_zip_valid': bool
                }
            }
        """
        try:
            config = load_config()
            app_settings = config.get('app_settings', {})
            user_settings = config.get('user_settings', {})
            text_types_config = config.get('text_types', [])

            # 提取文本类型列表
            text_types = [t.get('value', t.get('label', '')) for t in text_types_config]
            if not text_types:
                text_types = ['说明文本', '游戏简介']

            # 获取 7z 路径并验证
            seven_zip_path = app_settings.get('seven_zip_path', DEFAULT_SEVEN_ZIP_PATH)
            seven_zip_valid = Path(seven_zip_path).exists() if seven_zip_path else False

            return {
                'success': True,
                'data': {
                    'text_types': text_types,
                    'selected_text_type': user_settings.get('last_text_type', '说明文本'),
                    'source_files': [],
                    'archive_name': '',
                    'output_dir': str(APP_DIR),
                    'seven_zip_path': seven_zip_path,
                    'seven_zip_valid': seven_zip_valid
                }
            }
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'message': f'获取初始状态失败: {str(e)}'
            }
    
    def pick_files(self, payload=None) -> dict:
        """
        选择文件对话框，支持多选
        
        返回:
            dict: {'success': bool, 'data': {'files': list[str]}}
        """
        try:
            if self.window is None:
                return {'success': False, 'data': None, 'message': '窗口未初始化'}
            
            files = self.window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=True,
                file_types=('所有文件 (*.*)', '压缩文件 (*.7z;*.zip;*.rar)')
            )
            
            if files:
                return {
                    'success': True,
                    'data': {'files': [str(f) for f in files]}
                }
            else:
                return {
                    'success': True,
                    'data': {'files': []}
                }
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'message': f'选择文件失败: {str(e)}'
            }
    
    def pick_folder(self, payload=None) -> dict:
        """
        选择文件夹对话框
        
        返回:
            dict: {'success': bool, 'data': {'folder': str}}
        """
        try:
            if self.window is None:
                return {'success': False, 'data': None, 'message': '窗口未初始化'}
            
            folders = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            
            if folders:
                return {
                    'success': True,
                    'data': {'folder': str(folders[0])}
                }
            else:
                return {
                    'success': True,
                    'data': {'folder': ''}
                }
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'message': f'选择文件夹失败: {str(e)}'
            }
    
    def pick_output_dir(self, payload=None) -> dict:
        """
        选择输出目录对话框
        
        返回:
            dict: {'success': bool, 'data': {'output_dir': str}}
        """
        try:
            if self.window is None:
                return {'success': False, 'data': None, 'message': '窗口未初始化'}
            
            folders = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            
            if folders:
                return {
                    'success': True,
                    'data': {'output_dir': str(folders[0])}
                }
            else:
                return {
                    'success': True,
                    'data': {'output_dir': ''}
                }
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'message': f'选择输出目录失败: {str(e)}'
            }
    
    def validate_seven_zip(self, payload=None) -> dict:
        """
        验证 setting.yaml 中配置的 7z.exe 是否存在。

        返回:
            dict: {'success': bool, 'data': {'exists': bool, 'path': str}}
        """
        try:
            config = load_config()
            app_settings = config.get('app_settings', {}) if isinstance(config, dict) else {}
            seven_zip_path = (app_settings.get('seven_zip_path') or DEFAULT_SEVEN_ZIP_PATH).strip()
            exists = Path(seven_zip_path).exists()

            return {
                'success': True,
                'data': {
                    'exists': exists,
                    'path': seven_zip_path
                }
            }
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'message': f'验证7z路径失败: {str(e)}'
            }

    def update_seven_zip_path(self, payload: dict) -> dict:
        """
        更新7z路径配置（写入 setting.yaml）。

        参数:
            payload: {'path': str}

        返回:
            dict: {'success': bool, 'message': str}
        """
        try:
            if not payload or 'path' not in payload:
                return {
                    'success': False,
                    'message': '路径参数缺失'
                }

            new_path = str(payload['path']).strip()

            # 验证路径
            if not Path(new_path).exists():
                return {
                    'success': False,
                    'message': f'路径不存在: {new_path}'
                }

            # 检查是否是7z.exe
            if not new_path.lower().endswith('7z.exe'):
                return {
                    'success': False,
                    'message': '请选择有效的7z.exe文件'
                }

            config = load_config()
            if 'app_settings' not in config or not isinstance(config['app_settings'], dict):
                config['app_settings'] = {}

            config['app_settings']['seven_zip_path'] = new_path
            save_config(config)

            return {
                'success': True,
                'message': '7z路径更新成功'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'更新7z路径失败: {str(e)}'
            }

    def reveal_output_file(self, payload: dict = None) -> dict:
        """
        在资源管理器中定位输出文件。

        参数:
            payload: {'zip_path': str}

        返回:
            dict: {'success': bool, 'message': str}
        """
        try:
            if not payload or 'zip_path' not in payload:
                return {
                    'success': False,
                    'message': '输出文件路径缺失'
                }

            zip_path = str(payload.get('zip_path') or '').strip()
            if not zip_path:
                return {
                    'success': False,
                    'message': '输出文件路径为空'
                }

            target = Path(zip_path).resolve()
            parent = target.parent

            if sys.platform.startswith('win'):
                creationflags = subprocess.CREATE_NO_WINDOW

                if target.exists() and target.is_file():
                    subprocess.Popen(
                        ['explorer', f'/select,{str(target)}'],
                        creationflags=creationflags
                    )
                    return {
                        'success': True,
                        'message': '已打开输出文件位置'
                    }

                if parent.exists() and parent.is_dir():
                    subprocess.Popen(
                        ['explorer', str(parent)],
                        creationflags=creationflags
                    )
                    return {
                        'success': True,
                        'message': '已打开输出目录'
                    }
            else:
                if target.exists() and target.is_file() and parent.exists():
                    subprocess.Popen(['xdg-open', str(parent)])
                    return {
                        'success': True,
                        'message': '已打开输出目录'
                    }

                if parent.exists() and parent.is_dir():
                    subprocess.Popen(['xdg-open', str(parent)])
                    return {
                        'success': True,
                        'message': '已打开输出目录'
                    }

            return {
                'success': False,
                'message': f'路径不存在: {zip_path}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'打开输出位置失败: {str(e)}'
            }
    
    def start_packaging(self, payload: dict) -> dict:
        """
        开始打包
        
        参数:
            payload: {
                'source_files': list[str],
                'archive_name': str,
                'text_type': str,
                'text_content': str,
                'output_dir': str
            }
        
        返回:
            dict: {
                'success': bool,
                'message': str,
                'data': {
                    'password': str,
                    'zip_path': str
                }
            }
        """
        try:
            # 验证参数
            if not payload:
                return {
                    'success': False,
                    'message': '参数不能为空',
                    'data': None
                }
            
            source_files = payload.get('source_files', [])
            archive_name = payload.get('archive_name', '')
            text_type = payload.get('text_type', '说明文本')
            text_content = payload.get('text_content', '')
            output_dir = payload.get('output_dir', str(APP_DIR))
            
            if not source_files:
                return {
                    'success': False,
                    'message': '请选择要打包的文件',
                    'data': None
                }
            
            if not archive_name:
                return {
                    'success': False,
                    'message': '请输入压缩包名称',
                    'data': None
                }
            
            # 调用核心打包函数
            result = process_packaging(
                source_paths=source_files,
                output_dir=output_dir,
                archive_name=archive_name,
                text_type=text_type,
                text_content=text_content
            )
            
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'data': {
                    'password': result.get('password', ''),
                    'zip_path': result.get('zip_path', '')
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'打包过程异常: {str(e)}',
                'data': None
            }
    
    def confirm_delete(self, payload: dict) -> dict:
        """
        确认删除源文件
        
        参数:
            payload: {'files': list[str]}
        
        返回:
            dict: {
                'success': bool,
                'message': str,
                'data': {'deleted': list[str]}
            }
        """
        try:
            if not payload:
                return {
                    'success': False,
                    'message': '参数不能为空',
                    'data': {'deleted': []}
                }
            
            files = payload.get('files', [])
            
            if not files:
                return {
                    'success': False,
                    'message': '没有要删除的文件',
                    'data': {'deleted': []}
                }
            
            # 调用核心删除函数
            result = delete_source_files(files)
            
            return {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'data': {
                    'deleted': result.get('deleted', [])
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'删除过程异常: {str(e)}',
                'data': {'deleted': []}
            }
    
    def save_settings(self, payload: dict) -> dict:
        """
        保存用户设置

        参数:
            payload: 用户设置字典

        返回:
            dict: {'success': bool, 'message': str}
        """
        try:
            if not payload:
                return {
                    'success': False,
                    'message': '设置内容为空'
                }

            # 加载现有配置
            config = load_config()

            # 更新用户设置
            if 'user_settings' not in config:
                config['user_settings'] = {}

            config['user_settings'].update(payload)

            # 保存配置
            save_config(config)

            return {
                'success': True,
                'message': '设置保存成功'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'保存设置失败: {str(e)}'
            }

    def save_text_types(self, payload: dict) -> dict:
        """
        保存文本类型列表

        参数:
            payload: {'text_types': list[str]}

        返回:
            dict: {'success': bool, 'message': str}
        """
        try:
            if not payload or 'text_types' not in payload:
                return {
                    'success': False,
                    'message': '文本类型列表为空'
                }

            text_types = payload.get('text_types', [])
            if not isinstance(text_types, list) or len(text_types) == 0:
                return {
                    'success': False,
                    'message': '文本类型列表无效'
                }

            # 加载现有配置
            config = load_config()

            # 更新文本类型列表
            config['text_types'] = [
                {'label': t, 'value': t} for t in text_types
            ]

            # 保存配置
            save_config(config)

            return {
                'success': True,
                'message': '文本类型保存成功'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'保存文本类型失败: {str(e)}'
            }

    # ========================================================================
    # WC3技能生成器 API
    # ========================================================================

    def wc3_get_spell_tree(self, payload=None) -> dict:
        """
        获取技能分类树结构

        返回:
            dict: {'success': bool, 'data': {'tree': list}}
        """
        import json
        try:
            ensure_data_dirs()

            def build_tree(path: Path, depth: int = 0) -> list:
                """递归构建目录树"""
                if depth > 3:  # 限制最大深度为3层
                    return []

                items = []
                try:
                    for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
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
                            # 加载技能名称
                            try:
                                with open(item, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    name = data.get('name', item.stem)
                            except:
                                name = item.stem
                            items.append({
                                'type': 'spell',
                                'name': name,
                                'filename': item.stem,
                                'path': str(item.relative_to(SPELLS_DIR))
                            })
                except Exception as e:
                    print(f'读取目录失败: {e}')
                return items

            tree = build_tree(SPELLS_DIR)
            return {
                'success': True,
                'data': {'tree': tree}
            }
        except Exception as e:
            return {
                'success': False,
                'data': {'tree': []},
                'message': f'获取技能树失败: {str(e)}'
            }

    def wc3_create_category(self, payload: dict) -> dict:
        """
        创建新分类文件夹

        参数:
            payload: {'path': str}  相对路径，如 '英雄/圣骑士'

        返回:
            dict: {'success': bool, 'message': str}
        """
        try:
            if not payload or 'path' not in payload:
                return {'success': False, 'message': '路径参数缺失'}

            rel_path = payload['path'].strip()
            if not rel_path:
                return {'success': False, 'message': '分类名称不能为空'}

            # 验证路径安全性
            if '..' in rel_path or rel_path.startswith('/') or rel_path.startswith('\\'):
                return {'success': False, 'message': '无效的路径'}

            full_path = SPELLS_DIR / rel_path
            if full_path.exists():
                return {'success': False, 'message': '分类已存在'}

            full_path.mkdir(parents=True, exist_ok=True)
            return {'success': True, 'message': '分类创建成功'}
        except Exception as e:
            return {'success': False, 'message': f'创建分类失败: {str(e)}'}

    def wc3_delete_category(self, payload: dict) -> dict:
        """
        删除分类文件夹（含所有子内容）

        参数:
            payload: {'path': str}

        返回:
            dict: {'success': bool, 'message': str}
        """
        import shutil
        try:
            if not payload or 'path' not in payload:
                return {'success': False, 'message': '路径参数缺失'}

            rel_path = payload['path'].strip()
            if not rel_path:
                return {'success': False, 'message': '路径不能为空'}

            # 验证路径安全性
            if '..' in rel_path:
                return {'success': False, 'message': '无效的路径'}

            full_path = SPELLS_DIR / rel_path
            if not full_path.exists() or not full_path.is_dir():
                return {'success': False, 'message': '分类不存在'}

            shutil.rmtree(full_path)
            return {'success': True, 'message': '分类删除成功'}
        except Exception as e:
            return {'success': False, 'message': f'删除分类失败: {str(e)}'}

    def wc3_rename_category(self, payload: dict) -> dict:
        """
        重命名分类

        参数:
            payload: {'path': str, 'newName': str}

        返回:
            dict: {'success': bool, 'message': str}
        """
        try:
            if not payload or 'path' not in payload or 'newName' not in payload:
                return {'success': False, 'message': '参数缺失'}

            rel_path = payload['path'].strip()
            new_name = payload['newName'].strip()

            if not rel_path or not new_name:
                return {'success': False, 'message': '路径或名称不能为空'}

            if '..' in rel_path or '..' in new_name:
                return {'success': False, 'message': '无效的路径'}

            old_path = SPELLS_DIR / rel_path
            parent = old_path.parent
            new_path = parent / new_name

            if not old_path.exists():
                return {'success': False, 'message': '分类不存在'}

            if new_path.exists():
                return {'success': False, 'message': '目标名称已存在'}

            old_path.rename(new_path)
            return {'success': True, 'message': '重命名成功'}
        except Exception as e:
            return {'success': False, 'message': f'重命名失败: {str(e)}'}

    def wc3_save_spell(self, payload: dict) -> dict:
        """
        保存技能数据

        参数:
            payload: {'path': str, 'filename': str, 'data': dict}

        返回:
            dict: {'success': bool, 'message': str}
        """
        import json
        try:
            if not payload or 'data' not in payload:
                return {'success': False, 'message': '数据参数缺失'}

            data = payload['data']
            rel_path = payload.get('path', '').strip()
            filename = payload.get('filename', '').strip()

            # 如果没有文件名，使用技能名称
            if not filename:
                filename = data.get('name', '未命名技能')
                if not filename:
                    return {'success': False, 'message': '技能名称不能为空'}

            # 确保文件名有效
            filename = filename.replace('/', '_').replace('\\', '_').replace(':', '_')

            # 构建完整路径
            if rel_path:
                full_dir = SPELLS_DIR / rel_path
            else:
                full_dir = SPELLS_DIR

            full_dir.mkdir(parents=True, exist_ok=True)
            full_path = full_dir / f'{filename}.json'

            # 保存数据
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return {
                'success': True,
                'message': '技能保存成功',
                'data': {'path': str(full_path.relative_to(SPELLS_DIR))}
            }
        except Exception as e:
            return {'success': False, 'message': f'保存技能失败: {str(e)}'}

    def wc3_load_spell(self, payload: dict) -> dict:
        """
        加载技能数据

        参数:
            payload: {'path': str}

        返回:
            dict: {'success': bool, 'data': dict}
        """
        import json
        try:
            if not payload or 'path' not in payload:
                return {'success': False, 'message': '路径参数缺失', 'data': None}

            rel_path = payload['path'].strip()
            if not rel_path:
                return {'success': False, 'message': '路径不能为空', 'data': None}

            if '..' in rel_path:
                return {'success': False, 'message': '无效的路径', 'data': None}

            full_path = SPELLS_DIR / rel_path
            if not full_path.exists():
                return {'success': False, 'message': '技能文件不存在', 'data': None}

            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return {'success': True, 'data': data}
        except Exception as e:
            return {'success': False, 'message': f'加载技能失败: {str(e)}', 'data': None}

    def wc3_delete_spell(self, payload: dict) -> dict:
        """
        删除技能文件

        参数:
            payload: {'path': str}

        返回:
            dict: {'success': bool, 'message': str}
        """
        try:
            if not payload or 'path' not in payload:
                return {'success': False, 'message': '路径参数缺失'}

            rel_path = payload['path'].strip()
            if not rel_path:
                return {'success': False, 'message': '路径不能为空'}

            if '..' in rel_path:
                return {'success': False, 'message': '无效的路径'}

            full_path = SPELLS_DIR / rel_path
            if not full_path.exists():
                return {'success': False, 'message': '技能文件不存在'}

            full_path.unlink()
            return {'success': True, 'message': '技能删除成功'}
        except Exception as e:
            return {'success': False, 'message': f'删除技能失败: {str(e)}'}

    def wc3_rename_spell(self, payload: dict) -> dict:
        """
        重命名技能文件

        参数:
            payload: {'path': str, 'newName': str}

        返回:
            dict: {'success': bool, 'message': str}
        """
        import json
        try:
            if not payload or 'path' not in payload or 'newName' not in payload:
                return {'success': False, 'message': '参数缺失'}

            rel_path = payload['path'].strip()
            new_name = payload['newName'].strip()

            if not rel_path or not new_name:
                return {'success': False, 'message': '路径或名称不能为空'}

            if '..' in rel_path or '..' in new_name:
                return {'success': False, 'message': '无效的路径'}

            old_path = SPELLS_DIR / rel_path
            if not old_path.exists():
                return {'success': False, 'message': '技能文件不存在'}

            parent = old_path.parent
            new_path = parent / f'{new_name}.json'

            if new_path.exists():
                return {'success': False, 'message': '目标名称已存在'}

            # 更新技能数据中的名称
            with open(old_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['name'] = new_name

            old_path.rename(new_path)
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return {'success': True, 'message': '重命名成功'}
        except Exception as e:
            return {'success': False, 'message': f'重命名失败: {str(e)}'}

    def wc3_export_category(self, payload: dict) -> dict:
        """
        导出分类到JSON文件

        参数:
            payload: {'path': str}

        返回:
            dict: {'success': bool, 'message': str, 'data': {'exportPath': str}}
        """
        import json
        import shutil
        from datetime import datetime

        try:
            if not payload or 'path' not in payload:
                return {'success': False, 'message': '路径参数缺失'}

            rel_path = payload['path'].strip()
            if not rel_path:
                return {'success': False, 'message': '路径不能为空'}

            if '..' in rel_path:
                return {'success': False, 'message': '无效的路径'}

            source_path = SPELLS_DIR / rel_path
            if not source_path.exists():
                return {'success': False, 'message': '分类不存在'}

            # 生成导出文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_name = f'{rel_path.replace("/", "_").replace("\\", "_")}_{timestamp}.json'
            export_path = EXPORTS_DIR / export_name

            # 收集所有技能数据
            export_data = {
                'category': rel_path,
                'exportTime': timestamp,
                'spells': []
            }

            def collect_spells(path: Path, prefix: str = '') -> list:
                """递归收集技能"""
                spells = []
                for item in path.iterdir():
                    if item.is_dir():
                        spells.extend(collect_spells(item, f'{prefix}{item.name}/'))
                    elif item.is_file() and item.suffix == '.json':
                        try:
                            with open(item, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                spells.append({
                                    'relativePath': f'{prefix}{item.stem}',
                                    'data': data
                                })
                        except:
                            pass
                return spells

            export_data['spells'] = collect_spells(source_path)

            # 写入导出文件
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            return {
                'success': True,
                'message': f'导出成功，共{len(export_data["spells"])}个技能',
                'data': {'exportPath': str(export_path)}
            }
        except Exception as e:
            return {'success': False, 'message': f'导出失败: {str(e)}'}

    def wc3_import_file(self, payload: dict) -> dict:
        """
        导入JSON文件

        参数:
            payload: {'filePath': str} 或无参数则打开文件选择对话框

        返回:
            dict: {'success': bool, 'message': str, 'data': dict}
        """
        import json
        try:
            # 如果没有提供文件路径，打开文件选择对话框
            if not payload or 'filePath' not in payload:
                if self.window is None:
                    return {'success': False, 'message': '窗口未初始化'}

                files = self.window.create_file_dialog(
                    webview.OPEN_DIALOG,
                    allow_multiple=False,
                    file_types=('JSON文件 (*.json)',)
                )

                if not files:
                    return {'success': True, 'message': '未选择文件', 'data': None}

                file_path = files[0]
            else:
                file_path = payload['filePath']

            if not Path(file_path).exists():
                return {'success': False, 'message': '文件不存在'}

            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # 验证导入数据格式
            if 'spells' not in import_data:
                return {'success': False, 'message': '导入文件格式无效'}

            # 导入技能
            imported_count = 0
            for spell in import_data['spells']:
                rel_path = spell.get('relativePath', '')
                data = spell.get('data', {})

                if not data.get('name'):
                    continue

                # 确定保存路径
                parts = rel_path.split('/')
                if len(parts) > 1:
                    category_path = '/'.join(parts[:-1])
                    filename = parts[-1]
                else:
                    category_path = import_data.get('category', '')
                    filename = data.get('name', '未命名')

                # 保存技能
                result = self.wc3_save_spell({
                    'path': category_path,
                    'filename': filename,
                    'data': data
                })

                if result['success']:
                    imported_count += 1

            return {
                'success': True,
                'message': f'导入成功，共{imported_count}个技能',
                'data': {'importedCount': imported_count}
            }
        except Exception as e:
            return {'success': False, 'message': f'导入失败: {str(e)}'}

    def wc3_get_color_configs(self, payload=None) -> dict:
        """
        获取所有颜色配置列表

        返回:
            dict: {'success': bool, 'data': {'configs': list}}
        """
        import json
        try:
            ensure_data_dirs()

            configs = []
            for item in COLORS_DIR.iterdir():
                if item.is_file() and item.suffix == '.json':
                    try:
                        with open(item, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        configs.append({
                            'name': item.stem,
                            'config': data
                        })
                    except:
                        pass

            return {
                'success': True,
                'data': {'configs': configs}
            }
        except Exception as e:
            return {
                'success': False,
                'data': {'configs': []},
                'message': f'获取颜色配置失败: {str(e)}'
            }

    def wc3_save_color_config(self, payload: dict) -> dict:
        """
        保存颜色配置

        参数:
            payload: {'name': str, 'config': dict}

        返回:
            dict: {'success': bool, 'message': str}
        """
        import json
        try:
            if not payload or 'name' not in payload or 'config' not in payload:
                return {'success': False, 'message': '参数缺失'}

            name = payload['name'].strip()
            config = payload['config']

            if not name:
                return {'success': False, 'message': '名称不能为空'}

            # 确保名称有效
            name = name.replace('/', '_').replace('\\', '_').replace(':', '_')

            ensure_data_dirs()
            path = COLORS_DIR / f'{name}.json'

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            return {'success': True, 'message': '颜色配置保存成功'}
        except Exception as e:
            return {'success': False, 'message': f'保存颜色配置失败: {str(e)}'}

    def wc3_delete_color_config(self, payload: dict) -> dict:
        """
        删除颜色配置

        参数:
            payload: {'name': str}

        返回:
            dict: {'success': bool, 'message': str}
        """
        try:
            if not payload or 'name' not in payload:
                return {'success': False, 'message': '参数缺失'}

            name = payload['name'].strip()
            if not name:
                return {'success': False, 'message': '名称不能为空'}

            if name == 'default':
                return {'success': False, 'message': '不能删除默认配置'}

            path = COLORS_DIR / f'{name}.json'
            if not path.exists():
                return {'success': False, 'message': '配置不存在'}

            path.unlink()
            return {'success': True, 'message': '颜色配置删除成功'}
        except Exception as e:
            return {'success': False, 'message': f'删除颜色配置失败: {str(e)}'}

    def wc3_get_settings(self, payload=None) -> dict:
        """
        获取应用设置

        返回:
            dict: {'success': bool, 'data': dict}
        """
        import json
        try:
            ensure_data_dirs()

            if SETTINGS_PATH.exists():
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            else:
                settings = {
                    'lastCategory': '',
                    'lastSpell': '',
                    'colorConfig': 'default'
                }

            return {
                'success': True,
                'data': settings
            }
        except Exception as e:
            return {
                'success': False,
                'data': {},
                'message': f'获取设置失败: {str(e)}'
            }

    def wc3_save_settings(self, payload: dict) -> dict:
        """
        保存应用设置

        参数:
            payload: dict 设置内容

        返回:
            dict: {'success': bool, 'message': str}
        """
        import json
        try:
            if not payload:
                return {'success': False, 'message': '设置内容为空'}

            ensure_data_dirs()

            # 加载现有设置并更新
            if SETTINGS_PATH.exists():
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            else:
                settings = {}

            settings.update(payload)

            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)

            return {'success': True, 'message': '设置保存成功'}
        except Exception as e:
            return {'success': False, 'message': f'保存设置失败: {str(e)}'}

    def wc3_get_initial_state(self, payload=None) -> dict:
        """
        获取WC3生成器初始状态

        返回:
            dict: {'success': bool, 'data': dict}
        """
        import json
        try:
            ensure_data_dirs()

            # 获取分类树
            tree_result = self.wc3_get_spell_tree()
            tree = tree_result.get('data', {}).get('tree', [])

            # 获取颜色配置列表
            colors_result = self.wc3_get_color_configs()
            colors = colors_result.get('data', {}).get('configs', [])

            # 获取应用设置
            settings_result = self.wc3_get_settings()
            settings = settings_result.get('data', {})

            # 加载当前颜色配置
            color_name = settings.get('colorConfig', 'default')
            color_config = DEFAULT_COLOR_CONFIG
            for c in colors:
                if c['name'] == color_name:
                    color_config = c['config']
                    break

            return {
                'success': True,
                'data': {
                    'tree': tree,
                    'colorConfigs': colors,
                    'currentColorConfig': color_config,
                    'currentColorName': color_name,
                    'settings': settings,
                    'defaultSpellData': DEFAULT_SPELL_DATA
                }
            }
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'message': f'获取初始状态失败: {str(e)}'
            }


# ============================================================================
# 主函数入口
# ============================================================================
def ensure_config_exists():
    """
    确保配置文件存在，避免首次启动时阻塞。
    """
    try:
        if not CONFIG_PATH.exists():
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            default_config = get_default_config()
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)
    except Exception as e:
        print(f"初始化配置文件失败: {e}")


def main():
    """
    主函数入口

    创建pywebview窗口并启动应用。
    """
    # 预先确保配置文件存在，避免首次启动阻塞 UI
    ensure_config_exists()

    # 初始化WC3生成器数据目录
    ensure_data_dirs()

    api = AppApi()

    window = webview.create_window(
        'WC3技能文本生成器',
        url=str(WEBUI_INDEX),
        js_api=api,
        width=1100,
        height=750,
        min_size=(900, 600),
        text_select=True,
    )

    api.window = window

    def on_loaded():
        # 绑定 drop 事件（仅绑定一次）
        if not api._drop_bound:
            try:
                drop_zone = window.dom.get_element('#dropZone')
                if drop_zone:
                    drop_zone.on(
                        'drop',
                        DOMEventHandler(api._handle_native_drop, prevent_default=True)
                    )
                    api._drop_bound = True
            except Exception as e:
                print(f'绑定拖拽事件失败: {e}')

    window.events.loaded += on_loaded

    # 启动webview（debug=False用于生产环境）
    webview.start(debug=False)


if __name__ == '__main__':
    main()
