import tkinter as tk
from tkinter import ttk
from queue import Queue
from .WindowController import WindowController
from .utils import remove_ansi_codes


class TabbedWindow:
    def __init__(self, num_tabs):
        self.queue_list = [Queue() for _ in range(num_tabs)]
        self.num_tabs = num_tabs
        self.is_closed = False

        # 创建 Toplevel 窗口
        self.root = tk.Toplevel()
        self.root.title("Bot Bot Go!")

        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 计算窗口的位置和大小
        window_width = 600  # 固定宽度
        window_height = screen_height  # 高度占满整个屏幕
        x_position = screen_width - window_width  # 贴到屏幕最右边
        y_position = 0  # 顶部对齐

        # 设置窗口几何大小和位置
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

        # 创建 Notebook（选项卡）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 创建每个选项卡
        self.windows = []
        for idx in range(num_tabs):
            tab_frame = tk.Frame(self.notebook)
            self.notebook.add(tab_frame, text=f"Tab {idx + 1}")
            window = Tab(idx, window_width, parent=tab_frame, notebook=self.notebook, tab_id=idx)
            self.windows.append(window)

    def update(self):
        """更新每个选项卡的状态"""
        for window in self.windows:
            window.update()

        # 定期触发更新循环
        if not self.is_all_closed:
            self.root.after(100, self.update)
        else:
            self.root.destroy()  # 关闭窗口
            self.is_closed = True

    @property
    def is_all_closed(self):
        """检查是否所有窗口都关闭"""
        num_closed = len(list(filter(None, map(lambda window: window.is_closed, self.windows))))
        return num_closed == self.num_tabs

class Tab:
    def __init__(self, idx, width, parent=None, notebook=None, tab_id=None):
        """初始化窗口（支持嵌套到父容器）"""
        self.queue = Queue()
        self.is_closed = False
        self.notebook = notebook  # 保存 Notebook 的引用
        self.tab_id = tab_id  # 保存选项卡索引

        # 创建独立的容器，使用 Frame 作为父窗口内容
        self.root = tk.Frame(parent) if parent else tk.Toplevel()
        self.root.pack(fill=tk.BOTH, expand=True)

        # 顶部的 Label
        self.label = tk.Label(self.root,
                              text=f"Label for Tab {idx + 1}",
                              bg="lightblue",
                              fg="black",
                              font=("Arial", 14),
                              wraplength=width * 0.8,
                              justify="center",
                              pady=20)
        self.label.pack(fill=tk.X)  # 顶部水平填充

        # 文本框用于显示内容
        self.text_box = tk.Text(self.root, state="normal", width=40, height=10)
        self.text_box.insert(tk.END, "")  # 默认内容
        self.text_box.config(state="disabled")  # 设置为只读模式
        self.text_box.pack(fill=tk.BOTH, expand=True)

    def update(self):
        """更新窗口内容"""
        while not self.queue.empty():
            operation = self.queue.get()
            if isinstance(operation, WindowController.TerminateOperation):
                self.is_closed = True
                if self.notebook and self.tab_id is not None:
                    self.notebook.tab(self.tab_id, text="[完毕]")
                self.label.config(bg="lightgreen")
                return
            elif isinstance(operation, WindowController.PrintOperation):
                # 显示文本
                text = "---------------------\n" + remove_ansi_codes(operation.text)
                self.text_box.config(state="normal")
                self.text_box.insert(tk.END, text + "\n")
                self.text_box.config(state="disabled")
                self.text_box.see(tk.END)
            elif isinstance(operation, WindowController.SetLabelOperation):
                self.label.config(text=operation.label)
            elif isinstance(operation, WindowController.SetTitleOperation):
                if self.notebook and self.tab_id is not None:
                    self.notebook.tab(self.tab_id, text=operation.title)  # 修改选项卡标题


def get_tab_controllers_and_mainloop(num_tabs):
    tabbed_window = TabbedWindow(num_tabs)
    controllers = [WindowController(window.queue) for window in tabbed_window.windows]

    def mainloop():
        """启动主事件循环"""
        def check_tabs():
            if tabbed_window.is_closed:
                root.quit()  # 所有选项卡关闭时退出主循环
            else:
                root.after(100, check_tabs)

        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        tabbed_window.update()
        root.after(100, check_tabs)
        tk.mainloop()

    return controllers, mainloop