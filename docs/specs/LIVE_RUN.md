# LIVE_RUN — fresh checkout → live Pyrnova intelligence

For an ordinary internet-connected machine. ~5 minutes. USAspending needs no key; SAM needs one key.

## 1. Install
The only runtime dependency is `requests`. You do **not** need to install the package itself —
`python -m pyrnova.cli` runs from the repo root.
```bash
git clone https://github.com/stulogic/pyrnova && cd pyrnova
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # simplest, works on any pip
```
Editable install (`pip install -e .`) also works, but needs a modern pip — if it errors with
"editable mode currently requires a setuptools-based build", your pip is too old:
`pip install --upgrade pip` first, or just use the `requirements.txt` line above.

## 2. Configure
```bash
cp .env.example .env
```
Edit `.env` only if you want SAM (pre-solicitation) intelligence:
```
SAM_API_KEY=your_key_here
```

Pyrnova loads `SAM_API_KEY` automatically from the repository-local `.env` when the process
environment does not already provide it. The file is gitignored and should remain mode `600`, so
interactive and scheduled local runs use the same private source without putting credentials in Git.
Get the key: sign in at https://sam.gov → **Account Details → API Key** (or the public
"Get Opportunities" API at https://open.gsa.gov/api/get-opportunities-public-api/). Nothing else is
required — the evidence archive and state default to local folders (`./var/…`), no cloud needed.

## 3. Run — USAspending first (no key)
```bash
python -m pyrnova.cli capture-radar --profile examples/profiles/torch_technologies.json --live \
  --window-days 540 --min-amount 1000000
```
What it does: pulls the target's own award history + its NAICS recompete landscape from live
USAspending, archives the raw evidence (content-addressed, timestamped), detects recompete/expiry
candidates, matches them to the profile, and writes:
- `out/signal_brief_torchtechnologies.md`
- `out/capture_radar_torchtechnologies.md`
Predictions/reviews/scoreboard accrue under `./var/state/`.

## 4. Add SAM (pre-solicitation) once the key is set
Same command — it auto-includes SAM when `SAM_API_KEY` is present (Sources Sought, Presolicitation,
Special Notices for the profile's first NAICS, last 30 days).

## 5. Confirm a human review, then re-emit
Read the candidates, apply the review discipline in `docs/specs/REVIEW_TEMPLATE.md`, then stamp your name so
recommended items become confirmed STRIKEs:
```bash
python -m pyrnova.cli capture-radar --profile examples/profiles/torch_technologies.json --live \
  --window-days 540 --min-amount 1000000 --reviewer "YourName"
```

## 6. See what accumulated
```bash
python -m pyrnova.cli scoreboard
```

## Useful flags
- `--as-of YYYY-MM-DD` pin the reference date (default today)
- `--window-days N` recompete forward window (default 540)
- `--min-amount N` floor recompete award value
- `--threshold 0.3` relevance cutoff for a STRIKE
- `--fixtures` run fully offline against bundled sample data (no network)

## Diagnostics / graceful failures
- **`ProxyError` / `CONNECT tunnel failed 403`** → you're on a restricted network (e.g. a corporate/CI
  egress policy). Run from an ordinary internet connection. Do not disable TLS.
- **`SAM search failed: HTTP 401/403`** → bad/missing `SAM_API_KEY`. USAspending still runs without it;
  the CLI prints `[info] SAM_API_KEY not set — running recompete-only`.
- **`USAspending search failed: HTTP 4xx`** → usually a malformed filter; re-run without `--min-amount`,
  or narrow the profile NAICS list. Raw pages are only archived on HTTP 200.
- **No STRIKEs** → a legitimate result. Widen `--window-days`, lower `--threshold`, or try a second
  target profile. Record why (the scoreboard + rejected candidates capture it).

## Output paths
`out/` (briefs, gitignored) · `var/archive/` (raw evidence, gitignored) · `var/state/` (predictions,
reviews, scoreboard — the Day-1 accumulation, gitignored).
