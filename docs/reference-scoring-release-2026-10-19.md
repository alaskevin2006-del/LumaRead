# Reference comparison release measurements — 2026-10-19

Implementation: `522857b` (final UI), `24c9caa` (unchanged backend/scorer), fixed WavLM-Large revision
`c1423ed94bb01d80a3f5ce5bc39f6026a0f4828c`. Full FP32 final-layer features,
cosine DTW normalized by path length. Model file SHA256 verified on both machines.

Current server: 2 CPU cores, 3,723 MiB RAM, no detected NVIDIA runtime.
Isolated scorer: 2 GiB memory+swap cap, 0.75 CPU, one model process, private network.
No changes were made to Yixue or AUGENBLICK code or configuration.

## Measured results

| Test | Wall time | Result |
|---|---:|---|
| Model load, memory-mapped weights | 11.93 s | Success |
| 2-second generated signal, single feature extraction + self-DTW | 3.71 s | Index 100 |
| 10-second generated signal, single feature extraction + self-DTW | 7.65 s | Index 100 |
| 30-second generated signal, single feature extraction + self-DTW | 30.97 s | Index 100 |
| 61-second generated signal, single feature extraction + self-DTW | 89.49 s | Index 100 |
| Actual HTTP endpoint, 8-second excerpt of uploaded reference, first request | 24.57 s | HTTP 200, 4 segments |
| Same reference cached, 8-second recording | 6.02 s | HTTP 200, 4 segments |
| Actual HTTP endpoint, two 60-second generated signals | 176.81 s | HTTP 200, 30 segments |
| Production administrator UI, existing 30.762-second page reference self-comparison | 81 s | Real queued job succeeded, index 100, paired playback controls shown |

The full endpoint reached the 2 GiB cgroup peak. Memory reclamation occurred;
the container was not killed. These are single-request measurements, not a
concurrent-student capacity guarantee. Longer recordings are slow on this CPU.
The durable worker queue serializes requests; simultaneous students will wait.

The above self-comparisons verify mechanics and resource behavior only. Child/adult
cross-speaker, omission/substitution, natural speed changes and real-world recording
accuracy are not validated by these results. All displayed results remain experimental.
No simulated scores or fabricated word accuracy are used.

## Regression coverage

- Local backend + scorer: 37 passed, 1 PostgreSQL-only test skipped.
- Dedicated server PostgreSQL test database: 33 passed before activation.
- Browser workflows: 9 passed; production frontend build/typecheck passed.
- Fresh independent reviewer: legacy-round migration and 60-second recorder boundary
  findings reproduced and fixed. Restarted historical rounds no longer appear as active
  resume shortcuts; their history and original completion rules remain intact.
- Resource probe and endpoint test retained the full model, without quantization or
  chunked inference. A bounded one-second recording tolerance handles browser overhead.

Pre-deployment data backups:
`/opt/lumaread/backups/20261019T105819Z` and
`/opt/lumaread/backups/20261019T112122Z`.
Schema migration 0003 adds nullable reading-session mode/eligibility fields.
Operational instructions and rollback: `deploy/SCORING.md`.

Activated release: `ref-522857b`, provider `reference_similarity`, schema `0003`.
The scorer has no public port and restarts with the host. Production login, administration
and student navigation were checked over HTTPS; the other two sites returned HTTP 200.
The administrator smoke test creates no student attempt, completion or check-in.

Both real result audio assets passed authenticated byte-range playback checks. The
final UI patch widens the administrator trial dialog and wraps playback controls;
desktop/mobile bounds were reproduced failing and then passed. The final rollout
updates only web, retaining the already-verified warm scorer and backend containers.
Their images are aliased under the final release tag for subsequent full-stack starts.
