# AI Assistance Disclosure (Article 7):
# - Tool: OpenAI ChatGPT (Codex, GPT-5.4 / GPT-6.2 Sol); Google Antigravity (Gemini 3.1 Pro)
# - Scope: Implementation scaffolding, numerical verification, and automated test engineering
# - Date: 2026-11-20 to 2026-11-21
# - Team Verification: Mathematical models and outputs verified by Team#SWBMCM2613050.
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_DIR = REPO / "10_比赛工作区" / "src"
REVIEW_DIR = REPO / "10_比赛工作区" / "submission" / "b_revision_20261121"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
