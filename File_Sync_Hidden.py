# 打包时采用 pyi-makespec -F -w --uac-admin --icon img/loading.ico main.py -n 服务器同步软件.exe
# 修改 datas=[('img','img')],
# 最后生成 pyinstaller 服务器同步软件.exe.spec
import ctypes
import inspect
from os import system, walk
from os.path import realpath, abspath, join
from threading import Thread
from time import sleep, localtime
from winreg import EnumValue, CreateKey, HKEY_LOCAL_MACHINE, SetValueEx, REG_SZ

import paramiko
from PyQt5.QtCore import QCoreApplication, QSize
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import QMainWindow, QApplication, QSystemTrayIcon, QAction, QMenu

from MainWindow import Ui_MainWindow


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):  # 是否Bundle Resource
        base_path = sys._MEIPASS
    else:
        base_path = abspath(".")
    return join(base_path, relative_path)


def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):  # 停止线程
    try:
        _async_raise(thread.ident, SystemExit)
    except ValueError:
        pass


def ReadReg(key):  # 读取对应key的注册表值，返回字典
    regDict = {}
    try:
        i = 0
        while 1:
            # EnumValue方法用来枚举键值，EnumKey用来枚举子键
            name, value, type = EnumValue(key, i)
            regDict[name] = value
            i += 1
    except WindowsError:
        pass
    return regDict


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)  # 传入QtWidgets.QMainWindow子类(MyWindow)对象
        # 加载图片
        self.gif = QMovie(resource_path(join("img", "loading.gif")))
        self.gif.setScaledSize(QSize(30, 30))
        self.loading.setMovie(self.gif)
        self.ico = resource_path(join("img", "loading.ico"))
        self.setWindowIcon(QIcon(self.ico))
        # 初始化托盘
        self.initTrayIcon()
        self.trayIcon.show()
        # 绑定按钮功能
        self.actionboot.triggered.connect(self.AutoRun)  # 自启动
        self.btn_start.clicked.connect(self.startSyncFunction)
        self.btn_stop.clicked.connect(self.stopSyncFunction)
        self.btn_stop.setEnabled(False)
        # 读取注册表
        self.key = CreateKey(HKEY_LOCAL_MACHINE, r'SOFTWARE\\服务器同步软件')
        self.regDict = ReadReg(self.key)
        self.notError = True
        try:
            self.lineEdit_ip.clear()
            self.lineEdit_ip.setText(self.regDict['ip'])
            self.lineEdit_port.clear()
            self.lineEdit_port.setText(self.regDict['port'])
            self.lineEdit_username.clear()
            self.lineEdit_username.setText(self.regDict['user'])
            self.lineEdit_password.clear()
            self.lineEdit_password.setText(self.regDict['pwd'])
            self.lineEdit_localpath.clear()
            self.lineEdit_localpath.setText(self.regDict['lPath'])
            self.lineEdit_remotepath.clear()
            self.lineEdit_remotepath.setText(self.regDict['rPath'])
        except KeyError:
            self.notError = False

    def initTrayIcon(self):
        def open():
            self.showNormal()

        def quit():
            QCoreApplication.quit()

        def iconActivated(reason):
            if reason in (QSystemTrayIcon.DoubleClick,):
                open()

        startAction = QAction("开始同步", self)
        startAction.triggered.connect(self.startSyncFunction)
        stopAction = QAction("停止同步", self)
        stopAction.triggered.connect(self.stopSyncFunction)
        openAction = QAction("打开", self)
        openAction.setIcon(QIcon.fromTheme("media-record"))
        openAction.triggered.connect(open)
        quitAction = QAction("退出", self)
        quitAction.setIcon(QIcon.fromTheme("application-exit"))  # 从系统主题获取图标
        quitAction.triggered.connect(quit)

        menu = QMenu(self)
        menu.addAction(startAction)
        menu.addAction(stopAction)
        menu.addSeparator()
        menu.addAction(openAction)
        menu.addAction(quitAction)

        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setIcon(QIcon(self.ico))
        self.trayIcon.setToolTip("服务器同步软件")
        self.trayIcon.setContextMenu(menu)
        self.trayIcon.messageClicked.connect(open)
        self.trayIcon.activated.connect(iconActivated)

    def closeEvent(self, event):
        if self.trayIcon.isVisible():
            self.showMessage('File Sync', '程序已托盘运行')

    def showMessage(self, title, content):
        self.trayIcon.showMessage(title, content, QSystemTrayIcon.Information, 1000)

    def startSyncFunction(self):
        self.showMessage('File Sync', '开始同步')
        ip, port = self.lineEdit_ip.text(), self.lineEdit_port.text()
        user, pwd = self.lineEdit_username.text(), self.lineEdit_password.text()
        lPath, rPath = self.lineEdit_localpath.text(), self.lineEdit_remotepath.text()
        pwd_input = pwd
        try:
            pwd = pwd.replace('*', '')
            if pwd == '':
                pwd = self.regDict['pwd']
        except KeyError:
            pwd = pwd_input
        # 写入注册表
        SetValueEx(self.key, 'ip', 0, REG_SZ, ip)
        SetValueEx(self.key, 'port', 0, REG_SZ, port)
        SetValueEx(self.key, 'user', 0, REG_SZ, user)
        SetValueEx(self.key, 'pwd', 0, REG_SZ, pwd)
        SetValueEx(self.key, 'lPath', 0, REG_SZ, lPath)
        SetValueEx(self.key, 'rPath', 0, REG_SZ, rPath)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lineEdit_ip.setEnabled(False)
        self.lineEdit_port.setEnabled(False)
        self.lineEdit_username.setEnabled(False)
        self.lineEdit_password.clear()
        self.lineEdit_password.setText('*' * len(pwd_input))
        self.lineEdit_password.setEnabled(False)
        self.lineEdit_localpath.setEnabled(False)
        self.lineEdit_remotepath.setEnabled(False)
        self.loading.setVisible(True)
        self.gif.start()

        self.T_Upload = Thread(target=self.UploadFile, args=(ip, int(port), user, pwd, lPath, rPath))
        self.T_Upload.setDaemon(True)
        self.T_Upload.start()

    def stopSyncFunction(self):
        self.showMessage('File Sync', '停止同步')
        stop_thread(self.T_Upload)

        self.gif.stop()
        self.loading.setVisible(False)
        self.btn_stop.setEnabled(False)
        self.btn_start.setEnabled(True)
        self.lineEdit_ip.setEnabled(True)
        self.lineEdit_port.setEnabled(True)
        self.lineEdit_username.setEnabled(True)
        self.lineEdit_password.setEnabled(True)
        self.lineEdit_localpath.setEnabled(True)
        self.lineEdit_remotepath.setEnabled(True)

    def UploadFile(self, host_ip, host_port, host_username, host_password, local_path, remote_path):  # 上传函数
        while 1:
            sleep(1)
            try:
                if (localtime().tm_min) % 5 == 0:
                    scp = paramiko.Transport((host_ip, host_port))
                    scp.connect(username=host_username, password=host_password)
                    sftp = paramiko.SFTPClient.from_transport(scp)
                    self.recursiveUpload(sftp, local_path, remote_path)
                    try:
                        # linux给出chmod权限供filerun操作
                        client = paramiko.SSHClient()
                        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        client.connect(host_ip, host_port, host_username, host_password)
                        client.exec_command('chmod 777 -R ' + remote_path)
                        client.close()
                    except:
                        pass
                    scp.close()
            except Exception as e:
                print(e)
                self.loading.setText('信息错误请检查！！！')

    def recursiveUpload(self, sftp, localPath, remotePath):  # 递归上传，供上传函数调用
        for root, paths, files in walk(localPath):  # 遍历读取目录里的所有文件
            remote_files = sftp.listdir(remotePath)  # 获取远端服务器路径内所有文件名
            for file in files:
                if file not in remote_files:
                    print('正在上传', remotePath + '/' + file)
                    sftp.put(join(root, file), remotePath + '/' + file)
            for path in paths:
                if path not in remote_files:
                    print('创建文件夹', remotePath + '/' + path)
                    sftp.mkdir(remotePath + '/' + path)
                self.recursiveUpload(sftp, join(localPath, path), remotePath + '/' + path)
            break

    def AutoRun(self):  # 自启动函数
        try:
            exePath = realpath(sys.executable)
            AutoRunCommand = r'echo y | SCHTASKS /CREATE /TN "FileSync\FileSync" /TR "{}" /SC ONLOGON /DELAY 0000:30 /RL HIGHEST'.format(exePath)
            system(AutoRunCommand)
            self.showMessage('开机自启动', '设置成功')
        except:
            self.showMessage('开机自启动', '设置失败，请手动创建任务计划')


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    QApplication.setQuitOnLastWindowClosed(False)  # 关闭最后一个窗口不退出程序

    mw = MainWindow()
    # 如果信息全，则执行上传
    if mw.notError:
        if mw.trayIcon.isVisible():
            mw.showMessage('File Sync', '程序已托盘运行')
        mw.startSyncFunction()
    else:
        mw.show()

    sys.exit(app.exec_())
