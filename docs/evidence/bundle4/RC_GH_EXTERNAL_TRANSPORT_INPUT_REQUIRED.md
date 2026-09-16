# RC-G / RC-H — real external transport verification: INPUT REQUIRED

Both gates require a **real external SMTP send to an explicitly owner-authorized verification inbox**,
with the recipient actually receiving the message. The loopback-sink evidence (B4.16) is deterministic
transport proof only and does **not** satisfy these gates.

**Status: INPUT REQUIRED.** These gates were stopped cleanly — no local sink was substituted, nothing was
sent to any prospect/third party, and no delivery/alert result was fabricated.

## Why stopped

No external SMTP configuration and no authorized verification recipient are available in this environment:

- Process environment: `PYRNOVA_RC_VERIFY_RECIPIENT`, `PYRNOVA_SMTP_HOST`, `PYRNOVA_SMTP_PORT`,
  `PYRNOVA_SMTP_USERNAME`, `PYRNOVA_SMTP_PASSWORD`, `PYRNOVA_SMTP_USE_TLS`, `PYRNOVA_DELIVERY_SENDER` —
  **all unset**.
- The gitignored `/Users/stu/Documents/Pyrnova/.env` holds only S3 + `SAM_API_KEY` keys — **no SMTP,
  sender, or recipient keys**.
- Personal Gmail is forbidden; sending to MTSI/Torch/any prospect is forbidden.

## Operator-supplied values / actions required (to close G and H)

1. A real, reachable SMTP endpoint the operator authorizes for verification, provided via environment (not
   committed): `PYRNOVA_SMTP_HOST`, `PYRNOVA_SMTP_PORT`, `PYRNOVA_SMTP_USERNAME`, `PYRNOVA_SMTP_PASSWORD`,
   `PYRNOVA_SMTP_USE_TLS`, `PYRNOVA_DELIVERY_SENDER` (verified sender/from address).
2. An **explicitly owner-authorized verification inbox** address via `PYRNOVA_RC_VERIFY_RECIPIENT` (a
   mailbox the owner controls and will check for receipt — never a prospect).
3. Owner confirmation that the operator will **observe actual receipt** in that inbox and report it back
   (receipt cannot be self-verified from inside the candidate).

Credentials/recipient must come from the operator environment only; they will not be written to source,
tests, fixtures, or docs. Where evidence must record configuration identity, only a non-secret
identifier/fingerprint (e.g. host + a hash) will be stored — never the secret itself.

## What is already implemented and ready (no code change needed to run the verification)

- Candidate `SMTPEmailTransport` (real `smtplib`) is the production seam for **both** paths; config
  resolves it when SMTP env is set, else an explicit `DisabledTransport` (never a silent/fabricated
  delivery). Deterministic evidence already preserved: durable delivery result, tenant/customer
  association, duplicate suppression, retry/resume, non-silent FAILED, watcher/dead-man, heartbeat
  expiry, transport failure, bounded retry, restart/recovery, recurrence, redaction.
- When the values above are supplied, verification is: RC-G = one bounded real delivery to the authorized
  inbox (verify receipt, durable result, tenant ownership, no duplicate on deterministic re-execution);
  RC-H = one INFO + one OPERATOR_ATTENTION + one CRITICAL + one RESOLVED external transition to the same
  authorized inbox (controlled synthetic alert events; no production sources broken).

This is verification, not outreach.
