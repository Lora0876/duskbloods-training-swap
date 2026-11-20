param([switch]$Test)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms | Out-Null
Add-Type -AssemblyName System.Drawing | Out-Null

# 安装目录由安装器通过环境变量传进来
$dir = $env:DUSK_INSTALL_DIR
if (-not $dir) { $dir = $PSScriptRoot }
$desktop = [Environment]::GetFolderPath('Desktop')
$stage = '准备'
function Set-Stage($n) { $script:stage = $n }

trap {
  $msg = "安装没有完成`n`n在第「$($script:stage)」步出问题了。`n`n$_`n`n如果反复失败，把这张截图发给作者就行。"
  Write-Host $msg -ForegroundColor Yellow
  if (-not $Test) {
    [System.Windows.Forms.MessageBox]::Show($msg, '训练场换怪 · 安装未完成', 'OK', 'Warning') | Out-Null
  }
  exit 1
}

function Say($m, $c = 'White') { Write-Host $m -ForegroundColor $c }

# ---------------------------------------------------------------- Python
function Test-Python($exe) {
  if (-not (Test-Path $exe)) { return $false }
  try {
    & $exe -c "import sys,tkinter;assert sys.version_info>=(3,10)" 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
  } catch { return $false }
}

function Find-Python {
  $cands = New-Object System.Collections.Generic.List[string]
  if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
      $out = & py -3 -c "import sys;print(sys.executable)" 2>$null
      if ($out) { $cands.Add(([string]$out).Trim()) }
    } catch {}
  }
  foreach ($n in @('python', 'python3')) {
    $c = Get-Command $n -ErrorAction SilentlyContinue
    if ($c -and $c.Source) { $cands.Add($c.Source) }
  }
  foreach ($pat in @("$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe",
                     "$env:ProgramFiles\Python3*\python.exe",
                     "C:\Python3*\python.exe")) {
    Get-ChildItem $pat -ErrorAction SilentlyContinue | ForEach-Object { $cands.Add($_.FullName) }
  }
  foreach ($exe in $cands) {
    if (-not (Test-Python $exe)) { continue }
    $pw = Join-Path (Split-Path $exe) 'pythonw.exe'
    if (Test-Path $pw) { return $pw }
    return $exe
  }
  return $null
}

Set-Stage 'Python'
Say '=== 训练场换怪工具 1.0 · 一键安装 ===' 'Yellow'
Say "  安装目录: $dir"

$python = Find-Python
if (-not $python) {
  $msg = "没有找到可用的 Python（需要 3.10 以上，且带 tkinter）。`n`n" +
         "请到 python.org 安装 Python 3.12（安装时勾选 tcl/tk），装完再运行一次本程序。`n`n" +
         "工具文件已经放好了，装好 Python 后双击桌面上的快捷方式即可。"
  Write-Host $msg -ForegroundColor Yellow
  if (-not $Test) {
    [System.Windows.Forms.MessageBox]::Show($msg, '训练场换怪 · 需要 Python', 'OK', 'Warning') | Out-Null
  }
} else {
  Say "  Python: $python" 'Green'
}

