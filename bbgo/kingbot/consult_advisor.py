import debots
from pydantic import BaseModel, Field

KINGBOT_NAME = "kingbot"
ADVISOR_NAME = "curiousbot"


ADVISOR_PROMPT = (f"你是无知但好奇的顾问{ADVISOR_NAME},"
                  "你的目的是搞清楚\"{user_query}\",你输出的内容永远是你当前好奇的几个调查方向")

def get_consult_advisor_function(king: debots.Bot, advisor_model: debots.Model = debots.cor_gpt4o_mini):

    class AdvisorResponse(BaseModel):
        analyze: str = Field(..., description=f"{ADVISOR_NAME}的分析，必须以\"让我们一步步思考,\"开头。")
        say: str = Field(..., description=f"{ADVISOR_NAME}当前好奇的几个调查方向")

    def consult_advisor(inquiry: str) -> str:  # 返回 Consultant 的回复
        nonlocal king
        history = []
        for entry in king.history:
            history += [{"role": "user", "content": entry["content"]}]
        history += [{"role": "user", "content": f"{KINGBOT_NAME}对{ADVISOR_NAME}发问: {inquiry}? 现在我们还差哪些知识点?"}]

        system_prompt = ADVISOR_PROMPT.replace("{user_query}", king.last_prompt)
        consultant_response = advisor_model.structured_invoke(history, AdvisorResponse,
                                                              system_prompt_at_bottom=system_prompt)

        return consultant_response.say

    return consult_advisor

