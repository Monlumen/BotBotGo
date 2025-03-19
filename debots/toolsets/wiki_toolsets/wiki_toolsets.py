from debots.core import Toolset
from debots.core import FunctionTool, Tool
from debots.core import Model
from debots.core.models import cor_gpt4o_mini
import wikipedia
from debots.core import Message
from debots.message_colors import MESSAGE_COLOR_ORANGE
import hashlib
import re
from debots.toolsets.toolset_utils import *


class WikiToolset(Toolset):
    # current_page: wikipedia.WikipediaPage
    # model: Model

    @property
    def tools(self) -> [Tool]:
        return [
            FunctionTool(self.navigate, "NAVIGATE",
                         "导航到某个 Wikipedia 页面, 该页面必须存在. ",
                         "NAVIGATE(Taylor Swift) -> 到达 Taylor Swift 页面并返回页面总结; "
                         "NAVIGATE(Tayla Swift) -> 无法找到, 你是否在找 Taylor Swift",
                         self.color),
            FunctionTool(self.search_in_page, "LOOKUP",
                         "在当前页面搜索",
                         "NAVIGATE(Taylor Swift) -> 到达 Taylor Swift 页面了 -> LOOKUP(所有专辑) -> 返回 Taylor Swift 的专辑列表",
                         self.color),
            FunctionTool(self.fullpage, "FULLPAGE",
                         "返回当前页面的所有内容",
                         "NAVIGATE(United States) -> United States is a country on American Continent. -> FULLPAGE() -> "
                         "United States is a country on American Continent. It's considered one of the most developed countries in the world. "
                         "the population is ......(a lot of words)",
                         self.color)
        ]

    def __init__(self, model=cor_gpt4o_mini, color: int = MESSAGE_COLOR_ORANGE):
        super().__init__()
        self.model = model
        self.continuous_lookup = 0
        self.page_dir = {}
        self.current_page = None
        self.current_page_content = None
        self.color = color

    def navigate(self, title: str) -> str:
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        if "-" in title or "_" in title:
            return (f"You called NAVIGATE\"{title}\", which leads to an error. Because you can't put \"-\" or \"_\" "
                    f"in a page title. Call NAVIGATE(\"{title.replace("-", " ").replace("_", " ")}\") instead.")
        try:
            page = wikipedia.page(title, auto_suggest=False)
            assert page.title.lower() == title.lower()
            self.current_page = page
            self.current_page_content = None
            self.page_dir[page.title] = 0 if page.title not in self.page_dir else self.page_dir[page.title]
            fullpaged_promopt = "" if self.page_dir[page.title] >= 0 else (
                "I notice you have already called FULLPAGE on this page. "
                "So you already have had all the information on this page. "
                "I recommend you to NAVIGATE to another page right now.")
            return ("Title: " + page.title +
                    "\nShort Summary: " + page.summary + "...(Ellipsis)... (use LOOKUP(question) to"
                                                         " search the ellipsis part of this article)" +
                    "\nRelated Pages: " + ", ".join(wikipedia.search(title))) + fullpaged_promopt
        except Exception as e:
            self.current_page = None
            self.current_page_content = None
            dash_prompt = ", Please Notice You are inputting _ (dash) instead of space, which might lead to error. " \
                if "_" in title else ""
            similar = wikipedia.search(title)
            if title in similar:
                similar.remove(title)
            return f"Could not find: \"{title}\" " + dash_prompt + ", Similar:" + str(similar)

    def search_in_page(self, question) -> str:
        if self.current_page is None:
            return (f"Error: You called LOOKUP({question}) on a void page, which is not permitted. "
                    "You are on a void page because your last navigate was a failure")
        else:
            self.page_dir[self.current_page.title] += 1
            fullpage_prompt = f"tips: use FULLPAGE() if you think LOOKUP({question}) doesn't work well. "
            if self.page_dir[self.current_page.title] > 5:
                fullpage_prompt = (" I notice you have conducted more than 5 LOOKUPs on this page."
                                   " Do you want to call FULLPAGE() on this page to get all the "
                                   "information all at once?")
            self.current_page_content = self.current_page.content if self.current_page_content is None else self.current_page_content
            return (f"You called LOOKUP({question}) on page \"{self.current_page.title}\", here's the result: " +
                    self.model.invoke([
                        {"role": "user",
                         "content": "The wikipedia page states as followings: " + self.current_page.content},
                        {"role": "user", "content": "My query is: " + question}
                    ], "You are a helpful assistant. Your job is to list all facts in this wikipedia page"
                       "that are related with the user's query. "
                       " If no facts in this page are related enough, just report that to the user.")) + fullpage_prompt

    def fullpage(self, unused_str) -> str:
        if self.current_page is None:
            return ("Error: You called FULLPAGE() on a void page, which is not permitted. "
                    "You are on a void page because your last navigate was a failure")
        else:
            self.page_dir[self.current_page.title] -= 1000000
            return f"You called FULLPAGE() on page \"{self.current_page.title}\", here's the result: " + self.current_page.content


