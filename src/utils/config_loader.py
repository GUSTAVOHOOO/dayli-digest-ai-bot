import os
import yaml
from pathlib import Path

def load_env():
    """Load environment variables from .env file if it exists."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

def load_yaml(filepath: str) -> dict:
    """Load and parse a YAML file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}

def load_config(filepath: str) -> dict:
    """Combines env loading and YAML parsing."""
    load_env()
    return load_yaml(filepath)
