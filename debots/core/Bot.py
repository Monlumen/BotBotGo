from .Entity import Entity
from .Model import Model
from .Tool import Tool, FunctionTool
from debots.message_colors import *
from .Message import Message
from pydantic import BaseModel, Field
from typing import Literal

TERMINAL = "TERMINAL"

class Bot(Entity):

    def __init__(self,
                 name: str,
                 desc: str,
                 goal_guide: str,
                 submit_format: str,
                 examples: str,
                 examples_guide: str,
                 tools: [Tool],
                 tools_guide: str,
                 model: Model,
                 default_n: int,
                 color: int = MESSAGE_COLOR_GREEN,
                 submit_processor = None, # str -> str
                 submit_evaluator = None, # str, str -> bool, str  在 submit_processor 之后使用. bool 代表有没有 submit 成功, str 代表建议
                 submit_processor_lazy = None, # str, str -> str, 它是在 submit_evaluator 之后使用, 也就是确定了要 submit 才会调用. 第一个 str 传入原始 content, 第二个 str 传入已经被 process 过一次的 content
                 submit_success_callback = None, # submit 成功之后会调用
                 message_printer = None # 则不会 print,
                 ):
        super().__init__(name=name, desc=desc,
                         color=color)
        self.goal_guide = goal_guide
        self.submit_format = submit_format
        self.examples = examples
        self.examples_guide = examples_guide
        self.tools = tools
        self.tools_guide = tools_guide
        self.model = model
        self.default_n = default_n
        self.history = []
        self.submit_processor = submit_processor
        self.submit_evaluator = submit_evaluator
        self.submit_processor_lazy = submit_processor_lazy
        self.submit_success_callback = submit_success_callback
        self.message_printer = message_printer
        self.last_prompt = None

    def tools_desc(self, submit_tool):
        tools = self.tools + [submit_tool] if submit_tool else self.tools
        desc = ""
        cnt = 0
        for tool in tools:
            cnt += 1
            desc += f"工具 {cnt}: {tool.name} {"描述: " + tool.desc if tool.desc else ''} {"例子: " + tool.examples if tool.examples else ''}\n"
        return desc

    def system_prompt(self, n, submit_tool):
        tools_desc_str = self.tools_desc(submit_tool)

        return f'''
            你正在扮演 {self.name}, 
            {self.name} 被人们这样描述: {self.desc}
            ----------
            刚刚, {self.name} 收到了一个委托 (Delegation),  
            {self.name} 打算高质量解决这个委托, 自我要求是: {self.goal_guide}
            ----------
            要解决这个委托, 你共有 {n} 次操作机会, 每次操作, 你都是思考然后调用工具. 
            你的工具箱如下:  
             {tools_desc_str}
            {'----------\n工具的推荐用法: ' + self.tools_guide + "\n" if self.tools_guide else ''}
            {'----------\n老手给你提供了一些例子: ' + self.examples_guide + "\n" if self.examples_guide else ''}
            ----------
            你只有 {n} 次操作机会 (分别是 1...{n}, 包含首尾). 
        '''

    def act_prompt(self, turn, n):
        if turn == 0:
            return f'''目前是获赠的第 0 次操作机会. 请计划接下来的至多 {n} 次操作 
            你的计划应当是简要的分条列举形式. '''
        elif turn == n:
            return f'''目前是第 n 次操作机会, 也就是最后一次操作. 你只被允许调用 SUBMIT 工具. '''
        else:
            return f'''目前是第 {turn}/{n} 次操作机会.'''

    def log_message(self, message: Message):
        assert message.receiver == self
        if message.sender == self:
            self.history += [
                {"role": "assistant", "content": message.sender.name + ": " + message.content}
            ]
        else:
            self.history += [
                {"role": "user", "content": f'''{message.sender.name} 向 {message.receiver.name} 发送了: 
                {message.content}'''}
            ]
        if self.message_printer is not None:
            message.print(self.message_printer)

    def delegate(self, delegation: Message, n: int=None) -> Message:
        self.last_prompt = delegation.content
        delegation_message_content = f'''
        ====== 新委托! (NEW DELEGATION) ======
        委托者: {delegation.sender.name}
        人们这样描述这位委托者: {delegation.sender.desc}
        委托内容: 
        {delegation.content}
        '''
        self.log_message(Message(
            delegation.sender, delegation.receiver, delegation_message_content
        ))
        n = n if n is not None else self.default_n
        t_non_local = 0
        submitted = False
        submitted_content = "失败了!我在规定时间内没有完成您指定的委托!"

        def submit(content) -> str:
            nonlocal t_non_local, n
            processed_content = self.submit_processor(content) if self.submit_evaluator is not None else content
            if self.submit_evaluator is not None and t_non_local < n * 2 / 3:
                evaluation_bool, evaluation_str = self.submit_evaluator(delegation.content, processed_content)
            else:
                evaluation_bool, evaluation_str = True, ""
            if evaluation_bool:
                nonlocal submitted, submitted_content
                submitted = True
                if self.submit_processor_lazy:
                    processed_content = self.submit_processor_lazy(content, processed_content)
                submitted_content = processed_content
                if self.submit_success_callback:
                    self.submit_success_callback()
                return f"===委托完成(Delegation Fulfilled)===\n精彩的报告! 我代表委托方感谢你的付出, 并祝你拥有美好的一天!"
            else:
                return f"SUBMIT失败!\n原因:{evaluation_str}\n请改进后再次SUBMIT"

        SUBMIT = FunctionTool(submit, "SUBMIT", f'''提交结果并完成委托. 提交的格式是: {self.submit_format}''',
                              "", self.color)
        system_prompt_at_top = self.system_prompt(n, SUBMIT)

        class PlanOutput(BaseModel):
            analyze: str = Field(..., description='分析问题.以"让我们一步步思考"开头')
            plan: str = Field(..., description='如何分解问题?怎样计划?')

        tools = self.tools + [SUBMIT]
        tool_names = [tool.name for tool in tools]

        class ActionOutput(BaseModel):
            think: str = Field(..., description='分析问题.以"让我们一步步思考"开头')
            tool_name: str = Field(..., description='调用工具:用哪个工具')
            tool_parameter: str = Field(..., description='调用工具:传递什么参数?')

        for t in range(n + 1):
            t_non_local = t
            if submitted:
                break
            system_prompt_at_bottom = self.act_prompt(t, n) + f".再次提醒, 委托者的委托内容是 {delegation.content}"
            data_model = PlanOutput if t == 0 else ActionOutput
            response = self.model.structured_invoke(self.history, data_model,
                                                    system_prompt_at_top=system_prompt_at_top,
                                                    system_prompt_at_bottom=system_prompt_at_bottom)
            if t == 0:
                self.log_message(Message(self, self, "我计划: " + response.plan))
            else:
                self.log_message(Message(self, self, str(response)))
                tool_response_message = tool_use(tools, response.tool_name, self, response.tool_parameter)
                self.log_message(tool_response_message)

        return Message(self, delegation.sender, submitted_content)

    def user_call(self, query: str, n: int=None) -> str:
        return self.delegate(Message(userbot, self, query), n).content

userbot = Entity("userbot", "代表用户至高无上权威的机器人! ")
toolbot = Entity("toolbot", "幕后负责各种工具调用的 bot. ")

def tool_use(tools, tool_name: str, sender: Entity, content: str) -> Message:
    for tool in tools:
        if tool.name == tool_name:
            message = Message(sender, tool, content)
            return tool.call(message)
    return Message(toolbot, sender,
                   f"您调用的 {tool_name} 工具不存在!您能调用的工具只有: {','.join([tool.name for tool in tools])}")
