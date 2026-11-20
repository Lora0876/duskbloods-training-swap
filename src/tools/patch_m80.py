"""训练场（m80_00_00_00）实体改写工具。

MSB 结构（实测）：
  * 每个实体 = 1000 字节记录
  * 实体名 UTF-16 内联在记录固定位置
  * 名字前 0xA4 字节处是 u32 = 模型表索引 + 1（31/31 验证）
DCX：本游戏 map 用 Kraken 压缩，这里用 oo2core 的 OodleLZ_Compress 生成同样格式。

oo2core_9_win64.dll 怎么找（按优先级）：
  1. 环境变量 DUSK_OO2CORE（给文件或目录都行）
  2. 用户点「指定 Oodle...」选过并记住的路径（oo2core.path）
  3. 工具目录、上一级、上两级里的 oo2core_9_win64.dll
这个 DLL 是 Oodle 的私有库，本工具不随包分发；它在你自己的
《艾尔登法环》/《黑夜君临》游戏目录里。

用法：
  python patch_m80.py <romfs> <解压后的 m80 msb>          # 打补丁（7 个装饰物 -> 稻草人）
  python patch_m80.py <romfs> restore                     # 还原
"""
import ctypes
import os
import re
import shutil
import struct
import sys
import time
from pathlib import Path

DCX_DATA = 0x4C
DCX_VERSION = 0x00011000
KRAKEN = 8

OO2CORE_NAME = 'oo2core_9_win64.dll'
OO2CORE_ENV = 'DUSK_OO2CORE'            # 环境变量：给文件或目录
OO2CORE_SETTING = 'oo2core.path'        # 记住用户选过的路径（放在本文件旁边）
MODEL_INDEX = {'c1000': 1, 'c2000': 2, 'c2010': 3, 'c2020': 4, 'c2030': 5, 'c2210': 6}

_HERE = Path(__file__).resolve().parent
_LIB_CACHE = {}
OO2CORE = None                          # 兼容旧代码：当前解析到的路径（可能为 None）


def _as_dll(path):
    """把「文件或目录」统一成 dll 路径。"""
    p = Path(str(path).strip().strip('"')).expanduser()
    if p.is_dir():
        p = p / OO2CORE_NAME
    return p


def _saved_path():
    try:
        p = Path((_HERE / OO2CORE_SETTING).read_text(encoding='utf-8').strip())
    except (OSError, ValueError):
        return None
    return p if p.is_file() else None


def oo2core_path():
    """按优先级找 oo2core，找不到返回 None。"""
    global OO2CORE
    env = os.environ.get(OO2CORE_ENV)
    if env:
        p = _as_dll(env)
        if p.is_file():
            OO2CORE = p
            return p
    saved = _saved_path()
    if saved:
        OO2CORE = saved
        return saved
    for folder in (_HERE, _HERE.parent, _HERE.parent.parent):
        p = folder / OO2CORE_NAME
        if p.is_file():
            OO2CORE = p
            return p
    OO2CORE = None
    return None


def set_oo2core(path):
    """记住用户指定的 oo2core 路径（会先试着加载一次）。返回最终路径。"""
    p = _as_dll(path).resolve()
    if not p.is_file():
        raise FileNotFoundError(str(p))
    try:
        ctypes.WinDLL(str(p))
    except OSError as error:
        raise ValueError('这个文件加载不了（不是 oo2core_9_win64.dll？）：%s' % error)
    (_HERE / OO2CORE_SETTING).write_text(str(p), encoding='utf-8')
    _LIB_CACHE.clear()
    global OO2CORE
    OO2CORE = p
    return p


# ---------------------------------------------------------------------------------------------
# 自动搜索：Steam 库 / 常见游戏目录 / 用户下载目录
# ---------------------------------------------------------------------------------------------
# 命中这些名字的目录优先（FromSoftware 的游戏最可能带 oo2core）
_FROM_SOFT_HINTS = ('ELDEN', 'NIGHTREIGN', 'DARK SOULS', 'ARMORED CORE', 'DUSKBLOODS')
_SKIP_DIRS = {'windows', 'winsxs', 'temp', '$recycle.bin', 'node_modules', '.git',
              'system32', 'syswow64', 'installer', 'assembly'}


