"""训练场换怪工具（GUI · 官方配色 · 中英双语）

三个标靶各选一个生物，点「应用并启动」，进庭院后在面板里逐个切标靶看效果。

用法：双击 `训练场换怪工具.cmd`，或
    python training_tool.py [--en]
"""
import json
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

APP_TITLE = '黄昏血族 · 训练场换怪工具'
TOOL_VERSION = '1.0'

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

CATALOG = HERE / 'catalog.json'
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
        root.geometry(f'{int(760 * self.scale)}x{int(404 * self.scale)}')
        root.configure(bg=BG)
        root.resizable(False, False)

        self._style()
        self.catalog = load_catalog()
        self.rebuild_labels()
        self.rows = []

        self._header()
        self._version()
        self._search()
        self._form()
        self._footer()
        self.w_status = tk.Label(root, text=self.t('ready'), bg=BG, fg=MUTED,
                                 font=(FONT_FAMILY, 9), anchor='w')
        self.w_status.pack(fill='x', padx=18, pady=(0, 10))

    # ---------- 语言 ----------
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
        self.root.title(self.t('win_title'))
        self.b_launch.configure(text=self.t('apply_launch'))
        self.b_apply.configure(text=self.t('apply'))
        self.b_restore.configure(text=self.t('restore'))
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
        self.version_box = ttk.Combobox(row, textvariable=self.version_var,
                                        values=[], width=52, state='readonly')
        self.version_box.pack(side='left', padx=8)
        self.version_box.bind('<<ComboboxSelected>>', lambda e: self._on_version())
        self.w_rescan = tk.Button(row, text=self.t('rescan'), command=self._rescan_versions,
                                  bd=0, bg=CARD, fg=GOLD, activebackground=LINE,
                                  activeforeground=GOLD, font=(FONT_FAMILY, 9), padx=10, pady=1,
                                  cursor='hand2')
        self.w_rescan.pack(side='left')
        self._fill_versions()

    def _fill_versions(self):
        try:
            self._pkgs = paths.packages()
        except Exception:
            self._pkgs = []
        labels = [f'{lb} — {p}' for lb, p in self._pkgs]
        self.version_box.configure(values=labels)
        cur = paths.current_cloud()
        pick = next((lb for lb, p in self._pkgs if cur and Path(p) == Path(cur)), None)
        if pick:
            self.version_box.set(f'{pick} — {cur}')
        elif labels:
            self.version_box.set(labels[0])
            paths.set_current(self._pkgs[0][1])

    def _on_version(self):
        sel = self.version_var.get()
        for lb, p in getattr(self, '_pkgs', []):
            if f'{lb} — {p}' == sel:
                paths.set_current(p)
                self.log(self.t('build_selected').format(name=lb), 'ok')
                self.log(f'  {p}', 'muted')
                return

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
        for i, (title, slot, parts) in enumerate(TARGETS):
            lbl = tk.Label(grid, text=self.t('rows')[i], bg=CARD, fg=TEXT,
                           font=(FONT_FAMILY, FONT_SIZE, 'bold'), width=12, anchor='w')
            lbl.grid(row=i, column=0, padx=(14, 4), pady=7, sticky='w')
            self.w_row_labels.append(lbl)
            m = ttk.Combobox(grid, values=self.labels, width=40, state='readonly')
            m.grid(row=i, column=1, padx=(4, 6), pady=7, sticky='ew')
            v = ttk.Combobox(grid, values=[self.t('variant_default')], width=22,
                             state='readonly')
            v.grid(row=i, column=2, padx=(0, 14), pady=7, sticky='w')
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
        self.b_apply = ttk.Button(bar, text=self.t('apply'), command=self.apply_only)
        self.b_apply.pack(side='left', padx=8)
        self.b_restore = ttk.Button(bar, text=self.t('restore'), command=self.restore)
        self.b_restore.pack(side='left')
        self.b_reload = ttk.Button(bar, text=self.t('reload'), command=self.reload)
        self.b_reload.pack(side='left', padx=8)
        self.b_oodle = ttk.Button(bar, text=self.t('oodle'), command=self.pick_oodle)
        self.b_oodle.pack(side='left', padx=(8, 0))

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
        self.root.update_idletasks()

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
            preset = self.build_preset()
            out = paths.OUT / 'tool_last'
            self.log(self.t('building'))
            tb.build(preset, PROFILE, str(out))
            self.log(self.t('installing'))
            tb.install(str(out), PROFILE)
            if launch:
                self.log(self.t('installed_launch'), 'ok')
                self.launch()
            else:
                self.log(self.t('installed'), 'ok')
        except Exception as e:
            self.log(self.t('failed') + str(e), 'err')
            text = str(e)
            if not retried and ('oo2core' in text.lower() or 'Oodle' in text):
                if messagebox.askyesno(self.t('err_title'), self.t('oodle_ask')):
                    if self.pick_oodle():
                        return self.apply_only(launch=launch, retried=True)
                self.log(self.t('failed') + self.t('oodle_missing'), 'err')
                return
            messagebox.showerror(self.t('err_title'), text)

    def apply_and_launch(self):
        self.apply_only(launch=True)

    def launch(self):
        prof = paths.profile(PROFILE)
        if not prof.get('cmd'):
            self.log(self.t('no_launcher'), 'err')
            messagebox.showwarning(self.t('err_title'), self.t('dialog_no_cmd'))
            return
        subprocess.run(['powershell', '-NoProfile', '-Command',
                        'Get-Process lichii,DuskbloodsSolo,DuskbloodsCloud -ErrorAction SilentlyContinue | Stop-Process -Force'],
                       capture_output=True)
        time.sleep(2)
        subprocess.Popen(['cmd', '/c', str(prof['cmd'])], cwd=str(prof['sim']),
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        self.log(self.t('launched'), 'ok')

    def restore(self):
        try:
            tb.restore(PROFILE)
            self.log(self.t('restored'), 'ok')
        except Exception as e:
            self.log(self.t('restore_failed') + str(e), 'err')


if __name__ == '__main__':
    set_console_title(APP_TITLE)
    enable_dpi()
    root = tk.Tk()
    app = App(root)

    def _on_close():
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', _on_close)
    if '--en' in sys.argv:
        app.toggle_lang()
    root.mainloop()
