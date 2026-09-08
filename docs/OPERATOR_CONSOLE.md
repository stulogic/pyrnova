# Pyrnova Operator Console v0.1

The Operator Console is a local, internal analyst layer over Pyrnova's append-only state. It does not
run the engine or alter scoring. It shows persisted candidates by target, derived run activity,
explicitly observed/unobserved source state, evidence links, and the existing system disposition.

Analysts can record ACCEPT/WATCH/REJECT adjudications, assign PRIME/SUPPORT/TEAM/DEFEND posture, retain
notes and falsification, promote an accepted item to STRIKE through the existing review functions,
export a Signal Brief through the existing renderer, and record a small outcome label. All writes are
append-only JSONL under `PYRNOVA_STATE_DIR` (default `var/state`); exports go to `PYRNOVA_OUT_DIR`
(default `out`). Real customer data and output remain gitignored.

## Launch

From the repository root, using the existing environment:

```bash
python -m pyrnova.ops_server
```

Open `http://127.0.0.1:8765`. Run Capture Radar first if the selected target has no persisted
candidates. The server intentionally binds only to loopback and has no customer authentication or
remote deployment path.

## Boundaries

- Source health means only “an observation is/is not persisted”; it is not a live availability claim.
- Run status is reconstructed from persisted opportunity `run_id` values, not a job scheduler.
- Outcomes are operator-entered labels and are not verified pipeline ground truth.
- Export includes current persisted STRIKE items; it does not rerun or rescore them.
- Recovered reports may be imported only with explicit origin/freshness labels and unavailable scores;
  they remain pending review rather than being presented as fresh or promoted automatically.
- No portal, billing, CRM, Postgres, graph, mobile, realtime, broad analytics, or agents are included.
