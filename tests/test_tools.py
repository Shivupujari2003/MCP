import os

import pytest
from dotenv import load_dotenv
from google import genai

load_dotenv()


def test_gemini_api_key():
    api_key = os.getenv("GEMINI_API_KEY")
    assert api_key, "GEMINI_API_KEY is missing from .env"

    client = genai.Client(api_key=api_key)

    try:
        models = list(client.models.list())
        print(f"Available models: {[model.name for model in models]}")
        assert models, "No models returned by the API"
        print("Gemini API key is valid!")
    except Exception as e:
        pytest.fail(f"Gemini API test failed: {e}")
    finally:
        client.close()