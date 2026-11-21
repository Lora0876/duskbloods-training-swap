"""训练场换怪工具（GUI · 官方配色 · 中英双语）

三个标靶各选一个生物，点「应用并启动」，进庭院后在面板里逐个切标靶看效果。

用法：双击 `训练场换怪工具.cmd`，或
    python training_tool.py [--en]
"""
import contextlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
import tkinter as tk
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_TITLE = '黄昏血族 · 训练场换怪工具'
TOOL_VERSION = '1.4'

# 取自 campaign.theduskbloods.jp 网络测试导览的官方配色
BG = '#0f0b0b'
CARD = '#1a1212'
CARD2 = '#130d0d'
LINE = '#3a2a28'
TEXT = '#f2f2f2'
MUTED = '#8b7b78'
ACCENT = '#fb992f'
ACCENT_HI = '#ffb055'
GOLD = '#f0d26b'
OKC = '#b9c98a'
ERR = '#f65f5f'

TEXTS = {
    'zh': {
        'title': '训练场换怪',
        'sub': '把训练标靶换成任意敌人或眷属',
        'search': '搜索',
        'search_hint': '模型号或名字',
        'rows': ['墓地稻草人', '信徒（三位）', '巨人信徒'],
        'apply_launch': '应用并启动',
        'apply': '应用（只装）',
        'restore': '还原原版',
        'reload': '刷新清单',
        'ready': '选好三个标靶后点「应用并启动」',
        'building': '构建 MSB ...',
        'installing': '安装到 load 目录 ...',
        'installed': '✔ 已安装，启动游戏后进庭院切标靶即可',
        'installed_launch': '已安装，正在启动游戏 ...',
        'launched': '已启动：标题按 A；大厅按 Plus → 庭院 → A',
        'restored': '✔ 已还原原版训练场',
        'failed': '✘ 失败：',
        'restore_failed': '✘ 还原失败：',
        'lang': '语言：中文',
        'no_params': '没有参数，换不了',
        'oodle': '指定 Oodle...',
        'oodle_title': '选择 oo2core_9_win64.dll（改怪用的 Oodle 压缩库）',
        'oodle_ok': '已记住 Oodle 库：{path}',
        'oodle_bad': '这个文件不能用：{error}',
        'oodle_ask': ('缺少 oo2core_9_win64.dll（改怪用的 Oodle 压缩库）。\n\n'
                      '现在指定它吗？\n'
                      '它在你自己的《艾尔登法环》/《黑夜君临》游戏目录里。'),
        'oodle_missing': '没有指定 Oodle 库，改怪不会生效',
        'oodle_hint': ('提示：没找到 oo2core_9_win64.dll，点「应用」会失败。'
                       '点右下角「指定 Oodle...」选中它即可（在《艾尔登法环》/《黑夜君临》游戏目录里）。'),
        'model': '角色',
        'variant': '变体',
        'pick_package': '选择游戏包...',
        'pick_package_title': '选择游戏包文件夹（含 DuskbloodsCloud.exe 或 local\\settings.json 的那一层）',
        'pkg_ok': '已选择游戏包：{path}',
        'pkg_bad': ('这个文件夹看起来不是游戏包：\n\n{path}\n\n'
                    '请选到包含 DuskbloodsCloud.exe（或 02-启动游戏.cmd、local\\settings.json）的那一层文件夹。'),
        'pkg_none': '（没找到游戏包 —— 点「选择游戏包...」手动指定）',
        'no_pkg_hint': '提示：没找到游戏包。点「选择游戏包...」选到含 DuskbloodsCloud.exe 的那层文件夹。',
        'oodle_searching': '正在自动搜索 oo2core_9_win64.dll（第一次可能要十几秒）…',
        'oodle_found': '已自动找到 Oodle 库：{path}',
        'oodle_find_none': '自动搜索没找到 oo2core_9_win64.dll。点右下角「指定 Oodle...」手动选它（在《艾尔登法环》/《黑夜君临》游戏目录里）。',
        'refresh': '清单已刷新',
        'err_title': '失败',
        'lang_btn': 'EN',
        'game_build': '游戏版本',
        'rescan': '重新扫描',
        'rescanned': '已重新扫描游戏版本',
        'build_selected': '游戏版本：{name}',
        'variant_pick': '{model} 变体：{name}',
        'no_params_borrow': '{model} 没有参数行，自动借用 c6000（模型不变）',
        'no_launcher': '这个游戏版本没找到启动脚本',
        'win_title': '黄昏血族 · 训练场换怪工具',
        'variant_default': '默认',
    },
    'en': {
        'title': 'Training Ground Swap',
        'sub': 'Replace the courtyard training targets with any enemy or Kin',
        'search': 'Search',
        'search_hint': 'model id or name',
        'rows': ['Graveyard Scarecrow', 'Adherent (three)', 'Giant adherent'],
        'apply_launch': 'Apply & launch',
        'apply': 'Apply only',
        'restore': 'Restore',
        'reload': 'Reload',
        'ready': 'Pick the three targets, then press Apply & launch',
        'building': 'Building the MSB ...',
        'installing': 'Installing into the load directory ...',
        'installed': 'Installed. Enter the courtyard and switch targets in its panel.',
        'installed_launch': 'Installed, launching the game ...',
        'launched': 'Launched: press A at the title; in the hall press Plus > Courtyard > A',
        'restored': 'Vanilla training ground restored',
        'failed': 'Failed: ',
        'restore_failed': 'Restore failed: ',
        'lang': 'Language: English',
        'no_params': 'has no params',
        'oodle': 'Set Oodle...',
        'oodle_title': 'Pick oo2core_9_win64.dll (the Oodle library used for the MSB)',
        'oodle_ok': 'Oodle library remembered: {path}',
        'oodle_bad': 'That file cannot be used: {error}',
        'oodle_ask': ('oo2core_9_win64.dll (the Oodle library) is missing.\n\n'
                      'Pick it now?\n'
                      'It is in your own Elden Ring / Nightreign game folder.'),
        'oodle_missing': 'No Oodle library set; the swap will not work',
        'oodle_hint': ('Note: oo2core_9_win64.dll was not found, so "Apply" will fail. '
                       'Click "Set Oodle..." at the bottom right and pick it (it is in your '
                       'Elden Ring / Nightreign game folder).'),
        'model': 'Model',
        'variant': 'Variant',
        'pick_package': 'Pick game folder...',
        'pick_package_title': 'Pick the game folder (the one with DuskbloodsCloud.exe or local\\settings.json)',
        'pkg_ok': 'Game folder set: {path}',
        'pkg_bad': ('That folder does not look like a game package:\n\n{path}\n\n'
                    'Pick the folder that contains DuskbloodsCloud.exe (or 02-启动游戏.cmd, '
                    'or local\\settings.json).'),
        'pkg_none': '(no game folder found - click "Pick game folder..." to set it)',
        'no_pkg_hint': ('Note: no game folder was found. Click "Pick game folder..." and choose the '
                        'folder with DuskbloodsCloud.exe.'),
        'oodle_searching': 'Searching for oo2core_9_win64.dll automatically (the first time may take ~10 s)...',
        'oodle_found': 'Found the Oodle library automatically: {path}',
        'oodle_find_none': ('Automatic search did not find oo2core_9_win64.dll. Click "Set Oodle..." at the '
                            'bottom right to pick it (it is in your Elden Ring / Nightreign game folder).'),
        'refresh': 'Catalog reloaded',
        'err_title': 'Error',
        'lang_btn': '中文',
        'game_build': 'Game build',
        'rescan': 'Rescan',
        'rescanned': 'Game builds rescanned',
        'build_selected': 'Game build: {name}',
        'variant_pick': '{model} variant: {name}',
        'no_params_borrow': '{model} has no params; borrowing c6000 (the model stays the same)',
        'no_launcher': 'No launcher script for this game build',
        'win_title': 'The Duskbloods - Training Ground Swap',
        'variant_default': 'default',
        'dialog_no_server': ('Cannot reach the emulator debug service (127.0.0.1:6546).\n\n'
                             'Set this before starting the game:\nEDEN_NX2_DEBUG_SERVER=127.0.0.1:6546\n\n'
                             'Starting it from the Chinese playDB launcher already does this.'),
        'dialog_no_cmd': ('No launcher script found (02-启动游戏.cmd / 02-单人模式.cmd), '
                          'so the game cannot be started from here.\n\n'
                          'Start it with the playDB launcher yourself, then tick HP lock '
                          'once you are in the training ground / courtyard.'),
    },
}

def _pick_family():
    try:
        from tkinter import font as _font
        fams = set(_font.families())
        for name in ('Microsoft YaHei UI', 'Noto Sans SC', 'DengXian', 'SimHei'):
            if name in fams:
                return name
    except Exception:
        pass
    return 'Microsoft YaHei UI'


FONT_FAMILY = _pick_family()
FONT_SIZE = 10


def set_console_title(title):
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    except Exception:
        pass


def enable_dpi():
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, r'C:\Users\a\Downloads\dusk_exp\boss_work')

import paths              # noqa: E402
import patch_m80          # noqa: E402
import training_build as tb  # noqa: E402

class _LogTee:
    """把 print 输出转发到日志。"""

    def __init__(self, log):
        self._log = log

    def write(self, text):
        s = (text or '').rstrip('\n')
        if s.strip():
            self._log(s.strip(), 'muted')
        return len(text or '')

    def flush(self):
        pass


CATALOG = HERE / 'catalog.json'
LOG_DIR = HERE / 'logs'
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
PROFILE = 'cloud'

TARGETS = [
    ('scarecrow', 5, ['c2210_0000', 'c2210_0001']),
    ('adherents', 1, ['c2000_0000', 'c2000_0001', 'c2000_0002',
                      'c2000_0003', 'c2000_0004', 'c2000_0005']),
    ('giant', 2, ['c2010_0000', 'c2010_0001']),
]

KIND_TAG = {'enemy': '【敌】', 'companion': '【眷】'}
KIND_TAG_EN = {'enemy': '[Enemy] ', 'companion': '[Kin] '}


def load_catalog():
    if not CATALOG.exists():
        raise SystemExit('缺 catalog.json，先运行 tools/make_catalog.py --all')
    return json.loads(CATALOG.read_text(encoding='utf-8'))


