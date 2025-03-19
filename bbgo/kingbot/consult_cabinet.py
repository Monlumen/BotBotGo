import debots
from pydantic import BaseModel, Field
import concurrent.futures

import debots.core.models

KINGBOT_NAME = "kingbot"
SERIOUSBOT_NAME = "seriousbot"
GENIUSBOT_NAME = "geniusbot"
CURIOUSBOT_NAME = "curiousbot"
WIKIBOT_NAME = "wikibot"
WEBBOT_NAME = "webbot"
FILEBOT_NAME = "filebot"

SERIOUSBOT_PROMPT = (f"你扮演{SERIOUSBOT_NAME},是国王{KINGBOT_NAME}的一位顾问."
                     f"你注意到{KINGBOT_NAME}正在派{WIKIBOT_NAME},{WEBBOT_NAME}和{FILEBOT_NAME}搜集信息,以完成一份委托."
                     f"{SERIOUSBOT_NAME},你是一个刻板严肃的检查者,请列出高质量完成委托的三到五个要求(这些要求需要彼此正交)"
                     f",并说明目前的完成情况")
GENIUSBOT_PROMPT = (f"你扮演{GENIUSBOT_NAME},是国王{KINGBOT_NAME}的一位顾问."
                    f"你注意到{KINGBOT_NAME}正在派{WIKIBOT_NAME},{WEBBOT_NAME}和{FILEBOT_NAME}搜集信息,以完成一份委托."
                    f"{GENIUSBOT_NAME},你是一个天才推理家,请根据{WIKIBOT_NAME},{WEBBOT_NAME},{FILEBOT_NAME}返回的信息(以下简称为现有信息)推导出新的信息."
                    f"你的任何推导都必须基于现有信息."
                    f"如果现有信息太少,你就列出几个你希望获取信息的方向,这些方向应当彼此正交.")
CURIOUSBOT_PRMPT = (f"你扮演{CURIOUSBOT_NAME},是国王{KINGBOT_NAME}的一位顾问."
                     f"你注意到{KINGBOT_NAME}正在派{WIKIBOT_NAME},{WEBBOT_NAME}和{FILEBOT_NAME}搜集信息,以完成一份委托."
                     f"{CURIOUSBOT_NAME},你是一个好奇的探索者,请给国王提出三到五个下一步探索的维度."
                     f"这些维度应该彼此正交.")
NAME_PROMPT_PAIRS = [
    (SERIOUSBOT_NAME, SERIOUSBOT_PROMPT),
    (GENIUSBOT_NAME, GENIUSBOT_PROMPT),
    (CURIOUSBOT_NAME, CURIOUSBOT_PRMPT)
]

def get_consult_cabinet_function_ver0(king: debots.Bot, consultant_model: debots.Model = debots.core.models.openai_gpt4o_mini):

    class ConsultantResponse(BaseModel):
        analyze: str = Field(...,description="作为顾问,对问题的分析过程,必须以\"让我们一步步思考,\"开头")
        say: str = Field(..., description="对国王说的话")

    def log_consultant_message(history, consultant_name, consultant_prompt) -> str:
        nonlocal ConsultantResponse, consultant_model, king
        consultant_response = consultant_model.structured_invoke(history, ConsultantResponse,
                                                                 system_prompt_at_bottom=consultant_prompt)
        king.log_message(debots.Message(
            debots.Entity(consultant_name, ""),
            king,
            consultant_response.say
        ))
        return f"{consultant_name} 对 {KINGBOT_NAME} 说: {consultant_response.say}"

    def consult_cabinet(inquiry: str) -> str:  # 根据 king 的历史给 king 塞 3 条顾问信息, 并返回固定字符串
        nonlocal king
        history = []
        for entry in king.history:
            history += [{"role": "user", "content": entry["content"]}]
        history += [{"role": "user", "content": f"{KINGBOT_NAME}对{SERIOUSBOT_NAME},{GENIUSBOT_NAME}和{CURIOUSBOT_NAME}发问: {inquiry}"}]

        # seriousbot 和 geniusbot 需要先发言, 来为 curiousbot 的发言做铺垫
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor: # 同步发言以节省时间
            futures = [executor.submit(log_consultant_message, history, entry[0], entry[1])
                       for entry in NAME_PROMPT_PAIRS[:-1]]
            response_contents = [future.result() for future in concurrent.futures.as_completed(futures)]
            for content in response_contents:
                history += [{"role": "user", "content": content}]
        # curiousbot 发言
        log_consultant_message(history, CURIOUSBOT_NAME, CURIOUSBOT_PRMPT)

        return f"{KINGBOT_NAME}殿下,您的三位顾问已为您解答完毕.您可以再让他们解答其他问题,或是作出行动."

    return consult_cabinet

