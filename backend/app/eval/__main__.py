"""CLI: python -m app.eval - run the regression set and print the report."""

from __future__ import annotations

import os

from app.characters.claude import ClaudeRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.eval.report import render_report, run_eval
from app.providers.deepseek import DeepSeekProvider
from app.providers.mock import MockProvider


def main() -> None:
    has_key = bool(os.environ.get("DEEPSEEK_API_KEY"))
    if not has_key:
        print("（未检测到 DEEPSEEK_API_KEY：角色与评审都用 mock，评分为占位值）")
    judge = DeepSeekProvider() if has_key else MockProvider()
    runtimes = {
        "deepseek": DeepSeekRuntime(
            DeepSeekProvider() if has_key else MockProvider(character_id="deepseek")
        ),
        "claude": ClaudeRuntime(
            DeepSeekProvider() if has_key else MockProvider(character_id="claude")
        ),
    }
    print(render_report(run_eval(runtimes, judge)))


if __name__ == "__main__":
    main()