class App:
    def __init__(self, root):
        self.root = root
        self.lang = 'zh'
        root.title(self.t('win_title'))
        try:
            self.scale = max(1.0, root.winfo_fpixels('1i') / 96.0)
        except Exception:
            self.scale = 1.0
        try:
            root.tk.call('tk', 'scaling', self.scale * 1.3333)
        except Exception:
            pass
        root.geometry(f'{int(760 * self.scale)}x{int(430 * self.scale)}')
        root.configure(bg=BG)
        root.resizable(False, False)

        self._init_feedback_log()
        self._style()
        self.catalog = load_catalog()
        self.rebuild_labels()
        self.rows = []

        self._header()
        self._version()
        self._search()
        self._form()
        self._footer()
        bottom = tk.Frame(root, bg=BG)
        bottom.pack(fill='x', padx=18, pady=(0, 10))
        self.b_logs = tk.Button(bottom, text=self._t('运行日志', 'Logs'), command=self.open_logs_folder,
                                bd=0, bg=CARD, fg=MUTED, activebackground=LINE,
                                activeforeground=GOLD, font=(FONT_FAMILY, 9), padx=12, pady=2,
                                cursor='hand2')
        self.b_logs.pack(side='right', padx=(8, 0))
        self.b_github = tk.Button(bottom, text=self._t('去 GitHub 反馈问题', 'Report on GitHub'), command=self.feedback_github,
                                  bd=0, bg=CARD, fg=GOLD, activebackground=LINE,
                                  activeforeground=GOLD, font=(FONT_FAMILY, 9), padx=12, pady=2,
                                  cursor='hand2')
        self.b_github.pack(side='right')
        self.b_fix = tk.Button(bottom, text=self._t('一键修复', 'Auto Fix'), command=self.self_heal,
                               bd=0, bg=CARD, fg=OKC, activebackground=LINE,
                               activeforeground=OKC, font=(FONT_FAMILY, 9), padx=12, pady=2,
                               cursor='hand2')
        self.b_fix.pack(side='right', padx=(0, 8))
        self.w_status = tk.Label(bottom, text=self.t('ready'), bg=BG, fg=MUTED,
                                 font=(FONT_FAMILY, 9), anchor='w')
        self.w_status.pack(side='left', fill='x', expand=True)
        self._startup_hints()

    # ---------- 语言 ----------
    def _startup_hints(self):
        """刚打开时：oo2core 找不到就后台自动搜；还是没有再提示手动指定。顺带提示游戏包。"""
        self._oodle_search_result = 'idle'
        found = None
        try:
            found = patch_m80.oo2core_path()
        except Exception:
            pass
        if found is None:
            self.log(self.t('oodle_searching'), 'muted')
            self._oodle_search_result = None      # None = 搜索中
            import threading

            def worker():
                try:
                    self._oodle_search_result = patch_m80.auto_find_oo2core() or ''
                except Exception:
                    self._oodle_search_result = ''

            threading.Thread(target=worker, name='oodle-search', daemon=True).start()
            self.root.after(400, self._poll_oodle_search)
            return
        if not getattr(self, '_pkgs', None):
            self.log(self.t('no_pkg_hint'), 'muted')

    def _poll_oodle_search(self):
        """等后台搜索结束（线程只写一个字段，界面线程来读）。"""
        try:
            result = getattr(self, '_oodle_search_result', 'idle')
            if result is None:
                self.root.after(400, self._poll_oodle_search)
                return
            if result:
                self.log(self.t('oodle_found').format(path=result), 'ok')
            else:
                self.log(self.t('oodle_find_none'), 'muted')
            if not getattr(self, '_pkgs', None):
                self.root.after(1200, lambda: self.log(self.t('no_pkg_hint'), 'muted'))
        except Exception:
            pass

    def _translate_kind(self, label):
        if getattr(self, 'lang', 'zh') != 'en':
            return label
        return {'云分享包': 'Cloud build', '云包': 'Cloud build',
                '单人包': 'Solo build', '游戏包': 'Game build'}.get(label, label)

    def _translate_state(self, text):
        """把 Mod 状态文案翻成当前语言（内部逻辑仍用中文判断）。"""
        if getattr(self, 'lang', 'zh') != 'en' or not text:
            return text
        if text.startswith('已装'):
            return text.replace('已装 Mod', 'Mod installed').replace('字节', 'bytes')
        return {
            '未装 Mod': 'Mod not installed',
            '覆盖层是原版（等于没装）': 'Overlay is the original file (not installed)',
            '无游戏本体': 'No game data',
        }.get(text, text)

    def _t(self, zh, en):
        """按当前语言返回文案。"""
        return en if getattr(self, 'lang', 'zh') == 'en' else zh

    def t(self, key):
        return TEXTS[self.lang][key]

    def toggle_lang(self):
        self.lang = 'en' if self.lang == 'zh' else 'zh'
        self.lang_btn.configure(text=self.t('lang_btn'))
        self.w_title.configure(text=self.t('title'))
        self.w_sub.configure(text=self.t('sub'))
        self.w_search_lbl.configure(text=self.t('search'))
        self.w_search_hint.configure(text=self.t('search_hint'))
        for lbl, key in zip(self.w_row_labels, (0, 1, 2)):
            lbl.configure(text=self.t('rows')[key])
        # 游戏版本行
        self.w_build_lbl.configure(text=self.t('game_build'))
        self.w_rescan.configure(text=self.t('rescan'))
        if hasattr(self, 'w_pick_pkg'):
            self.w_pick_pkg.configure(text=self.t('pick_package'))
        if hasattr(self, 'w_variant_head'):
            self.w_model_head.configure(text=self.t('model'))
            self.w_variant_head.configure(text=self.t('variant'))
        self.root.title(self.t('win_title'))
        self.b_launch.configure(text=self.t('apply_launch'))
        if hasattr(self, 'b_install'):
            self.b_install.configure(text=self._t('安装 Mod', 'Install Mod'))
        if hasattr(self, 'b_uninstall'):
            self.b_uninstall.configure(text=self._t('卸载 Mod', 'Uninstall Mod'))
        if hasattr(self, 'b_fix'):
            self.b_fix.configure(text=self._t('一键修复', 'Auto Fix'))
        if hasattr(self, 'b_logs'):
            self.b_logs.configure(text=self._t('运行日志', 'Logs'))
        if hasattr(self, 'b_github'):
            self.b_github.configure(text=self._t('去 GitHub 反馈问题', 'Report on GitHub'))
        self.b_reload.configure(text=self.t('reload'))
        self.b_oodle.configure(text=self.t('oodle'))

        cur = [r['model'].get().split('  ')[0] for r in self.rows]
        # 先记下每个变体在列表里的下标（切语言后名字会变，用下标才能对回去）
        variant_index = []
        for row in self.rows:
            entry = self.by_label.get(row['model'].get()) or {}
            vs = entry.get('variants') or []
            shown = row['variant'].get()
            idx = next((i for i, v in enumerate(vs) if self._variant_label(v) == shown), 0)
            variant_index.append(idx)
        self.rebuild_labels()
        for row, m, idx in zip(self.rows, cur, variant_index):
            row['model'].configure(values=self.labels)
            row['model'].set(next((lb for lb in self.labels if lb.startswith(m + '  ')),
                                  next((lb for lb in self.labels if lb.startswith(m)), self.labels[0])))
            self._refresh_variants(row)
            vs = (self.by_label.get(row['model'].get()) or {}).get('variants') or []
            if vs:
                row['variant'].set(self._variant_label(vs[min(idx, len(vs) - 1)]))
        self.log(self.t('lang'), 'muted')

    # ---------- 外观 ----------
    def _style(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use('clam')
        except Exception:
            pass
        ui = (FONT_FAMILY, FONT_SIZE)
        st.configure('.', background=BG, foreground=TEXT, fieldbackground=CARD,
                     bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        st.configure('TLabel', background=BG, foreground=TEXT, font=ui)
        st.configure('TCombobox', fieldbackground=CARD, background=CARD, foreground=TEXT,
                     arrowcolor=MUTED, padding=6, borderwidth=1, relief='flat')
        st.map('TCombobox',
               fieldbackground=[('readonly', CARD), ('active', CARD)],
               foreground=[('readonly', TEXT)],
               selectbackground=[('readonly', CARD)],
               selectforeground=[('readonly', TEXT)],
               bordercolor=[('focus', ACCENT)],
               arrowcolor=[('active', TEXT)])
        st.configure('TEntry', fieldbackground=CARD2, foreground=TEXT, insertcolor=TEXT,
                     bordercolor=LINE, padding=5, relief='flat')
        st.configure('TButton', background=CARD, foreground=TEXT, borderwidth=0,
                     focuscolor=BG, padding=(15, 9), font=ui)
        st.map('TButton', background=[('active', LINE)], foreground=[('active', TEXT)])
        st.configure('Primary.TButton', background=ACCENT, foreground='#1a0d0d',
                     font=(FONT_FAMILY, FONT_SIZE, 'bold'))
        st.map('Primary.TButton', background=[('active', ACCENT_HI)])
        self.root.option_add('*TCombobox*Listbox.background', CARD)
        self.root.option_add('*TCombobox*Listbox.foreground', TEXT)
        self.root.option_add('*TCombobox*Listbox.selectBackground', ACCENT)
        self.root.option_add('*TCombobox*Listbox.selectForeground', '#1a0d0d')
        self.root.option_add('*TCombobox*Listbox.font', ui)

    def _version(self):
        """游戏版本切换：云分享包 / 单人包。"""
        row = tk.Frame(self.root, bg=BG)
        row.pack(fill='x', padx=18, pady=(10, 0))
        self.w_build_lbl = tk.Label(row, text=self.t('game_build'), bg=BG, fg=MUTED,
                                    font=(FONT_FAMILY, 9))
        self.w_build_lbl.pack(side='left')
        self.version_var = tk.StringVar()
        self.pkg_btn = tk.Button(row, text='…', command=self._show_pkg_menu, anchor='w',
                                 width=52, bd=0, bg=CARD, fg=TEXT, activebackground=LINE,
                                 activeforeground=TEXT, font=(FONT_FAMILY, 9), padx=6, pady=2,
                                 cursor='hand2')
        self.pkg_btn.pack(side='left', padx=8)
        self.w_rescan = tk.Button(row, text=self.t('rescan'), command=self._rescan_versions,
                                  bd=0, bg=CARD, fg=GOLD, activebackground=LINE,
                                  activeforeground=GOLD, font=(FONT_FAMILY, 9), padx=10, pady=1,
                                  cursor='hand2')
        self.w_rescan.pack(side='left')
        self.w_pick_pkg = tk.Button(row, text=self.t('pick_package'), command=self.pick_package,
                                    bd=0, bg=CARD, fg=GOLD, activebackground=LINE,
                                    activeforeground=GOLD, font=(FONT_FAMILY, 9), padx=10, pady=1,
                                    cursor='hand2')
        self.w_pick_pkg.pack(side='left', padx=(6, 0))
        self._fill_versions()

    def _fill_versions(self):
        try:
            self._pkgs = paths.packages()
        except Exception:
            self._pkgs = []
        # 只保留下拉里“真能换怪”的包：必须有游戏本体和 m80 地图
        usable, skipped = [], []
        for lb, p in self._pkgs:
            try:
                ok = bool(paths.detect.game_base(p)) and (Path(paths.detect.game_base(p))
                     / 'romfs' / 'map' / 'mapstudio' / 'm80_00_00_00.msb.dcx').exists()
            except Exception:
                ok = False
            (usable if ok else skipped).append((lb, p))
        if skipped:
            for lb, p in skipped:
                self.log(f'跳过（没有游戏本体 / 没有 m80 地图）：{lb} — {p}', 'muted')
        self._pkgs = usable or self._pkgs
        cur = paths.current_cloud()
        pick = next((lb for lb, p in self._pkgs if cur and Path(p) == Path(cur)), None)
        if not pick and self._pkgs:
            pick, cur = self._pkgs[0][0], self._pkgs[0][1]
            paths.set_current(cur)
        if pick:
            self.version_var.set(f'{pick} — {cur}')
        else:
            self.version_var.set(self.t('pkg_none'))
        self._refresh_ui_state()

    # ---------- Mod 安装检测 ----------
    @staticmethod
    def _mod_info(pkg):
        """返回 (可用, 覆盖层路径, 状态文字, 颜色键)。一个包可能有多个 load 目录。"""
        pkg = Path(pkg)
        try:
            base = paths.detect.game_base(pkg)
        except Exception:
            base = None
        orig = (Path(base) / 'romfs' / 'map' / 'mapstudio' / 'm80_00_00_00.msb.dcx') if base else None
        if not orig or not orig.exists():
            return False, None, '无游戏本体', 'err'
        try:
            targets = paths.detect.overlay_targets(pkg)
        except Exception:
            targets = []
        existing = [x for x in targets if x.exists()]
        if not existing:
            return True, (targets[0] if targets else None), '未装 Mod', 'warn'
        orig_bytes = None
        try:
            orig_bytes = orig.read_bytes()
        except Exception:
            pass
        best = None
        for x in existing:
            try:
                same = orig_bytes is not None and x.read_bytes() == orig_bytes
            except Exception:
                same = False
            if not same:
                best = x
                break
        if best is None:
            return True, existing[0], '覆盖层是原版（等于没装）', 'err'
        try:
            size = best.stat().st_size
        except Exception:
            size = 0
        return True, best, f'已装 Mod（{size:,} 字节）', 'ok'

    def _refresh_ui_state(self):
        cur = paths.current_cloud()
        if not cur:
            return
        _ok, _ov, text, color = self._mod_info(cur)
        installed = text.startswith('已装')
        try:
            shown = self.version_var.get() or '…'
            if getattr(self, 'lang', 'zh') == 'en':
                for zh, en in (('云分享包', 'Cloud build'), ('单人包', 'Solo build'),
                               ('游戏包', 'Game build')):
                    shown = shown.replace(zh, en)
            self.pkg_btn.configure(text=shown, fg=TEXT if installed else ERR)
        except Exception:
            pass

    def _show_pkg_menu(self):
        """自绘下拉：未装 Mod 的包标红，点击可切换。"""
        if not getattr(self, '_pkgs', None):
            return
        if getattr(self, '_menu', None):
            try:
                self._menu.destroy()
            except Exception:
                pass
            self._menu = None
        top = tk.Toplevel(self.root)
        self._menu = top
        top.overrideredirect(True)
        top.configure(bg=LINE)
        top.attributes('-topmost', True)
        box = tk.Listbox(top, bg=CARD, fg=TEXT, selectbackground=ACCENT, selectforeground=BG,
                         bd=0, highlightthickness=0, font=(FONT_FAMILY, 9),
                         activestyle='none', height=min(8, len(self._pkgs)))
        box.pack(fill='both', expand=True, padx=1, pady=1)
        cur = paths.current_cloud()
        for lb, p in self._pkgs:
            ok, _ov, text, color = self._mod_info(p)
            label = f'{self._translate_kind(lb)} — {p}'
            if not ok:
                label = f'✕ {label}（{text}）'
                fg = MUTED
            elif text.startswith('未装') or '原版' in text:
                label = f'● {label}（{text}）'
                fg = ERR
            else:
                label = f'✓ {label}'
                fg = OKC
            box.insert('end', label)
            box.itemconfig('end', foreground=fg)
            if cur and Path(p) == Path(cur):
                box.selection_set('end')

        width = max(46, max((len(f'{lb} — {p}') for lb, p in self._pkgs), default=30) + 18)
        box.configure(width=width)
        bx = self.pkg_btn.winfo_rootx()
        by = self.pkg_btn.winfo_rooty() + self.pkg_btn.winfo_height()
        top.update_idletasks()
        top.geometry(f'+{bx}+{by}')
        top.lift()

        def pick(index):
            lb, p = self._pkgs[index]
            if not self._mod_info(p)[0]:
                self.log(f'这个条目不能用（没有游戏本体）：{p}', 'err')
                return
            paths.set_current(p)
            self.version_var.set(f'{lb} — {p}')
            self._on_version()

        def on_release(_evt=None):
            sel = box.curselection()
            if sel:
                pick(sel[0])
            close()

        def on_out(evt):
            # 点在列表外就关闭
            if not (0 <= evt.x_root - top.winfo_rootx() < top.winfo_width()
                    and 0 <= evt.y_root - top.winfo_rooty() < top.winfo_height()):
                close()

        def close(_evt=None):
            try:
                top.grab_release()
            except Exception:
                pass
            try:
                top.destroy()
            except Exception:
                pass
            self._menu = None

        box.bind('<ButtonRelease-1>', on_release)
        box.bind('<Return>', on_release)
        box.bind('<Escape>', close)
        top.bind('<Button-1>', on_out)
        top.bind('<Escape>', close)
        box.focus_set()
        try:
            top.grab_set()
        except Exception:
            pass

    def _on_version(self):
        sel = self.version_var.get()
        for lb, p in getattr(self, '_pkgs', []):
            if f'{lb} — {p}' == sel:
                paths.set_current(p)
                self.version_var.set(sel)
                self.log(self.t('build_selected').format(name=lb), 'ok')
                self.log(f'  {p}', 'muted')
                self._refresh_ui_state()
                return

    @staticmethod
    def _looks_like_package(folder):
        """判断一个目录像不像游戏包：有 local/settings.json（且 main 存在），或带启动脚本。"""
        import json
        d = Path(folder)
        if not d.is_dir():
            return False
        settings = d / 'local' / 'settings.json'
        if settings.is_file():
            try:
                cfg = json.loads(settings.read_text(encoding='utf-8'))
                main = cfg.get('main')
                if main and Path(main).is_file():
                    return True
            except Exception:
                pass
        for name in ('DuskbloodsCloud.exe', 'DuskbloodsSolo.exe',
                     '02-启动游戏.cmd', '02-单人模式.cmd'):
            if (d / name).is_file():
                return True
        return False

    def pick_package(self):
        """让用户自己指定游戏包目录；合法就写进 config.json 并刷新下拉。"""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title=self.t('pick_package_title'))
        if not folder:
            return False
        folder = str(Path(folder))
        if not self._looks_like_package(folder):
            messagebox.showwarning(self.t('err_title'),
                                   self.t('pkg_bad').format(path=folder))
            return False
        try:
            paths.set_current(folder)
        except Exception as error:
            messagebox.showerror(self.t('err_title'), str(error))
            return False
        paths._PKGS = None
        self._fill_versions()
        self.log(self.t('pkg_ok').format(path=folder), 'ok')
        return True

    def _rescan_versions(self):
        paths._PKGS = None
        self._fill_versions()
        self.log(self.t('rescanned'), 'muted')

    def _header(self):
        h = tk.Frame(self.root, bg=BG)
        h.pack(fill='x', padx=18, pady=(16, 6))
        self.w_title = tk.Label(h, text=self.t('title'), bg=BG, fg=ACCENT,
                                font=(FONT_FAMILY, FONT_SIZE + 5, 'bold'))
        self.w_title.pack(side='left')
        self.w_sub = tk.Label(h, text=self.t('sub'), bg=BG, fg=MUTED, font=(FONT_FAMILY, 9))
        self.w_sub.pack(side='left', padx=(10, 0), pady=(7, 0))
        self.w_version = tk.Label(h, text='v' + TOOL_VERSION, bg=BG, fg=GOLD,
                                  font=(FONT_FAMILY, 9))
        self.w_version.pack(side='left', padx=(8, 0), pady=(8, 0))
        self.lang_btn = tk.Button(h, text=self.t('lang_btn'), command=self.toggle_lang, bd=0,
                                  bg=CARD, fg=GOLD, activebackground=LINE, activeforeground=GOLD,
                                  font=(FONT_FAMILY, 9, 'bold'), padx=10, pady=2, cursor='hand2')
        self.lang_btn.pack(side='right')
        tk.Frame(self.root, bg=LINE, height=1).pack(fill='x', padx=18)

    def _search(self):
        s = tk.Frame(self.root, bg=BG)
        s.pack(fill='x', padx=18, pady=(12, 4))
        self.w_search_lbl = tk.Label(s, text=self.t('search'), bg=BG, fg=MUTED,
                                     font=(FONT_FAMILY, 9))
        self.w_search_lbl.pack(side='left')
        self.search_var = tk.StringVar()
        ent = ttk.Entry(s, textvariable=self.search_var, width=22)
        ent.pack(side='left', padx=8)
        ent.bind('<KeyRelease>', lambda e: self.apply_filter())
        self.w_search_hint = tk.Label(s, text=self.t('search_hint'), bg=BG, fg=MUTED,
                                      font=(FONT_FAMILY, 8))
        self.w_search_hint.pack(side='left')

    def _form(self):
        grid = tk.Frame(self.root, bg=CARD)
        grid.pack(fill='x', padx=18, pady=(0, 4), ipady=8)
        grid.columnconfigure(1, weight=1)
        self.w_row_labels = []
        # 表头：说明右边两列分别是什么
        self.w_model_head = tk.Label(grid, text=self.t('model'), bg=CARD, fg=MUTED,
                                     font=(FONT_FAMILY, 8), anchor='w')
        self.w_model_head.grid(row=0, column=1, padx=(4, 6), pady=(6, 0), sticky='w')
        self.w_variant_head = tk.Label(grid, text=self.t('variant'), bg=CARD, fg=MUTED,
                                       font=(FONT_FAMILY, 8), anchor='w')
        self.w_variant_head.grid(row=0, column=2, padx=(0, 14), pady=(6, 0), sticky='w')
        for i, (title, slot, parts) in enumerate(TARGETS):
            lbl = tk.Label(grid, text=self.t('rows')[i], bg=CARD, fg=TEXT,
                           font=(FONT_FAMILY, FONT_SIZE, 'bold'), width=12, anchor='w')
            lbl.grid(row=i + 1, column=0, padx=(14, 4), pady=7, sticky='w')
            self.w_row_labels.append(lbl)
            m = ttk.Combobox(grid, values=self.labels, width=40, state='readonly')
            m.grid(row=i + 1, column=1, padx=(4, 6), pady=7, sticky='ew')
            v = ttk.Combobox(grid, values=[self.t('variant_default')], width=22,
                             state='readonly')
            v.grid(row=i + 1, column=2, padx=(0, 14), pady=7, sticky='w')
            v.set(self.t('variant_default'))
            default = {'scarecrow': 'c6000', 'adherents': 'c2110', 'giant': 'c2140'}[title]
            m.set(next((lb for lb in self.labels if lb.startswith(default)), self.labels[0]))
            self.rows.append({'title': title, 'slot': slot, 'parts': parts,
                              'model': m, 'variant': v})
            m.bind('<<ComboboxSelected>>', lambda e, row=self.rows[-1]: self._refresh_variants(row))
            if not hasattr(self, 'by_label'):
                self.by_label = {}
            self._refresh_variants(self.rows[-1])


    def _variant_label(self, variant):
        """变体在下拉里显示的名字：英文模式优先 name_en（官方英文），没有就退回中文名。"""
        if self.lang == 'en':
            return variant.get('name_en') or variant.get('name') or '?'
        return variant.get('name') or variant.get('name_en') or '?'

    def _refresh_variants(self, row):
        entry = self.by_label.get(row['model'].get()) or {}
        vs = entry.get('variants') or []
        names = [self._variant_label(x) for x in vs] or [self.t('variant_default')]
        row['variant'].configure(values=names)
        if row['variant'].get() not in names:
            row['variant'].set(names[0])

    def _footer(self):
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill='x', padx=18, pady=(10, 8))
        self.b_launch = ttk.Button(bar, text=self.t('apply_launch'), style='Primary.TButton',
                                   command=self.apply_and_launch)
        self.b_launch.pack(side='left')
        self.b_install = ttk.Button(bar, text=self._t('安装 Mod', 'Install Mod'), command=self.install_mod)
        self.b_install.pack(side='left', padx=(8, 4))
        self.b_uninstall = ttk.Button(bar, text=self._t('卸载 Mod', 'Uninstall Mod'), command=self.uninstall_mod)
        self.b_uninstall.pack(side='left', padx=(0, 8))
        self.b_reload = ttk.Button(bar, text=self.t('reload'), command=self.reload)
        self.b_reload.pack(side='left', padx=8)
        self.b_oodle = ttk.Button(bar, text=self.t('oodle'), command=self.pick_oodle)
        self.b_oodle.pack(side='left', padx=(8, 0))

        self._refresh_ui_state()

    # ---------- 报错日志 / GitHub 反馈 ----------
    def _session_logs(self):
        try:
            files = list(LOG_DIR.glob('[0-9]*.txt')) + list(LOG_DIR.glob('session-*.txt'))
            return sorted({f.resolve() for f in files}, key=lambda x: x.name, reverse=True)
        except Exception:
            return []

    def open_logs_folder(self):
        """打开存放日志的文件夹（反馈流水 + 每次游戏的会话日志都在这里）。"""
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(str(LOG_DIR))
            self.log(f'已打开日志文件夹：{LOG_DIR}', 'ok')
        except Exception as error:
            messagebox.showerror(self.t('err_title'),
                                 self._t(f'打不开日志文件夹：{error}', f'Cannot open log folder: {error}') + f'\n{LOG_DIR}')

    # ---------- 一键修复 ----------
    def _safe_label(self, prof):
        """挑一个“肯定能用”的模型标签：优先 c6000 尼柯，其次 c2000 信徒，再退而求其次。"""
        romfs = prof.get('romfs')
        labels = list(getattr(self, 'labels', []) or [])
        if not labels or not romfs:
            return labels[0] if labels else ''
        prefer = ('c6000', 'c2000', 'c2010', 'c2210')
        for want in prefer:
            for lb in labels:
                if lb.startswith(want) and (Path(romfs) / 'chr' / f'{want}.chrbnd.dcx').exists():
                    return lb
        for lb in labels:
            mid = lb.split()[0]
            if (Path(romfs) / 'chr' / f'{mid}.chrbnd.dcx').exists():
                return lb
        return labels[0]

    def _heal_scan(self):
        """扫描常见问题，返回 [{'what','how','fix'}...]；fix 为 None 表示只能提示。"""
        import shutil as _sh
        cur = paths.current_cloud()
        items = []
        if not cur:
            return items
        cur_p = Path(cur)

        # 配置里记住的包没了
        try:
            cfg_path = HERE / 'config.json'
            if cfg_path.exists():
                import json as _json
                saved = _json.loads(cfg_path.read_text(encoding='utf-8')).get('cloud_root')
                if saved and not Path(saved).exists():
                    def fix_cfg():
                        cfg = _json.loads(cfg_path.read_text(encoding='utf-8'))
                        cfg.pop('cloud_root', None)
                        cfg_path.write_text(_json.dumps(cfg, ensure_ascii=False, indent=1),
                                            encoding='utf-8')
                        paths._PKGS = None
                    items.append({'what': self._t('工具记着的游戏包被移动或删除了', 'The remembered game build was moved or deleted'),
                                  'how': self._t('清掉这条旧记录，重新扫描可用包', 'Clear the stale record and rescan'), 'fix': fix_cfg})
        except Exception:
            pass

        # 缺游戏本体
        base = paths.detect.game_base(cur)
        main = Path(base) / 'exefs' / 'main' if base else None
        if not base or not main or not main.exists():
            items.append({'what': self._t('这个包没有游戏本体（缺 base/exefs/main）', 'This build has no game data (base/exefs/main)'),
                          'how': self._t('无法自动修复，请在上面的下拉里换一个完整的游戏包',
                              'Cannot fix automatically; pick a complete game build above'), 'fix': None})

        # Oodle
        try:
            ok_dll = bool(patch_m80.oo2core_path())
        except Exception:
            ok_dll = False
        if not ok_dll:
            def fix_oodle():
                for hit in Path(cur).rglob('oo2core_9_win64.dll'):
                    patch_m80.set_oo2core(str(hit))
                    return f'已在游戏包里找到并使用 {hit.name}'
                return '没找到，请点「指定 Oodle...」手动选一次'
            items.append({'what': self._t('缺少压缩库 Oodle（打包时会失败）', 'Oodle compression library is missing'),
                          'how': self._t('自动在游戏包里找一份 oo2core_9_win64.dll 用上',
                              'Find oo2core_9_win64.dll inside the game build'), 'fix': fix_oodle})

        # 进程
        if self._game_running():
            def fix_proc():
                for exe in ('lichii.exe', 'DuskbloodsSolo.exe', 'DuskbloodsCloud.exe'):
                    subprocess.run(['taskkill', '/F', '/IM', exe], capture_output=True,
                                   creationflags=0x08000000)
                time.sleep(2)
                return '已关闭游戏和启动器'
            items.append({'what': self._t('游戏或启动器还开着（会占住 Mod 文件，导致写不进去）',
                                   'The game or launcher is still running (it locks the Mod files)'),
                          'how': self._t('关掉它们（游戏会被关闭）', 'Close them (the game will be closed)'), 'fix': fix_proc})

        # player.lock
        lock = Path(cur) / 'local' / 'player.lock'
        if lock.exists() and not self._game_running():
            def fix_lock():
                lock.unlink()
                return '删掉了锁文件'
            items.append({'what': self._t('上次游戏没退干净，留下了一个锁文件（可能挡住启动）',
                                   'The last run left a lock file behind'),
                          'how': self._t('删掉这个锁文件', 'Delete the lock file'), 'fix': fix_lock})

        # 会话缓存
        caches = list(Path(cur).glob('local/session-games/*'))
        if caches:
            def fix_cache():
                for c in caches:
                    _sh.rmtree(c, ignore_errors=True)
                return f'清掉了 {len(caches)} 个游戏缓存目录（下次启动自动重建）'
            items.append({'what': f'游戏缓存里存着 {len(caches)} 份旧地图（可能盖住 Mod）',
                          'how': '清掉缓存目录，下次启动游戏会自动重建', 'fix': fix_cache})

        # 覆盖层
        ok_pkg, _ov, text, _c = self._mod_info(cur)
        if ok_pkg and (text.startswith('未装') or '原版' in text or '不一致' in text):
            reason = ('还没装 Mod' if text.startswith('未装')
                      else 'Mod 文件被还原成了原版' if '原版' in text
                      else 'Mod 文件被别的程序改过')
            def fix_overlay():
                self.apply_only(launch=False)
                return '已按你当前选的三个标靶重新写入 Mod'
            items.append({'what': self._t(f'这个包的 Mod 不正常：{reason}（所以进游戏看不到换怪效果）',
                              f'Mod state is wrong: {reason}'),
                          'how': self._t('按你当前选的三个标靶重新生成并写入',
                              'Rebuild and write the Mod with your current picks'), 'fix': fix_overlay})

        # 选中的模型没有资源（会黑屏）
        try:
            prof_scan = paths.profile(PROFILE)
            bad = [x for x in self._model_checks(prof_scan) if x.get('chrbnd') is False]
            if bad:
                ids = '、'.join(x['model'] for x in bad)

                def fix_models(prof_scan=prof_scan, bad=bad):
                    safe = self._safe_label(prof_scan)
                    if not safe:
                        return '找不到可替换的可用模型，请手动选一个'
                    changed = []
                    for item in bad:
                        for row in self.rows:
                            if row['model'].get().strip().startswith(item['model']):
                                row['model'].set(safe)
                                if hasattr(self, '_refresh_variants'):
                                    try:
                                        self._refresh_variants(row)
                                    except Exception:
                                        pass
                                changed.append(item['model'])
                    if not changed:
                        return '界面上没找到对应的标靶行'
                    self.apply_only(launch=False)
                    return f'已把 {"/".join(changed)} 换成「{safe}」并重新安装'
                items.append({'what': f'选中的模型 {ids} 在这版游戏里没有资源（进游戏会黑屏）',
                              'how': f'自动换成可用的模型并重新安装',
                              'fix': fix_models})
        except Exception:
            pass

        # 其它包也装了
        try:
            others = []
            for lb, p in paths.packages():
                if Path(p) == cur_p:
                    continue
                if any(o.exists() for o in paths.detect.overlay_targets(p)):
                    others.append(Path(p))
            if others:
                names = '、'.join(x.parent.name for x in others[:3]) + ('等' if len(others) > 3 else '')
                items.append({'what': f'另外 {len(others)} 个游戏包也装了 Mod（{names}）',
                              'how': '如果那些包不用，可以切到那个包点「卸载 Mod」清掉；'
                                     '不影响当前包，可以忽略', 'fix': None})
        except Exception:
            pass

        # 快照堆积
        try:
            snaps = sorted(paths.SNAPS.glob('*'), key=lambda p: p.stat().st_mtime, reverse=True)
            if len(snaps) > 30:
                def fix_snaps():
                    for s in snaps[10:]:
                        _sh.rmtree(s, ignore_errors=True)
                    return f'清掉 {len(snaps) - 10} 份旧快照（保留最近 10 份）'
                items.append({'what': f'历史快照堆积了 {len(snaps)} 份（占空间）',
                              'how': '只保留最近 10 份，其余删除', 'fix': fix_snaps})
        except Exception:
            pass

        # 中文路径
        try:
            str(cur).encode('ascii')
        except UnicodeEncodeError:
            items.append({'what': '游戏包路径里有中文',
                          'how': '多数情况没问题；若模拟器报错，把游戏包移动到纯英文路径', 'fix': None})

        if not (HERE / 'catalog.json').exists():
            items.append({'what': '工具缺少怪物清单文件 catalog.json',
                          'how': '需要重新安装工具', 'fix': None})
        return items

    def self_heal(self):
        cur = paths.current_cloud()
        if not cur:
            messagebox.showerror(self.t('err_title'), self._t('还没有选择游戏版本。', 'No game build selected.'))
            return
        items = self._heal_scan()
        auto = [x for x in items if x['fix']]
        hints = [x for x in items if not x['fix']]

        if not auto:
            text = '没有发现可以自动修复的问题。'
            if hints:
                text += '\n\n另外有 %d 条提示（不影响使用）：\n' % len(hints)
                for x in hints:
                    text += f'\n· {x["what"]}\n  → {x["how"]}'
            else:
                text += '\n\n如果你在游戏里仍然看不到换怪效果，点「运行日志」把最新的 session 日志发我。'
            messagebox.showinfo(self._t('一键修复', 'Auto Fix'), text)
            return

        lines = [f'发现 {len(auto)} 个可以自动修复的问题：', '']
        for i, x in enumerate(auto, 1):
            lines.append(f'{i}. {x["what"]}')
            lines.append(f'   处理方式：{x["how"]}')
            lines.append('')
        if hints:
            lines.append(f'另有 {len(hints)} 条提示不会自动处理（不影响当前使用）。')
            lines.append('')
        lines.append('点「是」我自动处理这些（大约 10 秒），点「否」什么都不做。')
        if not messagebox.askyesno(self._t('一键修复', 'Auto Fix'), '\n'.join(lines)):
            return

        self.log('—— 一键修复开始 ——', 'ok')
        ok_n = fail_n = 0
        details = []
        for x in auto:
            try:
                msg = x['fix']()
                ok_n += 1
                details.append(f'✔ {x["what"]}\n   {msg or "已处理"}')
                self.log(f'[修复] {x["what"]} — {msg or "完成"}', 'ok')
            except Exception as error:
                fail_n += 1
                details.append(f'✘ {x["what"]}\n   失败：{error}')
                self._log_exception('self_heal', error)

        try:
            prof = paths.profile(PROFILE)
            out_dir = paths.OUT / 'tool_last'
            if (out_dir / 'm80_00_00_00.msb.dcx').exists():
                self._last_verdicts = self._diagnose(prof, out_dir)
                for level, text in self._last_verdicts:
                    self.log('[体检] ' + text, level)
        except Exception as error:
            self.log(f'[体检] 失败：{error}', 'err')

        bad = [x[1] for x in getattr(self, '_last_verdicts', []) if x[0] == 'err']
        head = f'处理完成：{ok_n} 项成功' + (f'，{fail_n} 项失败' if fail_n else '') + '。'
        if bad:
            head += '\n\n复查还发现这些问题：\n' + '\n'.join('✘ ' + b for b in bad)
        else:
            head += '\n复查通过，Mod 状态正常。'
        self.log('—— 一键修复结束 ——', 'ok')
        messagebox.showinfo(self._t('一键修复', 'Auto Fix'),
                            head + self._t('\n\n明细：\n', '\n\nDetails:\n') + '\n'.join(details))

    def _make_log_bundle(self):
        """把最新会话日志 + 当天流水 + 预设打成一个 zip，方便发给作者。"""
        import zipfile
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            out = LOG_DIR / f'反馈包-{stamp}.zip'
            picked = []
            latest = getattr(self, '_last_session_report', None)
            if latest and Path(latest).exists():
                picked.append(Path(latest))
            else:
                logs = self._session_logs()
                if logs:
                    picked.append(logs[0])
            if self._log_path.exists():
                picked.append(self._log_path)
            pj = paths.OUT / 'tool_last' / 'preset.json'
            with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f in picked:
                    if f.exists():
                        zf.write(f, f.name)
                if pj.exists():
                    zf.write(pj, 'preset.json')
            return out, [f.name for f in picked]
        except Exception:
            return None, []

    def _github_issue_url(self):
        cfg = HERE / 'github.txt'
        base = cfg.read_text(encoding='utf-8').strip() if cfg.exists() else ''
        if not base:
            from tkinter import simpledialog
            base = simpledialog.askstring(
                '作者 GitHub 地址',
                '填作者仓库地址（只需填一次），例如：\nhttps://github.com/用户名/仓库名',
                parent=self.root) or ''
            base = base.strip().rstrip('/')
            if not base:
                return None
            cfg.write_text(base, encoding='utf-8')
        if base.endswith('/issues'):
            return base + '/new'
        return base + '/issues/new'

    def feedback_github(self):
        import urllib.parse
        import webbrowser
        url = self._github_issue_url()
        if not url:
            return
        logs = self._session_logs()
        latest = getattr(self, '_last_session_report', None) or (logs[0] if logs else None)
        pkg = Path(paths.current_cloud() or '?').name
        logs0 = self._session_logs()
        sess = Path(getattr(self, '_last_session_report', None) or (logs0[0] if logs0 else '?')).name
        body = [f'工具 v{TOOL_VERSION}｜包 {pkg}｜会话 {sess}',
                '', '【问题描述】', '（请补充你看到的现象）', '',
                '【期望】', '（请补充）', '', '【环境】']
        try:
            body += [self._env_report()]
        except Exception:
            pass
        body += ['', f'【反馈日志文件】{latest}']
        if latest and Path(latest).exists():
            try:
                body += ['', '【日志摘要】', Path(latest).read_text(encoding='utf-8')[-2500:]]
            except Exception:
                pass
        text = '\n'.join(body)
        if len(text) > 6000:
            text = text[:6000] + '\n…（完整内容见反馈日志文件）'
        url += '?title=' + urllib.parse.quote('换怪工具问题反馈') + '&body=' + urllib.parse.quote(text)
        bundle_path, names = self._make_log_bundle()
        try:
            webbrowser.open(url)
            self.log('已打开 GitHub 反馈页（日志内容已填进正文）', 'ok')
            if bundle_path:
                self.log(f'已打包日志：{bundle_path}', 'ok')
                if names:
                    self.log('  包含：' + '、'.join(names), 'muted')
                messagebox.showinfo(
                    self._t('反馈日志已打包', 'Logs packed'),
                    self._t('已把日志打包到：', 'Logs packed to:') + '\n' + str(bundle_path)
                    + '\n\n'
                    + self._t('GitHub 页面里粘贴正文后，把这个 zip 拖进去当附件即可。',
                              'Paste the body into the GitHub page, then drag this zip in as an attachment.'))
        except Exception as error:
            messagebox.showerror(self.t('err_title'),
                                     self._t(f'打不开浏览器：{error}', f'Cannot open browser: {error}'))

    def pick_oodle(self):
        """让用户选 oo2core_9_win64.dll，选完记住（存在 tools/oo2core.path）。"""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title=self.t('oodle_title'),
            filetypes=[('Oodle 库', 'oo2core*.dll'), ('DLL', '*.dll'), ('所有文件', '*.*')])
        if not path:
            return False
        try:
            saved = patch_m80.set_oo2core(path)
        except Exception as error:
            messagebox.showerror(self.t('err_title'),
                                 self.t('oodle_bad').format(error=error))
            return False
        self.log(self.t('oodle_ok').format(path=saved), 'ok')
        return True

    # ---------- 逻辑 ----------
    def log(self, text, level='info'):
        try:
            self.w_status.configure(text=text,
                                    fg={'ok': OKC, 'err': ERR, 'muted': MUTED}.get(level, TEXT))
        except Exception:
            pass
        self._write_log(text, level)
        try:
            self.root.update_idletasks()
        except Exception:
            pass

    # ---------- 问题反馈日志 ----------
    def _init_feedback_log(self):
        self._log_lines = []
        self._session_id = datetime.now().strftime('%Y%m%d-%H%M%S')
        self._log_path = LOG_DIR / f'run-{datetime.now():%Y%m%d-%H%M%S}.log'
        self._write_log('', 'info', raw=True)
        self._write_log(f'===== 会话开始 {self._session_id} | 工具 v{TOOL_VERSION} =====', 'info')
        try:
            self._write_log(f'当前包：{paths.current_cloud()}', 'info')
        except Exception:
            pass

    MAX_LOG_BYTES = 2 * 1024 * 1024

    def _rotate_log(self):
        try:
            if self._log_path.exists() and self._log_path.stat().st_size > self.MAX_LOG_BYTES:
                stamp = datetime.now().strftime('%H%M%S')
                target = self._log_path.with_name(f'{self._log_path.stem}-{stamp}-旧.log')
                self._log_path.rename(target)
        except Exception:
            pass

    def _write_log(self, text, level='info', raw=False):
        try:
            self._log_lines.append((datetime.now().strftime('%H:%M:%S'), level, text))
            if len(self._log_lines) > 4000:
                del self._log_lines[:1000]
            if raw:
                return
            self._rotate_log()
            line = f'[{datetime.now():%Y-%m-%d %H:%M:%S}] [{level}] {text}\n'
            with open(self._log_path, 'a', encoding='utf-8') as fp:
                fp.write(line)
        except Exception:
            pass

    def _env_report(self):
        rows = ['--- 环境 ---']
        rows.append(f'时间: {datetime.now():%Y-%m-%d %H:%M:%S}')
        rows.append(f'工具版本: v{TOOL_VERSION}')
        rows.append(f'Python: {sys.version.split()[0]}  ({sys.executable})')
        rows.append(f'系统: {platform.platform()}  架构: {platform.machine()}')
        rows.append(f'中文编码: {sys.getfilesystemencoding()}')
        rows.append(f'工具目录: {HERE}')
        try:
            rows.append(f'oo2core: {paths.oo2core_path() if hasattr(paths, "oo2core_path") else
                                     (HERE / "tools" / "oo2core.path")}')
        except Exception:
            pass
        rows.append(f'当前包: {paths.current_cloud()}')
        try:
            import shutil as _sh
            du = _sh.disk_usage(str(HERE))
            rows.append(f'磁盘剩余: {du.free / 2**30:.1f} GB / 共 {du.total / 2**30:.1f} GB')
        except Exception:
            pass
        try:
            import ctypes as _ct
            rows.append('管理员权限: ' + ('是' if _ct.windll.shell32.IsUserAnAdmin() else '否'))
        except Exception:
            pass
        try:
            import locale as _lo
            rows.append(f'系统区域: {_lo.getdefaultlocale()[0]}  首选编码: {_lo.getpreferredencoding()}')
        except Exception:
            pass
        try:
            rows.append('--- 扫描到的包 ---')
            for lb, p in paths.packages():
                ok, overlay, text, _c = self._mod_info(p)
                rows.append(f'  [{lb}] {p}')
                rows.append(f'      Mod: {text}')
                if overlay:
                    rows.append(f'      覆盖层: {overlay}')
        except Exception as error:
            rows.append(f'  扫描失败: {error}')
        return '\n'.join(rows)

    def apply_filter(self):
        q = self.search_var.get().strip().lower()
        vals = [lb for lb in self.labels if not q or q in lb.lower()] or self.labels
        for row in self.rows:
            row['model'].configure(values=vals)
            if row['model'].get() not in vals:
                row['model'].set(vals[0])

    def rebuild_labels(self):
        self.by_model = {c['model']: c for c in self.catalog}
        self.by_label = {}
        tags = KIND_TAG_EN if self.lang == 'en' else KIND_TAG
        self.labels = []
        for c in self.catalog:
            name = (c.get('name_en') if self.lang == 'en' else c.get('name')) or c.get('name') or '?'
            tag = tags.get(c.get('kind'), '')
            mark = '' if (c.get('params') or c.get('variants')) else (
                '  (no params)' if self.lang == 'en' else '  （无参数）')
            self.labels.append(f"{c['model']}  {tag}{name}{mark}")
        self.label_to_model = {lb: lb.split('  ')[0] for lb in self.labels}
        for c, lb in zip(self.catalog, self.labels):
            self.by_label[lb] = c

    def reload(self):
        self.catalog = load_catalog()
        self.rebuild_labels()
        for row in self.rows:
            cur = row['model'].get().split('  ')[0]
            row['model'].configure(values=self.labels)
            row['model'].set(next((lb for lb in self.labels if lb.startswith(cur + '  ')),
                                  next((lb for lb in self.labels if lb.startswith(cur)), self.labels[0])))
        self.log(f'{self.t("refresh")}：{len(self.labels)}', 'ok')

    def build_preset(self):
        preset = {'map': 'm80_00_00_00', 'base': 'orig', 'bosses': [],
                  'rename_model_slots': [], 'set_params': []}
        for row in self.rows:
            label = row['model'].get()
            entry = self.by_label.get(label) or self.by_model.get(
                self.label_to_model.get(label, ''), {})
            model = entry.get('model') or self.label_to_model[label]
            params = entry.get('params')
            variants = entry.get('variants') or []
            if variants:
                want = row['variant'].get() if row.get('variant') else self._variant_label(variants[0])
                hit = (next((x for x in variants if self._variant_label(x) == want), None)
                       or next((x for x in variants if x['name'] == want), variants[0]))
                params = hit.get('params')
                self.log(self.t('variant_pick').format(model=model, name=hit['name']), 'muted')
            if not params:
                params = dict(self.by_model['c6000']['params'])
                self.log(self.t('no_params_borrow').format(model=model), 'muted')
            preset['rename_model_slots'].append({'slot': row['slot'], 'model': model})
            for part in row['parts']:
                preset['set_params'].append({'part': part,
                                             'a': params['a'], 'b': params['b'],
                                             'c': '0xffffffff', 'd': params['d']})
        return preset

    def apply_only(self, launch=False, retried=False):
        try:
            prof = paths.profile(PROFILE)
            msb = prof.get('msb')
            if not msb or not Path(msb).exists():
                self.log(self.t('failed') + '这个游戏版本里找不到 m80 训练场地图，'
                         '它不是完整的游戏包（只有模拟器、没有游戏本体）。', 'err')
                messagebox.showerror(self.t('err_title'),
                                     '这个游戏版本里找不到 m80 训练场地图。\n'
                                     '请确认选的是「游戏本体 + 模拟器」都在的包，'
                                     '而不是只有模拟器的目录。')
                return
            preset = self.build_preset()
            out = paths.OUT / 'tool_last'
            prof = paths.profile(PROFILE)
            self._log_selection(prof)
            self.log(self.t('building'))
            with contextlib.redirect_stdout(_LogTee(self.log)):
                tb.build(preset, prof, str(out))
            self.log(self.t('installing'))
            with contextlib.redirect_stdout(_LogTee(self.log)):
                tb.install(str(out), prof)
            self._verify_overlay(prof, out)
            if launch:
                self._refresh_ui_state()
                cur = paths.current_cloud()
                _ok, _ov, mod_text, _c = self._mod_info(cur) if cur else (False, None, '未知', 'err')
                if not mod_text.startswith('已装'):
                    self.log(f'启动前检查：这个包没有装好 Mod（{mod_text}）', 'err')
                    messagebox.showwarning(
                        '这个包没有装好 Mod',
                        f'检测结果：{mod_text}\n\n'
                        f'原因可能是：\n'
                        f'· 这个包没有游戏本体（缺 romfs/m80）\n'
                        f'· 覆盖层写入失败（游戏正在占用文件）\n'
                        f'· 写入后被程序/杀毒软件还原\n\n'
                        f'先关闭正在运行的模拟器，再点「安装 Mod」，'
                        f'状态变成「已装 Mod」后再启动。')
                    return
                self.log(self.t('installed_launch'), 'ok')
                self.launch()
            else:
                self._refresh_ui_state()
                self.log(self.t('installed'), 'ok')
        except Exception as e:
            self._log_exception('build/install', e)
            self.log(self.t('failed') + str(e), 'err')
            text = str(e)
            if not retried and ('oo2core' in text.lower() or 'Oodle' in text):
                if messagebox.askyesno(self.t('err_title'), self.t('oodle_ask')):
                    if self.pick_oodle():
                        return self.apply_only(launch=launch, retried=True)
                self.log(self.t('failed') + self.t('oodle_missing'), 'err')
                return
            messagebox.showerror(self.t('err_title'), text)

    def install_mod(self):
        """安装 Mod（构建 + 写入覆盖层）。"""
        cur = paths.current_cloud()
        if not cur:
            return
        ok, _ov, _text, _c = self._mod_info(cur)
        if not ok:
            messagebox.showerror(self.t('err_title'),
                                 self._t('这个包没有游戏本体，不能安装 Mod。',
                                         'This build has no game data (base/exefs/main), cannot install.'))
            return
        self.apply_only(launch=False)
        self._refresh_ui_state()

    def uninstall_mod(self):
        """卸载 Mod（删除覆盖层，恢复原版）。"""
        cur = paths.current_cloud()
        if not cur:
            return
        self.restore()
        self._refresh_ui_state()

    def _log_exception(self, stage, exc):
        """把异常记进日志：类型、文件名、WinError/errno、完整 traceback。"""
        import traceback as _tb
        bits = [f'阶段={stage}', f'类型={type(exc).__name__}', f'消息={exc}']
        for attr in ('filename', 'filename2', 'winerror', 'errno'):
            value = getattr(exc, attr, None)
            if value:
                bits.append(f'{attr}={value}')
        self.log('✘ 异常：' + '  '.join(bits), 'err')
        for line in _tb.format_exception(type(exc), exc, exc.__traceback__):
            for part in line.rstrip('\n').splitlines():
                self.log('    ' + part, 'muted')

    def _selection_models(self):
        """当前界面选了什么：[(显示名, 模型 id, 变体名), ...]。"""
        out = []
        try:
            for row in self.rows:
                label = row['model'].get().strip()
                mid = label.split()[0] if label else ''
                var = row['variant'].get().strip() if 'variant' in row else ''
                out.append((label, mid, var))
        except Exception:
            pass
        return out

    def _model_checks(self, prof, out_dir=None):
        """检查每个被换上的模型：资源文件是否存在、有没有写进构建产物的模型表。"""
        romfs = prof.get('romfs')
        result = []
        for label, mid, var in self._selection_models():
            item = {'label': label, 'model': mid, 'variant': var,
                    'chrbnd': None, 'anibnd': None, 'in_table': None}
            if romfs and mid:
                item['chrbnd'] = (Path(romfs) / 'chr' / f'{mid}.chrbnd.dcx').exists()
                item['anibnd'] = (Path(romfs) / 'chr' / f'{mid}.anibnd.dcx').exists()
            result.append(item)

        # 优先看本次构建产物里的模型表；没有构建产物再看原版
        msb = None
        if out_dir and (Path(out_dir) / 'm80_00_00_00.msb.dcx').exists():
            msb = Path(out_dir) / 'm80_00_00_00.msb.dcx'
        elif prof.get('msb') and Path(prof['msb']).exists():
            msb = Path(prof['msb'])
        if msb:
            try:
                import msb_inspect as _mi
                raw = bytearray(patch_m80.dcx_decode(msb))
                _base, table = _mi.model_table(raw)
                names = {m['short'] for m in table}
                for item in result:
                    item['in_table'] = item['model'] in names
            except Exception:
                pass
        for item in result:
            item['table_source'] = 'build' if (out_dir and (Path(out_dir) / 'm80_00_00_00.msb.dcx').exists()) else 'orig'
        return result

    def _log_selection(self, prof):
        """把本次选择和模型检查写进日志。"""
        checks = self._model_checks(prof)
        if not checks:
            return checks
        self.log('--- 本次选择 ---', 'info')
        for item in checks:
            self.log(f'  {item["label"]}  ←  {item["model"]}'
                     + (f'（{item["variant"]}）' if item['variant'] else ''), 'muted')
            files = []
            if item['chrbnd'] is not None:
                files.append('chrbnd ' + ('✓' if item['chrbnd'] else '✗缺失'))
            if item['anibnd'] is not None:
                files.append('anibnd ' + ('✓' if item['anibnd'] else '✗缺失'))
            if files:
                self.log(f'      资源：{"  ".join(files)}', 'muted')
            if item['in_table'] is False:
                self.log('      ⚠ 没有写进本次构建的模型表（改名可能失败）', 'err')
            elif item['in_table']:
                self.log('      模型表：已写入', 'muted')
        return checks

    def _verify_overlay(self, prof, out_dir):
        """写入后校验：构建产物 / 原版 / 每个覆盖层的 sha256 + 大小 + 会话缓存。"""
        import hashlib

        def sha(p):
            try:
                return hashlib.sha256(Path(p).read_bytes()).hexdigest()
            except Exception:
                return None

        built = Path(out_dir) / 'm80_00_00_00.msb.dcx'
        orig = prof.get('msb')
        b = sha(built) if built.exists() else None
        o = sha(orig) if orig else None
        bs = built.stat().st_size if built.exists() else 0
        os_ = Path(orig).stat().st_size if orig and Path(orig).exists() else 0
        self.log(f'[校验] 构建产物 {bs:,} 字节  sha={(b or "-")[:16]}', 'info')
        self.log(f'[校验] 原版 m80 {os_:,} 字节  sha={(o or "-")[:16]}', 'info')
        if b and o and b == o:
            self.log('[校验] ⚠ 构建产物和原版完全一样 —— 这次构建没有任何改动生效', 'err')

        targets = prof.get('overlays') or ([prof['overlay']] if prof.get('overlay') else [])
        ok_count = 0
        for target in targets:
            target = Path(target)
            exists = target.exists()
            s = sha(target) if exists else None
            size = target.stat().st_size if exists else 0
            if not exists:
                verdict, level = '✗ 文件不存在（没写进去）', 'err'
            elif b and s == b:
                verdict, level = '✓ 与构建一致', 'ok'
                ok_count += 1
            elif o and s == o:
                verdict, level = '✗ 等于原版（等于没装）', 'err'
            else:
                verdict, level = '✗ 与构建不一致（被还原或被改写）', 'err'
            self.log(f'[校验] {target}', 'muted')
            self.log(f'[校验]   {size:,} 字节  sha={(s or "-")[:16]}  {verdict}', level)

        root = prof.get('root')
        if root:
            try:
                cached = list(Path(root).glob(
                    'local/session-games/*/base/romfs/map/mapstudio/m80_00_00_00.msb.dcx'))
            except Exception:
                cached = []
            for h in cached:
                self.log(f'[校验] 会话缓存里也有同名文件 sha={(sha(h) or "-")[:16]}  {h}', 'muted')

        self.log(f'[校验] 结论：{ok_count}/{len(targets)} 个目标与本次构建一致',
                 'ok' if ok_count else 'err')
        try:
            verdicts = self._diagnose(prof, out_dir)
            self._last_verdicts = verdicts
            for level, text in verdicts:
                self.log('[体检] ' + text, level)
        except Exception as error:
            self.log(f'[体检] 生成结论失败：{error}', 'err')
        return ok_count

    def _diagnose(self, prof, out_dir=None):
        """根据文件事实给出结论（对应常见故障）。返回 [(level, text), ...]。"""
        import hashlib

        def sha(p):
            try:
                return hashlib.sha256(Path(p).read_bytes()).hexdigest()
            except Exception:
                return None

        out = []
        orig = prof.get('msb')
        orig_sha = sha(orig) if orig and Path(orig).exists() else None
        built_path = (Path(out_dir) / 'm80_00_00_00.msb.dcx') if out_dir else None
        build_sha = sha(built_path) if built_path and built_path.exists() else None

        if not orig_sha:
            out.append(('err', '这个包没有原版 m80 地图 —— 不是完整的游戏本体，无法换怪。'))
            return out
        if not build_sha:
            out.append(('err', '没有找到本次构建产物 —— 构建没有成功完成。'))
            return out
        if build_sha == orig_sha:
            out.append(('err', '构建产物和原版一模一样 —— 本次构建没有任何改动生效。'))
            return out

        targets = prof.get('overlays') or ([prof['overlay']] if prof.get('overlay') else [])
        if not targets:
            out.append(('err', '没有找到任何覆盖层目标 —— 这个包结构不认识。'))
            return out
        states = []
        for target in targets:
            target = Path(target)
            s = sha(target) if target.exists() else None
            states.append((target, s))
        same_build = [x for x, s in states if s == build_sha]
        missing = [x for x, s in states if s is None]
        same_orig = [x for x, s in states if s and s == orig_sha]
        other = [x for x, s in states if s and s not in (build_sha, orig_sha)]

        if missing and len(missing) == len(targets):
            out.append(('err', '所有覆盖层都没有写进去 —— 安装阶段失败（常见：游戏占着文件）。'))
        elif missing:
            out.append(('err', f'{len(missing)} 个覆盖层没写进去（共 {len(targets)} 个）。'))
        if same_orig:
            out.append(('err', f'{len(same_orig)} 个覆盖层等于原版 —— 等于没装（可能被杀软或"还原原版"改回去）。'))
        if other:
            out.append(('err', f'{len(other)} 个覆盖层与构建不一致 —— 被其它程序改写或还原过。'))
        if same_build:
            out.append(('ok', f'{len(same_build)}/{len(targets)} 个覆盖层与本次构建一致。'))

        root = prof.get('root')
        if root:
            try:
                cache = list(Path(root).glob(
                    'local/session-games/*/base/romfs/map/mapstudio/m80_00_00_00.msb.dcx'))
            except Exception:
                cache = []
            cache_orig = [h for h in cache if sha(h) == orig_sha]
            cache_mod = [h for h in cache if build_sha and sha(h) == build_sha]
            if cache_orig and not cache_mod:
                out.append(('info', f'会话缓存里有 {len(cache_orig)} 份原版 m80（正常：那是解包的基础副本，'
                                    f'覆盖层会在更高层生效；只有当你直接改 base/romfs 时才需要同步这里）。'))
            if cache_mod:
                out.append(('ok', f'会话缓存里有 {len(cache_mod)} 份也已是改过的 m80。'))
        if self._game_running():
            out.append(('err', '安装时有游戏在运行 —— 文件可能被占用，覆盖层可能没真正写进去。'))

        # 现场快照：给离线复现用的原始线索
        try:
            first = next((t for t in targets if Path(t).exists()), None)
            if first:
                head = Path(first).read_bytes()[:64].hex(' ')
                out.append(('info', f'快照：覆盖层开头 64 字节 = {head}'))
            import msb_inspect as _mi
            raw = bytearray(patch_m80.dcx_decode(built_path if built_path and built_path.exists()
                                                 else prof['msb']))
            _b, table = _mi.model_table(raw)
            parts = _mi.parts(raw)
            out.append(('info', f'快照：模型表 {len(table)} 项，部件 {len(parts)} 个'))
        except Exception:
            pass

        # 模型资源检查：黑屏/不显示的直接原因
        try:
            for item in self._model_checks(prof, out_dir):
                mid = item.get('model') or '?'
                if item.get('chrbnd') is False:
                    out.append(('err', f'模型 {mid} 在游戏里没有资源文件'
                                       f'（chr\\{mid}.chrbnd.dcx 不存在）—— 换成它会黑屏或完全不显示。'))
                elif item.get('anibnd') is False:
                    out.append(('err', f'模型 {mid} 缺动画文件（chr\\{mid}.anibnd.dcx）—— 可能黑屏或不动。'))
                if item.get('in_table') is False and item.get('chrbnd') is not False:
                    src = '本次构建产物' if item.get('table_source') == 'build' else '原版地图'
                    out.append(('err', f'模型 {mid} 没有出现在{src}的模型表里 —— '
                                       f'换怪可能没写进去，游戏里看到的还是原来的怪。'))
        except Exception as error:
            out.append(('info', f'模型资源检查失败：{error}'))
        if not out:
            out.append(('ok', '未发现异常。'))
        return out

    def apply_and_launch(self):
        cur = paths.current_cloud()
        ok, _ov, text, _c = self._mod_info(cur) if cur else (False, None, '未知', 'err')
        if not text.startswith('已装'):
            self.log(f'启动前检查：这个包还没有装 Mod（{text}）', 'err')
            messagebox.showwarning(
                self._t('还没有安装 Mod', 'Mod is not installed'),
                self._t(f'当前这个包还没有装好 Mod（{self._translate_state(text)}）。',
                          f'Mod is not installed for this build ({self._translate_state(text)}).')
                + '\n\n'
                + self._t('请先点「安装 Mod」，等状态变成「已装 Mod」后再点「应用并启动」。',
                          'Click "Install Mod" first; once it shows installed, click "Apply & Launch".'))
            return
        self.apply_only(launch=True)

    def launch(self):
        prof = paths.profile(PROFILE)
        if not prof.get('cmd'):
            self.log(self.t('no_launcher'), 'err')
            messagebox.showwarning(self.t('err_title'), self.t('dialog_no_cmd'))
            return False
        subprocess.run(['powershell', '-NoProfile', '-Command',
                        'Get-Process lichii,DuskbloodsSolo,DuskbloodsCloud -ErrorAction SilentlyContinue | Stop-Process -Force'],
                       capture_output=True)
        time.sleep(2)
        started = datetime.now()
        self._session = {'start': started, 'pids': [], 'bright': [],
                         'emu': self._emu_log_start(prof), 'end': None}
        subprocess.Popen(['cmd', '/c', str(prof['cmd'])], cwd=str(prof['sim']),
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        self.log(self.t('launched'), 'ok')
        self._last_session_report = None
        # 只监视由本工具启动的这一局；用户自己双击启动的不记录
        threading.Thread(target=self._watch_game, args=(started, self._session),
                         daemon=True).start()

    # ---------- 画面亮度（黑屏检测，纯 ctypes，无依赖） ----------
    @staticmethod
    def _screen_brightness():
        """采样屏幕亮度（0~1）。纯 ctypes，不依赖 PIL。"""
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)

            user32.GetDC.restype = wintypes.HDC
            user32.GetDC.argtypes = [wintypes.HWND]
            user32.ReleaseDC.restype = ctypes.c_int
            user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
            user32.GetSystemMetrics.restype = ctypes.c_int
            user32.GetSystemMetrics.argtypes = [ctypes.c_int]
            gdi32.GetPixel.restype = wintypes.COLORREF
            gdi32.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]

            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
            if width <= 0 or height <= 0:
                return None
            hdc = user32.GetDC(None)
            if not hdc:
                return None
            total = 0.0
            n = 0
            for i in range(16):
                x = int(width * (i + 0.5) / 16)
                for j in range(9):
                    y = int(height * (j + 0.5) / 9)
                    color = gdi32.GetPixel(hdc, x, y) & 0xFFFFFFFF
                    if color == 0xFFFFFFFF:
                        continue
                    r = color & 0xFF
                    g = (color >> 8) & 0xFF
                    b = (color >> 16) & 0xFF
                    total += (r + g + b) / 3.0
                    n += 1
            user32.ReleaseDC(None, hdc)
            return (total / n / 255.0) if n else None
        except Exception:
            return None

    def _emu_log_start(self, prof):
        """记下本次启动前模拟器日志的大小，之后只取新增部分。"""
        try:
            logs = sorted(Path(prof['root']).glob('local/players/*/user/log/eden_log.txt'),
                          key=lambda p: p.stat().st_mtime, reverse=True)
            if logs:
                return {'path': str(logs[0]), 'size': logs[0].stat().st_size}
        except Exception:
            pass
        return None

    # ---------- 游戏会话：结束后生成日志 ----------
    @staticmethod
    def _game_running():
        names = ('lichii.exe', 'DuskbloodsSolo.exe', 'DuskbloodsCloud.exe')
        try:
            out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True,
                                 creationflags=0x08000000).stdout.decode('utf-8', 'replace')
        except Exception:
            return False
        low = out.lower()
        return any(n.lower() in low for n in names)

    @staticmethod
    def _game_pids():
        """当前在跑的游戏/启动器进程 (名称, PID)。"""
        out = []
        try:
            raw = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True,
                                 creationflags=0x08000000).stdout.decode('utf-8', 'replace')
        except Exception:
            return out
        for line in raw.splitlines():
            parts = [x.strip('"') for x in line.split('","')]
            if len(parts) >= 2 and parts[0].lower() in (
                    'lichii.exe', 'duskbloodssolo.exe', 'duskbloodscloud.exe'):
                try:
                    out.append((parts[0], int(parts[1])))
                except Exception:
                    pass
        return out

    def _watch_game(self, started, session=None):
        session = session if isinstance(session, dict) else {'start': started}
        try:
            time.sleep(6)
            tick = 0
            while True:
                tick += 1
                if tick % 2 == 1:      # 每两次循环采一次亮度（约 50 秒）
                    bright = self._screen_brightness()
                    if bright is not None:
                        session.setdefault('bright', []).append((datetime.now(), bright))
                running = self._game_running()
                if running:
                    for name, pid in self._game_pids():
                        tag = f'{name}#{pid}'
                        if tag not in session.setdefault('pids', []):
                            session['pids'].append(tag)
                    time.sleep(25)
                    continue
                break
        except Exception:
            return
        session['end'] = datetime.now()
        try:
            path = self._write_session_report(started, session)
            self._last_session_report = path
            self.root.after(0, lambda: self.log(f'游戏已结束，会话日志：{path}', 'info'))
        except Exception as error:
            self.root.after(0, lambda: self.log(f'写会话日志失败：{error}', 'err'))

    def _brightness_summary(self, session):
        """把亮度采样压成“正常/黑屏”时间段。"""
        samples = (session or {}).get('bright') or []
        if not samples:
            return ['（没有采到画面，可能游戏没显示出窗口）']
        rows, bad = [], 0
        for ts, value in samples:
            tag = '黑屏' if value < 0.05 else ('很暗' if value < 0.12 else '正常')
            if value < 0.05:
                bad += 1
            rows.append(f'  {ts:%H:%M:%S}  亮度 {value:.3f}  {tag}')
        head = f'  采样 {len(samples)} 次，其中 {bad} 次接近全黑'
        if bad == len(samples):
            head += '（整局都是黑的）'
        elif bad:
            head += '（有黑屏片段）'
        return [head] + rows

    def _emulator_log_tail(self, prof, started, session=None, max_lines=260):
        """模拟器日志：优先只取本次会话新增部分；滤掉渲染刷屏。"""
        root = prof.get('root')
        if not root:
            return ['（没有包路径，跳过）']
        try:
            logs = sorted(Path(root).glob('local/players/*/user/log/eden_log.txt'),
                          key=lambda p: p.stat().st_mtime, reverse=True)
        except Exception:
            logs = []
        if not logs:
            return ['（这个包里没找到 eden_log.txt）']
        newest = logs[0]
        try:
            size = newest.stat().st_size
            mtime = datetime.fromtimestamp(newest.stat().st_mtime)
        except Exception:
            size, mtime = 0, None
        out = [f'文件：{newest}',
               f'大小：{size:,} 字节   最后修改：{mtime:%Y-%m-%d %H:%M:%S}' if mtime else '']
        if mtime and mtime < started:
            out.append('⚠ 这个日志在本次启动之前就没再更新过 —— 模拟器可能根本没起来。')
        base = (session or {}).get('emu') if isinstance(session, dict) else None
        try:
            with open(newest, 'rb') as fp:
                if base and base.get('path') == str(newest) and base.get('size', 0) <= size:
                    fp.seek(base['size'])
                    text = fp.read().decode('utf-8', 'replace')
                    out.append(f'（只取本次会话新增的 {size - base["size"]:,} 字节）')
                else:
                    fp.seek(max(0, size - 400_000))
                    text = fp.read().decode('utf-8', 'replace')
        except Exception as error:
            return out + [f'读取失败：{error}']
        raw = text.splitlines()[-4000:]
        noise = ('Present draw', 'DrawToFrame', 'WaitForFrame', 'TickFrame', 'blit_screen',
                 'PresentClientBuffer', 'last 600 presents', 'Buffer cache')
        kept = [ln for ln in raw if not any(n in ln for n in noise)]
        errors = [ln for ln in kept
                  if any(k in ln for k in ('<Error>', '<Critical>', ' error', 'failed', 'crashed'))]
        out += ['', f'--- 有效行（已滤掉渲染刷屏，共 {len(kept)} 行，取最后 {min(60, len(kept))} 行）---']
        out += [ln[-400:] for ln in kept[-60:]]
        if errors:
            out += ['', f'--- 其中的错误行（{len(errors)} 条）---']
            out += [ln[-400:] for ln in errors[-40:]]
        return [x for x in out if x is not None]

    def _write_session_report(self, started, session=None):

        from datetime import datetime as _dt
        end = _dt.now()
        prof = paths.profile(PROFILE)
        verdicts = getattr(self, '_last_verdicts', None) or []
        lines = ['黄昏血族 · 训练场换怪工具 · 会话日志',
                 f'（本次运行日志：{getattr(self, "_log_path", "")}）',
                 '=' * 52,
                 '',
                 '--- 体检结论 ---']
        if verdicts:
            for level, text in verdicts:
                lines.append(('  ✘ ' if level == 'err' else '  ✔ ') + text)
        else:
            lines.append('  （本次没有执行安装，无结论）')
        lines += ['', '=' * 52,
                 f'开始：{started:%Y-%m-%d %H:%M:%S}',
                 f'结束：{end:%Y-%m-%d %H:%M:%S}',
                 f'时长：{int((end - started).total_seconds() // 60)} 分钟',
                 '',
                 self._env_report(),
                 '',
                 '--- 当前界面选择 ---']
        session = session or getattr(self, '_session', None) or {}
        lines += ['', '--- 本次预设（preset.json）---']
        try:
            pj = paths.OUT / 'tool_last' / 'preset.json'
            lines.append(pj.read_text(encoding='utf-8') if pj.exists() else '（没有生成 preset.json）')
        except Exception as error:
            lines.append(f'（读取失败：{error}）')
        lines += ['', '--- 这台机器上的 mod 目录 ---']
        try:
            root0 = prof.get('root') or paths.current_cloud()
            dirs = list(Path(root0).glob('local/players/*/user/load/*'))
            if not dirs:
                lines.append('  （没找到 load 目录）')
            for d in dirs:
                lines.append(f'  {d.name}  （{d}）')
                if not d.is_dir():
                    continue
                for mod in d.iterdir():
                    if mod.is_dir():
                        files = sum(1 for x in mod.rglob('*') if x.is_file())
                        lines.append(f'      - {mod.name}  文件 {files} 个')
        except Exception as error:
            lines.append(f'  （读取失败：{error}）')
        lines += ['', '--- 画面亮度（黑屏判定）---']
        try:
            lines += self._brightness_summary(session)
        except Exception as error:
            lines.append(f'（亮度统计失败：{error}）')
        lines += ['', '--- 游戏进程 ---']
        pids = session.get('pids') or []
        lines.append('  ' + ('、'.join(pids) if pids else '（没检测到游戏进程）'))
        if session.get('end') and session.get('start'):
            lines.append('  运行时长：%d 分钟'
                         % int((session['end'] - session['start']).total_seconds() // 60))
        try:
            lines.append(f'  游戏版本: {self.version_var.get()}')
            for row in self.rows:
                lines.append(f'  标靶: {row["model"].get()} / {row["variant"].get()}'
                             if 'variant' in row else f'  标靶: {row["model"].get()}')
        except Exception:
            pass
        keys = ('构建', '安装', '校验', '体检', '启动前', '开始启动', '游戏版本')
        noise = ('Mod:', '覆盖层:', '[云分享包]', '[单人包]', '[游戏包]', '跳过（没有游戏本体')
        kept, skipped = [], 0
        for ts, lv, text in self._log_lines:
            plain = text.strip()
            if plain.startswith(('[', '  ')) and any(n in text for n in noise):
                skipped += 1
                continue
            if lv in ('ok', 'err') or any(k in text for k in keys):
                kept.append(f'[{ts}] [{lv}] {text}')
            else:
                skipped += 1
        lines += ['', '--- 关键操作日志 ---']
        lines += kept[-260:]
        if skipped:
            lines.append(f'（已省略 {skipped} 条明细；完整流水见 [报错日志] 里的 feedback 文件）')
        errs = [f'[{ts}] {text}' for ts, lv, text in self._log_lines if lv == 'err']
        lines += ['', '--- 错误汇总 ---']
        lines += errs[-60:] if errs else ['（没有错误）']
        lines += ['', '--- 模拟器日志（尾部）---']
        try:
            lines += self._emulator_log_tail(prof, started)
        except Exception as error:
            lines.append(f'（附加模拟器日志失败：{error}）')
        path = LOG_DIR / f'{end:%Y%m%d-%H%M%S}.txt'
        path.write_text('\n'.join(lines), encoding='utf-8')
        return path

    def restore(self):
        try:
            tb.restore(PROFILE)
            self.log(self.t('restored'), 'ok')
        except Exception as e:
            self._log_exception('restore', e)
            self.log(self.t('restore_failed') + str(e), 'err')


if __name__ == '__main__':
    set_console_title(APP_TITLE)
    enable_dpi()
    root = tk.Tk()
    app = App(root)

    def _hook(exc_type, exc, tb):
        try:
            app._write_log('未捕获异常:\n' + ''.join(traceback.format_exception(exc_type, exc, tb)),
                           'err')
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook

    def _on_close():
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', _on_close)
    if '--en' in sys.argv:
        app.toggle_lang()
    root.mainloop()
