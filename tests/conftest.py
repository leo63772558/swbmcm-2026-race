from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_DIR = REPO / "10_比赛工作区" / "src"
REVIEW_DIR = REPO / "10_比赛工作区" / "submission" / "b_revision_20261121"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
