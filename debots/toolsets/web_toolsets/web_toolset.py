from .web_toolset_utils import parse_or_duck_duck_go, SEARCH_PREFIX, PARSE_ERROR_TITLE
from debots.core import Toolset
from debots.core import FunctionTool, Tool
from debots import Model
from debots import cor_gpt4o_mini
from debots import Message
from debots.message_colors import *

HOME = "HOME"
SCROLL_DOWN = "Scroll Down"
SCROLL_UP = "Scroll up"
BACK = "Back"
FORWARD = "Forward"
FIXED = "FIXED"

# 保持名称一致性
DUCK_DUCK_GO = "DUCK_DUCK_GO"
CLICK = "CLICK"
FIND_NEXT = "FIND_NEXT"
SAVE_LINE_IDS = "SAVE_LINE_IDS"

class WebToolsetVer0(Toolset):

    urls_stack = [HOME]
    urls_idx = 0

    full_page: [str]
    page_title: str
    link_dict = {}
    # 改变页面时
    # 总是先改变 urls_stack, urls_idx 来改变 self.url,
    # 接着 self.parse() 来得到 full_page, page_title 和 link_dict
    # 接着 self.render() 得到下一个 screen_size 大小的内容并调整 url2line_idx

    url2render_range = {} # url -> (first_idx, last_idx) 上次 render 的第一行和最后一行
    url2saved_lines = {} # url -> (title, [(line_idx, line_content)])

    def __init__(self, screen_size: int):
        self.screen_size = screen_size
        self.open_url(HOME)
        self.color = MESSAGE_COLOR_ORANGE
        self.link_dict = {}

    @property
    def tools(self) -> [Tool]:
        return [
            FunctionTool(self.duck_duck_go, DUCK_DUCK_GO, "使用DuckDuckGo全网搜索,该工具的参数是搜索关键词,尽量使用英文",
                         f"{DUCK_DUCK_GO}(US) -> 1. United States - Wikipedia  2. News in US - CNN ...",
                        color=self.color),
            FunctionTool(self.click, CLICK, "点击任意被<a>和</a>扩住的内容, 不区分大小写.该工具的参数是被<a>包住的字符串",
                         f"example 1: An <a>artificial intelligence</a> agent refers to ... -> {CLICK}(artificial intelligence) -> (New Page)Artificial intelligence (AI) is technology that enables ..."
                         f"example 2: (line 100-105) ...<a>Scroll down</a>... -> {CLICK}(scroll down) -> (line 106-113) -> {CLICK}(Scroll Up) -> (line 100-105) "
                         f"example 3: <a>Back</a>---page--- -> {CLICK}(Back) -> (last page)",
                         color=self.color),
            FunctionTool(self.find_next, FIND_NEXT, "向下查找当前页面, 用逗号分开关键词. 建议一次输入多个同义词, 不区分大小写.该工具参数是关键词.",
                         f"{FIND_NEXT}(landmark, monument, signpost, point of interest) -> Found \"monument\" at line 342: 342|<h2>Monuments in London</h2> ...",
                         color=self.color),
            FunctionTool(self.save_lines, SAVE_LINE_IDS, "保存输入的行号. 用减号表示区间. 保存的行被自动交给委托者.该工具参数是行号",
                         f"{SAVE_LINE_IDS}(3, 10-13, 60-65, 75, 20-25) -> 3:保存成功, 10-13:保存成功, 共计4行, 60-65: ...",
                         color=self.color)
        ]

    @property
    def url(self) -> str:
        return self.urls_stack[self.urls_idx]

    def parse(self, url): # update page_title, full_page & link_dict according to url
        if url == HOME:
            self.page_title = "Homepage"
            content = "Search anything to start. "
        else:
            self.page_title, content, new_link_dict = parse_or_duck_duck_go(url)
            self.link_dict = self.link_dict | new_link_dict
        self.full_page = list(filter(None, content.split("\n")))

    def open_url(self, url) -> str:
        self.urls_stack = self.urls_stack[:self.urls_idx + 1]
        self.urls_stack += [url]
        self.urls_idx += 1

        self.parse(url)
        return self.render(FIXED)

    def back(self):
        self.urls_idx = max(0, self.urls_idx - 1)
        self.parse(self.url)
        return self.render(FIXED)

    def forward(self): # only changes urls_stack, urls_idx, full_page & link_dict
        self.urls_idx = min(len(self.urls_stack) - 1, self.urls_idx + 1)

        self.parse(self.url)
        return self.render(FIXED)

    def render(self, move_type: str) -> str:  # render a screen_size content at this url
        assert move_type in [SCROLL_DOWN, SCROLL_UP, FIXED]
        content = ""
        if self.url not in self.url2render_range:
            self.url2render_range[self.url] = (0, 0)
            move_type = SCROLL_DOWN
        first_line_idx = self.url2render_range[self.url][1] if move_type == SCROLL_DOWN else self.url2render_range[self.url][0]
        direction = -1 if move_type == SCROLL_UP else 1

        on_screen = 0
        line_idx = first_line_idx
        while on_screen < self.screen_size and len(self.full_page) > line_idx and line_idx >= 0:
            line = self.full_page[line_idx]
            on_screen += len(line)
            content = f"{line_idx}|{line}\n" + content if move_type == SCROLL_UP else content + f"{line_idx}|{line}\n"
            line_idx += direction

        last_line_idx = line_idx - direction
        range_0 = min(first_line_idx, last_line_idx)
        range_1 = max(first_line_idx, last_line_idx)
        if range_1 < len(self.full_page) - 1:
            content += f"... <a>{SCROLL_DOWN}</a> ..."
        if range_0 > 0:
            content = f"... <a>{SCROLL_UP}</a> ...\n" + content

        # 浏览器部分
        content = "--- page ---\n" + content
        if self.urls_idx != len(self.urls_stack) - 1:
            content += f"<a>{FORWARD}</a>\n" + content
        if self.urls_idx != 0:
            content = f"<a>{BACK}</a>\n" + content
        content = "title: " + self.page_title + "\n" + content
        content = "--- browser ---\n" + content

        self.url2render_range[self.url] = (range_0, range_1)
        return content + "\nTip: CLICK interesting texts embraced by <a> and </a>"

    def click(self, to_click) -> str:
        if to_click.lower() == SCROLL_DOWN.lower():
            return self.render(SCROLL_DOWN)
        elif to_click.lower() == SCROLL_UP.lower():
            return self.render(SCROLL_UP)
        elif to_click.lower() == BACK.lower():
            return self.back()
        elif to_click.lower() == FORWARD.lower():
            return self.forward()
        elif to_click in self.link_dict:
            return self.open_url(self.link_dict[to_click])
        else:
            for key in self.link_dict:
                if to_click.lower() in key.lower():
                    return self.open_url(self.link_dict[key])
            return f"Can't find {to_click} on this page."

    def duck_duck_go(self, query) -> str:
        return self.open_url(SEARCH_PREFIX + query)

    def find_next(self, keys_str: str) -> str:
        keys = keys_str.split(",")
        first_line_idx = self.url2render_range[self.url][0] + 1
        found_at = -1
        found = ""
        for line_idx in range(first_line_idx, len(self.full_page)):
            line = self.full_page[line_idx]
            for key in keys:
                if key.lower() in line.lower():
                    found_at = line_idx
                    found = key
                    break
            if found_at != -1:
                break
        if found_at == -1:
            return f"Can't find any of the following words: {keys_str}"
        else:
            self.url2render_range[self.url] = (found_at, found_at)
            return f"(Found \"{found.strip()}\" at line {found_at})\n" + self.render(SCROLL_DOWN)

    def save_lines(self, lines_str: str) -> str:
        segments = lines_str.split(",")
        response = ""
        for segment in segments:
            terminals = segment.split("-")
            try:
                terminals = [int(terminal.strip()) for terminal in terminals]
            except ValueError:
                response += f"{segment}: Failure: \"{segment}\" is not legal expression.\n"
                continue
            if not 1 <= len(terminals) <= 2:
                response += f"{segment}: Failure: \"{segment}\" is not legal expression\n"
                continue
            bad = False
            for terminal in terminals:
                if not 0 <= terminal < len(self.full_page):
                    response += f"{segment}: Failure: line {terminal} is out of page\n"
                    bad = True
                    break
            if bad:
                continue
            if len(terminals) == 1:
                terminals = (terminals[0], terminals[0])
            if terminals[1] < terminals[0]:
                response += f"{segment}: Failure: {terminals[0]} > {terminals[1]}\n"
                continue
            for i in range(terminals[0], terminals[1] + 1):
                if self.url not in self.url2saved_lines:
                    self.url2saved_lines[self.url] = (self.page_title, [])
                self.url2saved_lines[self.url][1].append((i, self.full_page[i]))
            response += f"{segment}: Success: {terminals[1] - terminals[0] + 1} line{'s' if terminals[0] != terminals[1] else ''} saved\n"
        return response

    def retrieve(self) -> str:
        content = ""
        for url in self.url2saved_lines:
            title, l = self.url2saved_lines[url]
            content += f"in page \"{title}\":\n"
            l = list(sorted(set(l), key=lambda x: x[0]))
            for line_idx, line_content in l:
                content += f"{line_idx}| {line_content}\n"
            content += "\n\n"
        return content

    def submit_process(self, submit_str) -> str:
        return submit_str + "\n\n" + self.retrieve()
