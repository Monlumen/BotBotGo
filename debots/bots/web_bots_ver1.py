
from debots.core import Model
from debots.message_colors import *
from debots.core.Bot import Bot
from debots.core.models import cor_gpt4o_mini
from debots.toolsets.web_toolsets.web_toolset_ver1 import WebToolsetVer1, SAVE_LINE_IDS_NOUN
from pydantic import BaseModel, Field
import random

def get_submit_evaluator(model: Model = cor_gpt4o_mini, min_requirement: int = 7):
    class Evaluation(BaseModel):
        relevance_evaluation: str = Field(...,description="报告是否直接回答委托者的问题，内容的整体相关性。")
        relevance_score: int = Field(...,  description="相关性评分，0 表示完全无关，10 表示高度相关。")
        sufficiency_evaluation: str = Field(...,description="报告中提供的事实和数据是否充足，以支持结论或回答委托者的问题。")
        sufficiency_score: int = Field(..., description="事实和数据的充足性评分，0 表示完全不足，10 表示完全充足。")
    system_prompt = f"一个委托者向一个网络信息搜索专员提出了一个调查委托,并收到了一份调查报告.你是一个专业的测评师,受雇于委托者,来检验调查报告是否合格."
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

def webbot_ver1(window_size: int = 5000, model: Model = cor_gpt4o_mini, evaluator_model: Model=cor_gpt4o_mini,
                evaluation_score_requirement=9, directly_selenium=True, auto_complete_saved_lines=False):
    selenium_user_name = str(random.randint(0, 100000))
    webenv = WebToolsetVer1(window_size, directly_selenium=directly_selenium,
                            selenium_user_name=selenium_user_name)

    return Bot(
        name="webbot",
        desc="网上冲浪的高手,能帮用户找到任何资料",
        goal_guide=f"在页面间跳转,用{SAVE_LINE_IDS_NOUN}批量标记资料",
        submit_format=f"介绍你用{SAVE_LINE_IDS_NOUN}标记的内容和结论.",
        examples="",
        examples_guide="努力分解问题.比如用户问\"Notion的创始人的业余爱好\",你就要分解为1.Notion的创始人是谁2.这个人的业余爱好是什么.所以你至少需要搜索两次",
        tools=webenv.tools,
        tools_guide=None,
        model=model,
        default_n=20,
        color= MESSAGE_COLOR_PURPLE,
        submit_processor=webenv.submit_process,
        submit_evaluator=get_submit_evaluator(evaluator_model, evaluation_score_requirement,),
        submit_processor_lazy=webenv.submit_process_lazy if auto_complete_saved_lines else None,
        submit_success_callback=webenv.logout_from_driver
    )

