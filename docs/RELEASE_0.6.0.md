# Better lyrics | 浮词 v0.6.0

作者：[kerwin](https://github.com/Kerwin0126)  
@ KUST (Kunming University of Science and Technology)

Windows x64 开发预览版。

## 下载哪个文件

普通用户只需下载 **`BetterLyrics-Setup-0.6.0-x64.exe`**。

安装包支持选择目录、桌面与开始菜单快捷方式、正常卸载；包含 Python、Qt、MSVC 应用本地运行库，不需要预先安装 Python / Qt。安装后会展开运行文件；“一个安装 EXE”不意味着安装后没有文件目录。

同页的三个 `.tar.xz` 是对应版本的 Qt / PySide / Shiboken 上游源码，供依赖许可、修改库或构建用途；普通使用者无需下载。`SHA256SUMS.txt` 用于校验发布文件。

## 这一版包含

- 双行与多行歌词，逐字配色、四向透视、柔和放大、字词波浪和圆角磨砂。
- 酷狗、QQ、汽水、网易云四个来源。各客户端的适配成熟度与接口限制详见 README。
- 汽水稀疏时间锚点的连续时钟，修复 3 秒后回跳停住的逻辑。
- 网易云无系统媒体会话时的原生窗口歌曲识别及进度读取。
- 启动自动恢复保存的来源。
- 关于页：作者 GitHub 主页、学校独立行、邮箱、反馈、教程与许可。
- 安装版用户数据独立保存在 `%LOCALAPPDATA%\BetterLyrics`。
- 含静态效果图、GIF 与完整源码部署／打包教程的 README。

## 验证范围

在开发机 Windows 11 x64 验证了中文与空格安装路径、安装及卸载、保留用户数据、移除 Python PATH 后启动、应用从自身目录加载 Python / Qt / MSVC，以及来源恢复和现有回归检查。

没有宣称已在全新 Windows 虚拟机或所有播放器版本测试。安装包当前没有代码签名证书；请从官方仓库下载并核对校验值，不要关闭系统防护。

## 许可

原创部分采用 **Kerwin 非商业署名许可 1.0**：允许非商业学习、使用、修改与分享；须保留作者与修改说明，禁止冒认原创或未经授权商业利用。它是附带非商业限制的源码公开许可，不属于 OSI 定义的开源许可。

第三方组件遵循各自许可；Qt / LGPL 权利不被本项目条款限制。完整说明见仓库 LICENSE 和 THIRD_PARTY_NOTICES.md。

联系：<kerwin126@foxmail.com>
