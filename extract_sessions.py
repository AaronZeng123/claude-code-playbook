#!/usr/bin/env python3
"""
Claude Code Session Extractor
从 ~/.claude/projects/ 提取所有会话，输出结构化 markdown 文件到桌面。

Usage:
  python3 extract_sessions.py
  python3 extract_sessions.py --output-dir ~/Desktop/my-sessions/
  python3 extract_sessions.py --format summary-only
  python3 extract_sessions.py --include-subagents
  python3 extract_sessions.py --projects "项目A,项目B"
"""

import json
import os
import sys
import time
import argparse
import unicodedata
from pathlib import Path
from collections import Counter


# ── Helpers ────────────────────────────────────────────

def sanitize_filename(name, max_len=60):
    """Remove problematic characters for file system safety."""
    safe = name.strip()
    # Keep only: Chinese characters, letters, digits, spaces, common punctuation
    result = []
    for c in safe:
        cat = unicodedata.category(c)
        # Allow letters (L*), numbers (N*), spaces (Zs), and basic punctuation
        if cat.startswith("L") or cat.startswith("N") or cat == "Zs":
            result.append(c)
        elif c in "_-+.,;:()（）【】「」『』《》·":
            result.append(c)
        # Skip everything else (box-drawing, symbols, control chars, etc.)
    safe = "".join(result).strip()
    # Remove problematic filesystem chars
    safe = safe.replace("/", "-").replace("\\", "-").replace(":", ".")
    # Collapse whitespace
    safe = " ".join(safe.split())
    if len(safe) > max_len:
        safe = safe[:max_len]
    return safe or "untitled"


def extract_text_content(message):
    """从 message.content 中提取纯文本（跳过 tool_use 和 tool_result blocks）"""
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    t = block.get("text", "")
                    if isinstance(t, str) and t.strip():
                        texts.append(t)
        return "\n".join(texts)
    return ""


def extract_tool_names_from_message(message):
    """从 assistant message 中提取工具名称列表"""
    tools = []
    content = message.get("content", "")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tools.append(block.get("name", "unknown"))
    return tools


def _is_banner(text):
    """检测是否是 Claude Code 欢迎横幅，避免将其作为首条 prompt"""
    banner_markers = [
        "Tips for getting started",
        "Welcome back",
        "Run /init to create",
        "Note: You have launched claude",
        "│",
        "╭───",
    ]
    return any(m in text for m in banner_markers)


# ── Session Parser ─────────────────────────────────────

