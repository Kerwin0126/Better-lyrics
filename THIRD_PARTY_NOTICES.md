# 第三方组件与许可

原创部分作者：**Kerwin**。根目录非商业许可仅适用于本项目有权按该许可授权的原创部分，不改变第三方代码的版权、许可和署名。

## Qt / PySide6 / Shiboken

使用 PySide6 Essentials 6.12.0、Shiboken6 6.12.0 和 Qt 6.12.0，选择可用的 LGPLv3 路径。实际应用包含 Qt Core、Gui、Widgets、Network、Svg。

- [Qt for Python 许可](https://doc.qt.io/qtforpython-6/licenses.html)
- [Qt LGPL 义务](https://www.qt.io/development/open-source-lgpl-obligations)
- 完整许可与上游第三方声明：[`third_party/licenses/`](third_party/licenses/)。
- 对应源码：[PySide / Shiboken](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz)、[Qt Base](https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtbase-everywhere-src-6.12.0.tar.xz)、[Qt Svg](https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/qtsvg-everywhere-src-6.12.0.tar.xz)。
- 构建入口：[Qt](https://doc.qt.io/qt-6/build-sources.html)、[Qt for Python](https://doc.qt.io/qtforpython-6/building_from_source/index.html)。

发行包的动态库目录保持独立，允许按上游许可修改、替换 LGPL 库，并为调试这些修改进行必要的逆向工程；没有阻止库替换的完整性校验。非商业限制不覆盖第三方库本身的上游权利。

二进制发行同时提供对应版本源码的获取入口。上游归档来自官方分发站，发布工具保留归档、校验值和许可清单。

## QRC 兼容 DES

`third_party/qq_des` 来自 [GotKiCry/QQMusicMonitor](https://github.com/GotKiCry/QQMusicMonitor/tree/main/src-tauri/src/qq_des)，采用 MIT，基于 Brad Conte 的 DES 实现。保留原版权、作者及源文件头，见 [完整许可](third_party/qq_des/LICENSE)。Kerwin 编写的是 `qrc_decode.c` 桥接，不是这些上游代码。

## Python 与运行依赖

本机二进制使用 Python 3.14.7，遵循 Python Software Foundation 及附带许可。Python、OpenSSL、libffi 等实际包含组件的许可位于 `third_party/licenses`，由构建工具依据环境收集。

[Python 许可](https://docs.python.org/3/license.html) · [OpenSSL 许可](https://openssl-library.org/source/license/)。

## 构建及安装工具

PyInstaller 按其 GPL 和 bootloader 分发例外使用；该例外允许生成采用其他许可的程序。[说明](https://pyinstaller.org/en/stable/license.html)。

安装程序使用 Inno Setup，工具许可随构建收集。[项目](https://jrsoftware.org/isinfo.php)。

简体中文安装向导翻译来自 Inno Setup 官方仓库的 `Files/Languages/ChineseSimplified.isl`，维护者 Zhenghan Yang (Kira)；保留文件中的原作者与来源信息。应用原创代码的 Kerwin 署名不覆盖该翻译。

Microsoft Visual C++ 运行库仅按其可再发行清单分发，适用 Microsoft 许可，不是 Kerwin 原创代码。[分发说明](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files)。

## 内容及边界

Windows 字体由系统提供，不分发字体文件。歌曲、歌词和音乐音频属于其权利人；本仓库不附带播放器缓存或音乐音频，展示使用原创示例文字。

免费不等于无需遵守第三方许可。本项目保留声明、提供对应版本源码入口及库替换机制。许可咨询：<kerwin126@foxmail.com>。
