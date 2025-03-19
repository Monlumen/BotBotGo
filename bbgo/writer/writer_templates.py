from pydantic import BaseModel, Field
from typing import List

# step 0: write outline
outline_prompt = '''你是国王 Kingbot 的记录官。国王刚完成了一次由手下执行的调查任务，现在需要你为这次调查撰写报告的大纲。

你的任务是：
1. 把聊天记录里的所有调查结果分为几个独立的子维度。每个子维度必须是材料内容中的核心要素，不能超出聊天记录中提到的范围。
2. 为每个维度提供清晰的解释, 让你的手下知道这个维度的定义是什么.
3. 你**不能**输出任何普适性的维度名.你**不能**输出"历史变革""新的趋势""对策"这些适用于任何问题的维度.一个好的维度是这样的维度:它放在这个问题里非常合适,
而放到任何其他问题都会不合适.

注意：手下会根据你的指导分别完成各自的维度，他们之间不会交流。你的指导必须准确、清晰，确保写作者能够独立完成任务，同时避免内容重复或遗漏。
请使用{language}作为主要语言'''

class DimensionInstruction(BaseModel):
    """表示单个小节的标题和写作指导"""
    title: str = Field(..., description="维度的名称.要新颖且独特.")
    definition: str = Field(..., description="维度的定义和解释")

class ReportOutline(BaseModel):
    """表示完整报告的大纲"""
    dimensions: List[DimensionInstruction] = Field(
        ...,
        description="包含所有维度的标题和解释的列表"
    )

# step 1: stuff dimensions

stuff_dimension_prompt = '''你是国王 kingbot 的记录官.
国王刚完成了一次由手下执行的调查任务，现在需要你从对话记录中提取一个特定维度的内容.
你负责的维度名称是{title}, 写这个维度的要求是{instruction}

你的任务是:
1. 从对话中搜集这个维度的所有信息
2. 找出这些信息里用户可能最关心的部分并输出
3. 你**不能**输出任何普适性的内容.你不能输出"理解和尊重是重要的""在新技术的加持下,出现了新的趋势"之类的可以用于任何一件事的话.
一句有信息量的话是这样的话:它放在这一维度非常合适,但是把它移动到其他任何维度都会不合适.
4. 请使用{language}作为主要语言
'''

stuff_dimension_prompt_ver1 = '''
在你面前的是国王kingbot派人调查某一事件的聊天记录，现在需要你从对话记录中提取一个特定维度的数据和事实.
你的任务:从这个对话中提取关于\"{title}\"的所有客观数据、事实并以直观结构输出, 写这个维度的要求是{instruction}

你的任务是:
1. 提取所有客观**数据**、事实、例子、清单
2. 将提取到的内容以子标题、列表的**清晰结构**输出
3. 若无必要, 不能输出概括性的话、抽象的话
4. 请使用{language}作为主要语言
'''

# step 2: page meta
rate_page_prompt_main = '''根据报告和页面内容,为所有页面给出一句话注释,为其与报告的相关性打分,为其信息密度打分,并为其选择一个代表性的emoji'''

class PageMetadata(BaseModel):
    '''表示一个页面的id, 一句话注释, 相关性评分, 信息密度评分, 代表性emoji'''
    page_id: int = Field(..., description="页面id")
    annotation: str = Field(..., description="一句话注释,这个页面讲了什么")
    relevance_rating: int = Field(..., description="页面和报告的相关程度.0分代表完全不相关.10分代表完全相关.")
    information_density_rating: int = Field(..., description="页面的信息密度.0分代表非常缺乏信息.10分代表富有信息.信息密度=信息量/页面长度.")
    emoji: str = Field(..., description="给这个页面选一个代表性的emoji,尽量减少与其他页面的重复")

class PageMetadataList(BaseModel):
    related_pages: List[PageMetadata] = Field(..., description="所有页面")


# step 3: dimension meta
rate_page_prompt_section = '''根据报告和页面内容,用一个短词形容每个页面与该报告的相关点,并给每个页面的相关性、信息量评分.'''

class PageRelevance(BaseModel):
    '''表示一个页面的id, 相关性评分, 相关点'''
    page_id: int = Field(..., description="页面id")
    relevance_point: str = Field(..., description="页面与报告的相关点,用一个短词表示.")
    relevance_rating: int = Field(..., description="页面和报告的相关程度.0分代表完全不相关.10分代表完全相关.")
    information_richness_rating: int = Field(..., description="页面的信息量评分.0分代表完全没信息.10分代表有很多信息.")

class PageRelevanceList(BaseModel):
    related_pages: List[PageRelevance] = Field(..., description="所有页面")


# step 4: translate
translate_page_prompt = '''Translate all texts of the following html into {language}. 
note:
1. Only texts with information should remain, and all the javascript and html tags should go.
2. all texts with information should be translated without adding or deleting anything.
3. reformat the output, do 3 things: a. break lines according to semantic structure. b. add markdown to titles(no #, only ## or smaller), if there exists title c. summarize a title if a chunk of words doesn't have one.
4. if already in {language}, then just reformat.'''

# step 5: refinement
refinement_prompt = '''Refine the paragraph of a report using the webpages.
note:
1. language: {language}
2. use as many facts and data as you can
3. don't change the focus of this paragraph
4. output in structured form
'''