def parse_session(jsonl_path):
    """
    解析单个 JSONL 会话文件，返回 SessionData dict。
    逐行读取，避免内存问题。
    """
    fname = jsonl_path.name
    session_id = fname.replace(".jsonl", "")

    data = {
        "session_id": session_id,
        "title": "",
        "date": "",
        "project": "",
        "models": Counter(),
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cache_read": 0,
        "tools_used": Counter(),
        "first_prompt": "",
        "last_prompt": "",
        "message_count_user": 0,
        "message_count_assistant": 0,
        "cwd": "",
        "git_branch": "",
        "entry_count": 0,
        "file_size_kb": 0,
    }

    try:
        file_size = os.path.getsize(jsonl_path)
        data["file_size_kb"] = round(file_size / 1024, 1)
    except OSError:
        pass

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                data["entry_count"] += 1
                entry_type = obj.get("type", "")

                # ── Title ──
                if entry_type == "ai-title":
                    data["title"] = obj.get("aiTitle", "")

                # ── Timestamp ──
                if not data["date"]:
                    ts = obj.get("timestamp", "")
                    if ts:
                        data["date"] = ts[:10]  # YYYY-MM-DD

                # ── Project / cwd ──
                if not data["cwd"]:
                    cwd = obj.get("cwd", "")
                    if cwd:
                        data["cwd"] = cwd
                if not data["git_branch"]:
                    gb = obj.get("gitBranch", "")
                    if gb:
                        data["git_branch"] = gb

                # ── User messages ──
                if entry_type == "user" and not obj.get("isSidechain"):
                    text = extract_text_content(obj.get("message", {}))
                    if text and not data["first_prompt"]:
                        # Skip Claude Code welcome banner / system prompts
                        if not _is_banner(text):
                            data["first_prompt"] = text
                    data["message_count_user"] += 1

                # ── Last prompt ──
                if entry_type == "last-prompt":
                    lp = obj.get("lastPrompt", "")
                    if lp and not data["last_prompt"]:
                        data["last_prompt"] = lp

                # ── Assistant messages (tools, model, tokens) ──
                if entry_type == "assistant":
                    msg = obj.get("message", {})
                    # Model
                    model = msg.get("model", "")
                    if model:
                        data["models"][model] += 1
                    # Tokens
                    usage = msg.get("usage", {})
                    if usage:
                        data["total_input_tokens"] += usage.get("input_tokens", 0)
                        data["total_output_tokens"] += usage.get("output_tokens", 0)
                        data["total_cache_read"] += usage.get("cache_read_input_tokens", 0)
                    # Tools
                    for tool_name in extract_tool_names_from_message(msg):
                        data["tools_used"][tool_name] += 1
                    data["message_count_assistant"] += 1

    except (OSError, PermissionError) as e:
        data["_error"] = str(e)

    # Fallback title
    if not data["title"] and data["first_prompt"]:
        prompt = data["first_prompt"].replace("\n", " ").strip()
        data["title"] = prompt[:60]

    if not data["title"]:
        data["title"] = session_id[:12]

    return data


# ── Session Discovery ──────────────────────────────────

def find_all_sessions(projects_dir, exclude_subagents=True):
    """
    遍历 ~/.claude/projects/ 下所有子目录，返回 (project_name, jsonl_path) 列表。
    """
    sessions = []
    base = Path(projects_dir).expanduser().resolve()
    if not base.exists():
        print(f"Error: {base} not found")
        return sessions

    for child in base.iterdir():
        if not child.is_dir():
            continue
        project_name = child.name
        for f in child.glob("*.jsonl"):
            # 排除子 agent 的会话文件
            if exclude_subagents and f.name.startswith("agent-"):
                continue
            sessions.append((project_name, f))

    return sessions


# ── Markdown Formatting ────────────────────────────────

def format_session_markdown(data):
    """将 SessionData 格式化为单个会话的 markdown 文档"""
    lines = [
        f"# {data['title']}",
        "",
        f"**日期**：{data['date'] or '未知'}",
        f"**会话 ID**：`{data['session_id']}`",
        f"**工作目录**：{data['cwd'] or '未知'}",
    ]
    if data["git_branch"]:
        lines.append(f"**Git 分支**：{data['git_branch']}")

    # Models
    if data["models"]:
        model_str = "、".join(f"{m}({c}次)" for m, c in data["models"].most_common(5))
        lines.append(f"**模型**：{model_str}")

    # Tokens
    tokens = data
    ti = tokens["total_input_tokens"]
    to = tokens["total_output_tokens"]
    cr = tokens["total_cache_read"]
    if ti or to:
        parts = []
        if ti:
            parts.append(f"{ti:,} 输入")
        if to:
            parts.append(f"{to:,} 输出")
        if cr:
            parts.append(f"{cr:,} 缓存读取")
        lines.append(f"**Token 用量**：{' / '.join(parts)}")

    lines.append(f"**消息数**：用户 {data['message_count_user']} / 助手 {data['message_count_assistant']}")
    lines.append(f"**文件大小**：{data['file_size_kb']} KB")
    lines.append("")

    # Summary
    lines.append("## 摘要")
    lines.append("")
    if data["first_prompt"]:
        fp = data["first_prompt"][:300].replace("\n", " ").strip()
        lines.append(f"**首次提问**：{fp}")
    if data["last_prompt"]:
        lp = data["last_prompt"][:300].replace("\n", " ").strip()
        lines.append(f"**最后提问**：{lp}")
    lines.append("")

    # Tools
    if data["tools_used"]:
        lines.append("## 使用工具")
        lines.append("")
        lines.append("| 工具 | 调用次数 |")
        lines.append("|------|---------|")
        for tool, count in data["tools_used"].most_common():
            lines.append(f"| {tool} | {count} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*由 Claude Code Session Extractor 生成*")

    return "\n".join(lines)