class FullPageWikiToolset(Toolset):
    current_page: wikipedia.WikipediaPage
    model: Model

    @property
    def tools(self) -> [Tool]:
        return [
            FunctionTool(self.navigate, "NAVIGATE",
                         "导航到某个 Wikipedia 页面, 该页面必须存在. ",
                         "NAVIGATE(Taylor Swift) -> 到达 Taylor Swift 页面并返回页面总结; "
                         "NAVIGATE(Tayla Swift) -> 无法找到, 你是否在找 Taylor Swift",
                         self.color),
            FunctionTool(self.fullpage, "FULLPAGE",
                         "返回当前页面的所有内容",
                         "NAVIGATE(United States) -> United States is a country on American Continent. -> FULLPAGE() -> "
                         "United States is a country on American Continent. It's considered one of the most developed countries in the world. "
                         "the population is ......(a lot of words)",
                         self.color)
        ]

    def __init__(self, color: int = MESSAGE_COLOR_ORANGE):
        super().__init__()
        self.continuous_lookup = 0
        self.current_page = None
        self.current_page_content = None
        self.color = color

    def navigate(self, title: str) -> str:
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        if "-" in title or "_" in title:
            return (f"You called NAVIGATE\"{title}\", which leads to an error. Because you can't put \"-\" or \"_\" "
                    f"in a page title. Call NAVIGATE(\"{title.replace("-", " ").replace("_", " ")}\") instead.")
        try:
            page = wikipedia.page(title, auto_suggest=False)
            assert page.title.lower() == title.lower()
            self.current_page = page
            self.current_page_content = None
            return ("Title: " + page.title +
                    "\nShort Summary: " + page.summary + "...(Ellipsis)... (use FULLPAGE to"
                                                         " get the full article)" +
                    "\nRelated Pages: " + ", ".join(wikipedia.search(title)))
        except Exception as e:
            self.current_page = None
            self.current_page_content = None
            dash_prompt = ", Please Notice You are inputting _ (dash) instead of space, which might lead to error. " \
                if "_" in title else ""
            similar = wikipedia.search(title)
            if title in similar:
                similar.remove(title)
            return f"Could not find: \"{title}\" " + dash_prompt + ", Similar:" + str(similar)

    def fullpage(self, unused_str) -> str:
        if self.current_page is None:
            return ("Error: You called FULLPAGE() on a void page, which is not permitted. "
                    "You are on a void page because your last navigate was a failure")
        else:
            return f"You called FULLPAGE() on page \"{self.current_page.title}\", here's the result: " + self.current_page.content


