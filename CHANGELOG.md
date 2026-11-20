# Changelog

## 1.0 — 2026-11-20

首个公开版本。

- 三个训练靶可换成任意敌人 / Boss / 眷属（共 27 个模型，含变体）
- 就地改 `m80_00_00_00.msb.dcx`：模型名 + think(AI) + npc + CharaInit
- 同时改菜单文本，靶子面板显示目标角色名
- 中英双语界面，英文使用游戏内官方叫法（`Graveyard Scarecrow` / `Adherent` / `Giant adherent` / `Kin` / `Bloodsworn`）
- 一键安装器：自动找 Python、装好文件、建桌面快捷方式
- 支持「还原原版」

### 未包含

- 不含 `oo2core_9_win64.dll`（Oodle 私有库，需用户自备）

### 修复

- Oodle 库不再写死别人的 Steam 路径：改成「环境变量 → 用户指定并记住 → 工具目录」三级查找，
  界面上新增 `指定 Oodle...` 按钮，缺库时点「应用」会弹窗询问并自动重试

- 缺 `oo2core_9_win64.dll` 时给出可读的中文提示，而不是 `WinError 126`
- 安装器写 `config.json` 使用无 BOM 的 UTF-8（带 BOM 会导致配置读取失败）