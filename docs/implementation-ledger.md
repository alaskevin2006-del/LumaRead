# Implementation ledger

2026-10-19: Product approved; user explicitly requested implementation, isolated deployment and GitHub upload. Existing local directory contains design package only. Initialized branch `codex/lumaread-mvp`; target actual link LumaRead. Both linked GitHub repos currently empty; connector reports read-only, local Git credential manager will be checked on push.

Server read-only inventory: Ubuntu, approximately 4 GB RAM, 47 GB free disk, Docker installed, ports 80/443 occupied, Yixue under /opt/yixue and /srv/yixue. No application changes made there. Need inspect proxy mounts before choosing entry. Password supplied by user remains out of repository and files.

Ruling: execute inline with testing and one independent final review; user already authorized implementation, deployment and upload. Preserve written plan for review without an extra approval interruption.

Ruling: scoring is a real external dependency, not a UI stub. Asking about available provider while proceeding independently with content and reading workflows. Never enable mock scores on public deployment.
