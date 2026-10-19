# Reference audio comparison implementation

Approved by user on 2026-10-19, including local, GitHub and production deployment.

Goal: runnable WavLM-Large reference comparison, with honest experimental results.
Architecture: isolated CPU scorer, existing durable worker queue, immutable job inputs,
reference feature cache and session eligibility snapshots. No change to other sites.
Stack: FastAPI, PyTorch CPU, Transformers, NumPy/Numba, PostgreSQL, Next.js.
Spec: ../specs/2026-10-19-reference-audio-scoring-design.md

Global constraints: fixed full precision model; no public scorer port; no secrets in Git;
resource test before provider activation; preserve old results; no invented word scores.

- [ ] 1. Core: failing tests for DTW and audio validation, implement scorer and pinned container; probe memory/latency safely.
- [ ] 2. Integration: failing tests for reference snapshot, authorization and no-audio completion; implement migration, adapter and API.
- [ ] 3. UI: implement experimental similarity and paired segment playback, admin page test, eligible-page controls; typecheck/build/e2e.
- [ ] 4. Release: fresh review, regression, backup, versioned deploy, smoke tests and Git sync.

Review focus: untrusted recording bounds, malformed scorer output, immutable reference
authorization, retained legacy sessions, no-audio completion, CPU/RAM isolation,
playback offsets after trimming, and silent changes of model/method.

Verification: backend pytest, scorer pytest, frontend typecheck/build and workflows;
server isolated PostgreSQL tests and actual model runs. Synthetic probes validate mechanics,
not child pronunciation accuracy. If model cannot safely fit, deploy integration disabled
and report measured blocker, without replacing the approved model.

## Execution ledger

- Base 0d07a19. Existing codex/lumaread-mvp branch is clean; update user's local checkout.
- Interfaces checked: scorer returns time offsets relative to original uploads; worker attaches
  authorized asset IDs. UI handles tagged similarity result separately from legacy word scores.
- User authorization covers push/deploy. No further approval loop required.
- Core tests: missing implementation failed first, then 4 scorer tests passed.
- Integration tests: 3 failures before implementation, now 5 reference tests pass.
- Full local suite: 35 passed, 1 PostgreSQL-only test skipped; 7 browser tests passed;
  production frontend build and TypeScript passed. Real model validation pending.
- Model weights downloaded and SHA256 verified locally; server source build and model
  upload ongoing. Server HF route timed out, so transfer pinned weights from local.
- No child recordings available: every similarity result is explicitly experimental.
