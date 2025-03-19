import bs4
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import os
from urllib.parse import urljoin
from selenium import webdriver
from debots.hyper_parameters import HEADERS
from debots.api_keys import current_serper_api_key
import time
import http
import json
import threading
import pyautogui
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import urllib.parse


PARSE_ERROR_TITLE = "Error Page"  # 当 parse 失败时, 返回的页面的标题
url2html = {}

session = requests.Session()

class SharedSingleDriver:
    def __init__(self):
        options = webdriver.ChromeOptions()
        self.driver = None

        self.user_tab_map = {}
        self.lock = threading.Lock()

    def switch_tab(self, user_name):
        if self.driver is None:
            options = webdriver.ChromeOptions()
            self.driver = webdriver.Chrome(options=options)

        if user_name in self.user_tab_map:
            self.driver.switch_to.window(self.user_tab_map[user_name])
        else:
            self.driver.switch_to.new_window('tab')
            self.user_tab_map[user_name] = self.driver.current_window_handle

    def load_url(self, url, user_name):
        with self.lock:
            self.switch_tab(user_name)
            self.driver.execute_script(f"window.location.href='{url}';") # 阻塞

    def has_load_completed(self, user_name):
        with self.lock:
            self.switch_tab(user_name)
            ready_state = self.driver.execute_script("return document.readyState")
            return ready_state == "complete"

    def get_loaded_html(self, user_name):
        with self.lock:
            self.switch_tab(user_name)
            return self.driver.page_source

    def end_loading(self, user_name):
        with self.lock:
            self.switch_tab(user_name)
            self.driver.execute_script("window.stop();")

    def logout(self, user_name):
        pass

class SharedDriverGroup:
    def __init__(self):
        options = webdriver.ChromeOptions()

        self.user_driver_map = {}
        self.offset_lock = threading.Lock()

    def get_driver(self, user_name):
        if user_name not in self.user_driver_map:
            with self.offset_lock:
                options = webdriver.ChromeOptions()
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
                self.user_driver_map[user_name] = driver

                # 设定窗口宽高
                screen_width, screen_height = pyautogui.size()
                driver.set_window_size(screen_width/2, screen_height - 50)

                # 设定左上角位置
                offset_per_window = 100
                print("offset len: " + str(len(self.user_driver_map) - 1))
                x = 0
                y = offset_per_window * (len(self.user_driver_map) - 1)
                driver.set_window_position(x, y)  # 左上角起点

        return self.user_driver_map[user_name]

    def load_url(self, url, user_name):
        driver = self.get_driver(user_name)
        driver.get(url)

    def has_load_completed(self, user_name):
        driver = self.get_driver(user_name)
        ready_state = driver.execute_script("return document.readyState")
        return ready_state == "complete"

    def get_loaded_html(self, user_name):
        driver = self.get_driver(user_name)
        return driver.page_source

    def end_loading(self, user_name):
        driver = self.get_driver(user_name)
        driver.execute_script("window.stop();")

    def logout(self, user_name):
        if user_name in self.user_driver_map:
            try:
                driver = self.user_driver_map[user_name]
                driver.quit()
                del self.user_driver_map[user_name]
            except Exception as e:
                print(f"Error during logout for user {user_name}: {e}")

    def set_load_time_limit(self, load_time_limit, user_name):
        driver = self.get_driver(user_name)
        driver.set_page_load_timeout(load_time_limit)

shared_driver_manager = SharedDriverGroup()

def logout(user_name):
    shared_driver_manager.logout(user_name)

def convert_to_full_url(base_url, url):
    # 去除前后空白
    if url is None or base_url is None:
        return ""

    url = url.strip()

    # 如果 URL 是以下无效格式，直接返回空字符串
    if not url or url.startswith(('javascript:', 'mailto:', '#')):
        return ""

    # 如果是完整的 URL，直接返回
    if url.startswith(('http://', 'https://')):
        return url

    # 否则，使用 urljoin 拼接成完整 URL
    return urljoin(base_url, url)


