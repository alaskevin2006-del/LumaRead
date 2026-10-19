# Reference comparison operations

The application supports `LUMA_SPEECH_PROVIDER=reference_similarity` and
`LUMA_REFERENCE_URL=http://scorer:8000`. It uses the page's saved audio interval.
Similarity is experimental; it is not a pronunciation correctness percentage.
There is no word-level assessment or pass mark in this mode.

## Bring up on a new server

1. Restore the application database and media using the existing deployment guide.
2. Place the pinned model files under `models/wavlm-large` as described in
   `scorer/README.md`; verify the model SHA256. Never put weights or credentials in Git.
3. Build the scorer using `docker compose -f compose.yml -f compose.scoring.yml build scorer`.
4. Run `scorer/probe.py` in a separate container with the same 2 GiB memory,
   2 GiB memory+swap, 0.75 CPU and no-network limits. Do not run multiple model
   instances concurrently on the current shared server.
5. Start the private scorer and test `/evaluate` through the application's private
   Docker network, including a long request and a repeated cached reference. The
   standalone feature probe does not include HTTP, decoder and reference-cache overhead.
6. Only after successful resource tests, set the above application variables and
   recreate `api` and `worker`. Keep the scorer private; do not publish its port.
7. Test the actual administrator page's optional trial tool. Then verify student
   recording, queued results, paired playback and completion on pages with reference audio.

Once enabled, include both Compose files when managing the full stack. The scorer
restarts after host reboot. The default base Compose file alone remains usable when
the comparison service is intentionally disabled. Never use `--remove-orphans`
without reviewing what Compose would remove.

## Failure and rollback

Set `LUMA_SPEECH_PROVIDER=disabled` and recreate `api`/`worker` to pause comparison
without changing stored results. A failed job can be retried. Existing reference
jobs keep their saved asset, interval and model revision. A model change requires
a versioned adapter update rather than silently reinterpreting an old job.

To roll back application code, select the previous `LUMA_RELEASE` image tag and
recreate only LumaRead services. Migration 0003 adds nullable columns, so the prior
application can still read the database; do not discard new records by restoring
an old dump unless recovery explicitly requires it. Backups contain sensitive data
and should remain private.

No-audio pages remain readable. New reference-mode rounds require only eligible
audio practice pages. Old rounds retain their previous requirements. Students can
explicitly start a new reference-mode round; the old incomplete round stays in history.

## Limits

- UI records up to 60 seconds; the decoder accepts a bounded extra second for browser
  timing/encoding overhead. Whole-sequence inference remains unchanged.
- One worker and one model instance; references are cached up to 512 MiB.
- CPU-only feedback is significantly slower on long recordings. A GPU deployment
  can be evaluated later without changing the model or scoring formula.
- Energy checks catch silence/low volume/clipping; they are not a speech detector.
- Cross-speaker, child/adult, omission and substitution accuracy still need actual
  institution samples. Self-comparison smoke tests only establish pipeline integrity.
