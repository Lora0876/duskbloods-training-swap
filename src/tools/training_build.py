"""训练场 MSB 构建器（M0 核心）。

  python training_build.py build presets/duo.json [--profile exp] [--out out/duo]
  python training_build.py install out/duo [--profile exp]
  python training_build.py restore [--profile exp]
  python training_build.py verify out/duo/m80_00_00_00.msb.dcx --preset presets/duo.json
  python training_build.py status [--profile exp]
  python training_build.py slots          # 打印模型表/槽位，生成 slots.json

设计要点（都是踩过的坑）：
  * 模型表项有两个名字：+0x28 短名、+0x34 长名，必须一起改；
  * 部件记录 +0x14 = 模型表下标 + 1（记录里存 1 基）；
  * 部件名 +0xB8，记录起点 = 名字位置 - 0xB8；
  * 参数 ID +0x2C0/+0x2C4：'base' 沿用 c6000 的 60000050/60001000（有血条、会打）。
"""
import argparse
import hashlib
import json
import shutil
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r'C:\Users\a\Downloads\dusk_exp')

import paths                     # noqa: E402
import patch_m80 as pm           # noqa: E402
from msb_inspect import model_table, parts  # noqa: E402

NAME_OFF = 0xB8
BASE_PARAMS = (0x60000050, 0x60001000)


# ---------- 基础工具 ----------

def dcx_read(path):
    return bytearray(pm.dcx_decode(path))


def dcx_write(raw, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pm.dcx_encode(bytes(raw)))
    back = pm.dcx_decode(path)
    if back != bytes(raw):
        raise SystemExit('roundtrip 校验失败：' + str(path))
    return path.stat().st_size


def find_part(raw, name):
    pos = raw.find(name.encode('utf-16-le'))
    if pos < 0:
        return None, None
    return pos, pos - NAME_OFF


def rename_model_entry(raw, table_base, idx, new):
    off = table_base + idx * 0x48
    if struct.unpack_from('<I', raw, off)[0] != 0x28:
        raise SystemExit(f'模型表第 {idx} 项魔数不对')
    # 表项 0x48 字节：短名 +0x28 起 12 字节、长名 +0x34 起 18 字节，
    # 写多了会踩到下一项的 0x28 魔数（duo 构建时踩过）。
    raw[off + 0x28:off + 0x28 + 12] = new.encode('utf-16-le').ljust(12, b'\x00')
    raw[off + 0x34:off + 0x34 + 18] = (new + '.sib').encode('utf-16-le').ljust(18, b'\x00')


def set_part(raw, pos, rec, name, model_slot, pos3, params, entity):
    raw[pos:pos + 20] = name.encode('utf-16-le').ljust(20, b'\x00')
    struct.pack_into('<I', raw, pos - 0xA4, model_slot + 1)
    struct.pack_into('<3f', raw, rec + 0x20, *pos3)
    if params == 'base':
        struct.pack_into('<II', raw, rec + 0x2C0, *BASE_PARAMS)
    if entity is not None:
        struct.pack_into('<I', raw, rec + 0x10, entity)


def m10_record(model):
    raw = paths.M10.read_bytes()
    pos, rec = find_part(raw, model + '_0000')
    if pos is None:
        pos, rec = find_part(raw, model + '_0001')
    if pos is None:
        raise SystemExit(f'm10 里找不到 {model} 的部件记录')
    return bytearray(raw[rec:rec + 1000])


# ---------- 构建 ----------

