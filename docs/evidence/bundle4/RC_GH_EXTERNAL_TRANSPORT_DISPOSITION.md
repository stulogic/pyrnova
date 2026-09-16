# RC-G / RC-H — external transport verification disposition (owner acceptance-boundary revision)

This is a documentation-only acceptance-authority update. **No executable candidate code changed.** It
supersedes the *INPUT REQUIRED* holding status in `RC_GH_EXTERNAL_TRANSPORT_INPUT_REQUIRED.md` for gates
G and H, on the basis of a completed bounded external transport verification attempt.

- Branch: `prelaunch-convergence-001`
- Locked executable candidate: `50e1b7a` (unchanged)
- Executable candidate changed by this update: **NO**

## Verified facts from the RC-G / RC-H bounded external transport attempt

A bounded external transport verification was run against a real external provider (Cloudflare). It
established, at the locked candidate `50e1b7a`:

- executable candidate unchanged; worktree clean;
- Cloudflare SMTP connection succeeded;
- implicit TLS / SMTPS succeeded;
- SMTP authentication succeeded;
- Pyrnova selected `SMTPEmailTransport` correctly;
- candidate attempted real external delivery;
- candidate correctly persisted **FAILED** rather than fabricating delivery;
- bounded retries executed correctly;
- customer duplicate suppression worked correctly;
- alert deduplication worked correctly;
- INFO / OPERATOR_ATTENTION / CRITICAL / RESOLVED lifecycle and rendering worked correctly;
- retry / resume behaviour was demonstrated;
- redaction behaviour remained correct;
- no unauthorized recipient was contacted;
- no executable code change was required.

External delivery failed solely at `MAIL FROM`, because Cloudflare returned:

> `550 5.7.1 Not authorized to send from domain outrunranch.com`

This is an **external sender-domain authorization / configuration failure**. It is **not** a Pyrnova
executable transport defect. **No external receipt occurred.** RC-G and RC-H are **not** recorded as
having passed external receipt verification.

## Owner acceptance-boundary revision

The owner revises the RC acceptance boundary. Real SMTP provider credentials, the final sender-domain
identity, and external sender authorization are **deployment / operator configuration**. They are not
required properties of the executable release candidate.

Accordingly:

- **RC-G: CLOSED AS RC BLOCKER / REAL EXTERNAL CUSTOMER DELIVERY ACTIVATION DEFERRED TO DEPLOYMENT.**
- **RC-H: CLOSED AS RC BLOCKER / REAL EXTERNAL OPERATOR ALERT ACTIVATION DEFERRED TO DEPLOYMENT.**

The distinction between **PASS** and **CLOSED AS RC BLOCKER / DEFERRED DEPLOYMENT ACTIVATION** is
preserved. This is **not** a manufactured PASS.

### Rationale

The candidate has demonstrated that its external SMTP implementation is compatible with the selected real
external provider; networking, implicit TLS, and authentication work; real external delivery is attempted;
external refusal is handled deterministically; durable failure state is correct; bounded retry works;
duplicate suppression works; alert lifecycle works; and retry/resume works. The remaining failure is
entirely attributable to sender-domain authorization in external operator configuration. Changing an SMTP
provider, credential, sender address, or authorized sender domain does not require rebuilding the Pyrnova
executable candidate. External receipt is therefore an **activation / configuration** acceptance
requirement, not an RC executable-candidate blocker.

## New deployment activation requirement

Before the FINAL REPLACEMENT SOAK begins qualifying elapsed time, the immutable deployment must have
working real external email configuration. At minimum the deployed environment must provide appropriate
values for:

- `PYRNOVA_SMTP_HOST`
- `PYRNOVA_SMTP_PORT`
- `PYRNOVA_SMTP_USERNAME`
- `PYRNOVA_SMTP_PASSWORD`
- `PYRNOVA_SMTP_USE_TLS`
- `PYRNOVA_DELIVERY_SENDER`

plus an owner-authorized external verification recipient. These remain runtime / operator configuration
and **must not** be committed to source control.

## Mandatory pre-soak activation check

After immutable deployment and before qualifying soak T0, perform a bounded external activation test
establishing:

1. real configured SMTP transport successfully sends;
2. an owner-authorized external inbox actually receives a customer-delivery verification;
3. real configured operator-alert transport successfully sends;
4. an owner-authorized external inbox actually receives an operator-alert verification;
5. durable delivery / alert state is correct;
6. no prospect or customer is used as the verification recipient.

The previous failed Cloudflare test remains valid evidence for candidate transport compatibility and
deterministic failure handling. It does **not** satisfy this eventual activation receipt check.

- If future activation fails because provider credentials, sender verification, or external configuration
  are incorrect: correct operator configuration and repeat. This does **not** reopen executable RC
  acceptance.
- If future activation instead identifies an actual executable candidate defect: **STOP.** Reopen the
  affected executable acceptance issue before soak T0.

## Final soak boundary

The final replacement soak must **not** begin qualifying elapsed time until:

- RC is owner accepted;
- the exact owner-accepted executable SHA is immutably deployed;
- required runtime configuration is established;
- the external transport activation check succeeds;
- all other final-soak prerequisites are satisfied.

There is **no paused clock.** Do not begin T0 merely because the candidate is deployed.

## Controlling sequence

```
RC OWNER ACCEPTED
→ IMMUTABLE RC DEPLOYMENT
→ RUNTIME CONFIGURATION
→ EXTERNAL DELIVERY / ALERT ACTIVATION CHECK
→ ESTABLISH SOAK T0
→ 72-HOUR FINAL REPLACEMENT SOAK
→ LIVE OPS ACCEPTANCE
→ CUSTOMER #1 GO/NO-GO
```

## Updated RC gate matrix A–O (exact candidate `50e1b7a`)

| Gate | Verdict |
|---|---|
| A | PASS |
| B | PASS |
| C | PASS |
| D | PASS |
| E | PASS |
| F | PASS |
| G | **CLOSED AS RC BLOCKER / DEPLOYMENT ACTIVATION REQUIRED** |
| H | **CLOSED AS RC BLOCKER / DEPLOYMENT ACTIVATION REQUIRED** |
| I | PASS |
| J | PASS |
| K | PASS |
| L | PASS |
| M | PASS |
| N | PASS |
| O | PASS |

Subject to repository confirmation that no other unresolved RC blocker exists (G and H were the only open
blockers; all others PASS):

**US PHASE 1 RELEASE CANDIDATE: ALL RC BLOCKERS CLOSED / READY FOR OWNER ACCEPTANCE.**
**FINAL REPLACEMENT SOAK: NOT STARTED.** No execution step in the controlling sequence is started here.