def _steam_libraries():
    """从注册表 + libraryfolders.vdf 找出所有 Steam 库目录。"""
    steam_dirs = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
                          (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam'),
                          (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Valve\Steam')):
            try:
                with winreg.OpenKey(hive, key) as handle:
                    steam_dirs.append(Path(winreg.QueryValueEx(handle, 'SteamPath')[0]))
            except OSError:
                continue
    except Exception:
        pass
    for steam in list(steam_dirs):
        vdf = steam / 'steamapps' / 'libraryfolders.vdf'
        if not vdf.is_file():
            continue
        try:
            text = vdf.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        for match in re.finditer(r'"path"\s+"([^"]+)"', text):
            steam_dirs.append(Path(match.group(1).replace('\\\\', '\\')))
    return [p for p in steam_dirs if p.is_dir()]


def _search_roots():
    """返回 [(目录, 最大深度)]，越靠前越可能是游戏目录。"""
    roots = []
    for steam in _steam_libraries():
        roots.append((steam / 'steamapps' / 'common', 4))
    for env in ('ProgramFiles(x86)', 'ProgramFiles'):
        base = os.environ.get(env)
        if not base:
            continue
        roots += [(Path(base) / 'Steam' / 'steamapps' / 'common', 4),
                  (Path(base) / 'Epic Games', 4),
                  (Path(base) / 'XboxGames', 4)]
    if os.environ.get('ProgramData'):
        roots.append((Path(os.environ['ProgramData']) / 'XboxGames', 4))
    for drive in 'CDEFGH':
        base = Path(drive + ':/')
        if not base.is_dir():
            continue
        roots += [(base / 'SteamLibrary' / 'steamapps' / 'common', 4),
                  (base / 'Games', 4),
                  (base / 'XboxGames', 4),
                  (base / 'Program Files' / 'Steam' / 'steamapps' / 'common', 4)]
    # 用户自己的下载/桌面兜底（用户常把 DLL 丢在这里），深度放小一点
    home = Path.home()
    roots += [(home / 'Downloads', 3), (home / 'Desktop', 2)]
    return [(p, d) for p, d in roots if p.is_dir()]


def auto_find_oo2core(budget_s=12.0):
    """尽量自己找到 oo2core_9_win64.dll；找到就记住并返回路径，找不到返回 None。

    只用有限的搜索范围 + 时间预算，避免卡住界面（调用方应该放后台线程）。
    """
    found = oo2core_path()
    if found:
        return found
    deadline = time.time() + max(1.0, float(budget_s))
    target = OO2CORE_NAME.lower()
    fallback = None
    for root, max_depth in _search_roots():
        if time.time() >= deadline:
            break
        base_depth = len(root.parts)
        for dirpath, dirnames, filenames in os.walk(str(root), onerror=lambda e: None):
            if time.time() >= deadline:
                break
            dirnames[:] = [d for d in dirnames if d.lower() not in _SKIP_DIRS]
            if len(Path(dirpath).parts) - base_depth > max_depth:
                dirnames[:] = []
                continue
            lowered = {f.lower() for f in filenames}
            if target not in lowered:
                continue
            candidate = Path(dirpath) / OO2CORE_NAME
            upper = str(candidate).upper()
            if any(hint in upper for hint in _FROM_SOFT_HINTS):
                return set_oo2core(candidate)      # 明显是 FromSoft 游戏，直接用
            if fallback is None:
                fallback = candidate              # 先记着，继续找更像的
    if fallback is not None:
        try:
            return set_oo2core(fallback)
        except Exception:
            return None
    return None


def _missing_message():
    return (
        '找不到 %s（改怪用的 Oodle 压缩库）。\n\n'
        '三种办法任选：\n'
        '  1. 在工具里点「指定 Oodle...」，选中这个 DLL；\n'
        '  2. 把它复制到工具目录（和 training_tool.py 同一层）；\n'
        '  3. 设置环境变量 %s 指向它（文件或目录都行）。\n\n'
        '这个 DLL 在你自己的《艾尔登法环》或《黑夜君临》游戏目录里。\n'
        '（只换现成补丁不需要它；只有「应用」要重新压 MSB 时才需要。）'
        % (OO2CORE_NAME, OO2CORE_ENV))


def _oodle():
    path = oo2core_path()
    if path is None:
        raise RuntimeError(_missing_message())
    key = str(path)
    lib = _LIB_CACHE.get(key)
    if lib is None:
        lib = ctypes.WinDLL(key)
        lib.OodleLZ_Compress.restype = ctypes.c_ssize_t
        _LIB_CACHE[key] = lib
    return lib


def dcx_encode(raw, level=4):
    lib = _oodle()
    need = lib.OodleLZ_GetCompressedBufferSizeNeeded(KRAKEN, len(raw))
    buf = ctypes.create_string_buffer(need + 64)
    got = lib.OodleLZ_Compress(KRAKEN, bytes(raw), len(raw), buf, level, None, None, None, 0)
    if got <= 0:
        raise RuntimeError('Oodle 压缩失败')
    comp = buf.raw[:got]
    header = bytearray()
    header += b'DCX\x00' + struct.pack('>I', DCX_VERSION)
    header += struct.pack('>I', 0x18) + struct.pack('>I', 0x24)
    header += struct.pack('>I', 0x44) + struct.pack('>I', DCX_DATA)
    header += b'DCS\x00' + struct.pack('>I', len(raw)) + struct.pack('>I', len(comp))
    header += b'DCP\x00' + b'KRAK' + struct.pack('>I', 0x20) + struct.pack('>I', level)
    header += struct.pack('>I', 0) + struct.pack('>I', 0) + struct.pack('>I', 0)
    header += b'\x00\x01\x01\x00'
    header += b'DCA\x00' + struct.pack('>I', 8)
    assert len(header) == DCX_DATA
    return bytes(header) + comp


def dcx_decode(path):
    d = Path(path).read_bytes()
    usize = struct.unpack_from('>I', d, 0x1C)[0]
    csize = struct.unpack_from('>I', d, 0x20)[0]
    payload = d[DCX_DATA:DCX_DATA + csize]
    if payload[:2] == b'\x78\xda':
        import zlib
        return zlib.decompress(payload)
    lib = _oodle()
    out = ctypes.create_string_buffer(usize)
    fn = lib.OodleLZ_Decompress
    fn.restype = ctypes.c_ssize_t
    got = fn(payload, csize, out, usize, 0, 0, 0, None, 0, None, None, None, 0, 3)
    if got != usize:
        raise RuntimeError(f'Oodle 解压失败 {got}/{usize}')
    return out.raw[:usize]


def main():
    romfs = Path(sys.argv[1])
    target = romfs / 'map' / 'mapstudio' / 'm80_00_00_00.msb.dcx'
    backup = target.with_suffix(target.suffix + '.orig')

    if len(sys.argv) > 2 and sys.argv[2] == 'restore':
        if backup.exists():
            shutil.copyfile(backup, target)
            print('已还原', target.name)
        else:
            print('没有备份')
        return

    raw = bytearray(Path(sys.argv[2]).read_bytes())
    if raw[:4] != b'MSB ':
        raise ValueError('不是 MSB 数据')
    if not backup.exists():
        shutil.copyfile(target, backup)
        print('备份 ->', backup.name)

    changed = []
    for n in range(7):
        old_name = f'c7030_{n:04d}'
        new_name = f'c2210_{n + 2:04d}'
        pos = raw.find(old_name.encode('utf-16-le'))
        if pos < 0:
            raise ValueError('找不到 ' + old_name)
        raw[pos:pos + len(old_name) * 2] = new_name.encode('utf-16-le')
        struct.pack_into('<I', raw, pos - 0xA4, MODEL_INDEX['c2210'])
        changed.append(f'{old_name}->{new_name}')

    packed = dcx_encode(raw)
    target.write_bytes(packed)
    print('改了', len(changed), '个:', ', '.join(changed))
    print('新 DCX', len(packed), 'bytes (Kraken); 回读校验:', len(dcx_decode(target)), 'bytes')


if __name__ == '__main__':
    main()