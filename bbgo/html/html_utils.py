import importlib.resources
import re
from markdown import markdown
from bbgo.parser.ParsedPage import ParsedPage
from bbgo.writer.Dimension import Dimension

HIDDEN = "hidden"

def read_html_file(file_name):
    package = "bbgo.html"
    with importlib.resources.open_text(package, file_name) as file:
        return file.read()

def remove_html_comments(content):
    # 移除 HTML 注释 <!-- ... -->
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    # 移除 CSS 注释 /* ... */
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    return content


main_template = read_html_file("main_template.html")
page_template = read_html_file("page_template.html")
section_template = read_html_file("section_template.html")
section_link_template = read_html_file("section_link_template.html")
navigate_item_template = read_html_file("navigate_item_template.html")

def page_name2id(page_name: str) -> str:
    return page_name.replace(" ", "-")

def stuff_html_template(template: str, **kwargs) -> str:
    def replace(match):
        key = match.group(1)
        return str(kwargs.get(key, match.group(0)))
    pattern = r"{%(.*?)%}"
    return re.sub(pattern, replace, template)

def parsed_page2html(page: ParsedPage) -> str:
    emoji = page.emoji
    emoji_display = "" if emoji != page.title.strip()[:1] else HIDDEN
    title = page.title
    id = page_name2id(title)
    url = page.url if page.url else ""
    url_display = "" if page.url else HIDDEN
    rating = page.rating
    rating_display = "" if page.rating else HIDDEN
    annotation = page.annotation if page.annotation else ""
    annotation_display = "" if page.annotation else HIDDEN
    content = markdown(escape_html_string(page.content))
    return stuff_html_template(page_template, name=title, url=url,
                               id=id,
                               emoji=emoji,emoji_display=emoji_display,
                               url_display=url_display, rating=rating,
                               rating_display=rating_display, annotation=annotation, annotation_display=annotation_display,
                               content=content)

def dimension2html(dimension: Dimension, lib: [ParsedPage]) -> str:
    def get_emoji(page_name: str):
        nonlocal lib
        for page in lib:
            if page.name == page_name:
                return page.emoji
        return ""

    content = dimension.refined_content if dimension.refined_content else dimension.content
    content = markdown(content)
    section_meta = ""

    maximum_rating = max(map(lambda x: x[2], dimension.page_relevance))
    for page_name, rel_keyword, rel_rating in dimension.useful_pages():
        rel_keyword = rel_keyword if rel_rating >= maximum_rating - 1 else ""
        section_meta += section_link_to_html(page_name, rel_keyword, rel_rating, get_emoji(page_name))
    return stuff_html_template(section_template, title=dimension.title, content=content,
                               meta=section_meta)

def dimensions2html(dimensions: [Dimension], lib: [ParsedPage]) -> str:
    return "".join(dimension2html(dimension, lib) for dimension in dimensions)

def lib2html(pages) -> str:
    return "<hr>".join(parsed_page2html(page) for page in pages)

def escape_html_string(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")

def section_link_to_html(page_name: str, rel_keyword: str, rel_rating: str, page_emoji: str) -> str:
    return stuff_html_template(section_link_template, page_id=page_name2id(page_name),
                               page_emoji=page_emoji, page_title=page_name,
                               rel_keyword=rel_keyword)

def parsed_page2navigate_item(idx, parsed_page):
    emoji = parsed_page.emoji
    emoji_display = "" if emoji else HIDDEN
    page_id = page_name2id(parsed_page.name)
    return stuff_html_template(navigate_item_template, emoji=emoji,
                               emoji_display=emoji_display, idx=idx+1,
                               page_id=page_id)

def lib2navigate(pages) -> str:
    return "".join(parsed_page2navigate_item(idx, parsed_page)
                   for idx, parsed_page in enumerate(pages))
