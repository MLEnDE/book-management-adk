"""
ADK & Gemini Enterprise Configuration Module.
Defines model parameters, safety policies, and environment setup.
"""

import os
from typing import List


class ADKBookManagementConfig:
    """Configuration class for ADK Agents and Gemini Enterprise Runtime."""
    
    DEFAULT_MODEL: str = "gemini-1.5-pro"  # Default Gemini model
    FAST_MODEL: str = "gemini-1.5-flash"   # Fast model for subagents
    APP_DATA_DIR: str = os.path.expanduser("~/.gemini/antigravity-cli/book_management")
    
    # Declarative Safety Policy Configuration
    SAFETY_POLICIES: List[str] = [
        "confirm_run_command", # Block/Ask for shell commands
        "workspace_only",      # Restrict file tools to project workspace
        "hitl_for_mutations"   # Require explicit approval for external mutations
    ]
    
    @classmethod
    def get_api_key(cls) -> str:
        """Retrieves GEMINI_API_KEY from environment."""
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            print("⚠️ WARNING: GEMINI_API_KEY not found in environment.")
            print("Get an API key from Google AI Studio: https://aistudio.google.com/app/api-keys")
        return key
