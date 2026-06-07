#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const os = require("os");

const SRC = __dirname;
const CLAUDE = path.join(os.homedir(), ".claude");
const SCRIPTS = path.join(CLAUDE, "scripts");
const SKILLS = path.join(CLAUDE, "skills");

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

console.log("=========================================");
console.log("  Claude Code Playbook — 安装");
console.log("=========================================");
console.log("");

// ── 1. extract_sessions.py ──
console.log("[1/3] 安装 extract_sessions.py...");
fs.mkdirSync(SCRIPTS, { recursive: true });
const pySrc = path.join(SRC, "extract_sessions.py");
const pyDest = path.join(SCRIPTS, "extract_sessions.py");
fs.copyFileSync(pySrc, pyDest);
fs.chmodSync(pyDest, 0o755);
console.log("  ✓ 已安装到 ~/.claude/scripts/extract_sessions.py");

// ── 2. skills ──
console.log("[2/3] 安装 skills...");
fs.mkdirSync(SKILLS, { recursive: true });

const skillsSrc = path.join(SRC, "skills");
if (fs.existsSync(skillsSrc)) {
  for (const name of fs.readdirSync(skillsSrc)) {
    const srcPath = path.join(skillsSrc, name);
    const destPath = path.join(SKILLS, name);
    if (fs.statSync(srcPath).isDirectory()) {
      copyDir(srcPath, destPath);
      console.log(`  ✓ ${name} skill`);
    }
  }
}

// ── 3. verify ──
console.log("[3/3] 验证安装...");
console.log("");

const checks = [
  [pyDest, "extract_sessions.py"],
  [path.join(SKILLS, "extract-scenes", "SKILL.md"), "extract-scenes skill"],
  [path.join(SKILLS, "extract-tips", "SKILL.md"), "extract-tips skill"],
];

let ok = true;
for (const [p, label] of checks) {
  if (fs.existsSync(p)) {
    console.log(`  ✓ ${label}`);
  } else {
    console.log(`  ✗ ${label} 未找到`);
    ok = false;
  }
}

console.log("");
if (ok) {
  console.log("安装完成！");
  console.log("");
  console.log("使用方法：");
  console.log("  python3 ~/.claude/scripts/extract_sessions.py");
  console.log("  /extract-scenes  （在 Claude Code 中运行）");
  console.log("  /extract-tips    （在 Claude Code 中运行）");
} else {
  console.log("安装失败，请检查上述错误。");
  process.exit(1);
}
