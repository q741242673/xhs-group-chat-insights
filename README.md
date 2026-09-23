# xhs-group-chat-insights

一个面向 Codex 的只读 Skill：在用户授权范围内抓取或增量更新小红书群聊，离线提取群话题，并分析多个群平时讨论什么、成员关心什么、互动如何发生，以及哪些问题仍未闭环。

> 重要：群聊记录和 Cookie 都属于敏感数据。这个仓库只放 Skill 本身，绝不能提交真实 Cookie、原始群聊、成员名单或含私聊证据的分析报告。

## 能做什么

- 全量抓取、断点续抓和增量更新用户有权访问的群聊
- 从已有 `messages.json` 中离线提取群话题和直接回复状态
- 规范化一个或多个群的聊天记录
- 生成话题、参与者和待深读事件三类研究表
- 基于原文上下文形成“讨论主题—成员关切—群差异—未闭环问题”的分析

不会自动发言、点赞、关注、邀请成员或修改群设置。

## 仓库结构

```text
skills/xhs-group-chat-insights/
├── SKILL.md
├── agents/openai.yaml
├── references/
└── scripts/
```

## 发布者：上传到 GitHub

先在 GitHub 新建一个空仓库，例如 `xhs-group-chat-insights`，不要勾选自动创建 README。然后在本目录执行：

```bash
git init -b main
git add .
git commit -m "Initial public release"
git remote add origin https://github.com/q741242673/xhs-group-chat-insights.git
git push -u origin main
```

发布前请再次运行 `git status` 和 `git diff --cached --stat`，确认提交内容只有 Skill 文件和说明文档。

## 使用者：安装 Skill

### 方式一：Codex 自带安装脚本

通过本仓库安装：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo q741242673/xhs-group-chat-insights \
  --path skills/xhs-group-chat-insights
```

安装后新开一个 Codex 对话，再使用 `$xhs-group-chat-insights`。

### 方式二：手动安装

```bash
git clone https://github.com/q741242673/xhs-group-chat-insights.git
mkdir -p ~/.codex/skills
cp -R xhs-group-chat-insights/skills/xhs-group-chat-insights ~/.codex/skills/
```

如果目标目录已存在，先人工确认是否需要升级；不要直接覆盖。

## 两种使用模式

### 只分析已有导出

不需要登录，也不需要 Spider_XHS。把 ZIP 或完整的 `messages.json` 提供给 Codex，然后说：

```text
请使用 $xhs-group-chat-insights 分析这些群聊记录，告诉我各群平时讨论什么、成员真正关心什么，并标注数据范围与局限。
```

### 抓取后再分析

实时抓取依赖外部项目 [Spider_XHS](https://github.com/cv-cat/Spider_XHS)。Skill 已内置只读群聊扩展、安装器、环境检查和二维码登录流程。安装要求：Python 3.10+、Node.js 20+、Git。

```bash
python3 ~/.codex/skills/xhs-group-chat-insights/scripts/setup_capture.py --check
python3 ~/.codex/skills/xhs-group-chat-insights/scripts/setup_capture.py
python3 ~/.codex/skills/xhs-group-chat-insights/scripts/xhs_group_tool.py login-qr
python3 ~/.codex/skills/xhs-group-chat-insights/scripts/xhs_group_tool.py doctor
```

第二条命令会下载依赖；第三条命令显示本地二维码，使用者需用自己的小红书 App 扫码确认。Cookie 只写入权限为 `600` 的本地配置文件，不会打印，也不得上传到 GitHub。配置完成后可说：

```text
请使用 $xhs-group-chat-insights 更新这个小红书群聊并分析本周新话题：<群聊链接>
```

更完整的运行说明见 Skill 内的 `references/setup.md` 和 `references/capture.md`。

## 许可与边界

本仓库中的 Skill 文件采用 MIT License。Spider_XHS 是独立的外部项目，没有随本仓库分发；其公开 README 当前说明“仅供学习交流、禁止商业化”。使用者须自行遵守该项目的最新说明、小红书平台规则以及适用法律。
