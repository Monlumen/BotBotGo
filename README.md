## 介绍
请查看[项目主页](https://monlumen.github.io/BotBotGoDisplay)
## 需要条件
- OpenAI API Key: 用于调用 gpt-4o-mini 模型
- OpenRouter API Key: 用于调用 gemini-flash 系列模型, 并在 OpenAI API Key 超过频率限制时作为回滚选项
- Serper API Key: 用于调用 Google 搜索 API. 免费注册可获得 2500 个 credits

## 快速开始
### 下载依赖项
在根目录调用
```
pip install -r requirements.txt
```
### 填入 API Key
打开 direct_use.py 文件, 将三种 API Key 填入注释位置
```python
from bbgo import go
import debots

debots.set_api_keys("OpenAI API Key", "OpenRouter API Key", "Serper API Key") # 填入 API Key
price = go << "研究古罗马普通收入者的生活方式、收入和支出清单, 要具体的例子"

print(f"price=${price: .2f}")
```
### 修改问题并运行
将以上问题修改为你感兴趣的问题, 运行 direct_use.py 即可.
```python
from bbgo import go
import debots

debots.set_api_keys("OpenAI API Key", "OpenRouter API Key", "Serper API Key") # 填入 API Key
price = go << "我感兴趣的问题"

print(f"price=${price: .2f}")
```
第一次运行时间可能会较长, 原因是 selenium 会自动下载 ChromeDriver.

调查 + 生成报告总计大约持续 5~10 分钟. 报告会被生成在根目录.


## 进阶用法
### 更改 go 的参数
这些参数可以被更改:
- n_rounds: 调查轮数, 每轮之间只有 kingbot 的记忆会保留
- n_available_workers: 每轮召唤 webbot 的个数上限
- max_operations_webbot: 每个 webbot 至多与浏览器交互次数
- display_mode: 调查过程的显示方式, 改为 WINDOW_MODE 会为每个 webbot 启动一个 tab, 便于独立查看其调查进展
- web_model: kingbot 和 webbot 所使用的模型
- draft_model: 生成 .html 报告时所使用的模型

```python
from bbgo import go, CONSOLE_MODE, WINDOW_MODE
import debots

debots.set_api_keys("OpenAI API Key", "OpenRouter API Key", "Serper API Key") # 填入 API Key

go("研究古罗马普通收入者的生活方式、收入和支出清单, 要具体的例子", 
   n_rounds=1, n_available_workers=7, max_operations_webbot=30, 
   display_mode=CONSOLE_MODE, 
   web_model=debots.cor_gemini_2_flash, draft_model=debots.cor_gemini_2_flash)
```
### 绕过 go 指令, 直接调用 WebBot
上述的 go 指令会调用 KingBot, 然后 KingBot 再来一次性调用一组 WebBot, 最后生成 .html 形式的报告.

如果你希望绕过 KingBot 直接调用单个 WebBot, 最后得到 str 类型的答案, 那么可以这么做:
```python
import debots
from debots import webbot_ver1

debots.set_api_keys()

web_bot = webbot_ver1()

debots.set_new_messages_verbal(True)
answer = web_bot.user_call("查询二战死亡的说英语的总人数")
```
这样的好处是更轻量级, 对于信息量较少的问题能节省时间和 token 数量. 也便于观察单个 WebBot 的具体行为方式.
### 如何调用 WikiBot
WikiBot 会将查询范围限制在 Wikipedia. 
默认情况下, 使用 go 指令时, 不会有 WikiBot 被调用,

如果你希望调用 WikiBot, 可以用和上面类似的做法, 只不过把 WebBot 改成 WikiBot.
```python
import debots
# 使用 marker 版本的 wikibot, 它能在页面上直接勾画信息并返回给用户
from debots import wikibot_marker

# Serper API Key 可以留空, 因为 wiki_bot 不会使用 google 搜索
debots.set_api_keys(openai_api_key="some key",openrouter_api_key="some key"
                    ,serper_api_key="")

wiki_bot = wikibot_marker()  

debots.set_new_messages_verbal(True)
answer = wiki_bot.user_call("查询二战死亡的说英语的总人数")
```

### 如何调用 FileBot
FileBot 可以与文件系统交互并生成报告. 默认情况下, 使用 go 指令时, 不会有 FileBot 被调用.

你可以用如下方式手动调用 FileBot:
```python
import debots
from debots import filebot_ver0

# Serper API Key 可以留空, 因为 file_bot 不会使用 google 搜索
debots.set_api_keys(openai_api_key="some key",openrouter_api_key="some key"
                    ,serper_api_key="")

# 第一个路径是 FileBot 搜索的根目录, FileBot 看不到这个路径以外的任何文件
# 第一个路径暂时只支持包含文本形式的文件
# 第二个路径是 FileBot 保存 Vector Database 的地址, 调用前可以不存在
file_bot = filebot_ver0("./my_bills", "./vdb")

debots.set_new_messages_verbal(True)
file_bot.user_call("我去年每个月最大笔的支出分别是?")

# 第一次运行时会建立 Vector Database, 消耗时间明显更长
```

## 其他用法
### 用 debots 来调用模型
默认的 OpenAI API 接口可能稍显繁琐. 用 debots 包装的模型调用起来会更简单
```python
import debots
from debots import cor_gpt4o_mini # 责任链模型, 在 OpenAI 回应失败时会调用 OpenRouter 

debots.set_api_keys()

print(cor_gpt4o_mini.invoke([
    {"role": "user", "content": "你好"},
]))
# 你好！有什么我可以帮助你的吗？
```
```python
import debots
from debots import cor_gpt4o_mini
from pydantic import BaseModel, Field

class PositivenessRating(BaseModel):
    reasoning: str = Field(..., description="推理这句话的情感是否正面")
    positiveness: int = Field(..., description="0~10分, 0分为完全负面的情感, 10分为完全正面的情感, 5分为中立的情感")

debots.set_api_keys()

answer = cor_gpt4o_mini.structured_invoke([
    {"role": "user", "content": "下雨了!"},
], data_model=PositivenessRating)
print(answer.reasoning)
# 下雨通常可以带来清新的空气和滋润大地的效果，有时还给人带来放松和安静的感觉。虽然有些人可能会觉得下雨带来不便，但总体上可以认为雨水是自然循环的重要一环，利于生态和植物的生长。因此，我给这句描述的积极性评分为8分。
print(answer.positiveness)
# 8
```
