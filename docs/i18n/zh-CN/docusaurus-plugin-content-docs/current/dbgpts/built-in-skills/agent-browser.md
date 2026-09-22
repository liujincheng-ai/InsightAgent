# agent-browser

## 概览

`agent-browser` 是一个面向智能体的内置浏览器自动化 skill，用于更确定性、更稳定的 Web 交互。

它不同于基于截图和视觉定位的浏览器流程，而是依赖 accessibility tree 快照和 ref 形式的元素选择。

## 仓库路径

```text
skills/agent-browser/
└── SKILL.md
```

## 适用场景

- 多步骤浏览器工作流
- 复杂单页应用（SPA）
- 需要稳定元素定位的场景
- 需要反复执行的隔离自动化会话

## 核心工作流

1. 打开目标页面。
2. 生成带交互 ref 的快照。
3. 读取返回的 JSON 结构。
4. 使用 `@e2` 这类 ref 与元素交互。
5. 页面跳转或 DOM 变化后重新生成快照。

## 常见命令

```bash
agent-browser open https://example.com
agent-browser snapshot -i --json
agent-browser click @e2
agent-browser fill @e3 "text"
agent-browser wait --load networkidle
```

## 这个 skill 重点描述什么

由于这个 skill 主要以 CLI 方式驱动，它的核心价值主要体现在 `SKILL.md` 中，包括：

- 页面导航模式
- 快照策略
- 基于 ref 的交互方式
- wait 策略
- 多 session 使用方式
- 状态保存与恢复

## 为什么它重要

当智能体需要可靠的网页自动化能力，而又不想依赖脆弱的视觉选择器时，这就是最适合使用的 built-in skill。
