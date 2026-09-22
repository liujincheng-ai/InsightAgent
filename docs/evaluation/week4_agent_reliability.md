# Week 4 Agent Reliability Evaluation

InsightAgent Week 4 evaluates bounded failure recovery on a frozen 20-case suite. It
uses request-local fault injection and preserves raw SSE events; it never mutates the
shared database, knowledge index, or global tools.

The dataset SHA-256 is
`446c84d32df7bf181a5f477850dfbc6b59ebcbb24d042b90b41cfb2d5d8851cc`.

## Run

```powershell
.\scripts\windows\run_week4_reliability.ps1 `
  -Profile after -Split all -Model deepseek-v4-flash -Repeats 3 `
  -RunPrefix <new-prefix> `
  -Endpoint http://127.0.0.1:5670/api/v1/chat/react-agent
```

The script refuses to overwrite a non-empty result directory. Each run stores raw
events, per-case records, JSON/CSV summaries, Git state, model settings, dataset hash,
and the fault-injection mode.

## Metrics

- recovery rate over cases whose expected completion is success;
- bounded termination within each case step budget;
- failure type, recovery action, and completion-state accuracy;
- blind retry rate for non-retryable failures;
- calls after the circuit breaker opened;
- duplicate failure calls, steps, and latency.

Candidate2 Flash After averaged 96.67% overall pass, 97.22% recovery, 100% bounded
termination, 0% non-retryable blind retry, and 0% calls after breaker open. The original
Pro run retained 100% bounded termination and 0% blind retry but recovered only 66.67%
of recoverable cases, below the 80% target. After explicit user-requested optimization,
lossless argument normalization, a request-wide recovery budget, bounded injected-fault
recovery, and an initial-tool evidence guard raised the same-suite Pro recovery rate to
91.67% and pass rate from 70% to 90%, while bounded termination remained 100%. This is
a post-failure same-suite regression, not an independent blind result.

Candidate1 is not a hidden result: a synchronous upstream bridge blocked its async event
loop and produced a 1127-second outlier. The bridge was changed to cancellable async
streaming, and the complete Before/After experiment—not selected cases—was rerun as
candidate2.
