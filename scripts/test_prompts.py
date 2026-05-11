#!/usr/bin/env python3
"""Script to test and adjust prompts with Ollama."""
import os
import sys
import httpx
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config_loader import load_config

OLLAMA_API = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
MODEL = os.getenv('OLLAMA_MODEL', 'qwen3.5:9b')

SAMPLE_TEXTS = {
    'papers': """
    Title: Attention Is All You Need
    Abstract: We propose a new simple network architecture, the Transformer,
    based solely on attention mechanisms, dispensing with recurrence and
    convolutions entirely. Experiments on two machine translation tasks show
    these models to be superior in quality while being more parallelizable.
    """,
    'github': """
    Release v2.0.0 - Breaking Changes
    - Removed deprecated API endpoints
    - Changed authentication to OAuth2
    - New: GPU acceleration support
    - Fix: Memory leaks in batch processing
    """,
    'blogs': """
    OpenAI announces GPT-5 with unprecedented reasoning capabilities.
    The new model demonstrates SOTA performance on mathematical benchmarks
    and can solve complex programming problems.
    """,
}

def test_prompt(category: str, text: str, temperature: float = 0.3, num_predict: int = 250):
    """Sends a generation request to Ollama and returns the response."""
    prompts = load_config('config/prompts.yaml')
    system = prompts.get(category, {}).get('system', '')

    prompt = f"{system}\n\nTexto:\n{text}"

    try:
        response = httpx.post(
            f"{OLLAMA_API}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": num_predict,
                }
            },
            timeout=60.0,
        )

        response.raise_for_status()
        data = response.json()
        return data.get('response', '')
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    print("=" * 60)
    print("Prompt Tuning - AI Daily Digest Bot")
    print("=" * 60)

    for category, text in SAMPLE_TEXTS.items():
        print(f"\n### Testing {category.upper()} ###")
        print(f"Input: {text[:100].strip()}...")

        result = test_prompt(category, text)
        print(f"\nOutput ({len(result)} chars):")
        print(result)
        print("-" * 40)

if __name__ == '__main__':
    main()