def format_summary_markdown(sessions_data, output_dir):
    """格式化 _summary.md 总索引"""
    total_tokens_in = sum(s["total_input_tokens"] for s in sessions_data)
    total_tokens_out = sum(s["total_output_tokens"] for s in sessions_data)
    total_sessions = len(sessions_data)
    total_size_kb = sum(s["file_size_kb"] for s in sessions_data)

    lines = [
        "# Claude Code 会话总览",
        "",
        f"**生成时间**：{time.strftime('%Y-%m-%d %H:%M')}",
        f"**会话总数**：{total_sessions}",
        f"**总 Token 用量**：{total_tokens_in:,} 输入 / {total_tokens_out:,} 输出",
        f"**总文件大小**：{total_size_kb / 1024:.1f} MB",
        "",
        "---",
        "",
        "## 会话索引",
        "",
        "| # | 标题 | 日期 | 项目 | 消息数 | 模型 | 工具 |",
        "|---|------|------|------|--------|------|------|",
    ]

    # Sort by date desc
    sorted_sessions = sorted(sessions_data, key=lambda s: s.get("date", ""), reverse=True)

    for i, s in enumerate(sorted_sessions, 1):
        title = s["title"][:40]
        date = s["date"] or "?"
        project = s.get("project", "") or "-"
        msgs = f"{s['message_count_user']}+{s['message_count_assistant']}"
        models = "、".join([m for m, _ in s["models"].most_common(3)])
        tools = "、".join([t for t, _ in s["tools_used"].most_common(5)])
        # Escape pipe chars in title
        title = title.replace("|", "\\|")

        lines.append(f"| {i} | {title} | {date} | {project} | {msgs} | {models} | {tools} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Tool summary across all sessions
    global_tools = Counter()
    for s in sessions_data:
        for tool, count in s["tools_used"].items():
            global_tools[tool] += count

    if global_tools:
        lines.append("## 全局工具使用统计")
        lines.append("")
        lines.append("| 工具 | 总调用次数 | 使用该工具的会话数 |")
        lines.append("|------|-----------|------------------|")
        tool_sessions = Counter()
        for s in sessions_data:
            for tool in s["tools_used"]:
                tool_sessions[tool] += 1
        for tool, count in global_tools.most_common(20):
            lines.append(f"| {tool} | {count:,} | {tool_sessions[tool]} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*由 Claude Code Session Extractor 生成*")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Claude Code Session Extractor — 从 ~/.claude/projects/ 提取会话到 markdown"
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.expanduser("~/Desktop/claude-sessions"),
        help="输出目录 (默认: ~/Desktop/claude-sessions/)",
    )
    parser.add_argument(
        "--format",
        choices=["individual", "summary-only", "json"],
        default="individual",
        help="输出格式: individual(每会话一个md) / summary-only(仅索引) / json(仅机器可读json)",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=5,
        help="跳过消息数少于 N 的会话 (默认: 5)",
    )
    parser.add_argument(
        "--projects",
        default=None,
        help="仅提取指定项目 (逗号分隔，如 '项目A,项目B')",
    )
    parser.add_argument(
        "--include-subagents",
        action="store_true",
        help="同时提取子 Agent 会话",
    )
    parser.add_argument(
        "--max-size-mb",
        type=int,
        default=0,
        help="跳过大于 N MB 的会话 (默认: 不限制)",
    )

    args = parser.parse_args()

    projects_dir = os.path.expanduser("~/.claude/projects/")
    output_dir = Path(args.output_dir).expanduser().resolve()

    if not os.path.exists(projects_dir):
        print(f"错误：未找到 ~/.claude/projects/ 目录。确保你使用过 Claude Code。")
        sys.exit(1)

    # ── Step 1: Discover sessions ──
    print("正在扫描会话文件...")
    all_sessions = find_all_sessions(projects_dir, exclude_subagents=not args.include_subagents)

    if args.projects:
        project_filter = set(p.strip() for p in args.projects.split(","))
        all_sessions = [(p, f) for p, f in all_sessions if p in project_filter]

    if not all_sessions:
        print("未找到任何会话文件。")
        sys.exit(0)

    print(f"找到 {len(all_sessions)} 个会话文件。")

    # ── Step 2: Parse sessions ──
    print("\n正在解析会话内容...")
    sessions_data = []
    error_count = 0

    for idx, (project_name, jsonl_path) in enumerate(all_sessions, 1):
        pct = idx * 100 // len(all_sessions)
        if pct % 10 == 0:
            print(f"  进度：{pct}% ({idx}/{len(all_sessions)})")

        data = parse_session(jsonl_path)
        data["project"] = project_name

        # Skip trivial sessions
        msg_count = data["message_count_user"] + data["message_count_assistant"]
        if msg_count < args.min_lines:
            continue

        # Skip oversized
        if args.max_size_mb > 0 and data["file_size_kb"] > args.max_size_mb * 1024:
            continue

        if "_error" in data:
            error_count += 1
            continue

        sessions_data.append(data)

    print(f"  完成！解析了 {len(sessions_data)} 个有效会话 (跳过 {error_count} 个错误)。")

    # ── Step 3: Write output ──
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n正在写入输出目录：{output_dir}")

    if args.format in ("individual", "summary-only"):
        # Write _summary.md
        summary_md = format_summary_markdown(sessions_data, output_dir)
        summary_path = output_dir / "_summary.md"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_md)
        print(f"  ✓ _summary.md ({len(sessions_data)} 条记录)")

        # Write _summary.json
        summary_json = [
            {
                "title": s["title"],
                "date": s["date"],
                "session_id": s["session_id"],
                "project": s.get("project", ""),
                "cwd": s["cwd"],
                "models": dict(s["models"].most_common()),
                "total_input_tokens": s["total_input_tokens"],
                "total_output_tokens": s["total_output_tokens"],
                "tools_used": dict(s["tools_used"].most_common()),
                "first_prompt": s["first_prompt"][:200] if s["first_prompt"] else "",
                "message_count": s["message_count_user"] + s["message_count_assistant"],
                "file_size_kb": s["file_size_kb"],
            }
            for s in sessions_data
        ]
        json_path = output_dir / "_summary.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary_json, f, ensure_ascii=False, indent=2)
        print(f"  ✓ _summary.json")

    if args.format == "individual":
        # Group by project and write individual .md files
        project_groups = {}
        for s in sessions_data:
            proj = s.get("project", "unknown")
            if proj not in project_groups:
                project_groups[proj] = []
            project_groups[proj].append(s)

        total_files = 0
        for proj, group in project_groups.items():
            proj_dir = output_dir / proj
            proj_dir.mkdir(parents=True, exist_ok=True)
            for s in group:
                md_content = format_session_markdown(s)
                safe_title = sanitize_filename(s["title"])
                filename = f"{safe_title}.md"
                filepath = proj_dir / filename
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(md_content)
                total_files += 1
        print(f"  ✓ {total_files} 个会话 markdown 文件")

    elif args.format == "json":
        json_path = output_dir / "_sessions.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary_json, f, ensure_ascii=False, indent=2)
        print(f"  ✓ _sessions.json")

    print(f"\n✅ 全部完成！输出目录：{output_dir}")
    print(f"   总会话数：{len(sessions_data)}")
    print(f"\n下一步：")
    print(f"   在 Claude Code 中运行 /extract-scenes 提取应用场景")
    print(f"   在 Claude Code 中运行 /extract-tips 提取操作技巧")


if __name__ == "__main__":
    main()
