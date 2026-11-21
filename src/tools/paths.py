"""路径：自动探测游戏包（云包/单人包），支持手动切换版本。

其他玩家的差别：
  · 云包可能放在任意目录
  · 可能是 host 角色也可能是 rooms/user 角色
  · 游戏本体路径由包自己的 local/settings.json 决定
"""
import json
from pathlib import Path

import detect

HERE = Path(__file__).resolve().parent.parent
CFG = HERE / 'config.json'
TID = detect.TID
MOD_DIR = detect.MOD_DIR

OUT = HERE / 'out'
PRESETS = HERE / 'presets'
SNAPS = HERE / 'snapshots'
RUNS = HERE / 'runs'
for _d in (OUT, PRESETS, SNAPS, RUNS):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def load_cfg():
    if CFG.exists():
        try:
            return json.loads(CFG.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}


def save_cfg(**kw):
    cfg = load_cfg()
    cfg.update({k: v for k, v in kw.items() if v is not None})
    try:
        CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding='utf-8')
    except Exception:
        pass


_CURRENT = None
_PKGS = None


def packages():
    """[(label, Path)]，云包优先；包含 config 里记住的包。"""
    global _PKGS
    if _PKGS is not None:
        return _PKGS
    cfg = load_cfg()
    found = detect.find_cloud()
    seen, out = set(), []
    remembered = cfg.get('cloud_root')
    if remembered and Path(remembered).exists():
        p = Path(remembered)
        seen.add(str(p))
        out.append((detect.label_for(p), p))
    for p in found:
        if str(p) not in seen:
            seen.add(str(p))
            out.append((detect.label_for(p), p))
    order = {'云分享包': 0, '云包': 1, '单人包': 2, '游戏包': 3}
    out.sort(key=lambda x: (order.get(x[0], 9), str(x[1])))
    _PKGS = out
    return out


def current_cloud():
    global _CURRENT
    if _CURRENT is not None:
        return _CURRENT
    cfg = load_cfg()
    remembered = cfg.get('cloud_root')
    if remembered and Path(remembered).exists():
        _CURRENT = Path(remembered)
        return _CURRENT
    pkgs = packages()
    _CURRENT = pkgs[0][1] if pkgs else None
    return _CURRENT


def set_current(path):
    """切换游戏版本（写入 config，之后一直用它）。"""
    global _CURRENT
    _CURRENT = Path(path)
    save_cfg(cloud_root=str(_CURRENT))


def _cmd_for(cloud):
    if not cloud:
        return None
    for n in ('02-启动游戏.cmd', '02-单人模式.cmd'):
        c = Path(cloud) / n
        if c.exists():
            return c
    return None


def profile(_name='cloud'):
    cloud = current_cloud()
    base = detect.game_base(cloud) if cloud else None
    targets = []
    if cloud:
        # 选中的包：总是写（目录不存在就建）
        for t in detect.overlay_targets(cloud):
            if t not in targets:
                targets.append(t)
        # 其它包：只更新“本来就有训练场覆盖层”的，不擅自给它装新 mod
        for _label, _root in packages():
            if Path(_root) == Path(cloud):
                continue
            try:
                for t in detect.overlay_targets(_root):
                    if t.exists() and t not in targets:
                        targets.append(t)
            except Exception:
                pass
        if not targets:
            targets = detect.overlay_targets(cloud)
    loads = detect.load_dirs(cloud) if cloud else []
    romfs = (base / 'romfs') if base else None
    msb = (romfs / 'map' / 'mapstudio' / 'm80_00_00_00.msb.dcx') if romfs else None
    return {
        'name': _name, 'root': cloud, 'sim': cloud, 'game': base, 'romfs': romfs,
        'msb': msb,
        'orig': msb.with_suffix(msb.suffix + '.orig') if msb else None,
        'load': loads[0] if loads else None,
        'overlay': targets[0] if targets else None,
        'overlays': targets,
        'cmd': _cmd_for(cloud),
    }
