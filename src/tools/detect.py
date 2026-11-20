"""自动定位游戏包（云分享/单人），并支持手动切换。"""
import json
import os
from pathlib import Path

TID = '0400D1D02399A000'
MOD_DIR = 'Dusk Training Ground'


def _candidate_roots():
    home = Path.home()
    roots = []
    here = Path(__file__).resolve().parent
    roots += [here, here.parent, here.parent.parent]
    for name in ('Downloads', 'Desktop', 'Documents', 'Documents\\Downloads'):
        roots.append(home / name)
    for drive in 'CDEFG':
        p = Path(drive + ':\\')
        if p.exists():
            roots.append(p)
            roots.append(p / 'Games')
    seen, out = set(), []
    for r in roots:
        try:
            r = r.resolve()
        except Exception:
            continue
        if r.exists() and r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _scan(roots, max_depth=3):
    hits = []
    for root in roots:
        if not root.exists():
            continue
        try:
            root = root.resolve()
        except Exception:
            continue
        base_depth = len(root.parts)
        for dirpath, dirnames, filenames in os.walk(root):
            depth = len(Path(dirpath).parts) - base_depth
            if depth > max_depth:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d not in
                           ('node_modules', '.git', 'Windows', 'Program Files',
                            'Program Files (x86)', '$Recycle.Bin', 'AppData', 'Temp')]
            names = {f.lower() for f in filenames}
            if ('duskbloodscloud.exe' in names or 'lichii.exe' in names
                    or '02-启动游戏.cmd' in filenames or '02-单人模式.cmd' in filenames):
                score = 0
                if 'duskbloodscloud.exe' in names:
                    score += 3
                if '02-启动游戏.cmd' in filenames:
                    score += 2
                hits.append((score, Path(dirpath)))
    return hits


def find_cloud(max_depth=3):
    """返回所有疑似游戏包的路径，云包优先。先查用户目录，找不到再扫盘。"""
    home = Path.home()
    fast = [home / 'Downloads', home / 'Desktop', home / 'Documents', home / 'Documents' / 'Downloads']
    hits = _scan(fast, max_depth)
    if not hits:
        slow = []
        for drive in 'CDEFG':
            d = Path(drive + ':\\')
            if d.exists():
                slow += [d, d / 'Games']
        here = Path(__file__).resolve().parent
        if 'appdata' not in str(here).lower():
            slow += [here, here.parent]
        hits = _scan(slow, max_depth)

    hits.sort(key=lambda x: -x[0])
    seen, out = set(), []
    for _, p in hits:
        k = str(p).lower()
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def label_for(path):
    d = Path(path)
    if (d / 'DuskbloodsCloud.exe').exists():
        return '云分享包'
    if (d / 'DuskbloodsSolo.exe').exists() or (d / '02-单人模式.cmd').exists():
        return '单人包'
    if (d / '02-启动游戏.cmd').exists():
        return '云包'
    return '游戏包'


def game_base(cloud):
    if not cloud:
        return None
    cloud = Path(cloud)
    st = cloud / 'local' / 'settings.json'
    if st.exists():
        try:
            cfg = json.loads(st.read_text(encoding='utf-8'))
            main = cfg.get('main')
            if main:
                p = Path(main)
                if p.name == 'main':
                    return p.parent.parent
                if p.is_dir():
                    return p if p.name == 'base' else p / 'base'
        except Exception:
            pass
    return None


def load_dirs(cloud):
    out = []
    if not cloud:
        return out
    players = Path(cloud) / 'local' / 'players'
    if not players.exists():
        return out
    for role in players.iterdir():
        if not role.is_dir():
            continue
        for sub in (role / 'user' / 'load', role / 'load'):
            if sub.is_dir() and sub not in out:
                out.append(sub)
        for sub in role.glob('*/user/load'):
            if sub.is_dir() and sub not in out:
                out.append(sub)
    return out


def overlay_targets(cloud):
    ts = []
    for load in load_dirs(cloud):
        ts.append(load / TID / MOD_DIR / 'romfs' / 'map' / 'mapstudio' / 'm80_00_00_00.msb.dcx')
    return ts


def describe(cloud):
    return {
        'cloud': str(cloud),
        'label': label_for(cloud),
        'game_base': str(game_base(cloud) or ''),
        'loads': [str(p) for p in load_dirs(cloud)],
        'targets': [str(p) for p in overlay_targets(cloud)],
    }


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    hits = find_cloud()
    print('找到', len(hits), '个游戏包:')
    for h in hits:
        print(f'  [{label_for(h)}] {h}')