class HashWikiToolset(Toolset):
    model: Model

    @property
    def tools(self) -> [Tool]:
        return [
            FunctionTool(self.navigate, "NAVIGATE",
                         "导航到某个 Wikipedia 页面, 该页面必须存在. ",
                         "NAVIGATE(Taylor Swift) -> 到达 Taylor Swift 页面并返回页面总结; "
                         "NAVIGATE(Tayla Swift) -> 无法找到, 你是否在找 Taylor Swift",
                         self.color),
            FunctionTool(self.fullpage, "FULLPAGE",
                         "返回当前页面的所有内容",
                         "NAVIGATE(United States) -> United States is a country on American Continent. -> FULLPAGE() -> "
                         "United States is a country on American Continent. It's considered one of the most developed countries in the world. "
                         "the population is ......(a lot of words)",
                         self.color),
            FunctionTool(self.mark, "MARK",
                         "标记当前页面的一列内容, 它们会直接返回给委托者. ",
                         "正确使用方法:  ... -> FULLPAGE() -> "
                         "---------58efa0588c9af09d73714b563646d7ae--------- United States is a country on American Continent. ---------6332c273195c8c992bd279e1acb06a21--------- It's considered one of the most developed countries in the world. "
                         "the population is ......(a lot of words) -> MARK(58efa0588c9af09d73714b563646d7ae, 6332c273195c8c992bd279e1acb06a21) -> 标记成功! 您标记的两个块已经返回给委托者!  错误使用方法: MARK(United States, Population) -> 标记失败! 你输入的不是 MD5 码!",
                         self.color)
        ]

    class PageDocument:
        title: str
        summary: str
        related_titles: str
        hashes: [int]

        def __init__(self, title, summary, related_titles, hashes):
            self.title = title
            self.summary = summary
            self.related_titles = related_titles
            self.hashes = hashes

    def __init__(self, color: int = MESSAGE_COLOR_ORANGE):
        super().__init__()
        self.current_page = None
        self.color = color
        self.page_documents = {}  # standard_title -> PageDocument
        self.chunks = {} # hash -> str
        self.marked_hashes = set()

    @staticmethod
    def hash(string) -> str:
        return str(hashlib.md5(string.encode()).hexdigest())

    def document_a_page(self, page: wikipedia.WikipediaPage):
        if page.title in self.page_documents:
            return
        summary = page.summary
        related_titles = ", ".join(wikipedia.search(page.title))
        hash_list = []
        chunks = page.content.split("\n")
        for chunk in chunks:
            if chunk.strip() == "":
                continue
            hash_value = HashWikiToolset.hash(chunk)
            hash_list += [hash_value]
            self.chunks[hash_value] = chunk
        self.page_documents[page.title] = HashWikiToolset.PageDocument(
            page.title,
            summary,
            related_titles,
            hash_list
        )

    def navigate(self, title: str) -> str:
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        if "-" in title or "_" in title:
            return (f"You called NAVIGATE\"{title}\", which leads to an error. Because you can't put \"-\" or \"_\" "
                    f"in a page title. Call NAVIGATE(\"{title.replace("-", " ").replace("_", " ")}\") instead.")
        try:
            page = wikipedia.page(title, auto_suggest=False)
            assert page.title.lower() == title.lower()
            self.document_a_page(page)
            self.current_page = self.page_documents[page.title]

            return ("Title: " + self.current_page.title +
                    "\nShort Summary: \n" +
                    self.current_page.summary + "...(Ellipsis)... (use FULLPAGE to"
                                   " get the full article)" +
                    "\nRelated Pages: " + self.current_page.related_titles)
        except (wikipedia.DisambiguationError, AssertionError, wikipedia.exceptions.PageError) as e:
            self.current_page = None
            dash_prompt = ", Please Notice You are inputting _ (dash) instead of space, which might lead to error. " \
                if "_" in title else ""
            similar = wikipedia.search(title)
            if title in similar:
                similar.remove(title)
            return f"Could not find: \"{title}\" " + dash_prompt + ", Similar:" + str(similar)

    def fullpage(self, unused_str) -> str:
        if self.current_page is None:
            return ("Error: You called FULLPAGE() on a void page, which is not permitted. "
                    "You are on a void page because your last navigate was a failure")
        else:
            hashes = self.current_page.hashes
            content = ""

            for hash_value in hashes:
                is_marked = hash_value in self.marked_hashes
                is_marked_tip = " (marked)" if is_marked else ""
                content += "\n----- " + hash_value + is_marked_tip + " -----\n" + self.chunks[hash_value]

            return (f"You called FULLPAGE() on page \"{self.current_page.title}\", here's the result: " +
                    content + "\n Above is the return of FULLPAGE(). "
                              "Now, you're supposed to MARK some chunks by referring to their MD5s. ")

    def retrieve(self) -> str:
        content = ""
        for page_title, page_document in self.page_documents.items():
            page_content = ""
            hashes = page_document.hashes
            for hash in hashes:
                if hash in self.marked_hashes:
                    page_content += self.chunks[hash] + "\n"
            if page_content != "":
                content += "--------------\n" + f'in page "{page_title}":\n' + page_content + "\n"
        return content

    def mark(self, tickets_str) -> str:
        content = ""
        tickets = re.split(r'[,\s，]+', tickets_str)
        tickets = [ticket.strip() for ticket in tickets]
        for ticket in tickets:
            if ticket in self.chunks:
                chunk = self.chunks[ticket]
                if ticket in self.marked_hashes:
                    content += f"{ticket}: 重复标记. 你之前标记过这段了, 内容是: {chunk[:10]}....\n"
                else:
                    content += f"{ticket}: 标记成功. 内容是: {chunk[:10]}....\n"
                    self.marked_hashes.add(ticket)
            elif re.match(r'^[a-fA-F0-9]{32}$', ticket) is None:
                content += f"{ticket}: 标记失败. \"{ticket}\" 不是一个 MD5 值, 你只能输入 MD5 值. \n"
            else:
                content += f"{ticket}: 标记失败. 未找到这个内容. \n"

        return content

    def submit_process(self, submission) -> str:
        return submission + "\n" + self.retrieve()


