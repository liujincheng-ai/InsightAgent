# Week 4 进度记录：失败恢复与稳定性

## 完成状态

- [x] 冻结 20 条故障集与 SHA-256，划分 12 dev / 6 test / 2 challenge。
- [x] 实现统一失败类型、Retry/Replan/Terminate 策略和一次恢复预算。
- [x] 实现参数规范化、SQL 归一化、失败指纹与连续两次相同失败断路器。
- [x] 实现 `success/failed/partial` 完成合同，保留已验证 Observation。
- [x] 将可靠性 ToolPack 接入数据库、知识和集成三条 InsightAgent 路径。
- [x] 实现请求级故障注入、逐步诊断事件、原始 SSE、CSV、manifest 和聚合器。
- [x] 修复异步评测桥中的阻塞 I/O；保留 candidate1，整套重跑 candidate2。
- [x] Flash Before/After 各完成三次 20 题正式运行。
- [x] 冻结最终配置后完成唯一一次 Pro 20 题运行，未补跑。
- [x] 按用户后续要求分析 Pro 失败、实现通用优化并用新目录完成同集复验。
- [x] 完成 20 次断路器确定性验收，20/20 触发且触发后调用为 0。
- [x] 主 Demo 经两轮可审计改进后严格 rubric 3/3。
- [x] InsightAgent 全量回归 199/199 通过。

## 冻结资产

- 数据集：`evaluation/dataset/failure_cases.json`，版本 1.0.0。
- SHA-256：`446c84d32df7bf181a5f477850dfbc6b59ebcbb24d042b90b41cfb2d5d8851cc`。
- 最终配置：`evaluation/week4_final_config.json`。
- Flash 正式结果：`week4-candidate2-20260918-{baseline|after}-...-run1..3`。
- Flash 聚合：`week4-candidate2-flash-comparison-20260918`。
- Pro 原始结果：`week4-final-pro-all-20260919`。
- Pro 优化后采用结果：
  `week4-pro-optimized-final-20260919-after-deepseek-v4-pro-all-run1`。
- 主 Demo 最终结果：`week4-main-demo-final-flash-3x-20260919`。
- 断路器结果：`week4-circuit-breaker-acceptance-20260919.json`。

## Flash 三次均值

| 指标 | Before | After | 变化 |
|---|---:|---:|---:|
| 总通过率 | 51.67% | 96.67% | +45.00pp |
| 可恢复任务恢复率 | 91.67% | 97.22% | +5.56pp |
| 有界终止率 | 96.67% | 100% | +3.33pp |
| 失败类型准确率 | 85.00% | 98.33% | +13.33pp |
| 恢复动作准确率 | 51.67% | 98.33% | +46.67pp |
| 完成状态准确率 | 71.67% | 96.67% | +25.00pp |
| 不可恢复盲重试率 | 33.33% | 0% | -33.33pp |
| 断路后重复调用率 | 0% | 0% | 0pp |
| 平均步骤 | 3.10 | 2.77 | -0.33 |
| 平均延迟 | 47.36s | 35.66s | -11.70s |
| P95 延迟 | 120.04s | 91.81s | -28.23s |

120 个 candidate2 case-run 的最大墙钟时间为 120.12 秒，无超过 121 秒的样本。

## 最终边界

- Flash After 三轮恢复率分别为 100%、100%、91.67%，全部达到 80% 门槛。
- Pro 原始恢复率 66.67%、总通过率 70%；通过无损参数归一、请求级共享预算、有界自动
  恢复和首 Tool 证据门禁，同集回归达到 91.67% 与 90%，终止率 100%、盲重试和
  断路后重复调用仍为 0%。该结果不是独立盲测。
- candidate1 曾出现 1127 秒阻塞，根因是评测桥在异步路由内执行同步 `urlopen`；改为
  `httpx.AsyncClient` 后整套 candidate2 重跑，旧结果没有删除。
