# Reference audio comparison implementation

Approved by user on 2026-10-19, including local, GitHub and production deployment.

Goal: runnable WavLM-Large reference comparison, with honest experimental results.
Architecture: isolated CPU scorer, existing durable worker queue, immutable job inputs,
reference feature cache and session eligibility snapshots. No change to other sites.
Stack: FastAPI, PyTorch CPU, Transformers, NumPy/Numba, PostgreSQL, Next.js.
Spec: ../specs/2026-10-19-reference-audio-scoring-design.md

Global constraints: fixed full precision model; no public scorer port; no secrets in Git;
resource test before provider activation; preserve old results; no invented word scores.

- [x] 1. Core: failing tests for DTW and audio validation, implement scorer and pinned container; probe memory/latency safely.
- [x] 2. Integration: failing tests for reference snapshot, authorization and no-audio completion; implement migration, adapter and API.
- [x] 3. UI: implement experimental similarity and paired segment playback, admin page test, eligible-page controls; typecheck/build/e2e.
- [x] 4. Release: fresh review, regression, backup, versioned deploy, smoke tests and Git sync.

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

- Fresh reviewer completed: two P2 findings; both reproduced RED then fixed GREEN.
  Legacy rounds retain their mode and can explicitly restart without losing history.
  Browser codec overhead now has a bounded one-second allowance, matching upload validation;
  full sequence remains unchanged. Probe covers 61 seconds. Full suite: 37 passed, 1 skipped.
- Review resource note accepted: actual HTTP endpoint memory must be measured, not only the standalone probe.

- Post-review restart-flow coverage also exposed the need to exclude inactive historical
  rounds from resume shortcuts; regression reproduced and fixed. Full local suite remains
  37 passed, 1 skipped; 8 browser tests passed. Final PostgreSQL suite: 33 passed.
- Resource gate passed: full 60-second HTTP comparison 176.81 seconds, 2 GiB cgroup
  peak, zero OOM events. Short 8-second comparison 24.57 seconds cold / 6.02 cached.
  Synthetic self-matches are mechanics tests, not pronunciation accuracy validation.
- Production activated as ref-24c9caa, reference_similarity, schema 0003. Real admin
  browser upload of existing 30.762-second reference completed in 81 seconds with
  index 100 and segment playback controls. No student learning records were created.
- No review findings deferred. Model is deployed unchanged; results remain experimental.

- Final visual inspection found clipped playback controls in the admin dialog. Added
  a failing desktop/mobile bounds test, widened the dialog and wrapped controls;
  production build and all 9 browser tests now pass. Final UI release ref-522857b.
  Actual reference/recording byte-range playback both returned HTTP 206.