# ---------------------------------------------------------------- 配置：自动找游戏包
function Find-Game-Package {
  $markers = @('02-启动游戏.cmd', '02-单人模式.cmd', 'DuskbloodsCloud.exe', 'DuskbloodsSolo.exe')
  $roots = @((Join-Path $env:USERPROFILE 'Downloads'), (Join-Path $env:USERPROFILE 'Desktop'),
             (Join-Path $env:USERPROFILE 'Documents'), $env:USERPROFILE)
  foreach ($drive in @('C:', 'D:', 'E:', 'F:')) {
    if (Test-Path "$drive\") { $roots += "$drive\"; $roots += "$drive\Games" }
  }
  $best = $null; $bestScore = -1
  foreach ($r in $roots) {
    if (-not (Test-Path $r)) { continue }
    try { $dirs = Get-ChildItem -LiteralPath $r -Directory -Recurse -Depth 3 -ErrorAction SilentlyContinue }
    catch { continue }
    foreach ($d in $dirs) {
      $hit = $false
      foreach ($m in $markers) { if (Test-Path (Join-Path $d.FullName $m)) { $hit = $true; break } }
      if (-not $hit) { continue }
      $score = 0
      $settings = Join-Path $d.FullName 'local\settings.json'
      if (Test-Path $settings) {
        try {
          $j = Get-Content -LiteralPath $settings -Raw -Encoding UTF8 | ConvertFrom-Json
          if ($j.main -and (Test-Path $j.main)) { $score = 10 }
        } catch {}
      }
      if (Test-Path (Join-Path $d.FullName 'DuskbloodsCloud.exe')) { $score += 2 }
      if ($score -gt $bestScore) { $bestScore = $score; $best = $d.FullName }
    }
  }
  return $best
}

Set-Stage '查找游戏包'
$cfg = Join-Path $dir 'config.json'
$cloud = Find-Game-Package
if ($cloud) {
  Say "  游戏包: $cloud" 'Green'
  $obj = [ordered]@{ cloud_root = $cloud; _说明 = '自动检测写入；换了游戏包目录就删掉这一行让它重新探测' }
  [System.IO.File]::WriteAllText($cfg, ($obj | ConvertTo-Json), (New-Object System.Text.UTF8Encoding($false)))
} else {
  Say '  没有自动找到游戏包：工具打开后可以在「游戏版本」下拉里手动切，或重新扫描。' 'Yellow'
  $blank = '{"cloud_root": "", "_说明": "留空则自动探测；必要时填游戏包目录（含 DuskbloodsCloud.exe 的那层）"}'
  [System.IO.File]::WriteAllText($cfg, $blank, (New-Object System.Text.UTF8Encoding($false)))
}

# ---------------------------------------------------------------- 快捷方式（只有一个）
$shortcutName = if ((Split-Path $dir -Leaf) -eq 'DuskTrainingTool') { '训练场换怪工具.lnk' }
                else { '训练场换怪工具-1.0.lnk' }
if ($python -and -not $Test) {
  Set-Stage '创建快捷方式'
  $sh = New-Object -ComObject WScript.Shell
  $lnk = $sh.CreateShortcut((Join-Path $desktop $shortcutName))
  $lnk.TargetPath = $python
  $lnk.Arguments = '"' + (Join-Path $dir 'training_tool.py') + '"'
  $lnk.WorkingDirectory = $dir
  $lnk.IconLocation = "$python,0"
  $lnk.Description = '训练场换怪工具 1.0'
  $lnk.Save()
  Say "  桌面快捷方式: $shortcutName" 'Green'
}

# ---------------------------------------------------------------- 自检
Set-Stage '自检'
foreach ($rel in @('training_tool.py', 'catalog.json', 'tools\training_build.py',
                   'tools\detect.py', 'tools\paths.py', 'tools\patch_m80.py',
                   'tools\msb_inspect.py')) {
  if (-not (Test-Path (Join-Path $dir $rel))) { throw "缺少 $rel" }
}
$tool = Get-Content -LiteralPath (Join-Path $dir 'training_tool.py') -Raw -Encoding UTF8
if ($tool -notmatch "TOOL_VERSION = '1\.0'") { Say '  注意：装的不是 1.0' 'Yellow' }
if ($tool -match '_lock_panel') { throw '安装包版本不对：文件里含有不该出现的功能代码' }
if (-not (Test-Path (Join-Path $dir 'oo2core_9_win64.dll'))) { Say '  注意：缺少 oo2core_9_win64.dll（改怪会失败）' 'Yellow' }
Say '  自检通过' 'Green'

$done = "安装完成！`n`n  · 版本：1.0`n  · 目录：$dir`n  · 快捷方式：桌面「$shortcutName」`n`n" +
        "用法：选三个标靶 → 应用并启动 → 标题按 A → 大厅 Plus → 庭院 → A → 在面板里切标靶。"
Say $done 'Green'
if (-not $Test) {
  [System.Windows.Forms.MessageBox]::Show($done, '训练场换怪 · 安装完成', 'OK', 'Information') | Out-Null
}
exit 0