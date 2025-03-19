
from debots.core import Model
from debots.message_colors import *
from debots.core.Bot import Bot
from debots.core.models import cor_gpt4o_mini
from debots.toolsets import FileToolsetVer0
from pydantic import BaseModel, Field
from debots.toolsets.file_toolsets.file_toolset import OPEN_FILE_NOUN,CLOSE_FILE_NOUN,UP_NOUN,LS_NOUN,CD_NOUN,SEARCH_NOUN,SCROLL_UP_NOUN,SCROLL_DOWN_NOUN,SAVE_LINE_RANGES_NOUN,FIND_NEXT_NOUN

def get_submit_evaluator(model: Model = cor_gpt4o_mini, min_requirement: int = 7):
    class Evaluation(BaseModel):
        relevance_evaluation: str = Field(...,description="报告是否直接回答委托者的问题，内容的整体相关性。")
        relevance_score: int = Field(...,  description="相关性评分，0 表示完全无关，10 表示高度相关。")
        sufficiency_evaluation: str = Field(...,description="报告中提供的事实和数据是否充足，以支持结论或回答委托者的问题。")
        sufficiency_score: int = Field(..., description="事实和数据的充足性评分，0 表示完全不足，10 表示完全充足。")
    system_prompt = f"一个委托者向一个信息搜索专员提出了一个调查委托,并收到了一份调查报告.你是一个专业的测评师,受雇于委托者,来检验调查报告是否合格."
    def submit_evaluator(delegation_content, submit_content) -> (bool, str):
        nonlocal Evaluation, model, min_requirement
        user_message_0 = f"我委托的内容是:{delegation_content}"
        user_message_1 = f"我收到的调查报告是:{submit_content}"
        evaluation = model.structured_invoke(
            [
                {"role": "user", "content": user_message_0},
                {"role":"user","content":user_message_1}
            ],
            Evaluation,
            system_prompt_at_bottom=system_prompt
        )
        ok = True
        evaluation_content = ""
        if evaluation.relevance_score < min_requirement:
            ok = False
            evaluation_content += f"报告与委托的相关性:至少需要{min_requirement}分,你得到了{evaluation.relevance_score}分.原因是:{evaluation.relevance_evaluation}\n"
        if evaluation.sufficiency_score < min_requirement:
            ok = False
            evaluation_content += f"事实和数据的充分度:至少需要{min_requirement}分,你得到了{evaluation.sufficiency_score}分.原因是{evaluation.sufficiency_evaluation}\n"
        return ok, evaluation_content
    return submit_evaluator

def filebot_ver0(file_dir: str, vdb_dir: str,
                window_size: int = 5000, model: Model = cor_gpt4o_mini,
                evaluator_model: Model=cor_gpt4o_mini, evaluation_score_requirement=6):
    fileenv = FileToolsetVer0(file_dir, vdb_dir, window_size=window_size)
    return Bot(
        name="filebot",
        desc="查询文件系统的高手,能搜刮整个文件系统中的所有用户想要的资料",
        goal_guide=f"在文件间跳转,用 {SAVE_LINE_RANGES_NOUN} 批量标记资料",
        submit_format=f"介绍你用 {SAVE_LINE_RANGES_NOUN} 标记的内容和结论.",
        examples="",
        examples_guide="",
        tools=fileenv.tools,
        tools_guide=f"在browser中使用browser提供的工具找到有趣的文件,使用{OPEN_FILE_NOUN},"
                    f"在文件中使用notepad提供的工具导航,用{SAVE_LINE_RANGES_NOUN}标记资料,使用{CLOSE_FILE_NOUN},循环.",
        model=model,
        default_n=20,
        color= MESSAGE_COLOR_PURPLE,
        submit_processor=fileenv.submit_process,
        submit_evaluator=get_submit_evaluator(evaluator_model, evaluation_score_requirement),
    )

