# Agent Evaluation

This eval set checks whether the research agent behaves like an evidence-grounded tool-using agent.

Metrics:

- `toolRecall`: expected tools were selected.
- `evidenceRecall`: required evidence types were produced.
- `citationRecall`: final answer cites expected source domains.
- `safetyPass`: answer avoids forbidden investment-advice phrases.

Run:

```bash
cd agent-service
source .venv-equity-research-agent/bin/activate
PYTHONPATH=src python evals/run_eval.py --run
```

The default `--run` mode is deterministic fixture scoring. Use live mode only when LLM/provider credentials are configured and external calls are acceptable:

```bash
PYTHONPATH=src python evals/run_eval.py --run --mode live --case-timeout-seconds 45
```

The runner writes `evals/latest-report.json`.