def build(preset, prof, out_dir):
    P = paths.profile(prof)
    base_path = P['orig'] if preset.get('base', 'orig') == 'orig' else P['msb']
    if preset.get('base', 'orig') == 'orig' and not P['orig'].exists() and P['msb'].exists():
        shutil.copyfile(P['msb'], P['orig'])
        print(f'  创建备份 {P["orig"].name}')
    if not base_path.exists():
        raise SystemExit(f'缺基准 MSB：{base_path}')
    raw = dcx_read(base_path)
    table_base, mt = model_table(raw)
    n_parts = len(parts(raw))
    PLACED = {}

    for i, b in enumerate(preset['bosses']):
        slot = b['part']
        pos, rec = find_part(raw, slot)
        if pos is None:
            raise SystemExit(f'找不到部件槽 {slot}')
        rename_model_entry(raw, table_base, b['model_slot'], b['model'])
        src = b.get('src', b['model'])
        try:
            recdata = m10_record(src)
        except SystemExit:
            # m10 里没有就用 m80 自己的记录当模板（和旧 add_mobs.py 一样）
            p2, r2 = find_part(raw, f'{src}_0000')
            if p2 is None:
                raise SystemExit(f'找不到模板记录 {src}')
            recdata = bytearray(raw[r2:r2 + 1000])
            print(f'  (模板取自 m80: {src}_0000)')
        name = b.get('name') or (slot if b.get('keep_name') else f"{b['model']}_{slot.split('_')[1]}")
        set_part(raw, pos, rec, name, b['model_slot'], b['pos'],
                 b.get('params', 'base'), b.get('entity', 40 + i))
        PLACED[slot] = (pos, rec)
        print(f"  {slot:<12} -> {name:<12} model_slot={b['model_slot']} params={b.get('params','base')}")

    for rm in preset.get('rename_model_slots', []):
        rename_model_entry(raw, table_base, rm['slot'], rm['model'])
        print(f"  rename 模型表[{rm['slot']}] -> {rm['model']}")
    used = {b['part'] for b in preset['bosses']}
    for sp in preset.get('set_params', []):
        pos, rec = PLACED.get(sp['part']) or find_part(raw, sp['part'])
        if pos is None:
            raise SystemExit('找不到部件 ' + sp['part'])
        struct.pack_into('<II', raw, rec + 0x2C0, int(sp['a'], 0), int(sp['b'], 0))
        if 'c' in sp:
            struct.pack_into('<I', raw, rec + 0x2D0, int(sp['c'], 0))
        if 'd' in sp:
            struct.pack_into('<I', raw, rec + 0x2D4, int(sp['d'], 0))
        print(f"  set_params {sp['part']} -> {sp['a']}/{sp['b']}"
              + (f" 2D0={sp['c']}" if 'c' in sp else '')
              + (f" 2D4={sp['d']}" if 'd' in sp else ''))
    for sf in preset.get('set_fields', []):
        pos, rec = PLACED.get(sf['part']) or find_part(raw, sf['part'])
        if pos is None:
            raise SystemExit('找不到部件 ' + sf['part'])
        off = int(sf['offset'], 0)
        val = int(sf['value'], 0)
        struct.pack_into('<I', raw, rec + off, val)
        print(f"  set_field {sf['part']} +{off:#x} = {val:#x}")

    for sn in preset.get('set_name', []):
        pos, rec = find_part(raw, sn['part'])
        if pos is None:
            raise SystemExit('找不到部件 ' + sn['part'])
        raw[pos:pos + 20] = sn['name'].encode('utf-16-le').ljust(20, b'\x00')
        print(f"  set_name {sn['part']} -> {sn['name']}")
    for sm in preset.get('set_model', []):
        pos, rec = find_part(raw, sm['part'])
        if pos is None:
            raise SystemExit('找不到部件 ' + sm['part'])
        struct.pack_into('<I', raw, pos - 0xA4, sm['model_slot'] + 1)
        print(f"  set_model {sm['part']} -> slot {sm['model_slot']} (只改 +0x14)")
    for mv in preset.get('move_parts', []):
        pos, rec = find_part(raw, mv['part'])
        if pos is None:
            raise SystemExit('找不到要移动的部件 ' + mv['part'])
        struct.pack_into('<3f', raw, rec + 0x20, *mv['pos'])
        print(f"  move {mv['part']} -> {tuple(round(v, 2) for v in mv['pos'])}")
    if preset.get('hide_all_parts'):
        for p in parts(raw):
            if p['name'] in used:
                continue
            pos, rec = find_part(raw, p['name'])
            struct.pack_into('<3f', raw, rec + 0x20, p['pos'][0], -9999.0, p['pos'][2])
        print('  hide ALL parts (except bosses)')
    elif preset.get('hide_unused_dummies', True):
        for p in parts(raw):
            if not p['name'].startswith('c0000_') or p['name'] in used:
                continue
            pos, rec = find_part(raw, p['name'])
            struct.pack_into('<3f', raw, rec + 0x20, p['pos'][0], -9999.0, p['pos'][2])
            print(f'  hide {p["name"]}')

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    size = dcx_write(raw, out_dir / 'm80_00_00_00.msb.dcx')
    (out_dir / 'preset.json').write_text(json.dumps(preset, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'built {out_dir / "m80_00_00_00.msb.dcx"}  {size:,} bytes  (parts={n_parts})')
    return out_dir


# ---------- 安装 / 回滚 / 校验 ----------

def install(src_dir, prof):
    P = paths.profile(prof)
    src = Path(src_dir) / 'm80_00_00_00.msb.dcx'
    if not src.exists():
        raise SystemExit('缺构建产物：' + str(src))
    targets = P.get('overlays') or [P['overlay']]
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
    target = targets[0]
    snap = paths.SNAPS / time.strftime('%Y%m%d-%H%M%S')
    snap.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, snap / 'm80_00_00_00.msb.dcx')
    pj = Path(src_dir) / 'preset.json'
    if pj.exists():
        shutil.copyfile(pj, snap / 'preset.json')
    (snap / 'sha256.txt').write_text(hashlib.sha256(target.read_bytes()).hexdigest(), encoding='ascii')
    print(f'installed -> {target}')
    print(f'snapshot  -> {snap}')


