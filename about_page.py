# Author: Kerwin
"""The project's author, documentation and licensing page."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QFrame,
                              QPushButton,QDialog,QTextBrowser,QScrollArea)
from app_paths import RESOURCE_DIR
from app_info import (PROJECT_NAME,VERSION,AUTHOR,EMAIL,AUTHOR_BIO,AUTHOR_PROFILE,REPOSITORY,
                      LICENSE_NAME,COPYRIGHT)


def caption(text,kind='Subtle'):
    item=QLabel(text)
    item.setObjectName(kind)
    item.setWordWrap(True)
    item.setTextFormat(Qt.TextFormat.PlainText)
    return item


def show_document(parent,title,filename):
    dialog=QDialog(parent)
    dialog.setWindowTitle('浮词 · '+title)
    dialog.resize(780,580)
    layout=QVBoxLayout(dialog)
    browser=QTextBrowser()
    browser.setOpenExternalLinks(True)
    browser.document().setBaseUrl(QUrl.fromLocalFile(str(RESOURCE_DIR)+'/'))
    path=RESOURCE_DIR/filename
    try:
        content=path.read_text(encoding='utf-8')
    except OSError:
        content='文档未包含在当前副本中，请查看项目仓库：\n\n'+REPOSITORY
    if path.suffix=='.md':browser.setMarkdown(content)
    else:browser.setPlainText(content)
    layout.addWidget(browser)
    close=QPushButton('关闭')
    close.clicked.connect(dialog.accept)
    layout.addWidget(close,alignment=Qt.AlignmentFlag.AlignRight)
    dialog.exec()


def build_about_page(studio):
    scroll=QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    body=QWidget()
    layout=QVBoxLayout(body)
    layout.setContentsMargins(0,0,8,0)
    layout.setSpacing(14)
    hero=QFrame(objectName='Card')
    row=QHBoxLayout(hero)
    row.setContentsMargins(24,22,24,22)
    icon=QLabel()
    icon.setPixmap(QPixmap(str(RESOURCE_DIR/'assets/floating-lyrics.png')).scaled(
        88,88,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    row.addWidget(icon)
    text=QVBoxLayout()
    text.addWidget(caption(PROJECT_NAME,'Section'))
    text.addWidget(caption('透明桌面歌词，让每一句都有自己的样子。'))
    text.addWidget(caption('版本 '+VERSION+'   ·   Windows x64','Overline'))
    row.addLayout(text,1)
    layout.addWidget(hero)

    author=QFrame(objectName='Card')
    info=QVBoxLayout(author)
    info.setContentsMargins(24,18,24,18)
    info.addWidget(caption('作者 / AUTHOR','Overline'))
    author_link=QLabel('作者：<a href="'+AUTHOR_PROFILE+'" style="color:#6F56AB;text-decoration:none">'+AUTHOR+'</a>')
    author_link.setObjectName('Section')
    author_link.setOpenExternalLinks(True)
    author_link.setAccessibleName('作者 '+AUTHOR+' GitHub 主页')
    info.addWidget(author_link)
    info.addWidget(caption(AUTHOR_BIO))
    info.addWidget(caption(EMAIL))
    info.addWidget(caption('个人学习与创作项目；学校信息仅为作者简介。'))
    buttons=QHBoxLayout()
    for title,url in [('GitHub 仓库',REPOSITORY),('反馈问题',REPOSITORY+'/issues'),
                      ('联系作者','mailto:'+EMAIL),('部署教程',REPOSITORY+'/blob/main/docs/DEPLOYMENT.md')]:
        button=QPushButton(title)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda checked=False,u=url:QDesktopServices.openUrl(QUrl(u)))
        buttons.addWidget(button)
    info.addLayout(buttons)
    layout.addWidget(author)

    legal=QFrame(objectName='Card')
    content=QVBoxLayout(legal)
    content.setContentsMargins(24,18,24,18)
    content.addWidget(caption('源码与许可 / SOURCE & LICENSE','Overline'))
    content.addWidget(caption(LICENSE_NAME,'Section'))
    content.addWidget(caption('原创代码允许非商业学习、使用、修改和分享；须保留 Kerwin 署名、许可及修改说明。禁止商业利用、换壳销售和冒认原创。'))
    content.addWidget(caption('本项目属于附带非商业限制的源码公开项目，不是 OSI 定义的开源软件。第三方组件继续适用其各自许可。'))
    content.addWidget(caption('本程序使用 Qt / PySide6、Shiboken（LGPLv3）。用户保有第三方库许可赋予的修改、替换和相关调试权利。QRC 解码组件保留 GotKiCry / Brad Conte 的原作者说明。'))
    links=QHBoxLayout()
    for title,filename in [('项目许可','LICENSE'),('第三方许可','THIRD_PARTY_NOTICES.md'),('使用说明','README.md')]:
        button=QPushButton(title)
        button.clicked.connect(lambda checked=False,t=title,f=filename:show_document(studio,t,f))
        links.addWidget(button)
    content.addLayout(links)
    layout.addWidget(legal)
    layout.addWidget(caption('数据说明：读取本机播放信息与歌词缓存；需要时联网查询歌词。无账号登录，不上传播放日志。截图和动效演示使用原创示例文字。'))
    layout.addWidget(caption(COPYRIGHT,'Overline'))
    layout.addStretch()
    scroll.setWidget(body)
    return scroll
