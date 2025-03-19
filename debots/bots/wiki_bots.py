from debots import Model
from debots.message_colors import *
from debots.core.Bot import Bot
from debots.core.models import cor_gpt4o_mini
from debots.toolsets.wiki_toolsets.wiki_toolsets import FullPageWikiToolset, HashWikiToolset

from debots.toolsets.wiki_toolsets.wiki_toolsets import WikiToolset

def wikibot(model: Model = cor_gpt4o_mini, wiki_model: Model = cor_gpt4o_mini):
    wikienv = WikiToolset(wiki_model)
    return Bot(
        name="wikibot",
        desc="搜索 wikipedia 的高手, 它能从 wikipedia 上帮你找到任何东西! ",
        goal_guide="按照用户要求从 wikipedia 上搜索所有相关信息",
        submit_format="长篇幅分条列举, 用大型报告的形式汇报你的所有发现, 要有详细的数据和事实支撑. "
                      "比如, 你不能说 1. A 存在  2. 有人认为 B  3. 我发现了 C  "
                      "而应该说 1. A 存在, 因为..., 也有认为, 至今观测到.., 可能有,... 但是也有人反驳说...."
                      " 2. 有人认为...., 他们列举了... 数据, 引用了.... 事实, 目前这个观点引发的事件有...."
                      " 3. 在搜索 ... 时, 我发现了 C, 它的具体定义是 ..., 它之所以说服人, 是因为..., 这样的话就会....,"
                      "这样的话就一定是 ...."
                      "  4. 重要的事实是 D, 这件事情在 ... 发生, 具体的过程是...., 引发了这些反响 ...., 大家这么评论这件事...."
                      " 5...... 6..... .......",
        examples="",
        examples_guide="如果你搜的关键词没有直接的页面, 有可能是你选择的关键词太细了. 比如你要找 A在B时的C, 那么大概率是没有这么细的页面的. 此时, 你可以 NAVIGATE(A), "
                       "然后 LOOKUP(B时的C), 或者 NAVIGATE(B时的C的总体情况), 然后 LOOKUP(A) 等. 这些做法都很可能给你信息.",
        tools=wikienv.tools,
        tools_guide=           "NAVIGATE 是搜索某个 Wikipedia 页面, 如果该页面存在, 就返回该页面的简要概括和相似页面. NAVIGATE 的参数只接受英文, 不接受任何其他语言."
                               "如果该页面不存在, 有可能返回该页面的类似页面, 也可能报错. "
                               "NAVIGATE 只会显示这个页面的部分内容, 在 NAVIGATE 一般都会使用 LOOKUP 来获取更详细的信息."
                               "LOOKUP 通常在 NAVIGATE 后使用, 用于向页面询问某个问题, 页面会返回此页中与该问题有关的事实. "
                               "FULLPAGE 通常是 LOOKUP 无法解决某个问题时才使用, 它不需要任何参数. 它会返回目前的整个页面, 内容量有可能会很大. ",
        model=model,
        default_n=20,
        color= MESSAGE_COLOR_PURPLE
    )

