from types import FunctionType
from pydantic import BaseModel, Field
from typing import List

import debots


def parse_line_ranges(lines_str: str, callback: FunctionType, num_lines_of_page: int) -> str:
    # 两种情况会恰好发生一种:
    # 返回值 str 是操作成功与否的报告
    # callback 会拿到解析到的行号作为输入
    segments = lines_str.split(",")
    response = ""
    for segment in segments:
        segment = segment.strip()
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
            if not 0 <= terminal < num_lines_of_page:
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
            callback(i)
        response += f"{segment}: Success: {terminals[1] - terminals[0] + 1} line{'s' if terminals[0] != terminals[1] else ''} saved\n"

    return response

def find_next_with_ai_fallback(keys_str: str,
                               page_lines: [str],  # 本页所有的行
                               start_line_idx: int,  # 从哪一行开始搜
                               return_at,  # 回调函数, 接受 idx(以全文视角的 idx): int 和 tip: str 作为输入, 输出一个找到的屏幕
                               tokenizer,  # 用于估算窗口 token 数量的 tokenizer
                               max_window_tokens = 20000,  # 最大允许提供给搜索 ai 多少个 token
                               ai_model: debots.Model = debots.cor_gpt4o
                               ) -> str: # str 是一个关于找到与否的简单描述, 可以不使用
    keys = keys_str.split(",")
    found_at = -1
    found = ""
    for line_idx in range(start_line_idx, len(page_lines)):
        line = page_lines[line_idx]
        for key in keys:
            if key.lower() in line.lower():
                found_at = line_idx
                found = key
                break
        if found_at != -1:
            break
    if found_at != -1: # 硬匹配找到了
        return return_at(found_at, tip=f"(Found \"{found.strip()}\" at line {found_at})\n")
    else: # 硬匹配没找到, 现在试试用 AI 来软匹配
        class QueryRelatedLine(BaseModel):
            """
            表示文档中某一行与查询 (query) 的相关性。
            """
            line_idx: int = Field(..., description="行号，从 0 开始计数。")
            relevance_score: int = Field(
                ...,
                description="该行与查询 (query) 的相关程度。0 表示完全不相关，10 表示高度相关。"
            )

        class QueryRelatedLines(BaseModel):
            """
            函数输出结果：包含与查询 (query) 相关的所有行及其相关性评分。
            """
            lines: List[QueryRelatedLine] = Field(
                ...,
                description="一个包含相关行的列表，每个元素表示某行与查询的相关性。"
            )
        lines_to_search = []
        in_window_tokens = 0
        for line in page_lines[start_line_idx:]:
            lines_to_search += [line]
            in_window_tokens += len(tokenizer.encode(line))
            if in_window_tokens > max_window_tokens:
                break
        lines_content = "".join([f"{start_line_idx+line_idx}|{line}\n" for line_idx, line in enumerate(lines_to_search)])
        system_prompt = "你是一个眼睛超敏捷的秘书.你要从用户的article中返回与用户的query有关的行号.如果没有,就返回空列表"
        user_content_0 = f"article如下:\n{lines_content}"
        user_content_1 = f"query是{keys_str}"
        query_related_line_list = ai_model.structured_invoke([
            {"role": "user", "content": user_content_0},
            {"role": "user", "content": user_content_1}
        ],
            system_prompt_at_bottom=system_prompt,
            data_model=QueryRelatedLines
        ).lines
        query_related_line_list = list(filter(lambda x: x.relevance_score > 5, query_related_line_list))
        if not query_related_line_list:
            return f"No lines found related to {keys_str}"
        highest_score = max(map(lambda x: x.relevance_score, query_related_line_list))
        query_related_line_list = sorted(query_related_line_list, key=lambda x: x.relevance_score)
        for line_info in query_related_line_list:
            if line_info.relevance_score >= highest_score - 1:
                return return_at(line_info.line_idx, tip=f"(Approximate match found at line {line_info.line_idx})\n")
        return f"No lines found related to {keys_str}" # 这行不应该被运行到