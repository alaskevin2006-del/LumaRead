# Implementation ledger

2026-10-19: Product approved; user explicitly requested implementation, isolated deployment and GitHub upload. Existing local directory contains design package only. Initialized branch `codex/lumaread-mvp`; target actual link LumaRead. Both linked GitHub repos currently empty; connector reports read-only, local Git credential manager will be checked on push.

Server read-only inventory: Ubuntu, approximately 4 GB RAM, 47 GB free disk, Docker installed, ports 80/443 occupied, Yixue under /opt/yixue and /srv/yixue. No application changes made there. Need inspect proxy mounts before choosing entry. Password supplied by user remains out of repository and files.

Ruling: execute inline with testing and one independent final review; user already authorized implementation, deployment and upload. Preserve written plan for review without an extra approval interruption.

Ruling: scoring is a real external dependency, not a UI stub. Asking about available provider while proceeding independently with content and reading workflows. Never enable mock scores on public deployment.

2026-10-19: Tasks 1–3 implemented with 13 passing API tests (auth, immutable versions, PDF import, media authorization, reading/check-in semantics, strict evaluation mapping). Explicit frozen initial Alembic migration generated; local upgrade exercised. Task 4 implemented; TypeScript/Next production build and 2 real browser workflows passed. Screens and student full lifecycle still undergoing verification.

Ruling: no provider account and no real child samples exist; do not deploy a fake or unvalidated word score. Ship adapter-ready code with a visible unavailable gate. Default installation cannot be called all-features accepted; real scoring and dependent completion/check-in remain blocked until configured and sample-tested. Current 4 GB shared server should not load a large speech model; a future evaluation server can connect via the documented contract.

Ruling: current server also now runs AUGENBLICK on port 18443. Use independent LumaRead port 8443 with dedicated volumes and containers. A new timer only copies the existing IP certificate into LumaRead's directory; it does not mount or modify another project's files. Renewal source must be replaced upon migration.

Task 5 in progress: release package uploaded to a new /opt/lumaread directory; build not started yet. Independent read-only final code reviewer dispatched per executing-plans skill.

Final review: four Important findings confirmed and fixed: streaming WebM duration fallback; ordered page renumbering; PDF retry/publication shared version locking with per-page worker rechecks; pending microphone permission invalidation on page change. Regression tests were observed failing before fixes and passing afterwards. Full backend suite: 18 passed. Browser suite: 4 passed, including actual audio playback and pending permission cancellation. Production frontend build passed.

Final: reviewer minor upload-job visibility was regraded Important because navigation could strand the user in an incorrect recording state; job responses now refresh session state independent of visible page. Reviewer minor unbounded login-key memory was regraded Important for a public service; expiry and a 4096-key limit added and verified RED→GREEN. No reviewer minors remain deferred.

Deployment build: first attempt hit existing root-owned Docker builder metadata; use sudo only for LumaRead Compose rather than altering Docker ownership. Debian HTTP downloads stalled; Dockerfile now supports an HTTPS mirror and bounded transport retries. Current server build uses Tencent's Debian mirror only within the LumaRead build. Existing application containers were not restarted.
