# skill-creator

## 概览

`skill-creator` 是内置的 meta-skill，用于设计、搭建、校验和打包新的 skill。

它也是当前仓库中关于“skill 应该如何组织”的最佳实践参考。

## 仓库路径

```text
skills/skill-creator/
├── SKILL.md
├── scripts/
│   ├── init_skill.py
│   ├── package_skill.py
│   └── quick_validate.py
├── references/
│   ├── workflows.md
│   └── output-patterns.md
└── LICENSE.txt
```

## 适用场景

- 创建新的 skill
- 改进已有 skill
- 判断什么内容应放进 `SKILL.md`、`scripts/`、`references/` 和 `assets/`
- 校验并打包成可分发的 `.skill` 文件

## 它教授的核心流程

1. 理解目标 use case。
2. 规划可复用脚本、参考资料和资源文件。
3. 初始化一个 skill 骨架。
4. 实现并打磨打包资源。
5. 编写或完善 `SKILL.md`。
6. 校验并打包最终 skill。

## 关键资源

| 资源 | 作用 |
|---|---|
| `scripts/init_skill.py` | 创建新的 skill 骨架 |
| `scripts/package_skill.py` | 把 skill 打包成可分发产物 |
| `scripts/quick_validate.py` | 快速校验 skill 结构和质量 |
| `references/workflows.md` | 多步骤 skill 工作流设计指南 |
| `references/output-patterns.md` | 输出格式与质量模式指南 |

## 为什么它重要

这个 built-in skill 定义了 InsightAgent 中编写自定义 skill 和未来内置 skill 的最佳实践模型。
