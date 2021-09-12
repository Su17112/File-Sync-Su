# 打包时采用 pyi-makespec -F -w --uac-admin --icon img/loading.ico File_Sync_Hidden.py -p SysTrayIcon.py
# 修改 datas=[('img','img')],
# 最后生成 pyinstaller -F -w --uac-admin File_Sync_Hidden.spec
import ctypes
import inspect
import threading
import tkinter as tk
from tkinter.ttk import Frame
import paramiko
import os
import sys
from PIL import Image, ImageTk, ImageSequence
import time
from winreg import *
from SysTrayIcon import SysTrayIcon


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):  # 是否Bundle Resource
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


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


class MainPage(object):
    def __init__(self, root):
        self.SysTrayIcon = None
        self.root = root
        self.root.geometry('%dx%d' % (580, 250))  # 设置窗口大小
        self.root.bind("<Unmap>",
                       lambda
                           event: self.Hidden_window() if self.root.state() == 'iconic' else False)  # 窗口最小化判断，可以说是调用最重要的一步
        self.root.protocol('WM_DELETE_WINDOW', self.exit)  # 点击Tk窗口关闭时直接调用s.exit，不使用默认关闭
        # 输入框配置
        self.page = Frame(self.root, padding=(5, 20, 10, 20))  # 创建Frame,左上右下
        self.page.pack()
        # 按钮配置
        self.buttonPage = Frame(self.root, padding=(10, 10, 10, 20))
        self.buttonPage.pack(side=tk.BOTTOM)
        # 读取注册表
        self.key = CreateKey(HKEY_LOCAL_MACHINE, r'SOFTWARE\\服务器同步软件')
        self.regDict = ReadReg(self.key)
        errorFlag = 0
        # ip输入
        tk.Label(self.page, text='IP         ：').grid(row=1, column=1)
        self.ipText = tk.Entry(self.page)
        self.ipText.grid(row=1, column=2)
        try:
            self.ipText.delete(0, tk.END)
            self.ipText.insert(0, self.regDict['ip'])
        except KeyError:
            errorFlag += 1
        tk.Label(self.page, text='    ').grid(row=1, column=3)
        # 端口输入
        tk.Label(self.page, text='端      口：').grid(row=1, column=4)
        self.portText = tk.Entry(self.page)
        self.portText.grid(row=1, column=5)
        try:
            self.portText.delete(0, tk.END)
            self.portText.insert(0, self.regDict['port'])
        except KeyError:
            errorFlag += 1
        # 空行
        tk.Label(self.page, text='    ').grid(row=2)
        # 用户名输入
        tk.Label(self.page, text='用 户 名 ：').grid(row=3, column=1)
        self.username = tk.Entry(self.page)
        self.username.grid(row=3, column=2)
        try:
            self.username.delete(0, tk.END)
            self.username.insert(0, self.regDict['user'])
        except KeyError:
            errorFlag += 1
        tk.Label(self.page, text='    ').grid(row=3, column=3)
        # 密码输入
        tk.Label(self.page, text='密      码：').grid(row=3, column=4)
        self.password = tk.Entry(self.page)
        self.password.grid(row=3, column=5)
        try:
            self.password.delete(0, tk.END)
            self.password.insert(0, self.regDict['pwd'])
        except KeyError:
            errorFlag += 1
        # 空行
        tk.Label(self.page, text='    ').grid(row=4)
        # 本地文件夹输入
        tk.Label(self.page, text='本地路径：').grid(row=5, column=1)
        self.localPath = tk.Entry(self.page, width=54)
        self.localPath.grid(row=5, column=2, columnspan=4)
        try:
            self.localPath.delete(0, tk.END)
            self.localPath.insert(0, self.regDict['lPath'])
        except KeyError:
            errorFlag += 1
        # 空行
        tk.Label(self.page, text='    ').grid(row=6)
        # 远程文件夹输入
        tk.Label(self.page, text='远端路径：').grid(row=7, column=1)
        self.remotePath = tk.Entry(self.page, width=54)
        self.remotePath.grid(row=7, column=2, columnspan=4)
        try:
            self.remotePath.delete(0, tk.END)
            self.remotePath.insert(0, self.regDict['rPath'])
        except KeyError:
            errorFlag += 1
        # 同步按钮
        self.startSyncButton = tk.Button(self.buttonPage, text='开始同步', command=self.startSyncFunction)
        self.startSyncButton.grid(row=1, column=0)
        tk.Label(self.buttonPage, text='                               ').grid(row=1, column=1)
        # 停止按钮
        self.stopSyncButton = tk.Button(self.buttonPage, text='停止同步', state='disabled', command=self.stopSyncFunction)
        self.stopSyncButton.grid(row=1, column=2)
        # 如果信息全，则执行上传
        if errorFlag == 0:
            self.startSyncFunction()
            self.Hidden_window()

    def startSyncFunction(self):
        ip, port = self.ipText.get(), self.portText.get()
        user, pwd = self.username.get(), self.password.get()
        lPath, rPath = self.localPath.get(), self.remotePath.get()
        pwd_input = pwd
        try:
            pwd = pwd.replace('*', '')
            if pwd == '':
                pwd = self.regDict['pwd']
        except KeyError:
            pwd = pwd_input
        self.startSyncButton.config(state='disabled')
        self.stopSyncButton.config(state='normal')
        self.ipText.config(state='disabled')
        self.portText.config(state='disabled')
        self.username.config(state='disabled')
        self.password.delete(0, tk.END)
        self.password.insert(0, '*' * len(pwd_input))
        self.password.config(state='disabled')
        self.localPath.config(state='disabled')
        self.remotePath.config(state='disabled')
        SetValueEx(self.key, 'ip', 0, REG_SZ, ip)
        SetValueEx(self.key, 'port', 0, REG_SZ, port)
        SetValueEx(self.key, 'user', 0, REG_SZ, user)
        SetValueEx(self.key, 'pwd', 0, REG_SZ, pwd)
        SetValueEx(self.key, 'lPath', 0, REG_SZ, lPath)
        SetValueEx(self.key, 'rPath', 0, REG_SZ, rPath)
        tk.Label(self.buttonPage, text='                               ').grid(row=1, column=1)
        # 转圈圈子线程
        self.T_loading = threading.Thread(target=self.loadingImg)
        # 上传子线程
        self.T_Upload = threading.Thread(target=self.UploadFile, args=(ip, int(port), user, pwd, lPath, rPath))
        # 子线程开始
        self.T_loading.start()
        self.T_Upload.start()

    def stopSyncFunction(self):
        stop_thread(self.T_Upload)
        stop_thread(self.T_loading)
        tk.Label(self.buttonPage, text='                               ').grid(row=1, column=1)
        self.stopSyncButton.config(state='disabled')
        self.startSyncButton.config(state='normal')
        self.ipText.config(state='normal')
        self.portText.config(state='normal')
        self.username.config(state='normal')
        self.password.config(state='normal')
        self.localPath.config(state='normal')
        self.remotePath.config(state='normal')

    def loadingImg(self):  # 转圈圈函数
        while 1:
            img = Image.open(resource_path(os.path.join("img", "loading.gif")))  # 打开图片
            iter = ImageSequence.Iterator(img)  # 分割成帧
            for frame in iter:  # 每个frame是1帧
                frame = frame.convert('RGBA')
                frame = frame.resize((25, 25), Image.ANTIALIAS)
                pic = ImageTk.PhotoImage(frame)  # 转换成TK格式
                tk.Label(self.buttonPage, image=pic).grid(row=1, column=1)
                time.sleep(0.2)
                self.root.update_idletasks()
                self.root.update()

    def UploadFile(self, host_ip, host_port, host_username, host_password, local_path, remote_path):  # 上传函数
        while 1:
            time.sleep(1)
            try:
                if (time.localtime().tm_min) % 5 == 0:
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
            except:
                tk.Label(self.buttonPage, text='信息错误请检查！！！', fg='red').grid(row=1, column=1)
                # 结束转圈圈线程
                stop_thread(self.T_loading)
                break

    def recursiveUpload(self, sftp, localPath, remotePath):  # 递归上传，供上传函数调用
        for root, paths, files in os.walk(localPath):  # 遍历读取目录里的所有文件
            remote_files = sftp.listdir(remotePath)  # 获取远端服务器路径内所有文件名
            for file in files:
                if file not in remote_files:
                    print('正在上传', remotePath + '/' + file)
                    sftp.put(os.path.join(root, file), remotePath + '/' + file)
            for path in paths:
                if path not in remote_files:
                    print('创建文件夹', remotePath + '/' + path)
                    sftp.mkdir(remotePath + '/' + path)
                self.recursiveUpload(sftp, os.path.join(localPath, path), remotePath + '/' + path)
            break

    # def DownloadFile(self, host_ip, host_port, host_username, host_password, local_path, remote_path):
    #     scp = paramiko.Transport((host_ip, host_port))
    #     scp.connect(username=host_username, password=host_password)
    #     sftp = paramiko.SFTPClient.from_transport(scp)
    #     try:
    #         remote_files = sftp.listdir(remote_path)
    #         for file in remote_files:  # 遍历读取远程目录里的所有文件
    #             print(file)
    #             time.sleep(1)
    #             # local_file = local_path + file
    #             # remote_file = remote_path + file
    #             # sftp.get(remote_file, local_file)
    #     except IOError:  # 如果目录不存在则抛出异常
    #         return ("remote_path or local_path is not exist")
    #     scp.close()
    # 以下是菜单功能
    def show_msg(self, title='标题', msg='内容', time=5):
        self.SysTrayIcon.refresh(title=title, msg=msg, time=time)

    def use_startSyncFunc(self, _sysTrayIcon, icon=resource_path(os.path.join("img", "loading.ico"))):
        # 此函数调用开始同步函数
        self.startSyncFunction()
        _sysTrayIcon.icon = icon
        _sysTrayIcon.refresh()
        # 气泡提示的例子
        self.show_msg(title='开始同步', msg='开始同步！', time=5)

    def use_stopSyncFunc(self, _sysTrayIcon, icon=resource_path(os.path.join("img", "loading.ico"))):
        # 此函数调用停止同步函数
        self.stopSyncFunction()
        _sysTrayIcon.icon = icon
        _sysTrayIcon.refresh()
        # 气泡提示的例子
        self.show_msg(title='停止同步', msg='停止同步！', time=5)

    def Hidden_window(self, icon=resource_path(os.path.join("img", "loading.ico")), hover_text="服务器同步软件"):
        '''隐藏窗口至托盘区，调用SysTrayIcon的重要函数'''

        # 托盘图标右键菜单, 格式: ('name', None, callback),下面也是二级菜单的例子
        # 24行有自动添加‘退出’，不需要的可删除
        menu_options = (('开始同步', None, self.use_startSyncFunc),
                        ('停止同步', None, self.use_stopSyncFunc))

        self.root.withdraw()  # 隐藏tk窗口
        if not self.SysTrayIcon:
            self.SysTrayIcon = SysTrayIcon(
                icon,  # 图标
                hover_text,  # 光标停留显示文字
                menu_options,  # 右键菜单
                on_quit=self.exit,  # 退出调用
                tk_window=self.root,  # Tk窗口
            )
        self.SysTrayIcon.activation()

    def exit(self, _sysTrayIcon=None):
        self.root.destroy()
        print('exit...')


root = tk.Tk()
root.iconbitmap(resource_path(os.path.join("img", "loading.ico")))
root.title('服务器同步软件')
MainPage(root)
root.mainloop()
