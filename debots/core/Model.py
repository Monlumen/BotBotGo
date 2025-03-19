import openai
from openai import OpenAI, AsyncOpenAI
from debots.core.APIKey import APIKey
from abc import ABC, abstractmethod
import asyncio
from debots.core.APIKey import NullAPIKeyException

verbal_invoking = False # this is only used for testing
verbal_warning = True
n_most_tries = 300

usd_cost = 0

def log_cost(num):
    global usd_cost
    usd_cost += max(num, 0)

usd_cost_valid = True

def set_usd_cost_invalid():
    global usd_cost_valid
    usd_cost_valid = False

def read_cost():
    global usd_cost, usd_cost_valid
    return usd_cost if usd_cost_valid else None

class Model(ABC):

    def __init__(self, usd_1m_uncached_prompt_tokens=None,
                 usd_1m_cached_prompt_tokens=None,
                 usd_1m_output_tokens=None):
        self.usd_1m_uncached_prompt_tokens = usd_1m_uncached_prompt_tokens
        self.usd_1m_cached_prompt_tokens = usd_1m_cached_prompt_tokens
        self.usd_1m_output_tokens = usd_1m_output_tokens

    def invoke(self, message_list, system_prompt_at_top="", system_prompt_at_bottom="") -> str:
        assert False
        return asyncio.run(self.async_invoke(message_list, system_prompt_at_top, system_prompt_at_bottom))

    def structured_invoke(self, message_list, data_model, system_prompt_at_top="", system_prompt_at_bottom=""):
        assert False
        return asyncio.run(self.async_structured_invoke(message_list, data_model, system_prompt_at_top, system_prompt_at_bottom))

    def log_usage(self, num_uncached_prompt_tokens, num_cached_prompt_tokens,
                  num_output_tokens):
        assert isinstance(num_output_tokens, int)
        assert isinstance(num_uncached_prompt_tokens, int)
        assert isinstance(num_cached_prompt_tokens, int)
        global usd_cost_valid
        if not usd_cost_valid:
            return
        if num_uncached_prompt_tokens and self.usd_1m_uncached_prompt_tokens is None:
            set_usd_cost_invalid()
            return
        if num_cached_prompt_tokens and self.usd_1m_cached_prompt_tokens is None:
            set_usd_cost_invalid()
            return
        if num_output_tokens and self.usd_1m_output_tokens is None:
            set_usd_cost_invalid()
            return
        one_m = 1000 * 1000
        log_cost(num_cached_prompt_tokens * self.usd_1m_cached_prompt_tokens / one_m +
                 num_uncached_prompt_tokens * self.usd_1m_uncached_prompt_tokens / one_m +
                 num_output_tokens * self.usd_1m_output_tokens / one_m)

    @abstractmethod
    async def async_invoke(self, message_list, system_prompt_at_top="", system_prompt_at_bottom="") -> str:
        pass

    @abstractmethod
    async def async_structured_invoke(self, message_list, data_model, system_prompt_at_top="", system_prompt_at_bottom=""):
        pass

