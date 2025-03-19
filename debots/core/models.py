from .Model import OpenAIModel, ChainOfResponsibilityModel
from debots.hyper_parameters import OPENROUTER_BASE_URL
from ..api_keys import current_openai_api_key, current_openrouter_api_key

openai_gpt4o = OpenAIModel(current_openai_api_key, "gpt-4o",
                           usd_1m_uncached_prompt_tokens=2.5,
                           usd_1m_cached_prompt_tokens=1.25,
                           usd_1m_output_tokens=10)
openai_gpt4o_mini = OpenAIModel(current_openai_api_key, "gpt-4o-mini",
                                usd_1m_uncached_prompt_tokens=0.15,
                                usd_1m_cached_prompt_tokens=0.075,
                                usd_1m_output_tokens=0.6)
openrouter_gpt4o = OpenAIModel(current_openrouter_api_key, "openai/gpt-4o-2024-11-20", OPENROUTER_BASE_URL,
                               usd_1m_uncached_prompt_tokens=2.5,
                               usd_1m_cached_prompt_tokens=1.25,
                               usd_1m_output_tokens=10)
openrouter_gpt4o_mini = OpenAIModel(current_openrouter_api_key, "openai/gpt-4o-mini", OPENROUTER_BASE_URL,
                                    usd_1m_uncached_prompt_tokens=0.15,
                                    usd_1m_cached_prompt_tokens=0.075,
                                    usd_1m_output_tokens=0.6)
openrouter_gemini_flash_2 = OpenAIModel(current_openrouter_api_key, "google/gemini-2.0-flash-001", OPENROUTER_BASE_URL,
                                        usd_1m_uncached_prompt_tokens=0.1,
                                        usd_1m_cached_prompt_tokens=0.1,
                                        usd_1m_output_tokens=0.4)
openrouter_gemini_flash_1point5_8b = OpenAIModel(current_openrouter_api_key, "google/gemini-flash-1.5-8b", OPENROUTER_BASE_URL,
                                                 usd_1m_uncached_prompt_tokens=0.0375,
                                                 usd_1m_cached_prompt_tokens=0.0375,
                                                 usd_1m_output_tokens=0.15)
openrouter_gemini_flash_1point5 = OpenAIModel(current_openrouter_api_key, "google/gemini-flash-1.5", OPENROUTER_BASE_URL,
                                              usd_1m_uncached_prompt_tokens=0.075,
                                              usd_1m_cached_prompt_tokens=0.075,
                                              usd_1m_output_tokens=0.3)
openrouter_haiku = OpenAIModel(current_openrouter_api_key, "anthropic/claude-3.5-haiku", OPENROUTER_BASE_URL,
                               usd_1m_uncached_prompt_tokens=0.8,
                               usd_1m_cached_prompt_tokens=0.08,
                               usd_1m_output_tokens=4)
openrouter_sonnet = OpenAIModel(current_openrouter_api_key, "anthropic/claude-3.5-sonnet", OPENROUTER_BASE_URL,
                                usd_1m_uncached_prompt_tokens=3,
                                usd_1m_cached_prompt_tokens=0.3,
                                usd_1m_output_tokens=15)
openrouter_deepseek_chat = OpenAIModel(current_openrouter_api_key, "deepseek/deepseek-chat", OPENROUTER_BASE_URL,
                                       usd_1m_uncached_prompt_tokens=0.14,
                                       usd_1m_cached_prompt_tokens=0.014,
                                       usd_1m_output_tokens=0.28)

cor_gpt4o_mini = ChainOfResponsibilityModel(
    OpenAIModel(current_openai_api_key, "gpt-4o-mini", auto_retry=False,
                usd_1m_uncached_prompt_tokens=0.15,
                usd_1m_cached_prompt_tokens=0.075,
                usd_1m_output_tokens=0.6),
    openrouter_gpt4o_mini
)

cor_gpt4o = ChainOfResponsibilityModel(
    OpenAIModel(current_openai_api_key, "gpt-4o", auto_retry=False,
                usd_1m_uncached_prompt_tokens=2.5,
                usd_1m_cached_prompt_tokens=1.25,
                usd_1m_output_tokens=10),
    openrouter_gpt4o
)

cor_gemini_2_flash = ChainOfResponsibilityModel(
    OpenAIModel(current_openrouter_api_key, "google/gemini-2.0-flash-001", OPENROUTER_BASE_URL,
                auto_retry=False,
                usd_1m_uncached_prompt_tokens=0.1,
                usd_1m_cached_prompt_tokens=0.1,
                usd_1m_output_tokens=0.4),
    cor_gpt4o_mini
)