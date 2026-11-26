#!/usr/bin/env python3
"""审计 vibecoding 模板的真实使用情况，输出瘦身建议。

用法：
    python audit.py <project-root> [--stage M2]

判断依据不是"模板文件被打开过"，而是"模板是否被实例化为真实文件"，
并结合项目阶段区分"确实用不上"与"还没到用它的阶段"。
"""

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS = SKILL_ROOT / "assets"

TEMPLATES = {
    "REQ.md": {"patterns": ["docs/requirements/REQ-*.md"], "stage": 0},
    "TASK.md": {"patterns": ["docs/tasks/TASK-*.md"], "stage": 0},
    "PR.md": {
        "patterns": [".github/PULL_REQUEST_TEMPLATE.md",
                     ".github/PULL_REQUEST_TEMPLATE/*.md"],
        "stage": 0,
    },
    "ADR.md": {"patterns": ["docs/adr/[0-9]*.md", "docs/adr/ADR-*.md"], "stage": 1},
    "COMMIT.md": {"patterns": [], "stage": 1},
    "CHANGELOG.md": {"patterns": ["CHANGELOG.md", "docs/CHANGELOG.md"], "stage": 1},
    "DECISION.md": {"patterns": ["docs/decisions/DEC-*.md", "docs/decisions/*.md"], "stage": 2},
    "ACCEPTANCE.md": {
        "patterns": ["docs/acceptance/*.md", "docs/**/*验收单*.md"],
        "stage": 3,
    },
    "RISK.md": {
        "patterns": ["docs/risks/RISK-*.md", "docs/**/*风险*.md"],
        "stage": 3,
    },
}

COMMIT_RE = re.compile(
    r"^[0-9a-f]+\s+(feat|fix|refactor|test|docs|chore|perf|revert)(\(.+\))?!?: "
)


def count_instances(root, patterns):
    total = 0
    for pattern in patterns:
        try:
            total += sum(1 for p in root.glob(pattern) if p.is_file())
        except (OSError, ValueError):
            pass
    return total


def check_commits(root):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "--oneline", "-n", "100"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    matched = sum(1 for line in lines if COMMIT_RE.match(line))
    return matched, len(lines)


def agents_status(root):
    target = root / "AGENTS.md"
    if not target.exists():
        return "缺失", False
    original = ASSETS / "AGENTS.md"
    if not original.exists():
        return "无法比对", False
    try:
        same = (hashlib.sha256(target.read_bytes()).digest()
                == hashlib.sha256(original.read_bytes()).digest())
    except OSError:
        return "无法读取", False
    if same:
        return "存在但未定制", True
    return "已定制", True


def main():
    parser = argparse.ArgumentParser(description="审计 vibecoding 模板使用情况")
    parser.add_argument("target", help="目标项目根目录")
    parser.add_argument("--stage", default="M3", help="当前项目阶段，如 M0/M1/M2/M3（默认 M3）")
    args = parser.parse_args()

    root = Path(args.target).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print("错误：目标目录不存在或不是目录：" + str(root))
        sys.exit(1)

    stage_match = re.fullmatch(r"[Mm]([0-3])", args.stage)
    current_stage = int(stage_match.group(1)) if stage_match else 3

    print("=== vibecoding 模板使用审计 ===")
    print("项目：" + str(root))
    print("阶段：M" + str(current_stage))
    print("")

    status_text, agents_ok = agents_status(root)
    print("AGENTS.md：" + status_text)
    if status_text == "存在但未定制":
        print("  提醒：与原始模板完全一致，说明 <按项目填写> 处可能从未补齐。")
    print("")

    downgrade = []
    overdue = []
    active = 0

    print("{:<16}{:<10}{:<12}{}".format("模板", "实例数", "起始阶段", "判断"))
    print("-" * 60)

    for name, meta in TEMPLATES.items():
        if name == "COMMIT.md":
            result = check_commits(root)
            if result is None:
                count_text, verdict = "-", "无法读取 git 历史"
            else:
                matched, total = result
                rate = matched / total * 100 if total else 0
                count_text = str(matched) + "/" + str(total)
                verdict = "符合率 {:.0f}%".format(rate)
        else:
            count = count_instances(root, meta["patterns"])
            count_text = str(count)
            if count > 0:
                active += 1
                verdict = "活跃，保留"
            elif meta["stage"] > current_stage:
                verdict = "未到阶段，暂不处理"
            elif meta["stage"] == current_stage:
                overdue.append(name)
                verdict = "本阶段应有，需补用"
            else:
                downgrade.append(name)
                verdict = "阶段已过仍未用，可降级"

        print("{:<16}{:<10}{:<12}{}".format(name, count_text, "M" + str(meta["stage"]), verdict))

    print("")
    print("活跃模板：" + str(active) + " / " + str(len(TEMPLATES)))
    if overdue:
        print("需补用：" + "、".join(overdue))
    if downgrade:
        print("降级候选（从预铺改为按需取用，不要直接删除）：" + "、".join(downgrade))
        print("  降级方式：在 scaffold.py 的 STAGE_TEMPLATES 中把上述模板移到更晚阶段。")
    if not downgrade and not overdue:
        print("结论：当前无瘦身动作。数据不足时，保留比猜测更安全。")


if __name__ == "__main__":
    main()