class OpenAIModel(Model):
    client: OpenAI
    model_name: str
    auto_retry: bool

    def __init__(self, api_key: APIKey, model_name: str, base_url: str = None, auto_retry: bool = True,
                 usd_1m_uncached_prompt_tokens=None, usd_1m_cached_prompt_tokens=None,
                 usd_1m_output_tokens=None):
        super().__init__(usd_1m_uncached_prompt_tokens, usd_1m_cached_prompt_tokens, usd_1m_output_tokens)
        self.model_name = model_name
        self.auto_retry = auto_retry
        self.base_url = base_url
        self.api_key = api_key
        self.client = None

    def make_clients(self):
        if self.base_url is not None:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key.get()
            )
            self.async_client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key.get()
            )
        else:
            self.client = OpenAI(
                api_key=self.api_key.get()
            )
            self.async_client = AsyncOpenAI(
                api_key=self.api_key.get()
            )

    def log_usage_by_completion(self, completion):
        num_output_tokens = completion.usage.completion_tokens
        num_prompt_tokens = completion.usage.prompt_tokens
        if (hasattr(completion.usage, "prompt_tokens_details") and
                completion.usage.prompt_tokens_details is not None):
            # 有时 completion.usage.prompt_tokens_details 会是 None
            num_cached_prompt_tokens = completion.usage.prompt_tokens_details.cached_tokens
        else:
            num_cached_prompt_tokens = 0
        num_uncached_prompt_tokens = num_prompt_tokens - num_cached_prompt_tokens
        self.log_usage(num_uncached_prompt_tokens, num_cached_prompt_tokens, num_output_tokens)

    # 覆盖了默认的基于 async_invoke 的实现. 是因为 AsyncOpenAI 对于某些特定输入似乎存在永远无法响应的情况
    # 卡在 async_invoke 的 await self.async_client 那一行
    # 似乎与单次未 hit-cache 的消息部分的长度有关, 只要超过某个长度就无法响应
    # 所以最好尽量避免使用 async_client 和 async_invoke
    def invoke(self, message_list, system_prompt_at_top="", system_prompt_at_bottom="") -> str:
        if not self.client:
            self.make_clients()
        if verbal_invoking:
            print(f"invoking {self.model_name}\n")
        messages = message_list
        if system_prompt_at_top:
            messages = [{"role": "system", "content": system_prompt_at_top}] + messages
        if system_prompt_at_bottom:
            messages = messages + [{"role": "system", "content": system_prompt_at_bottom}]
        for retries in range(n_most_tries):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
                response = completion.choices[0].message.content
                self.log_usage_by_completion(completion)
                return response
            except openai.RateLimitError as e:
                if retries == n_most_tries or self.auto_retry == False:
                    raise e
                if verbal_warning:
                    print(f"WARNING: 当调用一个 model_name 为 {self.model_name} "
                          f"的类 OpenAI 模型的 invoke 时发生了 RateLimitError, "
                          f"即将进行第 {retries + 1} / {n_most_tries} 次重试.\n{str(e)}")

    # 覆盖了默认实现
    # 原因同上
    def structured_invoke(self, message_list, data_model, system_prompt_at_top="", system_prompt_at_bottom=""):
        if not self.client:
            self.make_clients()
        if verbal_invoking:
            print(f"invoking {self.model_name}\n")
        messages = message_list
        if system_prompt_at_top:
            messages = [{"role": "system", "content": system_prompt_at_top}] + messages
        if system_prompt_at_bottom:
            messages = messages + [{"role": "system", "content": system_prompt_at_bottom}]
        for retries in range(n_most_tries):
            try:
                completion = self.client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=messages,
                    response_format=data_model,
                )
                response = completion.choices[0].message
                self.log_usage_by_completion(completion)
                break
            except openai.RateLimitError as e:
                if retries == n_most_tries or self.auto_retry == False:
                    raise e
                if verbal_warning:
                    print(f"WARNING: 当调用一个 model_name 为 {self.model_name} "
                          f"的类 OpenAI 模型的 structured_invoke 时发生了 RateLimitError, "
                          f"即将进行第 {retries + 1} / {n_most_tries} 次重试.\n{str(e)}")
        return response.parsed

    async def async_invoke(self, message_list, system_prompt_at_top="", system_prompt_at_bottom="") -> str:
        if not self.client:
            self.make_clients()
        if verbal_invoking:
            print(f"invoking {self.model_name}\n")
        messages = message_list
        if system_prompt_at_top:
            messages = [{"role": "system", "content": system_prompt_at_top}] + messages
        if system_prompt_at_bottom:
            messages = messages + [{"role": "system", "content": system_prompt_at_bottom}]
        for retries in range(n_most_tries):
            try:
                completion = await self.async_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
                response = completion.choices[0].message.content
                self.log_usage_by_completion(completion)
                return response
                break
            except openai.RateLimitError as e:
                if retries == n_most_tries or self.auto_retry == False:
                    raise e
                if verbal_warning:
                    print(f"WARNING: 当调用一个 model_name 为 {self.model_name} "
                          f"的类 OpenAI 模型的 invoke 时发生了 RateLimitError, "
                          f"即将进行第 {retries + 1} / {n_most_tries} 次重试.\n{str(e)}")

    async def async_structured_invoke(self, message_list, data_model, system_prompt_at_top="", system_prompt_at_bottom=""):
        if not self.client:
            self.make_clients()
        if verbal_invoking:
            print(f"invoking {self.model_name}\n")
        messages = message_list
        if system_prompt_at_top:
            messages = [{"role": "system", "content": system_prompt_at_top}] + messages
        if system_prompt_at_bottom:
            messages = messages + [{"role": "system", "content": system_prompt_at_bottom}]
        for retries in range(n_most_tries):
            try:
                completion = await self.async_client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=messages,
                    response_format=data_model,
                )
                response = completion.choices[0].message
                self.log_usage_by_completion(completion)
                break
            except openai.RateLimitError as e:
                if retries == n_most_tries or self.auto_retry == False:
                    raise e
                if verbal_warning:
                    print(f"WARNING: 当调用一个 model_name 为 {self.model_name} "
                          f"的类 OpenAI 模型的 structured_invoke 时发生了 RateLimitError, "
                          f"即将进行第 {retries + 1} / {n_most_tries} 次重试.\n{str(e)}")

        return response.parsed


