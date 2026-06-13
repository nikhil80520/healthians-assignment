"""
config.py — Settings & Constants for Healthians AI (AWS Bedrock)
Environment variables from .env, domain data loaded from data/ JSON files.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application-wide settings loaded from environment and data files."""

    # --- AWS Bedrock Configuration ---
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")

    # Bedrock Model IDs (uncomment the one you want to use)
    # Qwen3 32B Dense (current requested model):
    MODEL_NAME: str = "qwen.qwen3-32b-v1:0"
    # Claude 3.5 Sonnet v2 (best quality):
    # MODEL_NAME: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    # Claude 3.5 Haiku (fast & affordable):
    # MODEL_NAME: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    # Claude 3 Haiku (cheapest):
    # MODEL_NAME: str = "us.anthropic.claude-3-haiku-20240307-v1:0"

    ANTHROPIC_VERSION: str = "bedrock-2023-05-31"
    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 0.7
    MAX_HISTORY: int = 20  # Max messages per session before trimming


settings = Settings()
