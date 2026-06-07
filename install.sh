#!/bin/bash
# Claude Code Playbook — 一键安装脚本
# 将 extract_sessions.py 和 skills 安装到 ~/.claude/ 目录

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "========================================="
echo "  Claude Code Playbook — 安装"
echo "========================================="
echo ""

# ── 1. 复制 extract_sessions.py ──
echo "[1/3] 安装 extract_sessions.py..."
mkdir -p "$CLAUDE_DIR/scripts"
cp "$SCRIPT_DIR/extract_sessions.py" "$CLAUDE_DIR/scripts/extract_sessions.py"
chmod +x "$CLAUDE_DIR/scripts/extract_sessions.py"
echo "  ✓ 已安装到 ~/.claude/scripts/extract_sessions.py"

# ── 2. 复制 skills ──
echo "[2/3] 安装 skills..."
mkdir -p "$CLAUDE_DIR/skills"

if [ -d "$SCRIPT_DIR/skills/extract-scenes" ]; then
    cp -r "$SCRIPT_DIR/skills/extract-scenes" "$CLAUDE_DIR/skills/extract-scenes"
    echo "  ✓ extract-scenes skill"
fi

if [ -d "$SCRIPT_DIR/skills/extract-tips" ]; then
    cp -r "$SCRIPT_DIR/skills/extract-tips" "$CLAUDE_DIR/skills/extract-tips"
    echo "  ✓ extract-tips skill"
fi

# ── 3. 验证 ──
echo "[3/3] 验证安装..."
echo ""

PY_SCRIPT="$CLAUDE_DIR/scripts/extract_sessions.py"
SCENES_SKILL="$CLAUDE_DIR/skills/extract-scenes/SKILL.md"
TIPS_SKILL="$CLAUDE_DIR/skills/extract-tips/SKILL.md"

ALL_OK=true

if [ -f "$PY_SCRIPT" ]; then
    echo "  ✓ extract_sessions.py"
else
    echo "  ✗ extract_sessions.py 未找到"
    ALL_OK=false
fi

if [ -f "$SCENES_SKILL" ]; then
    echo "  ✓ extract-scenes skill"
else
    echo "  ✗ extract-scenes skill 未找到"
    ALL_OK=false
fi

if [ -f "$TIPS_SKILL" ]; then
    echo "  ✓ extract-tips skill"
else
    echo "  ✗ extract-tips skill 未找到"
    ALL_OK=false
fi

echo ""

if [ "$ALL_OK" = true ]; then
    echo "✅ 安装完成！"
    echo ""
    echo "使用方法："
    echo "  python3 ~/.claude/scripts/extract_sessions.py"
    echo "  /extract-scenes  （在 Claude Code 中运行）"
    echo "  /extract-tips    （在 Claude Code 中运行）"
else
    echo "❌ 安装失败，请检查上述错误。"
    exit 1
fi
