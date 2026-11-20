"""m80 MSB 结构盘点：模型表 + 部件记录。输出 JSON 给 slots.json 用。

用法:
  python msb_inspect.py [--json out.json]
"""
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, r'C:\Users\a\Downloads\dusk_exp')
import patch_m80 as pm  # noqa: E402

ROMFS = Path(r'C:\Users\a\Downloads\黄昏血族网测（单人） - 实验\黄昏血族网测（单人）\游戏本体：THE DUSKBLOODS NETWORK TEST VER\base\romfs')
MSB = ROMFS / 'map' / 'mapstudio' / 'm80_00_00_00.msb.dcx'
ORIG = MSB.with_suffix(MSB.suffix + '.orig')
TBASE = 0x5A0
ENT = 0x48
NAME_OFF = 0xB8


def s16(b, off, n):
    return b[off:off + n].decode('utf-16-le', 'ignore').split('\x00')[0]


def model_table(raw):
    """从 TBASE 起按 0x48 步长找连续的 0x28 魔数串。"""
    starts = []
    for base in range(TBASE, TBASE + 0x1000, 4):
        if struct.unpack_from('<I', raw, base)[0] != 0x28:
            continue
        n, o = 0, base
        while o + ENT <= len(raw) and struct.unpack_from('<I', raw, o)[0] == 0x28:
            n += 1
            o += ENT
        if n >= 3:
            starts.append((base, n))
    if not starts:
        raise SystemExit('找不到模型表魔数串')
    base, n = max(starts, key=lambda x: x[1])
    out = []
    for i in range(n):
        o = base + i * ENT
        out.append({
            'i': i,
            'off': hex(o),
            'short': s16(raw, o + 0x28, 16),
            'long': s16(raw, o + 0x34, 24),
            'count': struct.unpack_from('<I', raw, o + 0x18)[0],
        })
    return base, out


def parts(raw):
    """扫部件记录：名字形如 cXXXX_YYYY，记录起点 = 名字位置 - 0xB8。"""
    import re
    pat = re.compile(rb'c\x00[0-9]\x00[0-9]\x00[0-9]\x00[0-9]\x00_\x00[0-9]\x00[0-9]\x00[0-9]\x00[0-9]\x00')
    out = []
    for m in pat.finditer(raw):
        pos = m.start()
        rec = pos - NAME_OFF
        if rec < 0:
            continue
        out.append({
            'name': m.group(0).decode('utf-16-le'),
            'rec': hex(rec),
            'model_idx': struct.unpack_from('<I', raw, pos - 0xA4)[0],
            'entity': struct.unpack_from('<I', raw, rec + 0x10)[0],
            'pos': [round(v, 3) for v in struct.unpack_from('<3f', raw, rec + 0x20)],
            'param_a': hex(struct.unpack_from('<I', raw, rec + 0x2C0)[0]),
            'param_b': hex(struct.unpack_from('<I', raw, rec + 0x2C4)[0]),
        })
    return out


def main():
    raw = pm.dcx_decode(ORIG)
    base, mt = model_table(raw)
    pt = parts(raw)
    print(f'MSB={len(raw):,} bytes  model_table@{hex(base)} entries={len(mt)}  parts={len(pt)}')
    print('\n== 模型表 ==')
    for e in mt:
        print(f"  [{e['i']:>2}] {e['short']:<10} {e['long']:<14} instances={e['count']}")
    print('\n== 部件记录 ==')
    for p in pt:
        print(f"  {p['name']:<12} model_idx={p['model_idx']:>2} entity={p['entity']:>3} pos={p['pos']} "
              f"param={p['param_a']}/{p['param_b']}")
    if '--json' in sys.argv:
        path = sys.argv[sys.argv.index('--json') + 1]
        Path(path).write_text(json.dumps({'model_table': mt, 'parts': pt}, ensure_ascii=False, indent=1), encoding='utf-8')
        print('\nwritten', path)


if __name__ == '__main__':
    main()
