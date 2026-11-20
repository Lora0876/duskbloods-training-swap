# Changelog

## 1.2 — 2026-11-20

- **自动搜索 oo2core**：打开工具就自己在后台找 `oo2core_9_win64.dll`——先查注册表里的 Steam 库与 `libraryfolders.vdf`，
  再扫 Epic / Xbox / 各盘 SteamLibrary / Games，最后兜底扫用户的 Downloads、Desktop；命中 FromSoftware 游戏目录优先。
  找到就自动记住并提示，**不用用户手动选**；找不到才提示手动指定
- 搜索跑在后台线程（带 12 秒预算），不卡界面

## 1.1 — 2026-11-20

- **首次打开就提示**：缺 `oo2core_9_win64.dll` 时状态栏直接告诉你怎么补，不用等点「应用」才报错
- **游戏包可以自己选**：版本行新增「选择游戏包...」，选到含 `DuskbloodsCloud.exe` / `local\settings.json` 的文件夹即可，会记住
- 快捷方式名固定 `训练场换怪工具.lnk`（不再带版本后缀）
- 打包脚本跟 `TOOL_VERSION` 走，改版本号不用再手改多处

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