verbal_walking_responsibility_chain = False # this is used only in testing

class ChainOfResponsibilityModel(Model):

    def __init__(self, *args):
        super().__init__(None, None, None)
        for model in args:
            assert isinstance(model, Model)
        self.models = args

    # 覆盖了默认实现
    # 原因同 OpenAIModel
    def invoke(self, message_list, system_prompt_at_top="", system_prompt_at_bottom="") -> str:
        errors = []
        for model in self.models:
            try:
                return model.invoke(message_list,
                                                system_prompt_at_top=system_prompt_at_top,
                                                system_prompt_at_bottom=system_prompt_at_bottom)
            except Exception as e:
                if verbal_walking_responsibility_chain:
                    print(f"switching to next model due to: {e}")
                errors.append(e)
        raise RuntimeError(f"All Models Failed: {errors}")

    # 覆盖了默认实现
    # 原因同 OpenAIModel
    def structured_invoke(self, message_list, data_model, system_prompt_at_top="", system_prompt_at_bottom=""):
        errors = []
        for model in self.models:
            try:
                return model.structured_invoke(message_list, data_model,
                                                           system_prompt_at_top=system_prompt_at_top,
                                                           system_prompt_at_bottom=system_prompt_at_bottom)
            except Exception as e:
                if verbal_walking_responsibility_chain:
                    print(f"switching to next model due to: {e}")
                errors.append(e)
        raise RuntimeError(f"All Models Failed: {errors}")

    async def async_invoke(self, message_list, system_prompt_at_top="", system_prompt_at_bottom="") -> str:
        errors = []
        for model in self.models:
            try:
                return await model.async_invoke(message_list,
                                    system_prompt_at_top=system_prompt_at_top,
                                    system_prompt_at_bottom=system_prompt_at_bottom)
            except Exception as e:
                if verbal_walking_responsibility_chain:
                    print(f"switching to next model due to: {e}")
                errors.append(e)
        raise RuntimeError(f"All Models Failed: {errors}")

    async def async_structured_invoke(self, message_list, data_model, system_prompt_at_top="", system_prompt_at_bottom=""):
        errors = []
        for model in self.models:
            try:
                return await model.async_structured_invoke(message_list, data_model,
                                               system_prompt_at_top=system_prompt_at_top,
                                               system_prompt_at_bottom=system_prompt_at_bottom)
            except Exception as e:
                if verbal_walking_responsibility_chain:
                    print(f"switching to next model due to: {e}")
                errors.append(e)
        raise RuntimeError(f"All Models Failed: {errors}")