def get_text_with_a(tag, link_dict, base_url, strip=False, link_tag_name="a"):
    result = []
    for content in tag.contents:
        if content.name == 'a':  # 如果是 <a> 标签
            href = convert_to_full_url(base_url, content.get("href"))
            text = content.get_text().strip() if strip else content.get_text()
            if text.startswith("\"") and text.endswith("\""):
                text = text[1:-1]
            if href:
                result.append(f"<{link_tag_name}>" + text + f"</{link_tag_name}>")  # 保留原始 HTML
                link_dict[text] = href
            else:
                result.append(text)
        elif hasattr(content, 'contents'):  # 如果是其他标签，递归处理
            result.append(get_text_with_a(content, link_dict, base_url, strip=strip, link_tag_name=link_tag_name))
        elif isinstance(content, bs4.NavigableString):
            result.append(content.strip() if strip else content)
    return ''.join(result)

def directly_get_html(url):
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.content
    except Exception:
        return None

def selenium_get_html(url, load_timeout=10, user_name="default user"):
    global shared_driver_manager
    try:
        shared_driver_manager.set_load_time_limit(load_timeout, user_name)
        shared_driver_manager.load_url(url, user_name)
        start_time = time.time()
        while time.time() - start_time < load_timeout:
            if shared_driver_manager.has_load_completed(user_name):
                break
            time.sleep(0.5)  # 等待一段时间，避免频繁轮询
        return shared_driver_manager.get_loaded_html(user_name)
    except Exception as e:
        print(f"Error: {str(e).splitlines()[0]}")
        return None


def parse(url, link_tag_name="a", selenium_first=True, selenium_user_name="default user"):
    try:
        # use cached html
        html = None if url not in url2html else url2html[url]
        # get html from web
        if html is None:
            if selenium_first:
                html = selenium_get_html(url, user_name=selenium_user_name)
                if html is None:
                    html = directly_get_html(url)
            else:
                html = directly_get_html(url)
                if html is None:
                    html = selenium_get_html(url)
        # no html received
        if html is None:
            raise RuntimeError(f"Can't get the html of {url}")
        url2html[url] = html
        # 使用 BeautifulSoup 解析 HTML 内容
        soup = BeautifulSoup(html, 'html.parser')

        # 提取主要内容区域
        content = soup

        # 保存输出内容的列表
        output = []

        # 链接字典
        link_dict = {}

        def process_node(node, output_list):
            """递归处理节点"""
            # 处理直接可用的文本
            if node.name in ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "dd", "dt"]:
                text = get_text_with_a(node, link_dict, url, strip=True, link_tag_name=link_tag_name)
                if text:
                    if node.name[0] == "h":
                        text = f"<{node.name}>{text}</{node.name}>"
                    output_list.append(text)
                    return
            # 处理代码结点
            elif node.name in ["code", "pre"]:
                text = node.get_text()
                text = f"<{node.name}>\n" + text + f"</{node.name}>"
                if text:
                    output_list.append(text)
                    return
            # 处理表格
            elif node.name == "table":
                try:
                    sub_table = node.find('table')
                    if not sub_table:
                        table = pd.read_html(StringIO(str(node)))[0]  # 解析表格
                        caption = node.find('caption')
                        caption_text = (" caption=\"" + get_text_with_a(caption, link_dict, url, strip=True, link_tag_name=link_tag_name)
                                        + "\"") if caption else ""
                        output_list.append(f"<table{caption_text}>")
                        output_list.append(table.to_csv(index=False, header=True))
                        output_list.append("</table>")
                        return
                except Exception as e:
                    output_list.append("<table>FetchError</table>")

            # 遍历子节点
            if not hasattr(node, "children"):
                return
            for child in node.children:
                if hasattr(child, "name"):  # 确保是 HTML 标签
                    process_node(child, output_list)

        # 处理主要内容
        if content:
            process_node(content, output)

        return soup.title.get_text(), "\n".join(output), link_dict

    except Exception as e:
        return PARSE_ERROR_TITLE, "Can't open this page. ", {}

