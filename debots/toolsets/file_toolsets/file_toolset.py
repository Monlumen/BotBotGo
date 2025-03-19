from .file_utils import *
import tiktoken
from .VectorDatabase import VectorDatabase
from debots import Model, Tool
from ...core.models import cor_gpt4o_mini
from pydantic import BaseModel, Field
from typing import List
from debots import Toolset, FunctionTool
from debots.message_colors import *
from debots.toolsets.toolset_utils import *

CD_NOUN = "CD"
LS_NOUN = "LS"
UP_NOUN = "UP"
OPEN_FILE_NOUN = "OPEN_FILE"
SEARCH_NOUN = "SEARCH"
FIND_NEXT_NOUN = "FIND_NEXT"
SAVE_LINE_RANGES_NOUN = "SAVE_LINE_RANGES"
CLOSE_FILE_NOUN = "CLOSE_FILE"
SCROLL_UP_NOUN = "SCROLL_UP"
SCROLL_DOWN_NOUN = "SCROLL_DOWN"

class FileToolsetVer0(Toolset):
    def __init__(self, root_dir, db_dir, window_size=5000, tokenizer_name: str="cl100k_base", num_search_results: int=10,
                 model_for_find_next:Model=cor_gpt4o_mini, max_tokens_for_find_next:int=20000,
                 color=MESSAGE_COLOR_PINK):
        self.root_dir_abs = safe_link_path(getcwd(), root_dir, None) # 绝对路径
        self.db_dir_abs = safe_link_path(getcwd(), db_dir, None)
        self.tokenizer = tiktoken.get_encoding(tokenizer_name)
        self.vdb = VectorDatabase(self.root_dir_abs, self.db_dir_abs, tokenizer_name=tokenizer_name)
        self.num_search_results = num_search_results
        self.model_for_find_next = model_for_find_next
        self.max_tokens_for_find_next = max_tokens_for_find_next
        self.color = color
        # viewer
        self.current_file_path_rel = None
        self.current_file_lines = []
        self.current_line_range_start = 0
        self.current_line_range_end = 0
        self.window_size = window_size
        # browser
        self.current_dir_rel = "/" # 相对于 root_dir 的路径
        self.short_names = {} # name -> file_path_rel
        self.file_path_rel2line_idx = {} # file_path_rel -> int
        # save_lines
        self.rel_path2saved_lines = {} # path -> [set(line_idx, line_content)]

    @property
    def tools(self) -> [Tool]:
        return [
            FunctionTool(self.CD, CD_NOUN, "(仅在file browser可用)输入一个文件夹的相对位置/绝对位置,进入该文件夹",
                         "在/A使用CD(B)进入/A/B",
                         self.color),
            FunctionTool(self.LS, LS_NOUN, "(仅在file browser可用)查看本文件夹下的所有子文件夹和文件",
                         "",
                         self.color),
            FunctionTool(self.UP, UP_NOUN, "(仅在file browser可用)进入上一层文件夹",
                         "",
                         self.color),
            FunctionTool(self.SEARCH, SEARCH_NOUN, "(仅在file browser可用)在整个磁盘搜索某个关键词或者问题",
                         "",
                         self.color),
            FunctionTool(self.OPEN_FILE, OPEN_FILE_NOUN, "(仅在file browser可用)打开某个文件,并进入notepad",
                         "",
                         self.color),
            FunctionTool(self.CLOSE_FILE, CLOSE_FILE_NOUN, "(仅在notepad可用)关闭该文件并返回file browser",
                         "",
                         self.color),
            FunctionTool(self.FIND_NEXT, FIND_NEXT_NOUN, "(仅在notepad可用)向下查找当前页面, 用逗号分开关键词. 建议一次输入多个同义词, 不区分大小写.该工具参数是关键词.",
                         f"{FIND_NEXT_NOUN}(landmark, monument, signpost, point of interest) -> Found \"monument\" at line 342: 342|<h2>Monuments in London</h2> ...",
                         color=self.color),
            FunctionTool(self.SAVE_LINE_IDS, SAVE_LINE_RANGES_NOUN, "(仅在notepad可用)保存输入的行号区间.保存的行被自动交给委托者.该工具参数是行号区间",
                         f"{SAVE_LINE_RANGES_NOUN}(10-13, 60-65, 20-25) -> 10-13:保存成功, 共计4行, 60-65: ...",
                         color=self.color),
            FunctionTool(self.SCROLL_UP, SCROLL_UP_NOUN, "(仅在notepad可用)向上滑动页面",
                         "当页面上部未展示完时可用",
                         color=self.color),
            FunctionTool(self.SCROLL_DOWN, SCROLL_DOWN_NOUN, "(仅在notepad可用)向下滑动页面",
                         "当页面下部未展示完时可用",
                         color=self.color),
        ]

    def to_abs_path(self, path_relative_to_root_dir) -> str:
        return safe_link_path(self.root_dir_abs, "." + path_relative_to_root_dir, self.root_dir_abs)


    @property
    def current_dir_abs(self) -> str:
        return self.to_abs_path(self.current_dir_rel)

    @staticmethod
    def browser_interface(path, l, search=None, search_results=None) -> str:
        content = "---file browser---\n"
        content += f"current dir: {path}\n"

        # 列出当前目录内容
        for entry in l:
            content += f"[{'D' if entry[1] else 'F'}] {entry[0]}\n"

        # 如果有搜索内容
        if search is not None and search_results is not None:
            content += "---search results---\n"
            content += f"You searched: {search}\n"
            for entry in search_results:
                content += f"[F] {entry[0]}: {entry[1]}\n"

        # 工具说明
        content += "---you can---\n"
        content += f"{CD_NOUN}(relative_path): Navigate to a subdirectory in the current directory.\n"
        content += f"{LS_NOUN}(unused_str): List all files and directories in the current directory.\n"
        content += f"{UP_NOUN}(unused_str): Navigate to the parent directory (one level up from the current directory)."
        content += f"{OPEN_FILE_NOUN}(file_name): Open a file from the current directory or the search results.\n"
        content += f"{SEARCH_NOUN}(query): Search throughout the directory structure.\n"

        return content

    def render_browser(self, search=None, search_results=None) -> str:
        # render a browser using self.current_dir
        current_dir_ls = ls(self.current_dir_abs)
        return FileToolsetVer0.browser_interface(self.current_dir_rel, current_dir_ls, search, search_results)

    def load_short_names(self):
        # update self.short_names according to self.current_dir
        # print(self.current_dir_rel)
        # print(self.current_dir_abs)
        l = ls(self.current_dir_abs)
        for entry in l:
            if entry[1] == False:
                self.short_names[entry[0]] = safe_link_path(self.current_dir_rel, entry[0], None)

    def CD(self, relative_path) -> str:
        if self.current_file_path_rel is not None:
            return f"You need to {CLOSE_FILE_NOUN} before {CD_NOUN}"
        new_path_rel = safe_link_path(self.current_dir_rel, relative_path, None)
        # print("new_path_rel: " + new_path_rel)
        if not is_dir(self.to_abs_path(new_path_rel)):
            return f"{new_path_rel} is not a valid directory. typo?"
        else:
            self.current_dir_rel = new_path_rel
            self.load_short_names()
            return self.render_browser()

    def UP(self, unused_str=None) -> str:
        if self.current_file_path_rel is not None:
            return f"You need to {CLOSE_FILE_NOUN} before {UP_NOUN}"
        return self.CD("../")

    def LS(self, unused_str=None) -> str:
        if self.current_file_path_rel is not None:
            return f"You need to {CLOSE_FILE_NOUN} before {LS_NOUN}"
        return self.CD(".")

    @staticmethod
    def notepad_interface(file_lines: [str], start: int, end: int, tip_info: str=None) -> str:
        # 包含 start 和 end
        view_content = ""
        tool_content = ""
        start = max(0, start)
        end = min(end, len(file_lines) - 1)
        for idx in range(start, end + 1):
            view_content += f"{idx}|{file_lines[idx]}\n"
        if start != 0:
            view_content = f"({SCROLL_UP_NOUN}: View earlier lines)\n" + view_content
            tool_content += f"{SCROLL_UP_NOUN}(unused_str): View earlier lines\n"
        if end != len(file_lines) - 1:
            view_content += f"({SCROLL_DOWN_NOUN}: View later lines)\n"
            tool_content += f"{SCROLL_DOWN_NOUN}(unused_str): View later lines\n"
        else:
            view_content += "(END)\n"
        tool_content += f"{FIND_NEXT_NOUN}(keywords): Jump to the next line matching your keywords\n"
        tool_content += f"{SAVE_LINE_RANGES_NOUN}(line_ids): Save specific line ranges by their IDs. Input can be one or multiple ranges (e.g., 30-50 or 30-50, 56-60)\n"
        tool_content += f"{CLOSE_FILE_NOUN}(unused_str): Close this file and go back to file browser\n"
        content = "---notepad---\n"
        content += tip_info + "\n" if tip_info else ""
        content += view_content
        content += "---you can---\n"
        content += tool_content

        return content

    def move_current_line_range(self, direction: int):
        # it only changes self.current_line_range
        assert direction in [-1, 0, 1]
        if direction == 0:
            return
        first_line_idx = self.current_line_range_end if direction == 1 else self.current_line_range_start
        line_idx = first_line_idx
        in_window = 0
        while in_window < self.window_size and 0 <= line_idx < len(self.current_file_lines):
            in_window += len(self.tokenizer.encode(self.current_file_lines[line_idx]))
            line_idx += direction
        last_line_idx = line_idx - direction
        self.current_line_range_start = min(first_line_idx, last_line_idx)
        self.current_line_range_end = max(first_line_idx, last_line_idx)

    def render_notepad(self, tip_info: str=None):
        return FileToolsetVer0.notepad_interface(self.current_file_lines,
                                                 self.current_line_range_start,
                                                 self.current_line_range_end,
                                                 tip_info=tip_info)

    def SCROLL_UP(self, unused_str=None) -> str:
        if self.current_file_path_rel is None:
            return f"You need to {OPEN_FILE_NOUN} before {SCROLL_UP_NOUN}"
        self.move_current_line_range(-1)
        return self.render_notepad()

    def SCROLL_DOWN(self, unused_str=None) -> str:
        if self.current_file_path_rel is None:
            return f"You need to {OPEN_FILE_NOUN} before {SCROLL_DOWN_NOUN}"
        self.move_current_line_range(1)
        return self.render_notepad()


    def FIND_NEXT(self, keywords: str) -> str:
        if self.current_file_path_rel is None:
            return f"You need to {OPEN_FILE_NOUN} before {FIND_NEXT_NOUN}"
        def return_at(idx: int, tip: str):
            self.current_line_range_start = max(idx - 2, 0)
            self.current_line_range_end = self.current_line_range_start
            self.move_current_line_range(1)
            return self.render_notepad(tip)
        return find_next_with_ai_fallback(keywords, self.current_file_lines, self.current_line_range_start,
                                   return_at, self.tokenizer,
                                   self.max_tokens_for_find_next, self.model_for_find_next)

    def CLOSE_FILE(self, unused_str=None) -> str:
        if self.current_file_path_rel is None:
            return f"You need to {OPEN_FILE_NOUN} before {CLOSE_FILE_NOUN}"
        if self.current_file_path_rel != None:
            self.file_path_rel2line_idx[self.current_file_path_rel] = self.current_line_range_start
        self.current_file_lines = []
        self.current_file_path_rel = None
        self.current_line_range_start = 0
        self.current_line_range_end = 0
        return self.render_browser()

    def try_open_file(self, file_name) -> bool:
        rel_path = None
        if not "/" in file_name:
            if file_name in self.short_names:
                rel_path = self.short_names[file_name]
        else:
            rel_path = safe_link_path(self.current_dir_rel, file_name, None)
        if rel_path is not None:
            content = read_file(self.to_abs_path(rel_path))
            start_line_idx = self.file_path_rel2line_idx[rel_path] if rel_path in self.file_path_rel2line_idx else 0
            if content is not None:
                self.current_file_path_rel = rel_path
                self.current_file_lines = content.split("\n")
                self.current_line_range_start = start_line_idx
                self.current_line_range_end = start_line_idx
                self.move_current_line_range(1)
                return True
        return False

    def OPEN_FILE(self, file_name) -> str:
        if self.current_file_path_rel is not None:
            return f"You need to {CLOSE_FILE_NOUN} before {OPEN_FILE_NOUN}"
        if self.try_open_file(file_name):
            return self.render_notepad()
        else:
            return f"{file_name} doesn't exist. typo?"

    def SAVE_LINE_IDS(self, lines_str: str) -> str:
        def callback(idx: int):
            if not self.current_file_path_rel in self.rel_path2saved_lines:
                self.rel_path2saved_lines[self.current_file_path_rel] = set()
            self.rel_path2saved_lines[self.current_file_path_rel].add((idx, self.current_file_lines[idx]))
        return parse_line_ranges(lines_str, callback, len(self.current_file_lines))

    def get_saved_lines(self) -> str:
        # path -> [set(line_idx, line_content)]
        all_content = "\n"
        for path in self.rel_path2saved_lines:
            content = ""
            s = self.rel_path2saved_lines[path]
            l = (sorted(list(s), key=lambda x: x[0]))
            for entry in l:
                content += f"{entry[0]}| {entry[1]}\n"
            if content != "":
                all_content += f"in file \"{path}\": \n{content}\n"
        return all_content

    def SEARCH(self, query) -> str:
        if self.current_file_path_rel is not None:
            return f"You need to {CLOSE_FILE_NOUN} before {SEARCH_NOUN}"
        l = self.vdb.search(query, 10)
        name_desc_pairs = [(entry[0], entry[1][:30].replace("\n","\\n")) for entry in l]
        for entry in name_desc_pairs:
            name = entry[0]
            if "/" in name:
                name = name.split("/")[-1]
            self.short_names[name] = entry[0]
        return self.render_browser(query, name_desc_pairs)

    def submit_process(self, submit_content: str) -> str:
        return submit_content + "\n" + self.get_saved_lines()