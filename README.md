# Claude Code Playbook

> 172 个真实应用场景 + 一套会话提取工具，帮你从「会用 Claude Code」到「用出花样」。

## 这是什么

一个开源项目，包含两部分：

**知识库** — 12 篇文章、172 个真实应用场景，覆盖内容创作、数据处理、自动化、客户沟通等领域。基于 780+ 次真实 Claude Code 会话提炼。

**提取工具** — 一个 Python 脚本 + 两个 Claude Code Skill，能把你自己的 `~/.claude/projects/` 里所有会话导成结构化 Markdown，自动归类应用场景、提取操作技巧。

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/YOUR_USERNAME/claude-code-playbook.git
cd claude-code-playbook

# 2. 安装
bash install.sh

# 3. 提取你的所有 Claude Code 会话
python3 ~/.claude/scripts/extract_sessions.py

# 4. 在 Claude Code 中运行
# /extract-scenes   → 生成应用场景报告
# /extract-tips     → 生成操作技巧报告
```

输出目录：`~/Desktop/claude-sessions/`

## 知识库：172 个应用场景

| # | 分类 | 场景数 | 一句话 |
|---|------|--------|--------|
| 01 | [内容创作](knowledge-base/01-内容创作.md) | 18 | 公众号、小红书、视频脚本 — 从选题到发布全链路 |
| 02 | [内容抓取与素材处理](knowledge-base/02-内容抓取与素材处理.md) | 15 | 网页剪藏、公众号抓取、数据清洗 |
| 03 | [音视频与语音处理](knowledge-base/03-音视频与语音处理.md) | 12 | 播客转文字、视频字幕、语音合成 |
| 04 | [财务与数据处理](knowledge-base/04-财务与数据处理.md) | 14 | Excel 处理、报表生成、对账分析 |
| 05 | [文档处理](knowledge-base/05-文档处理.md) | 13 | PDF 转换、合同审查、批量排版 |
| 06 | [客户沟通与销售](knowledge-base/06-客户沟通与销售.md) | 16 | 话术生成、客户分析、方案定制 |
| 07 | [项目方案与交付](knowledge-base/07-项目方案与交付.md) | 13 | 方案撰写、项目管理、交付物生成 |
| 08 | [企业培训](knowledge-base/08-企业培训.md) | 17 | 课件制作、培训大纲、知识考核 |
| 09 | [调研与情报](knowledge-base/09-调研与情报.md) | 15 | 竞品分析、行业调研、信息聚合 |
| 10 | [知识管理](knowledge-base/10-知识管理.md) | 14 | 笔记整理、知识图谱、Obsidian 联动 |
| 11 | [自动化与视频产线](knowledge-base/11-自动化与视频产线.md) | 12 | 批量处理、工作流串联、API 对接 |
| 12 | [Claude Code 工具与环境](knowledge-base/12-Claude-Code-工具与环境.md) | 13 | MCP 配置、Skill 开发、环境调优 |

## 提取工具说明

### extract_sessions.py

纯 Python stdlib，零依赖。扫描 `~/.claude/projects/` 下所有 JSONL 会话文件，为每个会话生成一个独立 .md 文件，同时生成汇总索引。

```bash
python3 extract_sessions.py                          # 默认输出到 ~/Desktop/claude-sessions/
python3 extract_sessions.py --format summary-only    # 仅生成索引
python3 extract_sessions.py --projects "项目A,项目B" # 筛选项目
python3 extract_sessions.py --include-subagents      # 含子 Agent 会话
python3 extract_sessions.py --min-lines 10           # 跳过少于 10 条消息的会话
```

### /extract-scenes

在 Claude Code 中运行，自动：
1. 读取会话索引 → 主题聚类 → 采样验证
2. 输出 `scenes-report.md`（~12-15 个应用场景分类 + 典型案例）

### /extract-tips

在 Claude Code 中运行，自动：
1. 从会话中筛选包含技巧的对话 → 深读提取
2. 输出 `tips-report.md`（CLI 命令、配置方案、Workflow、避坑指南）

## 输出示例

```
~/Desktop/claude-sessions/
├── _summary.md              # 总索引
├── _summary.json            # 机器可读索引
├── scenes-report.md         # 应用场景报告（/extract-scenes 生成）
├── tips-report.md           # 操作技巧报告（/extract-tips 生成）
├── -Users-AaronZeng/        # 按项目分目录
│   ├── 编写extract_sessions脚本.md
│   ├── 飞书知识库内容抓取.md
│   └── ...
└── my-project/
    └── ...
```

## 关于作者

**曾俊（Aaron Zeng）** — [硅基行动](https://硅基行动.com) CEO

一人公司 + 外部合作伙伴。三块业务：
- **Agent 定制**：把你的业务经验变成可复制的 AI Agent（自交付 / 技术合作）
- **AI 落地陪跑咨询**：不下课、不讲课，陪你把 AI 真正用到业务里（主推）
- **AI 团队赋能**：用 AI 改造团队核心工作流（讲师合作交付）

产品经理出身，懂业务也懂技术。走「咨询型陪跑」路线 — 这意味着你不会拿到一套通用课程，而是针对你的业务场景，一起找到 AI 的真实切入点。

**联系我**：
- 公众号：曾俊 AI 实战笔记
- 微信：zengjun_ai

---

*本项目的知识库内容采用 [CC BY 4.0](LICENSE) 许可。提取工具脚本采用 MIT 许可。*
