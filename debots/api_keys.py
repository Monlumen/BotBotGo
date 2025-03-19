from debots.core.APIKey import APIKey

current_openai_api_key = APIKey("OpenAI Models", "")
current_openrouter_api_key = APIKey("OpenRouter Models", "")
current_serper_api_key = APIKey("Serper(Google Search API Provider)", "")

def set_api_keys(openai_api_key: str, openrouter_api_key: str, serper_api_key: str):
    global current_openai_api_key, current_serper_api_key, current_openrouter_api_key
    current_openai_api_key.set(openai_api_key)
    current_openrouter_api_key.set(openrouter_api_key)
    current_serper_api_key.set(serper_api_key)