def wikibot_fullpage(model: Model = cor_gpt4o_mini):
    wikienv_fullpage = FullPageWikiToolset()
    return Bot(
        name="wikibot",
        desc="搜索 wikipedia 的高手, 它能从 wikipedia 上帮你找到任何东西! ",
        goal_guide="按照用户要求从 wikipedia 上搜索所有相关信息",
        submit_format="长篇幅分条列举, 用大型报告的形式汇报你的所有发现, 要有详细的数据和事实支撑. "
                      "比如, 你不能说 1. A 存在  2. 有人认为 B  3. 我发现了 C  "
                      "而应该说 1. A 存在, 因为..., 也有认为, 至今观测到.., 可能有,... 但是也有人反驳说...."
                      " 2. 有人认为...., 他们列举了... 数据, 引用了.... 事实, 目前这个观点引发的事件有...."
                      " 3. 在搜索 ... 时, 我发现了 C, 它的具体定义是 ..., 它之所以说服人, 是因为..., 这样的话就会....,"
                      "这样的话就一定是 ...."
                      "  4. 重要的事实是 D, 这件事情在 ... 发生, 具体的过程是...., 引发了这些反响 ...., 大家这么评论这件事...."
                      " 5...... 6..... .......",
        examples="",
        examples_guide="如果你搜的关键词没有直接的页面, 有可能是你选择的关键词太细了. 比如你要找 A在B时的C, 那么大概率是没有这么细的页面的. 此时, 你可以 NAVIGATE(A), "
                       "然后 FULLPAGE() 寻找其中的B时的C , 或者 NAVIGATE(B时的C的总体情况), 然后 FULLPAGE() 寻找 A 等. 这些做法都很可能给你信息.",
        tools=wikienv_fullpage.tools,
        tools_guide=           "NAVIGATE 是搜索某个 Wikipedia 页面, 如果该页面存在, 就返回该页面的简要概括和相似页面. NAVIGATE 的参数只接受英文, 不接受任何其他语言."
                               "如果该页面不存在, 有可能返回该页面的类似页面, 也可能报错. "
                               "NAVIGATE 只会显示这个页面的部分内容, 如果这部分信息不够, 使用 FULLPAGE 获取页面的全部内容."
                               "FULLPAGE 它不需要任何参数. 它会返回目前的整个页面, 内容量有可能会很大. ",
        model=model,
        default_n=20,
        color= MESSAGE_COLOR_PURPLE
    )

def wikibot_marker(model: Model = cor_gpt4o_mini):
    wikienv_hash = HashWikiToolset()

    submit_format = f'''长篇幅分条列举, 用大型报告的形式汇报你的所有发现, 要有详细的数据和事实支撑. "
    "比如, 你不能说 1. A 存在  2. 有人认为 B  3. 我发现了 C  "
    "而应该说 1. A 存在, 因为..., 也有认为, 至今观测到.., 可能有,... 但是也有人反驳说...."
    " 2. 有人认为...., 他们列举了... 数据, 引用了.... 事实, 目前这个观点引发的事件有...."
    " 3. 在搜索 ... 时, 我发现了 C, 它的具体定义是 ..., 它之所以说服人, 是因为..., 这样的话就会....,"
    "这样的话就一定是 ...."
    "  4. 重要的事实是 D, 这件事情在 ... 发生, 具体的过程是...., 引发了这些反响 ...., 大家这么评论这件事...."
    " 5...... 6..... .......'''

    return Bot(
        name="wikibot",
        desc="搜索 wikipedia 的高手, 它能从 wikipedia 上帮你找到任何东西! ",
        goal_guide="按照用户要求从 wikipedia 上搜索所有相关信息, 通过 MARK 标记给用户, 然后通过 SUBMIT 提出一段总结.",
        submit_format=submit_format,
        examples="",
        examples_guide="如果你搜的关键词没有直接的页面, 有可能是你选择的关键词太细了. 比如你要找 A在B时的C, 那么大概率是没有这么细的页面的. 此时, 你可以 NAVIGATE(A), "
                       "然后 FULLPAGE() 寻找其中的B时的C , 或者 NAVIGATE(B时的C的总体情况), 然后 FULLPAGE() 寻找 A 等. 这些做法都很可能给你信息.\n"
                       "",
        tools=wikienv_hash.tools,
        tools_guide=           "NAVIGATE 是搜索某个 Wikipedia 页面, 如果该页面存在, 就返回该页面的简要概括和相似页面. NAVIGATE 的参数只接受英文, 不接受任何其他语言."
                               "如果该页面不存在, 有可能返回该页面的类似页面, 也可能报错. "
                               "NAVIGATE 只会显示这个页面的部分内容, 如果这部分信息不够, 使用 FULLPAGE 获取页面的全部内容."
                               "FULLPAGE 它不需要任何参数. 它会返回目前的整个页面, 内容量有可能会很大. "
                               "MARK 用于将你看到的内容传递给委托人. 你可以看到 Wikipedia 给你的所有内容都是分块的, 每块都有一个 MD5 码, "
                               "调用 MARK 时, 一次性可以输入很多个 MD5 码, 按照逗号分隔, 它们会被直接呈现给调用者. 重点 MARK 数据和事实, 而非观点和结论. ",
        model=model,
        default_n=20,
        color= MESSAGE_COLOR_PURPLE,
        submit_processor=wikienv_hash.submit_process,
    )