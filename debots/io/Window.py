import tkinter as tk
from queue import Queue
from types import FunctionType
from .WindowController import WindowController
from .utils import remove_ansi_codes

class Window:

    def __init__(self, idx, total_windows):
        """初始化窗口"""
        self.queue = Queue()
        self.is_closed = False

        # 创建独立的 Toplevel 窗口
        self.root = tk.Toplevel()

        # 获取屏幕宽高
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 估计标题栏和标签的高度
        dummy_label = tk.Label(self.root, text="", font=("Arial", 14))
        dummy_label.update_idletasks()  # 强制更新以获取真实尺寸
        label_height = dummy_label.winfo_reqheight()

        dummy_root = tk.Toplevel()
        dummy_root.withdraw()  # 隐藏用于计算标题栏高度
        title_bar_height = dummy_root.winfo_rooty() - dummy_root.winfo_y()
        dummy_root.destroy()

        # 计算窗口大小和位置
        total_non_text_height = label_height + title_bar_height
        window_height = (screen_height - total_non_text_height * total_windows) // total_windows
        window_width = int(screen_width * 0.3)  # 设置宽度为屏幕的 20%
        x_position = screen_width - window_width  # 靠右对齐
        y_position = idx * (window_height + total_non_text_height)  # 按索引计算垂直位置

        # 设置窗口的几何大小和位置
        self.root.title(f"Window {idx}")
        self.root.geometry(f"{window_width}x{window_height + total_non_text_height}+{x_position}+{y_position}")

        # 使用 grid 布局
        self.root.rowconfigure(1, weight=1)  # 第二行 Text 扩展
        self.root.columnconfigure(0, weight=1)  # 第一列扩展

        # 顶部的 Label
        self.label = tk.Label(self.root, text="", bg="lightblue", fg="black", font=("Arial", 14))
        self.label.grid(row=0, column=0, sticky="ew")  # 占满顶部水平空间

        # 文本框用于显示内容
        self.text_box = tk.Text(self.root, state="disabled", width=40, height=10)
        self.text_box.grid(row=1, column=0, sticky="nsew")  # 占满剩余空间

    def update(self):  # mainprocess
        """更新窗口内容"""
        while not self.queue.empty():
            operation = self.queue.get()
            if isinstance(operation, WindowController.TerminateOperation):
                # 处理 TerminateOperation
                self.is_closed = True
                self.root.destroy()  # 关闭窗口
                return
            elif isinstance(operation, WindowController.PrintOperation):
                # 处理 PrintOperation
                text = "---------------------\n" + remove_ansi_codes(operation.text)
                self.text_box.config(state="normal")
                self.text_box.insert(tk.END, text + "\n")  # 显示文本
                self.text_box.config(state="disabled")
                self.text_box.see(tk.END)  # 滚动到底部
            elif isinstance(operation, WindowController.SetLabelOperation):
                # 处理 SetLabelOperation
                self.label.config(text=operation.label)  # 更新 Label 内容
            elif isinstance(operation, WindowController.SetTitleOperation):
                self.root.title(operation.title)
        if not self.is_closed:
            self.root.after(100, self.update)


def get_window_controllers_and_mainloop(num_windows: int) -> ([WindowController], FunctionType):
    windows = [Window(idx, num_windows) for idx in range(num_windows)]

    # 创建一个隐式根窗口用于控制主循环
    root = tk.Tk()
    root.withdraw()  # 确保主窗口保持隐藏

    def mainloop():
        """启动主事件循环"""
        def check_windows():
            if all(window.is_closed for window in windows):
                root.quit()  # 所有窗口关闭时退出主循环
            else:
                root.after(100, check_windows)

        # 启动窗口更新
        for window in windows:
            window.update()

        # 启动检查窗口状态的循环
        root.after(100, check_windows)
        tk.mainloop()

    return [WindowController(window.queue) for window in windows], mainloop