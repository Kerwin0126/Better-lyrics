# 源码部署、运行与打包

作者：**Kerwin** · <kerwin126@foxmail.com>

这是 Windows 桌面程序。“部署”指从源码运行、生成应用目录，以及制作可选安装位置的单文件安装程序，不需要服务器。

## 1. 准备环境

本机验证：Windows 11 x64、Python 3.14 x64、PySide6 Essentials 6.12.0、MSVC 14.51、Windows SDK 10.0.26100、.NET Framework 4.x。其他组合未逐一验证。

需要安装：

1. [Python for Windows](https://www.python.org/downloads/windows/)，推荐 3.14 **64 位**。
2. [Git for Windows](https://git-scm.com/downloads/win)，或用 GitHub 的 Code → Download ZIP。
3. [C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)，选择“使用 C++ 的桌面开发”，包含 x64 MSVC 和 Windows 10 / 11 SDK。脚本通过 `vswhere.exe` 定位编译器。
4. Windows .NET Framework 4.x 的 C# 编译器；不需要 .NET 3.5。
5. 仅制作安装包时需要 [Inno Setup 6](https://jrsoftware.org/isdl.php)。

这些是开发机依赖，普通安装版用户不需要安装 Python、Qt 或编译器。

## 2. 获取源码与 Python 依赖

打开 Windows PowerShell：

```powershell
git clone https://github.com/Kerwin0126/Better-lyrics.git
cd Better-lyrics
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
```

直接调用虚拟环境的 Python 即可，不必执行 `Activate.ps1`。

## 3. 编译读取器及原生组件

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_reader.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_backdrop.ps1
```

| 输出 | 功能 |
| --- | --- |
| `PlaybackReader.exe` | 酷狗 / 网易云 MSAA 读取 |
| `MediaReader.exe` | 系统媒体会话与进程状态 |
| `RoundedBackdrop.dll` | Windows 磨砂与圆角 |
| `QrcDecode.dll` | QQ 本地 QRC 解码桥接 |

找不到 C++ 编译器或 SDK 时，请补装工作负载；不要改成作者电脑上的绝对路径。

## 4. 运行

```powershell
.\.venv\Scripts\python.exe desktop_lyrics.py
```

用 `.venv\Scripts\pythonw.exe` 可不显示终端。打开音乐播放器并播放，随后在顶部选择来源。检测到进程不等于已经取得有效进度；QQ / 汽水通常需先建立媒体会话，网易云另有原生窗口回退。

## 5. 生成可携带的 EXE 应用目录

先从托盘退出浮词：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1
```

脚本编译原生组件、整理许可与运行依赖、生成图标，再使用 PyInstaller 打包。构建依赖和上游许可／源码的准备可能需要联网；普通用户安装时不需要通过 pip 下载环境。

输出为 `浮词.exe` 和 `_internal`，两者必须一起保留。要跳过构建机桌面快捷方式：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1 -SkipDesktopShortcut
```

## 6. 生成单个安装 EXE

先成功构建应用，再运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_installer.ps1
```

可用 `-CompilerPath` 指定自定义位置的 `ISCC.exe`。版本来自 `app_info.py`。

输出在 `.release`：`BetterLyrics-Setup-版本号-x64.exe`。用户下载这一个文件，可选择安装位置、快捷方式，并通过系统应用列表卸载。安装程序内包含完整应用、Python、Qt 及所需运行库，不在安装期间联网下载 Python 或 Qt。

安装版和解压版的数据位置不同，见 [数据说明](PRIVACY.md)。不要把开发机的 `appearance.json`、歌词缓存、播放日志打入安装包。

## 7. 回归检查

以下检查不要求四个播放器同时打开：

```powershell
.\.venv\Scripts\python.exe verify_timeline.py
.\.venv\Scripts\python.exe verify_resilience.py
.\.venv\Scripts\python.exe verify_multi_player.py
.\.venv\Scripts\python.exe verify_advanced.py
.\.venv\Scripts\python.exe verify_fixes.py
.\.venv\Scripts\python.exe verify_effects.py
.\.venv\Scripts\python.exe verify_paths.py
```

时间轴回归模拟两分钟 / 7200 帧及暂停、继续、跳转、旧样本拒绝。模拟检查不能替代真实播放器验证。实测需覆盖启动恢复来源、播放／暂停／继续、切歌、前后拖动、首页和后台，并记录系统及播放器版本。

## 8. 文档截图与 GIF

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-docs.txt
.\.venv\Scripts\python.exe tools\make_gallery.py
```

展示使用实际界面／渲染器、原创演示文字和隔离设置，不接入音乐播放器、不改日常外观。原生磨砂需要在 Windows 运行展示场景后截图；命令见脚本帮助。

## 9. 发布

- 保持 `app_info.py`、Windows 版本资源与安装包版本一致。
- Git 提交源码、教程、原创演示图和许可；运行目录与大体积安装包放 Releases。
- 排除个人路径、歌词缓存、日志和本机设置。
- 随二进制提供许可、第三方声明及对应版本源码的实际获取入口。
- Qt 动态库保持独立、可替换；不加入阻止 LGPL 库替换的完整性限制。
- 没有在干净 Windows 环境测试时，不宣称已在全新系统验证。

## 常见问题

**缺少 `windowsapp.lib` / `winrt/...` / `CoreMessaging.lib`**：补装完整 Windows SDK，选择 x64 工具链。

**EXE / DLL 被占用**：退出浮词和本项目的调试读取器，不要结束音乐播放器或其他无关进程。

**Qt ICU 入口点错误**：保留 spec 中的 ICU 排除处理，完整替换运行目录，不混入另一套 Python / Qt DLL。

**安装后设置无法保存**：安装版应在当前用户数据目录写入，而非要求用户写入 Program Files；检查安装标识与数据目录逻辑。

**未知发布者提示**：项目目前没有代码签名证书。请从项目仓库下载并核对发布哈希，不要关闭系统防护或绕过安全拦截。
