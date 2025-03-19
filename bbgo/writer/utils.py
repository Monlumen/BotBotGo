import re

def stuff_prompt_template(template: str, **kwargs) -> str:
    for key, value in kwargs.items():
        template = template.replace("{" + key + "}", value)
    return template

def get_query(first_message_content: str) -> str:
    match = re.search(r"委托内容:\s*(.*)", first_message_content, re.DOTALL)

    if match:
        delegation_content = match.group(1).strip()  # 提取并去掉多余空格
        return delegation_content
    else:
        return ""