class LinesWikiToolset(Toolset):
    @property
    def tools(self) -> [Tool]:
        return [
            FunctionTool(self.navigate, "NAVIGATE",
                         "导航到某个 Wikipedia 页面, 该页面必须存在. ",
                         "NAVIGATE(Taylor Swift) -> 到达 Taylor Swift 页面并返回页面总结; "
                         "NAVIGATE(Tayla Swift) -> 无法找到, 你是否在找 Taylor Swift",
                         self.color),
            FunctionTool(self.fullpage, "FULLPAGE",
                         "返回当前页面的所有内容",
                         "NAVIGATE(United States) -> United States is a country on American Continent. -> FULLPAGE() -> "
                         "United States is a country on American Continent. It's considered one of the most developed countries in the world. "
                         "the population is ......(a lot of words)",
                         self.color),
            FunctionTool(self.save_line_ranges, "SAVE_LINE_RANGES",
                         "保存输入的行号区间.保存的行被自动交给委托者.该工具参数是行号区间",
                         "SAVE_LINE_RANGES(10-13, 60-65, 20-25) -> 10-13:保存成功, 共计4行, 60-65: ...",
                         self.color)
        ]

    class PageDocument:
        title: str
        summary: str
        related_titles: str
        lines: [str]

        def __init__(self, title, summary, related_titles, lines):
            self.title = title
            self.summary = summary
            self.related_titles = related_titles
            self.lines = lines
            self.saved_line_idxs = set()

    def __init__(self, color: int = MESSAGE_COLOR_ORANGE):
        super().__init__()
        self.current_page = None
        self.color = color
        self.page_documents = {}  # standard_title -> PageDocument

    def document_a_page(self, page: wikipedia.WikipediaPage):
        if page.title in self.page_documents:
            return
        summary = page.summary
        related_titles = ", ".join(wikipedia.search(page.title))
        lines = list(filter(None, page.content.splitlines()))
        self.page_documents[page.title] = LinesWikiToolset.PageDocument(
            page.title,
            summary,
            related_titles,
            lines
        )

    def navigate(self, title: str) -> str:
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        title = title.replace("-", " ").replace("_", " ")
        try:
            page = wikipedia.page(title, auto_suggest=False)
            assert page.title.lower() == title.lower()
            self.document_a_page(page)
            self.current_page = self.page_documents[page.title]

            return ("Title: " + self.current_page.title +
                    "\nShort Summary: \n" +
                    self.current_page.summary + "...(Ellipsis)... (use FULLPAGE to"
                                                " get the full article)" +
                    "\nRelated Pages: " + self.current_page.related_titles)
        except (wikipedia.DisambiguationError, AssertionError, wikipedia.exceptions.PageError) as e:
            self.current_page = None
            similar = wikipedia.search(title)
            if title in similar:
                similar.remove(title)
            return f"Could not find: \"{title}\" " + ", Similar:" + str(similar)

    def fullpage(self, unused_str=None) -> str:
        if self.current_page is None:
            return ("Error: You called FULLPAGE() on a void page, which is not permitted. "
                    "You are on a void page because your last navigate was a failure")
        else:
            content = "\n".join([f"{idx}|{line}" for idx, line in enumerate(self.current_page.lines)])

            return (f"You called FULLPAGE() on page \"{self.current_page.title}\", here's the result: " +
                    content)

    def get_saved_lines(self) -> str:
        content = ""
        for page_title, page_document in self.page_documents.items():
            page_content = "\n".join([f"{idx}|{page_document.lines[idx]}"
                                      for idx in sorted(page_document.saved_line_idxs)])
            if page_content != "":
                content += "\n" + f'in page "{page_title}":\n' + page_content + "\n"
        return content

    def save_line_ranges(self, lines_str: str) -> str:
        def callback(idx: int):
            self.current_page.saved_line_idxs.add(idx)
        return parse_line_ranges(lines_str, callback, len(self.current_page.lines))

    def submit_process(self, submission) -> str:
        return submission + "\n" + self.get_saved_lines()
