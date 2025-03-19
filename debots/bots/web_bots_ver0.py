
from debots.core import Model
from debots.message_colors import *
from debots.core.Bot import Bot
from debots.core.models import cor_gpt4o_mini
from debots.toolsets.web_toolsets.web_toolset import WebToolsetVer0, DUCK_DUCK_GO, CLICK, FIND_NEXT, SAVE_LINE_IDS

def webbot_ver0(window_size: int = 10000, model: Model = cor_gpt4o_mini):
    webenv = WebToolsetVer0(window_size)
    return Bot(
        name="webbot",
        desc="探索网络的高手, 它能从网上帮你找到任何东西! ",
        goal_guide=f"在网上严格按照用户的要求寻找资料, 并使用 {SAVE_LINE_IDS} 传递给用户.",
        submit_format=f"介绍你用 {SAVE_LINE_IDS} 传递了哪些东西, 得到了什么结论.",
        examples="",
        examples_guide="总是分解问题.比如用户问\"Notion的创始人的业余爱好\",你就要分解为1.Notion的创始人是谁2.这个人的业余爱好是什么.所以你至少需要搜索两次",
        tools=webenv.tools,
        tools_guide=f"用 {DUCK_DUCK_GO} 搜索内容, 用 {CLICK} 点击<a></a>包住的内容, 用 {FIND_NEXT} 进行页内查找, 用 {SAVE_LINE_IDS} 将网络信息传递给用户",
        model=model,
        default_n=20,
        color= MESSAGE_COLOR_PURPLE,
        submit_processor=webenv.submit_process
    )

