import debots
from ..parser import ParsedHistory, ParsedPage
from .writer_templates import *
from .utils import *
import asyncio
import os
from datetime import datetime
import json
from bbgo.html.html_utils import (dimensions2html, lib2html,
                                  stuff_html_template, main_template,
                                  lib2navigate, HIDDEN, remove_html_comments,
                                  )
import re
from .Dimension import Dimension
from concurrent.futures import ThreadPoolExecutor


async def combine_coroutines(list_of_coroutines):
    return await asyncio.gather(*list_of_coroutines)

class Draft:

    def __init__(self, king_history, query="",
                 dimensions=None,
                 lib=None,
                 main_model=debots.cor_gpt4o_mini, language="中文",
                 content_model=debots.openrouter_gemini_flash_1point5,
                 translate=True,
                 translation_model=None,
                 refinement=True,
                 refinement_model=None):
        # 放置 query 和 history
        self.query = query
        self.history = []
        for entry in king_history:
            self.history += [{
                "role": "user",
                "content": entry["content"]
            }]
        # 如果有的话, 放置 dimensions 和 lib
        self.dimensions = dimensions if dimensions else [] # step 0 & 1
        self.lib = lib if lib else list(ParsedHistory(self.history).library) # step 2 & 3 & 4
        # 放置超参数
        self.main_model = main_model
        self.content_model = content_model if content_model else self.main_model
        self.language = language
        self.translate = translate
        self.translation_model = translation_model if translation_model else self.content_model
        self.refinement = refinement
        self.refinement_model = refinement_model if refinement_model else self.content_model

    def is_step_0_done(self):
        if self.dimensions:
            return True
        return False

    def step_0_write_outline(self):
        if self.is_step_0_done():
            return False
        self.dimensions = []
        outline = self.main_model.structured_invoke(self.history, ReportOutline,
                                                    system_prompt_at_bottom=stuff_prompt_template(outline_prompt,
                                                                                             language=self.language))
        for dimension in outline.dimensions:
           self.dimensions.append(Dimension(title=dimension.title, instruction=dimension.definition))
        return True

    def is_step_1_done(self):
        return any(map(lambda x: x.content, self.dimensions))

    def step_1_stuff_dimensions(self):
        if self.is_step_1_done() or not self.is_step_0_done():
            return False
        futures = []
        with ThreadPoolExecutor() as executor:
            for dimension in self.dimensions:
                system_prompt = stuff_prompt_template(stuff_dimension_prompt, title=dimension.title,
                                                      instruction=dimension.instruction,
                                                      language=self.language)
                futures.append(executor.submit(self.content_model.invoke, self.history,
                                                      "", system_prompt))
            results = [future.result() for future in futures]
        for i, result in enumerate(results):
            self.dimensions[i].content = result
        for dimension in self.dimensions:
            cleaned_content = re.sub(f"#+ {dimension.title}\n+", "", dimension.content)
            dimension.content = cleaned_content
        return True

    def get_simple_lib_str(self): # used in step2 & step3
        return "\n\n".join(f"页面id: {idx}\n页面内容:\n{page.content}"
                           for idx, page in enumerate(self.lib))

    def is_step_2_done(self):
        return any(map(lambda x: x.rating, self.lib))

    def step_2_page_meta(self):
        if self.is_step_2_done() or not self.is_step_1_done():
            return False
        user_content_common = self.get_simple_lib_str()
        user_content_main = "报告内容: [" + ", ".join(dimension.title_content()
                                                    for dimension in self.dimensions) + "]"
        system_prompt = rate_page_prompt_main
        related_pages = self.main_model.structured_invoke([
            {"role": "user", "content": user_content_common},
            {"role": "user", "content": user_content_main},
        ], data_model=PageMetadataList, system_prompt_at_bottom=system_prompt).related_pages
        for related_page in related_pages:
            if 0 <= related_page.page_id < len(self.lib):
                self.lib[related_page.page_id].rating = (related_page.relevance_rating +
                                                         related_page.information_density_rating) / 2
                self.lib[related_page.page_id].annotation = related_page.annotation
                self.lib[related_page.page_id].emoji = related_page.emoji[:1] if related_page.emoji \
                    else ""
        return True

    def is_step_3_done(self):
        return any(map(lambda x: x.page_relevance, self.dimensions))

    def step_3_dim_meta(self):
        if self.is_step_3_done() or not self.is_step_1_done(): # 实际上 step 3 不需要 step 2
            return False
        user_content_common = self.get_simple_lib_str()

        def worker(messages, system_prompt):
            return self.main_model.structured_invoke(messages, PageRelevanceList, "", system_prompt)
        with ThreadPoolExecutor() as executor:
            futures = []
            for dimension in self.dimensions:
                user_content_dim = f"报告标题:{dimension.title}\n报告内容:{dimension.content}"
                messages = [
                    {"role": "user", "content": user_content_common},
                    {"role": "user", "content": user_content_dim}
                ]
                system_prompt = rate_page_prompt_section
                futures.append(executor.submit(worker, messages, system_prompt))
            results = [future.result() for future in futures]

        for i_dim, result in enumerate(results):
            dimension = self.dimensions[i_dim]
            related_pages = result.related_pages
            for page_relevance in related_pages:
                if 0 <= page_relevance.page_id < len(self.lib):
                    page_name = self.lib[page_relevance.page_id].name
                    dimension.page_relevance.append((
                        page_name,
                        page_relevance.relevance_point,
                        (page_relevance.relevance_rating + page_relevance.information_richness_rating) / 2
                    ))
        return True

    def is_step_4_done(self):
        if not self.translate:
            return True
        return any(map(lambda x: x.translation, self.lib))

    def step_4_translate(self):
        if self.is_step_4_done():
            return False
        system_prompt = stuff_prompt_template(translate_page_prompt, language=self.language)
        coroutines = []
        for page in self.lib:
            coroutines.append(self.translation_model.async_invoke([
                {"role": "user", "content": page.content},
            ], system_prompt_at_top=system_prompt))
        results = asyncio.run(combine_coroutines(coroutines))
        for idx, translation in enumerate(results):
            self.lib[idx].translation = translation
        return True

    def is_step_5_done(self):
        if not self.refinement:
            return True
        return any(map(lambda x: x.refined_content, self.dimensions))

    def step_5_refinement(self):
        if self.is_step_5_done() or not self.is_step_3_done():
            return False
        system_prompt = stuff_prompt_template(refinement_prompt, language=self.language)
        coroutines = []
        for dimension in self.dimensions:
            messages = []
            for page_name, _, _ in dimension.useful_pages():
                the_page = None
                for page in self.lib:
                    if page.name == page_name:
                        the_page = page
                        break
                if the_page:
                    messages += [{
                        "role": "user",
                        "content": f"webpage title: {the_page.name}\n"
                                   f"{the_page.content}"
                    }]
            messages += [{
                "role": "user",
                "content": f"paragraph of a report\n"
                           f"report title: {self.query}\n"
                           f"paragraph title: {dimension.title}\n"
                           f"paragraph content to be refined: {dimension.content}"
            }]
            coroutines.append(self.refinement_model.async_invoke(
                messages, system_prompt_at_bottom=system_prompt
            ))
        results = asyncio.run(combine_coroutines(coroutines))
        for idx, refined_content in enumerate(results):
            self.dimensions[idx].refined_content = refined_content
        return True

    def save(self, directory="saved_drafts", prefix="draft"):
        """保存当前对象状态到文件"""
        if not os.path.exists(directory):
            os.makedirs(directory)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(directory, f"{prefix}_{timestamp}.json")

        # 保存数据到文件
        data = {
            "history": self.history,
            "query": self.query,
            "dimensions": [dimension.to_dict() for dimension in self.dimensions],
            "lib": [page.to_dict() for page in self.lib]
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return filename

    @classmethod
    def load(cls, filepath,
             writer_model=debots.cor_gpt4o_mini, language="中文",
             translate=True,
             translation_model=debots.openrouter_gemini_flash_1point5):
        """从文件加载到当前实例"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            king_history=data.get("history"),
            query=data.get("query", ""),
            dimensions=[Dimension.from_dict(dimension_dict)
                        for dimension_dict in data.get("dimensions", [])],
            lib=[ParsedPage.from_dict(page_dict)
                 for page_dict in data.get("lib", [])],
            main_model=writer_model, language=language,
            translate=translate,
            translation_model=translation_model
        )

    def to_html(self) -> str:  # dirty code
        if not (self.is_step_0_done() and self.is_step_1_done() and
                self.is_step_2_done() and self.is_step_3_done() and self.is_step_4_done()):
            return "Draft should be finished before compiling"

        self.lib.sort(key=lambda x: x.rating, reverse=True)
        sections_html = dimensions2html(self.dimensions, self.lib)
        lib_html = lib2html(self.lib)
        navigate_html = lib2navigate(self.lib)
        query = self.query if self.query else get_query(self.history[0]["content"])
        # 如果没有记录 query , 就从聊天记录的第一行获取 (为了向后兼容)
        query = "忘记您的查询内容了! 这是来自旧版本的 Draft 吗?" if not query else query
        query_display = ""
        html = stuff_html_template(main_template, sections=sections_html,
                                   pages=lib_html, query=query, query_display=query_display,
                                   title=query, navigate=navigate_html)
        return remove_html_comments(html)

    def save_as_html(self, filepath="output.html") -> bool:
        html = self.to_html()
        if len(html) < 20:
            return False
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(html)
        return True