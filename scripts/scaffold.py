#!/usr/bin/env python3
"""把 vibecoding 规范骨架铺到目标项目。

用法：
    python scaffold.py <project-root> [--minimal | --stage M2] [--force] [--dry-run]

默认行为：只创建缺失文件，已存在文件一律跳过（规范文件一旦被人改过，
脚本不得静默覆盖，否则破坏可追溯性）。
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS = SKILL_ROOT / "assets"

FULL_TEMPLATES = [
    "REQ.md", "TASK.md", "ADR.md", "COMMIT.md", "PR.md",
    "CHANGELOG.md", "DECISION.md", "ACCEPTANCE.md", "RISK.md",
]
MINIMAL_TEMPLATES = ["REQ.md", "TASK.md", "PR.md"]

FULL_CHECKLISTS = [
    "requirement.md", "task-breakdown.md", "pre-commit.md",
    "code-review.md", "release.md",
]
MINIMAL_CHECKLISTS = ["requirement.md", "pre-commit.md", "code-review.md"]

STAGE_TEMPLATES = {
    0: ["REQ.md", "TASK.md", "PR.md"],
    1: ["ADR.md", "COMMIT.md", "CHANGELOG.md"],
    2: ["DECISION.md"],
    3: ["ACCEPTANCE.md", "RISK.md"],
}
STAGE_CHECKLISTS = {
    0: ["requirement.md", "pre-commit.md", "code-review.md"],
    1: ["task-breakdown.md"],
    2: [],
    3: ["release.md"],
}

WORK_DIRS = ["docs/requirements", "docs/tasks", "docs/adr"]


def record(actions, status, path, note):
    actions.append((status, str(path), note))


def copy_asset(src, dst, force, dry_run, actions):
    if not src.exists():
        record(actions, "MISS", src, "源文件不存在，请检查 skill 安装")
        return
    existed = dst.exists()
    if existed and not force:
        record(actions, "SKIP", dst, "已存在，未覆盖")
        return
    if dry_run:
        suffix = "（覆盖）" if existed else ""
        record(actions, "WOULD", dst, "将写入" + suffix)
        return
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    except OSError as exc:
        record(actions, "ERROR", dst, "写入失败：" + str(exc))
        return
    suffix = "（覆盖）" if existed else ""
    record(actions, "OK", dst, "已写入" + suffix)


def main():
    parser = argparse.ArgumentParser(description="把 vibecoding 规范骨架铺到目标项目")
    parser.add_argument("target", help="目标项目根目录")
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="只铺核心文件（AGENTS.md + 3 模板 + 3 清单），呼应第一周精益起步",
    )
    parser.add_argument(
        "--stage",
        help="按阶段铺设，如 M0/M1/M2/M3；包含该阶段及之前全部模板",
    )
    parser.add_argument("--force", action="store_true", help="覆盖已存在文件，谨慎使用")
    parser.add_argument("--dry-run", action="store_true", help="只预览将要执行的动作")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        print("错误：目标目录不存在或不是目录：" + str(target))
        sys.exit(1)

    if args.stage:
        stage_match = re.fullmatch(r"[Mm]([0-3])", args.stage)
        if not stage_match:
            print("错误：--stage 只接受 M0/M1/M2/M3，收到：" + args.stage)
            sys.exit(1)
        stage = int(stage_match.group(1))
        templates = [name for s in range(stage + 1)
                     for name in STAGE_TEMPLATES.get(s, [])]
        checklists = [name for s in range(stage + 1)
                      for name in STAGE_CHECKLISTS.get(s, [])]
    else:
        templates = MINIMAL_TEMPLATES if args.minimal else FULL_TEMPLATES
        checklists = MINIMAL_CHECKLISTS if args.minimal else FULL_CHECKLISTS
    actions = []

    copy_asset(ASSETS / "AGENTS.md", target / "AGENTS.md",
               args.force, args.dry_run, actions)

    for name in templates:
        copy_asset(ASSETS / "templates" / name,
                   target / "docs" / "_templates" / name,
                   args.force, args.dry_run, actions)

    for name in checklists:
        copy_asset(ASSETS / "checklists" / name,
                   target / "docs" / "_checklists" / name,
                   args.force, args.dry_run, actions)

    for rel in WORK_DIRS:
        directory = target / rel
        if directory.exists():
            record(actions, "SKIP", directory, "目录已存在")
        elif args.dry_run:
            record(actions, "WOULD", directory, "将创建目录")
        else:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                (directory / ".gitkeep").write_text("", encoding="utf-8")
                record(actions, "OK", directory, "已创建目录")
            except OSError as exc:
                record(actions, "ERROR", directory, "创建失败：" + str(exc))

    for status, path, note in actions:
        print("[" + status + "] " + path + " — " + note)

    counts = {}
    for status, _, _ in actions:
        counts[status] = counts.get(status, 0) + 1
    mode = "预览" if args.dry_run else "完成"
    print("")
    print(mode + "：写入 " + str(counts.get("OK", 0))
          + "，预览 " + str(counts.get("WOULD", 0))
          + "，跳过 " + str(counts.get("SKIP", 0))
          + "，失败 " + str(counts.get("ERROR", 0))
          + "，缺失 " + str(counts.get("MISS", 0)))
    if not args.dry_run:
        print("下一步：打开 AGENTS.md，补齐所有 <按项目填写> 标记处。")


if __name__ == "__main__":
    main()
