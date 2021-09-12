本人手里面有一个安装 FileRun 的 Linux 服务器，其中有一个文件夹存放的内容与本人电脑中一个文件夹相同，每次有文件增添时都要手动上传，FileRun 提供的软件只能在 https 域名上使用，而我的是 http ，所以闲着没事自己写了个同步的软件。

软件自动记录上次配置信息（写入注册表），可以托盘运行（上传使用的是额外线程，不会阻塞），支持开机自启（使用 os.system 操作 SchTasks）。

目前开机自启需要手动创建任务计划，后面考虑增加设置。

## 1. 主要使用的库
		Tkinter
		paramiko(需要安装pycrytodome)
		winreg
		thread
		pillow
## 2. 文件上传部分（paramiko）
```python
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
```
这部分代码参考了此博客
> [Python通过paramiko复制远程文件及文件目录到本地——作者：森林番茄](https://blog.csdn.net/fangfu123/article/details/83859204)

上面代码中，前三行是创建了一个sftp对象，使用该对象进行文件操作。
**recursiveUpload** 函数用于递归上传，主要作用是将子目录和其中文件也上传到服务器。
接下来的代码是赋予上传的文件 777 权限，因为不给权限的话在 FileRun 中不能操作，try 部分代码如不需要可删除。

**recursiveUpload** 函数如下

```python
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
```
## 3. GUI 部分（Tkinter）
界面如图

![在这里插入图片描述](https://img-blog.csdnimg.cn/18fe018e2b56484d85279695dae13467.png?#pic_centerx-oss-process=image/watermark,type_ZHJvaWRzYW5zZmFsbGJhY2s,shadow_50,text_Q1NETiBAQOiLj-S4tg==,size_20,color_FFFFFF,t_70,g_se,x_16)

GUI 部分主要使用了 **pack** 布局，代码如下，通过类的实例化操作来实现。

```python
def __init__(self, root):
    self.root = root
    self.root.geometry('%dx%d' % (580, 250))  # 设置窗口大小
    # 输入框配置
    self.page = Frame(self.root, padding=(5, 20, 10, 20))  # 创建Frame,左上右下
    self.page.pack()
    # 按钮配置
    self.buttonPage = Frame(self.root, padding=(10, 10, 10, 20))
    self.buttonPage.pack(side=tk.BOTTOM)
    # ip输入
    tk.Label(self.page, text='IP         ：').grid(row=1, column=1)
    self.ipText = tk.Entry(self.page)
    self.ipText.grid(row=1, column=2)
    tk.Label(self.page, text='    ').grid(row=1, column=3)
    # 端口输入
    tk.Label(self.page, text='端      口：').grid(row=1, column=4)
    self.portText = tk.Entry(self.page)
    self.portText.grid(row=1, column=5)
    # 空行
    tk.Label(self.page, text='    ').grid(row=2)
    # 用户名输入
    tk.Label(self.page, text='用 户 名 ：').grid(row=3, column=1)
    self.username = tk.Entry(self.page)
    self.username.grid(row=3, column=2)
    tk.Label(self.page, text='    ').grid(row=3, column=3)
    # 密码输入
    tk.Label(self.page, text='密      码：').grid(row=3, column=4)
    self.password = tk.Entry(self.page)
    self.password.grid(row=3, column=5)
    # 空行
    tk.Label(self.page, text='    ').grid(row=4)
    # 本地文件夹输入
    tk.Label(self.page, text='本地路径：').grid(row=5, column=1)
    self.localPath = tk.Entry(self.page, width=54)
    self.localPath.grid(row=5, column=2, columnspan=4)
    # 空行
    tk.Label(self.page, text='    ').grid(row=6)
    # 远程文件夹输入
    tk.Label(self.page, text='远端路径：').grid(row=7, column=1)
    self.remotePath = tk.Entry(self.page, width=54)
    self.remotePath.grid(row=7, column=2, columnspan=4)
    # 同步按钮
    self.startSyncButton = tk.Button(self.buttonPage, text='开始同步', command=self.startSyncFunction)
    self.startSyncButton.grid(row=1, column=0)
    tk.Label(self.buttonPage, text='                               ').grid(row=1, column=1)
    # 停止按钮
    self.stopSyncButton = tk.Button(self.buttonPage, text='停止同步', state='disabled', command=self.stopSyncFunction)
    self.stopSyncButton.grid(row=1, column=2)
```
其中 **startSyncButton** 响应开始同步按钮，主要作用是启动上传文件线程，**stopSyncButton** 响应停止同步按钮，主要作用是强制停止上传文件线程。

**startSyncButton**函数如下

```python
def startSyncFunction(self):
    ip, port = self.ipText.get(), self.portText.get()
    user, pwd = self.username.get(), self.password.get()
    lPath, rPath = self.localPath.get(), self.remotePath.get()
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
    tk.Label(self.buttonPage, text='                               ').grid(row=1, column=1)
    # 转圈圈子线程
    self.T_loading = threading.Thread(target=self.loadingImg)
    # 上传子线程
    self.T_Upload = threading.Thread(target=self.UploadFile, args=(ip, int(port), user, pwd, lPath, rPath))
    # 子线程开始
    self.T_loading.start()
    self.T_Upload.start()
```
**stopSyncButton** 代码如下

```python
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
```
其中 **stop_thread** 用于停止线程，代码如下

```python
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
```
这部分代码参考了此博客
> [强行停止python子线程最佳方案——作者：熊彬彬](https://blog.csdn.net/A18373279153/article/details/80050177)

## 4. 配置信息写入注册表（winreg）
使用 **winreg** 读写注册表，每次点击开始同步时，向注册表中写入 ip、port、username、password 等信息，每次启动时自动读取注册表信息，如果信息完全，则直接开始同步。

写入代码如下

```python
SetValueEx(self.key, 'ip', 0, REG_SZ, ip)
SetValueEx(self.key, 'port', 0, REG_SZ, port)
SetValueEx(self.key, 'user', 0, REG_SZ, user)
SetValueEx(self.key, 'pwd', 0, REG_SZ, pwd)
SetValueEx(self.key, 'lPath', 0, REG_SZ, lPath)
SetValueEx(self.key, 'rPath', 0, REG_SZ, rPath)
```
读取代码如下
```python
self.key = CreateKey(HKEY_LOCAL_MACHINE, r'SOFTWARE\\服务器同步软件')
self.regDict = ReadReg(self.key)
```
其中 **ReadReg** 函数为读取 key 中所有的注册表项，并返回一个字典。代码如下

```python
def ReadReg(key):
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
```
## 5. 程序最小化至托盘（SysTrayIcon）
Tkinter 没有原生托盘代码，因此参考了相关博客，使用了 win32api 等一些库实现程序托盘，并添加了右键菜单和弹窗提示。

使用的托盘类代码如下
```python
import win32api, win32con, win32gui_struct, win32gui, os


class SysTrayIcon(object):
    '''SysTrayIcon类用于显示任务栏图标'''
    QUIT = 'QUIT'
    SPECIAL_ACTIONS = [QUIT]
    FIRST_ID = 5320

    def __init__(s, icon, hover_text, menu_options, on_quit, tk_window=None, default_menu_index=None,
                 window_class_name=None):
        '''
        icon         需要显示的图标文件路径
        hover_text   鼠标停留在图标上方时显示的文字
        menu_options 右键菜单，格式: (('a', None, callback), ('b', None, (('b1', None, callback),)))
        on_quit      传递退出函数，在执行退出时一并运行
        tk_window    传递Tk窗口，s.root，用于单击图标显示窗口
        default_menu_index 不显示的右键菜单序号
        window_class_name  窗口类名
        '''
        s.icon = icon
        s.hover_text = hover_text
        s.on_quit = on_quit
        s.root = tk_window

        menu_options = menu_options + (('退出', None, s.QUIT),)
        s._next_action_id = s.FIRST_ID
        s.menu_actions_by_id = set()
        s.menu_options = s._add_ids_to_menu_options(list(menu_options))
        s.menu_actions_by_id = dict(s.menu_actions_by_id)
        del s._next_action_id

        s.default_menu_index = (default_menu_index or 0)
        s.window_class_name = window_class_name or "SysTrayIconPy"

        message_map = {win32gui.RegisterWindowMessage("TaskbarCreated"): s.restart,
                       win32con.WM_DESTROY: s.destroy,
                       win32con.WM_COMMAND: s.command,
                       win32con.WM_USER + 20: s.notify, }
        # 注册窗口类。
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32gui.GetModuleHandle(None)
        wc.lpszClassName = s.window_class_name
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW;
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.lpfnWndProc = message_map  # 也可以指定wndproc.
        s.classAtom = win32gui.RegisterClass(wc)

    def activation(s):
        '''激活任务栏图标，不用每次都重新创建新的托盘图标'''
        hinst = win32gui.GetModuleHandle(None)  # 创建窗口。
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        s.hwnd = win32gui.CreateWindow(s.classAtom,
                                       s.window_class_name,
                                       style,
                                       0, 0,
                                       win32con.CW_USEDEFAULT,
                                       win32con.CW_USEDEFAULT,
                                       0, 0, hinst, None)
        win32gui.UpdateWindow(s.hwnd)
        s.notify_id = None
        s.refresh(title='软件已后台！', msg='点击重新打开', time=5)

        win32gui.PumpMessages()

    def refresh(s, title='', msg='', time=500):
        '''刷新托盘图标
           title 标题
           msg   内容，为空的话就不显示提示
           time  提示显示时间'''
        hinst = win32gui.GetModuleHandle(None)
        if os.path.isfile(s.icon):
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            hicon = win32gui.LoadImage(hinst, s.icon, win32con.IMAGE_ICON,
                                       0, 0, icon_flags)
        else:  # 找不到图标文件 - 使用默认值
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        if s.notify_id:
            message = win32gui.NIM_MODIFY
        else:
            message = win32gui.NIM_ADD

        s.notify_id = (s.hwnd, 0,  # 句柄、托盘图标ID
                       win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP | win32gui.NIF_INFO,
                       # 托盘图标可以使用的功能的标识
                       win32con.WM_USER + 20, hicon, s.hover_text,  # 回调消息ID、托盘图标句柄、图标字符串
                       msg, time, title,  # 提示内容、提示显示时间、提示标题
                       win32gui.NIIF_INFO  # 提示用到的图标
                       )
        win32gui.Shell_NotifyIcon(message, s.notify_id)

    def show_menu(s):
        '''显示右键菜单'''
        menu = win32gui.CreatePopupMenu()
        s.create_menu(menu, s.menu_options)

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(s.hwnd)
        win32gui.TrackPopupMenu(menu,
                                win32con.TPM_LEFTALIGN,
                                pos[0],
                                pos[1],
                                0,
                                s.hwnd,
                                None)
        win32gui.PostMessage(s.hwnd, win32con.WM_NULL, 0, 0)

    def _add_ids_to_menu_options(s, menu_options):
        result = []
        for menu_option in menu_options:
            option_text, option_icon, option_action = menu_option
            if callable(option_action) or option_action in s.SPECIAL_ACTIONS:
                s.menu_actions_by_id.add((s._next_action_id, option_action))
                result.append(menu_option + (s._next_action_id,))
            else:
                result.append((option_text,
                               option_icon,
                               s._add_ids_to_menu_options(option_action),
                               s._next_action_id))
            s._next_action_id += 1
        return result

    def restart(s, hwnd, msg, wparam, lparam):
        s.refresh()

    def destroy(s, hwnd=None, msg=None, wparam=None, lparam=None, exit=1):
        nid = (s.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0)  # 终止应用程序。
        if exit and s.on_quit:
            s.on_quit()  # 需要传递自身过去时用 s.on_quit(s)
        else:
            s.root.deiconify()  # 显示tk窗口

    def notify(s, hwnd, msg, wparam, lparam):
        '''鼠标事件'''
        if lparam == win32con.WM_LBUTTONDBLCLK:  # 双击左键
            pass
        elif lparam == win32con.WM_RBUTTONUP:  # 右键弹起
            s.show_menu()
        elif lparam == win32con.WM_LBUTTONUP:  # 左键弹起
            s.destroy(exit=0)
        return True
        """
        可能的鼠标事件：
          WM_MOUSEMOVE      #光标经过图标
          WM_LBUTTONDOWN    #左键按下
          WM_LBUTTONUP      #左键弹起
          WM_LBUTTONDBLCLK  #双击左键
          WM_RBUTTONDOWN    #右键按下
          WM_RBUTTONUP      #右键弹起
          WM_RBUTTONDBLCLK  #双击右键
          WM_MBUTTONDOWN    #滚轮按下
          WM_MBUTTONUP      #滚轮弹起
          WM_MBUTTONDBLCLK  #双击滚轮
        """

    def create_menu(s, menu, menu_options):
        for option_text, option_icon, option_action, option_id in menu_options[::-1]:
            if option_icon:
                option_icon = s.prep_menu_icon(option_icon)

            if option_id in s.menu_actions_by_id:
                item, extras = win32gui_struct.PackMENUITEMINFO(text=option_text,
                                                                hbmpItem=option_icon,
                                                                wID=option_id)
                win32gui.InsertMenuItem(menu, 0, 1, item)
            else:
                submenu = win32gui.CreatePopupMenu()
                s.create_menu(submenu, option_action)
                item, extras = win32gui_struct.PackMENUITEMINFO(text=option_text,
                                                                hbmpItem=option_icon,
                                                                hSubMenu=submenu)
                win32gui.InsertMenuItem(menu, 0, 1, item)

    def prep_menu_icon(s, icon):
        # 加载图标。
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXSMICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYSMICON)
        hicon = win32gui.LoadImage(0, icon, win32con.IMAGE_ICON, ico_x, ico_y, win32con.LR_LOADFROMFILE)

        hdcBitmap = win32gui.CreateCompatibleDC(0)
        hdcScreen = win32gui.GetDC(0)
        hbm = win32gui.CreateCompatibleBitmap(hdcScreen, ico_x, ico_y)
        hbmOld = win32gui.SelectObject(hdcBitmap, hbm)
        brush = win32gui.GetSysColorBrush(win32con.COLOR_MENU)
        win32gui.FillRect(hdcBitmap, (0, 0, 16, 16), brush)
        win32gui.DrawIconEx(hdcBitmap, 0, 0, hicon, ico_x, ico_y, 0, 0, win32con.DI_NORMAL)
        win32gui.SelectObject(hdcBitmap, hbmOld)
        win32gui.DeleteDC(hdcBitmap)

        return hbm

    def command(s, hwnd, msg, wparam, lparam):
        id = win32gui.LOWORD(wparam)
        s.execute_menu_option(id)

    def execute_menu_option(s, id):
        menu_action = s.menu_actions_by_id[id]
        if menu_action == s.QUIT:
            win32gui.DestroyWindow(s.hwnd)
        else:
            menu_action(s)

```
这部分代码参考了此博客
> [SysTrayIcon 改的 python tkinter 最小化至系统托盘——作者：我的眼_001](https://blog.csdn.net/wodeyan001/article/details/82497564)

结合 GUI 的代码如下

在类的初始化部分
```python
self.root.bind("<Unmap>",
               lambda
                   event: self.Hidden_window() if self.root.state() == 'iconic' else False)  # 窗口最小化判断，可以说是调用最重要的一步
self.root.protocol('WM_DELETE_WINDOW', self.exit)  # 点击Tk窗口关闭时直接调用s.exit，不使用默认关闭
```
托盘、右键菜单和消息弹窗部分代码如下

```python
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
```
## 6. 自启动部分（SchTasks）
拟采用 **os.system** 执行 **SchTasks** 命令。

代码写的比较匆忙，暂未实现，目前可通过手动创建管理员权限（由于进行了注册表操作）的任务计划，并将程序属性中以管理员权限启动打钩来实现开机自启动。

具体方法参考以下链接

> [如何创建Windows计划任务](https://jingyan.baidu.com/article/0964eca2cb8c17c284f53670.html)

## 7. 生成exe文件（Pyinstaller）
使用 **Pyinstaller** 进行打包，生成单exe命令，由于代码中使用了图片等数据，为了将这些数据一起打包，首先生成 **spec** 文件，代码如下

```python
pyi-makespec -F -w --uac-admin --icon img/loading.ico File_Sync_Hidden.py -p SysTrayIcon.py
```
然后将 **spec** 文件中的 **data行** 修改为

```python
datas=[('img','img')]
```
img为目前要打包的其他数据所在目录，img为使用时生成临时文件所在目录。

最后生成exe，代码如下

```python
pyinstaller -F -w --uac-admin File_Sync_Hidden.spec
```
