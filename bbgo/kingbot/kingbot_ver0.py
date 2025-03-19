import math

import debots
from .consult_advisor import get_consult_advisor_function

SPAWN_WORKERS_NOUN = "SPAWN_WORKERS"
CONSULT_ADVISOR_NOUN = "CONSULT_ADVISOR"

def get_spawn_workers_example(enable_wikibot, enable_webbot, enable_filebot, n_available_workers):
    import math

    assert enable_wikibot or enable_webbot or enable_filebot
    intro = "例子是: (假设用户希望了解气候变化的影响和应对措施)\n"
    question_examples = [
        "气候变化对农业的具体影响",
        "气候变化对海洋生态的影响",
        "各国政府应对气候变化的政策",
        "企业在减少碳排放方面的行动",
        "个人减少碳足迹的实际方法"
    ]
    prefixes = {
        "wikibot": "在 Wikipedia 搜索",
        "webbot": "在互联网上详细调查",
        "filebot": "在文件系统中调查相关文档"
    }
    if enable_webbot:
        n_webbots = max(1, n_available_workers - int(enable_filebot) - int(enable_wikibot))
        n_wikibots = int(enable_wikibot)
        n_filebots = int(enable_filebot)
    else:
        n_webbots = 0
        if not enable_wikibot:
            n_filebots = n_available_workers
            n_wikibots = 0
        elif not enable_filebot:
            n_filebots = 0
            n_wikibots = n_available_workers
        else:
            n_filebots = int(math.floor(n_available_workers / 2))
            n_wikibots = n_available_workers - n_filebots
    bot_names = ["webbot"] * n_webbots + ["wikibot"] * n_wikibots + ["filebot"] * n_filebots
    examples = [bot_name + ": " + prefixes[bot_name] + question_examples[idx % len(question_examples)]
                for idx, bot_name in enumerate(bot_names)]
    return intro + "\n".join(examples) + "\n"


def kingbot_ver0(n_rounds: int=1,
                 n_available_workers: int=3,
                 kingbot_model: debots.Model = debots.cor_gpt4o_mini,
                 advisor_model: debots.Model = debots.cor_gpt4o_mini,
                 worker_model: debots.Model = debots.cor_gpt4o_mini,
                 enable_wikibot: bool = True,
                 enable_webbot: bool = True,
                 enable_filebot: bool = False,
                 max_operations_wikibot: int = 20,
                 max_operations_webbot: int = 20,
                 max_operations_filebot: int = 20,
                 webbot_auto_complete_saved_lines: bool=True,
                 file_root: str = None,
                 vdb_root: str = None,
                 kingbot_message_printer = None,
                 workers_print_type ="DONT_PRINT") -> debots.Bot:
    assert enable_wikibot or enable_webbot or enable_filebot
    if enable_filebot:
        assert file_root, vdb_root
    def filebot_generator():
        bot = debots.filebot_ver0(file_root, vdb_root, model=worker_model)
        bot.default_n = max_operations_filebot
        return bot
    def wikibot_generator():
        bot = debots.wikibot_marker(model=worker_model)
        bot.default_n = max_operations_wikibot
        return bot
    def webbot_generator():
        bot = debots.webbot_ver1(model=worker_model,
                                 auto_complete_saved_lines=webbot_auto_complete_saved_lines)
        bot.default_n = max_operations_webbot
        return bot
    available_bot_names = []
    if enable_wikibot:
        available_bot_names += ["wikibot"]
    if enable_webbot:
        available_bot_names += ["webbot"]
    if enable_filebot:
        available_bot_names += ["filebot"]
    available_bot_names_str = ",".join(available_bot_names)
    kingbot = debots.Bot(
        name="kingbot",
        desc=f"机器人世界的国王，同时也是用户 userbot 的臣子。擅长信息收集，拥有 {len(available_bot_names)} 种类型的 worker: {available_bot_names_str}",
        goal_guide=f"灵活借助顾问的智慧，合理分配 {available_bot_names_str} 的任务，确保搜集到最全面的信息。",
        submit_format="报告形式，包含所有搜集到的有价值信息。",
        examples="",
        examples_guide="",
        tools=[],
        tools_guide=f"你最多可以使用 {n_rounds} 次 {SPAWN_WORKERS_NOUN}，但可以无限次使用 {CONSULT_ADVISOR_NOUN}。"
                    f"在使用宝贵的 {SPAWN_WORKERS_NOUN} 之前，多与顾问交流。"
                    f"每次 {SPAWN_WORKERS_NOUN} 时，尽量确保所有 bot 的搜索方向相互独立，也就是让它们的子问题交叉尽可能少。",
        model=kingbot_model,
        default_n=20,
        color=debots.MESSAGE_COLOR_GOLD,
        message_printer=kingbot_message_printer
    )

    spawn_workers_tool = debots.FunctionTool(
        debots.get_spawn_bots_function([
            (wikibot_generator, "wikibot"),
            (webbot_generator, "webbot"),
            (filebot_generator, "filebot")
        ], kingbot, n_available_workers, n_rounds,
        bots_print_type=workers_print_type),
        SPAWN_WORKERS_NOUN,
        f'''你可以一次召唤最多 {n_available_workers} 个 workers，总共有 {n_rounds} 次召唤机会。
使用 SPAWN_WORKERS 的格式如下：
[botname]:[bot任务内容](在这里换行) * {n_available_workers}
示例：
{get_spawn_workers_example(enable_wikibot=enable_wikibot, enable_webbot=enable_webbot,
                           enable_filebot=enable_filebot, n_available_workers=n_available_workers)}

请注意：
1. 你召唤的 bot 唯一的记忆就是你提供的任务内容，因此任务内容必须写得非常详细，否则 bot 无法完成任务。
比如, 如果你要让一个bot收集气候变化对农业的影响,你不能直接说「收集对农业的影响」,这样的话它绝对会以为只要是对农业的影响都可以.
你必须说的非常清楚明白,是「气候变化对农业的影响」.你的bot都不知道用户的委托,只有你知道,所以你必须把用户的委托中的所有需要的相关信息都传递给bot.
2. {SPAWN_WORKERS_NOUN} 只能使用 {n_rounds} 次，请谨慎规划。
''',
        "",
        debots.MESSAGE_COLOR_DARK_RED
    )
    consult_cabinet_tool = debots.FunctionTool(
        get_consult_advisor_function(kingbot, advisor_model=advisor_model),
        CONSULT_ADVISOR_NOUN,
        f"向顾问提问，顾问可以帮你规划下一步、指出信息不足、进行推理等操作。{CONSULT_ADVISOR_NOUN}可无限使用。",
        "",
        debots.MESSAGE_COLOR_DARK_RED
    )

    kingbot.tools = [spawn_workers_tool, consult_cabinet_tool]

    return kingbot

