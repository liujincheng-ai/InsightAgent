# 使用自定义 Skill

InsightAgent 支持三种方式使用自定义 skill：使用内置的 `skill-creator` 从零创建、上传 zip 包导入、通过 GitHub 链接导入。

## 方式一：使用 skill-creator 创建

`skill-creator` 是 InsightAgent 内置的 meta-skill（元技能），专门用于帮助你创建业务定制化的 skill。你只需在对话中描述需求，`skill-creator` 会自动完成从设计、编写到打包的全部流程。

### 操作步骤

1. 在 InsightAgent 对话界面中，选择 `skill-creator` 技能。
2. 用自然语言描述你想要创建的 skill，例如："帮我创建一个数据分析 skill，能够读取 CSV 文件并生成可视化报表"。
3. `skill-creator` 会自动完成以下工作：
   - 分析需求并规划 skill 结构
   - 生成 `SKILL.md`（包含元数据和执行指令）
   - 创建所需的脚本、参考文档和资源文件
   - 校验并打包为可分发的 `.skill` 文件

![使用 skill-creator 创建 Skill](/img/skill/create_skill_zh.jpg)

更多关于 `skill-creator` 的详细用法，请参阅 [skill-creator 文档](./built-in-skills/skill-creator.md)。

## 方式二：上传 Zip 包

如果你已经有一个打包好的 skill（`.zip` 或 `.skill` 文件），可以直接在 InsightAgent 的 Web UI 中上传。

### 操作步骤

1. 进入 InsightAgent 的 **Skills** 页面。

![Skill 列表页](/img/skill/skill_list_zh.png)

2. 点击上传按钮，选择本地的 `.zip` 或 `.skill` 文件上传。

![上传 Skill](/img/skill/upload_skill_zh.png)

3. 上传完成后，skill 会自动出现在列表中，即可在对话中使用。

## 方式三：通过 GitHub 链接导入

InsightAgent 支持直接从 GitHub 仓库导入 skill，适合使用社区或团队共享的 skill。

### 操作步骤

1. 进入 InsightAgent 的 **Skills** 页面。
2. 点击 GitHub 导入按钮，粘贴 skill 所在的 GitHub 仓库链接。

![通过 GitHub 导入 Skill](/img/skill/import_github_skill_zh.png)

3. 系统会自动拉取仓库内容并完成导入，导入成功后即可使用。

## 相关阅读

- [skill-creator](./built-in-skills/skill-creator.md) — 了解 skill-creator 的完整能力和资源
- [Skills 总览](./introduction.md) — 了解 skill 的定义、结构和工作原理
