from .web_toolset_utils import parse_or_duck_duck_go, SEARCH_PREFIX, PARSE_ERROR_TITLE, logout
from debots import Toolset
from debots import FunctionTool, Tool
from debots import Model
from debots import cor_gpt4o_mini
from debots import Message
from debots.message_colors import *
import tiktoken
from pydantic import BaseModel, Field
from typing import List
from debots.toolsets.toolset_utils import *
import asyncio
from concurrent.futures import ThreadPoolExecutor

HOME = "HOME"
FIXED = "FIXED"

# 保持名称一致性
DUCK_DUCK_GO_NOUN = "DUCK_DUCK_GO"
CLICK_LINK_NOUN = "CLICK_LINK"
FIND_NEXT_NOUN = "FIND_NEXT"
SAVE_LINE_IDS_NOUN = "SAVE_LINE_RANGES"
SCROLL_DOWN_NOUN = "SCROLL_DOWN"
SCROLL_UP_NOUN = "SCROLL_UP"
BACK_NOUN = "BACK"
FORWARD_NOUN = "FORWARD"
LINK_TAG_NAME = "link"

class WebToolsetVer1(Toolset):

    # urls_stack = [HOME]
    # urls_idx = 0
    #
    # page_lines: [str]
    # page_title: str
    # link_dict = {}
    # # 改变页面时
    # # 总是先改变 urls_stack, urls_idx 来改变 self.url,
    # # 接着 self.parse() 来得到 full_page, page_title 和 link_dict
    # # 接着 self.render() 得到下一个 screen_size 大小的内容并调整 url2line_idx
    #
    # url2render_range = {} # url -> (first_idx, last_idx) 上次 render 的第一行和最后一行
    # url2saved_lines = {} # url -> [line_idx]
    # url2all_lines = {} # url -> [str]
    # url2page_title = {} # url -> str
    def __init__(self, window_tokens_size: int=3000, tokenizer_name: str= "cl100k_base",
                 model_for_find_next: Model=cor_gpt4o_mini,
                 max_tokens_for_find_next: int=30000,
                 model_for_expanded_get_saved_lines: Model=cor_gpt4o_mini,
                 directly_selenium=True,
                 selenium_user_name="default user"):
        self.window_tokens_size = window_tokens_size
        self.tokenizer = tiktoken.get_encoding(tokenizer_name)
        self.directly_selenium = directly_selenium
        self.model_for_find_next = model_for_find_next
        self.max_tokens_for_find_next = max_tokens_for_find_next
        self.model_for_auto_complete = model_for_expanded_get_saved_lines
        self.selenium_user_name = selenium_user_name

        self.urls_stack = [HOME]
        self.urls_idx = 0
        self.url2render_range = {}
        self.url2saved_line_idxs = {}
        self.url2all_lines = {}
        self.url2page_title = {}

        self.open_url(HOME)
        self.color = MESSAGE_COLOR_ORANGE
        self.link_dict = {}

    @property
    def tools(self) -> [Tool]:
        return [
            FunctionTool(self.DUCK_DUCK_GO, DUCK_DUCK_GO_NOUN, "使用DuckDuckGo全网搜索,尽量用英文",
                         f"{DUCK_DUCK_GO_NOUN}(US) -> 1. United States - Wikipedia  2. News in US - CNN ...",
                         color=self.color),
            FunctionTool(self.CLICK_LINK, CLICK_LINK_NOUN, "点击一个页面中的一个链接",
                         f"当你观察到页面中有链接可能具备重要信息时,就可以使用该工具点击此链接",
                         color=self.color),
            FunctionTool(self.FIND_NEXT, FIND_NEXT_NOUN, "向下查找当前页面, 用逗号分开关键词. 建议一次输入多个同义词, 不区分大小写.该工具参数是关键词.",
                         f"{FIND_NEXT_NOUN}(landmark, monument, signpost, point of interest) -> Found \"monument\" at line 342: 342|<h2>Monuments in London</h2> ...",
                         color=self.color),
            FunctionTool(self.SAVE_LINE_IDS, SAVE_LINE_IDS_NOUN, "保存输入的行号区间.保存的行被自动交给委托者.该工具参数是行号区间",
                         f"{SAVE_LINE_IDS_NOUN}(10-13, 60-65, 20-25) -> 10-13:保存成功, 共计4行, 60-65: ...",
                         color=self.color),
            FunctionTool(self.SCROLL_UP, SCROLL_UP_NOUN, "向上滑动页面",
                         "当页面上部未展示完时可用",
                         color=self.color),
            FunctionTool(self.SCROLL_DOWN, SCROLL_DOWN_NOUN, "向下滑动页面",
                         "当页面下部未展示完时可用",
                         color=self.color),
            FunctionTool(self.BACK, BACK_NOUN, "返回浏览历史中的上一个页面",
                         "",
                         color=self.color),
            FunctionTool(self.FORWARD, FORWARD_NOUN, "恢复到浏览历史中的下一个页面",
                         "",
                         color=self.color),
        ]

    @property
    def url(self) -> str:
        return self.urls_stack[self.urls_idx]

    def parse(self, url): # update page_title, full_page & link_dict according to url
        if url == HOME:
            self.page_title = "Homepage"
            self.page_lines = ["Search anything to start. "]
        elif url in self.url2page_title:
            self.page_lines = self.url2all_lines[self.url]
            self.page_title = self.url2page_title[self.url]
        else:
            self.page_title, content, new_link_dict = parse_or_duck_duck_go(url,
                                                                            link_tag_name=LINK_TAG_NAME,
                                                                            directly_selenium=self.directly_selenium,
                                                                            selenium_user_name=self.selenium_user_name)
            self.link_dict = self.link_dict | new_link_dict
            self.page_lines = list(filter(None, content.split("\n")))
            self.url2all_lines[self.url] = self.page_lines
            self.url2page_title[self.url] = self.page_title

    def open_url(self, url) -> str:
        self.urls_stack = self.urls_stack[:self.urls_idx + 1]
        self.urls_stack += [url]
        self.urls_idx += 1

        self.parse(url)
        return self.render(FIXED)

    def BACK(self, unused_str=None) -> str:
        self.urls_idx = max(0, self.urls_idx - 1)
        self.parse(self.url)
        return self.render(FIXED)

    def FORWARD(self, unused_str=None) -> str: # only changes urls_stack, urls_idx, full_page & link_dict
        self.urls_idx = min(len(self.urls_stack) - 1, self.urls_idx + 1)

        self.parse(self.url)
        return self.render(FIXED)

    def SCROLL_UP(self, unused_str=None) -> str:
        return self.render(SCROLL_UP_NOUN)

    def SCROLL_DOWN(self, unused_str=None) -> str:
        return self.render(SCROLL_DOWN_NOUN)

    def render(self, move_type: str, tip: str = None) -> str:  # render a screen_size content at this url
        assert move_type in [SCROLL_DOWN_NOUN, SCROLL_UP_NOUN, FIXED]
        browser_content = ""
        lines_content = ""
        tools_content = ""

        # lines_content
        if self.url not in self.url2render_range:
            self.url2render_range[self.url] = (0, 0)
            move_type = SCROLL_DOWN_NOUN
        first_line_idx = self.url2render_range[self.url][1] if move_type == SCROLL_DOWN_NOUN else self.url2render_range[self.url][0]
        direction = -1 if move_type == SCROLL_UP_NOUN else 1
        tokens_on_screen = 0
        line_idx = first_line_idx
        while tokens_on_screen < self.window_tokens_size and len(self.page_lines) > line_idx and line_idx >= 0:
            line = self.page_lines[line_idx]
            tokens_on_screen += len(self.tokenizer.encode(line))
            lines_content = f"{line_idx}|{line}\n" + lines_content if move_type == SCROLL_UP_NOUN else lines_content + f"{line_idx}|{line}\n"
            line_idx += direction
        last_line_idx = line_idx - direction
        range_0 = min(first_line_idx, last_line_idx)
        range_1 = max(first_line_idx, last_line_idx)
        if range_0 != 0:
            lines_content = f"({SCROLL_UP_NOUN} to view earlier lines)\n" + lines_content
        if range_1 != len(self.page_lines) - 1:
            lines_content = lines_content + f"({SCROLL_DOWN_NOUN} to view later lines)\n"
        self.url2render_range[self.url] = (range_0, range_1)

        # tools_content
        tools_content += "Cross-page Operations:\n(These actions open a new page)\n"
        tools_content += f"- {DUCK_DUCK_GO_NOUN}(query): Search the web using DuckDuckGo\n"
        tools_content += f"- {CLICK_LINK_NOUN}(link_name): Open a page by clicking <link>link_name</link>\n"
        tools_content += f"- {BACK_NOUN}(unused_str): Return to the previous page\n" if self.urls_idx > 1 else ""
        tools_content += f"- {FORWARD_NOUN}(unused_str): Go to the next page\n" if self.urls_idx < len(self.urls_stack) - 1 else ""

        tools_content += "In-page Operations:\n(These actions stay within the current page)\n"
        tools_content += f"- {SAVE_LINE_IDS_NOUN}(id_ranges): Save specific line ranges by their IDs. Input can be one or multiple ranges (e.g., 30-50 or 30-50, 56-60).\n"
        tools_content += f"- {FIND_NEXT_NOUN}(query): Find and jump to the next matching line\n"
        tools_content += f"- {SCROLL_UP_NOUN}(unused_str): Scroll up to view earlier lines\n" if range_0 != 0 else ""
        tools_content += f"- {SCROLL_DOWN_NOUN}(unused_str): Scroll down to view later lines\n" if range_1 != len(self.page_lines) - 1 else ""

        # browser_content
        browser_content += f"title: {self.page_title}\n"

        # assemble
        content = ""
        content += browser_content
        content += tip if tip else ""
        content += "---page---\n"
        content += lines_content
        content += "---you can---\n"
        content += tools_content
        return content

    def CLICK_LINK(self, to_click) -> str:
        if to_click in self.link_dict:
            return self.open_url(self.link_dict[to_click])
        else:
            for key in self.link_dict:
                if to_click.lower() in key.lower():
                    return self.open_url(self.link_dict[key])
            return f"Can't find {to_click} as a link. typo?"

    def DUCK_DUCK_GO(self, query) -> str:
        return self.open_url(SEARCH_PREFIX + query)

    def FIND_NEXT(self, keys_str: str) -> str:
        def return_at(line_idx: int, tip: str) -> str:
            line_idx = max(line_idx - 3, 0)
            self.url2render_range[self.url] = (line_idx, line_idx)
            return self.render(SCROLL_DOWN_NOUN, tip=f"{tip}\n")
        return find_next_with_ai_fallback(keys_str,
                                        self.page_lines,
                                        self.url2render_range[self.url][0],
                                        return_at,
                                        self.tokenizer,
                                        self.max_tokens_for_find_next,
                                        self.model_for_find_next)

    def SAVE_LINE_IDS(self, lines_str: str) -> str:
        def callback(idx):
            if self.url not in self.url2saved_line_idxs:
                self.url2saved_line_idxs[self.url] = []
            self.url2saved_line_idxs[self.url].append(idx)
        return parse_line_ranges(lines_str, callback, len(self.page_lines))

    def get_saved_lines(self) -> str:
        content = ""
        for url in self.url2saved_line_idxs:
            lines = self.url2all_lines[url]
            l = [(idx, lines[idx]) for idx in sorted(self.url2saved_line_idxs[url])]
            title = self.url2page_title[url]
            content += f"in page \"{title.strip()}\":\n"
            content += f"({url})\n"
            l = list(sorted(set(l), key=lambda x: x[0]))
            for line_idx, line_content in l:
                content += f"{line_idx}| {line_content}\n"
            content += "\n\n"
        return content

    def submit_process(self, submit_str) -> str:
        return submit_str + "\n\n" + self.get_saved_lines()

    def logout_from_driver(self):
        logout(self.selenium_user_name)

    def auto_complete_id_ranges(self):
        futures = []
        urls = []
        with ThreadPoolExecutor() as executor:
            for url in self.url2saved_line_idxs:
                saved_line_idxs = set(self.url2saved_line_idxs[url])
                lines = self.url2all_lines[url]
                user_prompt = "\n".join(f"{idx}{'(Saved)' if idx in saved_line_idxs else ''}|{line}"
                                    for idx, line in enumerate(lines))
                system_prompt = f'''上面是一个.html文件的节选,每行的最开头是行号,有些行被用户保存了,因此加了(Saved)标记.
                你的任务是输出最少的行, 使得保存这些行后, 形成最小的语意闭包, 也就是包含了用户保存的行的最小语意完整体.
                也就是输出这些行号: a.解释说明用户保存内容的行 b.和用户保存内容形成并列的行 c.为用户保存内容举例的行 d.如果用户保存了某个子标题行,输出这个子标题行的所有子行
                你输出的格式是以逗号连接的行号区间, 格式类似于: 10-13, 60-65, 20-25'''
                futures += [executor.submit(self.model_for_auto_complete.invoke, [
                    {"role": "user", "content": user_prompt}
                ], "", system_prompt)]
                urls += [url]

            results = [future.result() for future in futures]
            for url, result_str in zip(urls, results):
                def callback(idx):
                    nonlocal url
                    self.url2saved_line_idxs[url].append(idx)
                parse_line_ranges(result_str, callback, len(self.page_lines))
            # 检查这部分代码并测试

    def get_completed_saved_lines(self):
        self.auto_complete_id_ranges()
        return self.get_saved_lines()

    def submit_process_lazy(self, submit_str, processed_submit_str) -> str:
        print("submit_process_lazy")
        return submit_str + "\n\n" + self.get_completed_saved_lines()