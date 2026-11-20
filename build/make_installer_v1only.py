"""打包「训练场换怪工具」单文件一键安装包（仓库内直接跑，版本号从 src 读）。

来源：本仓库的 src\\（1.0）
出口：
    dist\\训练场换怪工具1.0-一键安装.exe     单文件
    dist\\训练场换怪工具1.0.zip             exe + 说明.txt
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parent.parent      # 仓库根（含 src/ release/）
SRC = ROOT / 'src'                                 # 1.0 的源码
WORK = ROOT / 'build' / '_work'
PAYLOAD = WORK / 'payload'
DIST = ROOT / 'release'
OUT_EXE = OUT_ZIP = OUT_SINGLE = None   # 读到版本号后填（见 main）
VERSION = ''
CSC = Path(r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe')

# 单版本：payload 平铺在根上（和以前那个包一致）
FILES = [
    'training_tool.py',
    'catalog.json',
    # oo2core_9_win64.dll 是 Oodle 的私有库，不随包分发（GitHub 上会有版权问题）。
    # 用户从自己的《艾尔登法环 / 黑夜君临》目录复制一份到工具目录即可；
    # 工具在缺少它时会给出明确提示。
    'tools/detect.py',
    'tools/msb_inspect.py',
    'tools/patch_m80.py',
    'tools/paths.py',
    'tools/training_build.py',
]
PRESET = None


def main() -> int:
    global OUT_EXE, OUT_ZIP, OUT_SINGLE, VERSION
    if not SRC.is_dir():
        raise SystemExit('找不到源码目录: %s' % SRC)

    # 版本号从源码读，文件名和文案都跟着它走
    tool = (SRC / 'training_tool.py').read_text(encoding='utf-8')
    m = re.search(r"TOOL_VERSION\s*=\s*'([^']+)'", tool)
    if not m:
        raise SystemExit('读不到 TOOL_VERSION')
    VERSION = m.group(1)
    if not VERSION.startswith('1.'):
        raise SystemExit('版本号不对劲: ' + VERSION)
    OUT_EXE = DIST / ('训练场换怪工具%s-一键安装.exe' % VERSION)
    OUT_ZIP = DIST / ('训练场换怪工具%s.zip' % VERSION)
    OUT_SINGLE = DIST / ('训练场换怪工具%s-单文件版.zip' % VERSION)
    if '_lock_panel' in tool:
        raise SystemExit('源目录里含有不该出现的功能代码，版本不对，拒绝打包')

    if WORK.exists():
        shutil.rmtree(WORK)
    PAYLOAD.mkdir(parents=True)

    for rel in FILES:
        src = SRC / rel
        if not src.exists():
            raise SystemExit('缺文件: %s' % src)
        dst = PAYLOAD / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    if PRESET and PRESET.exists():
        (PAYLOAD / 'presets').mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PRESET, PAYLOAD / 'presets' / 'boss_c6000.json')

    blank = {'cloud_root': '', '_说明': '安装时自动填入游戏包目录；也可手动改'}
    (PAYLOAD / 'config.json').write_text(
        json.dumps(blank, ensure_ascii=False, indent=1), encoding='utf-8')

    HERE = Path(__file__).resolve().parent
    ps1 = (HERE / 'install_template_v1only.ps1').read_text(encoding='utf-8-sig')
    (PAYLOAD / 'install.ps1').write_bytes(ps1.encode('utf-8-sig'))

    DIST.mkdir(parents=True, exist_ok=True)
    print('payload: %d 个文件' % len(list(PAYLOAD.rglob('*'))))
    args = [str(CSC), '/nologo', '/target:exe', '/platform:anycpu', f'/out:{OUT_EXE}',
            str(HERE / 'launcher_v1only.cs')]
    for f in sorted(PAYLOAD.rglob('*')):
        if f.is_file():
            args.append(f'/resource:{f},payload/' + f.relative_to(PAYLOAD).as_posix())
    print('编译 %s ...' % OUT_EXE.name)
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print('编译失败:\n', r.stdout, r.stderr)
        return 1
    print('  生成 %s  (%.0f KB)' % (OUT_EXE.name, OUT_EXE.stat().st_size / 1024))

    # 说明（单文件版格式，和老包一致：zip 根上就两个文件）
    readme_text = (
        '黄昏血族 · 训练场换怪（单文件安装器 · %s）\n' % VERSION +
        '\n'
        '用法：\n'
        '  1. 双击「一键安装.exe」（放在哪都行，桌面上也可以）\n'
        '  2. 它会自己检查 Python，然后把工具装好\n'
        '  3. 装完桌面会多一个快捷方式，双击就能用\n'
        '\n'
        '版本：%s\n' % VERSION +
        '\n'
        '前置：\n'
        '  · Python 3.10 以上（带 tkinter）；没装会提示你去 python.org 装 3.12\n'
        '  · 游戏本体要你自己准备（本工具不含游戏）\n'
        '\n'
        '用法：\n'
        '  选三个标靶 → 应用并启动 → 标题按 A → 大厅 Plus → 庭院 → A → 面板里切标靶。\n'
        '  界面右上角 EN / 中文 可切换语言。\n'
        '\n'
        '需要 oo2core_9_win64.dll（Oodle 压缩库）才能生成自定义换怪：\n'
        '  · 点工具右下角的「指定 Oodle...」选中它（会记住）；或\n'
        '  · 把它复制到工具目录；或\n'
        '  · 设环境变量 DUSK_OO2CORE 指向它。\n'
        '  它在《艾尔登法环》/《黑夜君临》的游戏目录里。包里不带（版权原因）。\n'
        '\n'
        '卸载：删除桌面快捷方式和 %LOCALAPPDATA% 下的工具目录；\n'
        '      游戏里的补丁用工具里的「还原原版」清掉即可。\n'
    )
    readme = WORK / '说明.txt'
    readme.write_text(readme_text, encoding='utf-8')

    # ---- 单文件版：zip 根上只有 一键安装.exe + 说明.txt（照 dist\单文件版\ 的格式）----
    single_dir = ROOT / 'release' / ('单文件版-' + VERSION)
    if single_dir.exists():
        shutil.rmtree(single_dir)
    single_dir.mkdir(parents=True)
    shutil.copyfile(OUT_EXE, single_dir / '一键安装.exe')
    shutil.copyfile(readme, single_dir / '说明.txt')
    if OUT_SINGLE.exists():
        OUT_SINGLE.unlink()
    shutil.make_archive(str(OUT_SINGLE.with_suffix('')), 'zip', root_dir=single_dir)
    print('  生成 %s  (%.0f KB, 内含 2 个文件)' % (OUT_SINGLE.name, OUT_SINGLE.stat().st_size / 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())