def restore(prof):
    P = paths.profile(prof)
    for target in (P.get('overlays') or [P['overlay']]):
        if target.exists():
            target.unlink()
            print('removed overlay', target)
    target = (P.get('overlays') or [P['overlay']])[0]
    d = target.parent
    while d != P['load'] and d.exists() and not any(d.iterdir()):
        d.rmdir()
        d = d.parent
    if P['orig'].exists():
        cur = hashlib.sha256(P['msb'].read_bytes()).hexdigest()
        org = hashlib.sha256(P['orig'].read_bytes()).hexdigest()
        if cur != org:
            shutil.copyfile(P['orig'], P['msb'])
            print('restored romfs msb from .orig')
        else:
            print('romfs msb 已是原版')
    else:
        print('没有 .orig，跳过 romfs 还原')


def verify(path, preset_path):
    raw = dcx_read(path)
    table_base, mt = model_table(raw)
    preset = json.loads(Path(preset_path).read_text(encoding='utf-8-sig'))
    ok = True
    for b in preset['bosses']:
        i = b['model_slot']
        got = mt[i]['short'] if i < len(mt) else '?'
        exp = b['model']
        flag = 'OK ' if got == exp else 'BAD'
        ok &= got == exp
        print(f'  [{flag}] model_slot {i}: {got} (expect {exp})')
        pos, rec = find_part(raw, b.get('name') or f"{b['model']}_{b['part'].split('_')[1]}")
        if pos is None:
            print(f'  [BAD] 找不到部件 {b.get("name")}')
            ok = False
            continue
        got_pos = struct.unpack_from('<3f', raw, rec + 0x20)
        d = max(abs(got_pos[k] - b['pos'][k]) for k in range(3))
        print(f"  [{'OK ' if d < 0.01 else 'BAD'}] {b['part']} pos {tuple(round(v,2) for v in got_pos)}")
        ok &= d < 0.01
    print('verify:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


def status(prof):
    P = paths.profile(prof)
    print('profile :', prof)
    print('overlay :', P['overlay'], 'EXISTS' if P['overlay'].exists() else '-')
    if P['overlay'].exists():
        print('  sha256:', hashlib.sha256(P['overlay'].read_bytes()).hexdigest()[:16])
    print('romfs   :', P['msb'], hashlib.sha256(P['msb'].read_bytes()).hexdigest()[:16] if P['msb'].exists() else 'MISSING')
    if P['orig'].exists():
        print('orig    :', hashlib.sha256(P['orig'].read_bytes()).hexdigest()[:16])


def dump_slots(prof):
    P = paths.profile(prof)
    raw = dcx_read(P['orig'] if P['orig'].exists() else P['msb'])
    table_base, mt = model_table(raw)
    pt = parts(raw)
    used = {}
    for p in pt:
        used[p['model_idx']] = used.get(p['model_idx'], 0) + 1
    data = {'map': 'm80_00_00_00', 'table_base': hex(table_base),
            'model_table': [dict(e, used_by_parts=used.get(e['i'] + 1, 0)) for e in mt],
            'parts': pt}
    out = HERE.parent / 'slots.json'
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    print('written', out)
    for e in data['model_table']:
        tag = 'FREE' if e['used_by_parts'] == 0 else f"used={e['used_by_parts']}"
        print(f"  [{e['i']:>2}] {e['short']:<10} {tag}")
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build'); b.add_argument('preset'); b.add_argument('--profile', default='exp'); b.add_argument('--out')
    i = sub.add_parser('install'); i.add_argument('dir'); i.add_argument('--profile', default='exp')
    r = sub.add_parser('restore'); r.add_argument('--profile', default='exp')
    v = sub.add_parser('verify'); v.add_argument('path'); v.add_argument('--preset', required=True)
    s = sub.add_parser('status'); s.add_argument('--profile', default='exp')
    d = sub.add_parser('slots'); d.add_argument('--profile', default='exp')
    a = ap.parse_args()

    if a.cmd == 'build':
        preset = json.loads(Path(a.preset).read_text(encoding='utf-8-sig'))
        out = a.out or str(paths.OUT / Path(a.preset).stem)
        build(preset, a.profile, out)
    elif a.cmd == 'install':
        install(a.dir, a.profile)
    elif a.cmd == 'restore':
        restore(a.profile)
    elif a.cmd == 'verify':
        return verify(a.path, a.preset)
    elif a.cmd == 'status':
        status(a.profile)
    elif a.cmd == 'slots':
        dump_slots(a.profile)
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