def duck_duck_go(query):
    """
    Scrape DuckDuckGo's non-JS web version for search results.

    :param query: The search query string.
    :return: A list of (title, description, url) tuples.
    """
    base_url = "https://duckduckgo.com/html/"
    params = {
        "q": query  # 查询关键字
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        # 发起 GET 请求
        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()

        # 解析 HTML 页面
        soup = BeautifulSoup(response.text, "html.parser")

        # 提取搜索结果
        results = []
        for result in soup.find_all("div", class_="result"):
            # 提取标题
            title_tag = result.find("a", class_="result__a")
            title = title_tag.text.strip() if title_tag else None

            # 提取链接
            link = title_tag["href"] if title_tag else None

            # 提取描述
            description_tag = result.find("a", class_="result__snippet")
            description = description_tag.text.strip() if description_tag else ""

            if title and link:
                results.append((title, description, link))

        return results
    except requests.exceptions.RequestException as e:
        return []

def duck_duck_go_with_fallbacks(query, verbal_fallback=False):
    """
    Scrape DuckDuckGo's non-JS web version for search results with fallback strategies,
    including a final fallback to google.serper.dev API.

    :param query: The search query string.
    :param api_key: API key for google.serper.dev.
    :return: A list of (title, description, url) tuples.
    """
    base_url = "https://duckduckgo.com/html/"
    fallback_url = "https://www.bing.com/search"  # Fallback to Bing search
    params = {
        "q": query  # Query string
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def parse_duckduckgo(html):
        """Parse DuckDuckGo HTML results."""
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for result in soup.find_all("div", class_="result"):
            title_tag = result.find("a", class_="result__a")
            title = title_tag.text.strip() if title_tag else None
            link = title_tag["href"] if title_tag else None
            description_tag = result.find("a", class_="result__snippet")
            description = description_tag.text.strip() if description_tag else ""
            if title and link:
                results.append((title, description, link))
        return results

    def parse_bing(html):
        """Parse Bing HTML results."""
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for result in soup.find_all("li", class_="b_algo"):
            title_tag = result.find("a")
            title = title_tag.text.strip() if title_tag else None
            link = title_tag["href"] if title_tag else None
            description_tag = result.find("p")
            description = description_tag.text.strip() if description_tag else ""
            if title and link:
                results.append((title, description, link))
        return results

    def google_serper_dev(query):
        """Query the google.serper.dev API."""
        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({"q": query})
        headers = {
            'X-API-KEY': current_serper_api_key.get(),
            'Content-Type': 'application/json'
        }
        try:
            conn.request("POST", "/search", payload, headers)
            res = conn.getresponse()
            data = res.read()
            result_json = json.loads(data)
            results = []
            # Parse organic results
            for item in result_json.get("organic", []):
                title = item.get("title")
                link = item.get("link")
                description = item.get("snippet", "")
                if title and link:
                    results.append((title, description, link))
            return results
        except Exception as e:
            print(f"google.serper.dev API failed: {e}")
            return []

    try:
        # Primary request to DuckDuckGo
        response = requests.get(base_url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        l = parse_duckduckgo(response.text)
        if l:
            return l
    except requests.exceptions.RequestException as e:
        print(f"DuckDuckGo request failed: {e}")

    try:
        # Fallback request to Bing
        if verbal_fallback:
            print("Attempting fallback to Bing...")
        response = requests.get(fallback_url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        l = parse_bing(response.text)
        if l:
            return l
    except requests.exceptions.RequestException as e:
        print(f"Bing fallback request failed: {e}")

    # fallback to google.serper.dev API
    if current_serper_api_key:
        if verbal_fallback:
            print("Attempting final fallback to google.serper.dev API...")
        l = google_serper_dev(query)
        if l:
            return l
    return []


SEARCH_PREFIX = "DDG:"
def parse_or_duck_duck_go(url, link_tag_name="a", directly_selenium=True, selenium_user_name="default user"):
    if url.startswith(SEARCH_PREFIX):
        link_dict = {}
        query = url[len(SEARCH_PREFIX):]
        results = duck_duck_go_with_fallbacks(query)
        content = "Search: " + query + "\nResults:\n"
        for idx, item in enumerate(results):
            content += f"<{link_tag_name}>{idx+1}</{link_tag_name}>: <{link_tag_name}>{item[0]}</{link_tag_name}>" + "\n  -" + item[1] + "\n"
            link_dict[item[0]] = item[2]
            link_dict[str(idx+1)] = item[2]
        return f"{query} at DuckDuckGo", content, link_dict
    else:
        return parse(url, link_tag_name=link_tag_name, selenium_first=directly_selenium,
                     selenium_user_name=selenium_user_name)