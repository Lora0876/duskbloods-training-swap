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
import shutil
import struct
import sys
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