# config.py
# =============================================================================
# CogniFi — Configuration
# =============================================================================
#
# SETUP:
#   1. Copy this file or set environment variables
#   2. Get a Gemini API key at: https://aistudio.google.com/app/apikey
#   3. Set GEMINI_API_KEY below or via environment variable
#
# SECURITY:
#   Never commit your actual API key to version control.
#   Use environment variables in production:
#     export GEMINI_API_KEY="your-key-here"
# =============================================================================

import os

# Gemini API Key — set via environment variable or replace with your key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")

# Model
GEMINI_MODEL = "gemini-3-flash"

# Counter-evidence engine defaults
DEFAULT_THRESHOLD = 0.20   # Minimum 5-day return for FOMO episode detection
DEFAULT_WINDOW    = 5      # Days to look back for price movement
DEFAULT_FORWARD   = 30     # Days forward to measure correction probability
