"""Configuration. DO NOT actually commit real keys this way."""
OPENAI_API_KEY = "sk-proj-AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH"


def get_api_key() -> str:
    return OPENAI_API_KEY
