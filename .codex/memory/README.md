# Repository memory

This directory stores durable, reviewable project context for LibreOffice
Material. It is documentation, not authority over source, build results, or
external state. When memory conflicts with a commit, test artifact, or GitHub
result, update memory to match the evidence.

## Files

- [`project-state.md`](project-state.md) — scope, milestone, known facts, and next
  gates;
- [`decision-log.md`](decision-log.md) — architectural and evidence-policy
  decisions with reasons;
- [`evidence-ledger.md`](evidence-ledger.md) — accepted build, interaction, and
  visual evidence only;
- [`verification-log.md`](verification-log.md) — source, documentation, and site
  integrity checks and their exact scope.

## Update contract

- use absolute dates and exact commit identifiers;
- distinguish planned, attempted, failed, and verified work;
- link only to artifacts that exist;
- never summarize an image as accepted before its run manifest passes review;
- record dirty-worktree state when it affects reproducibility;
- do not store credentials, tokens, personal documents, or sensitive captures;
- update related roadmap and public status claims in the same change.

Memory entries should be append-only when preserving history matters. Correct a
factual error visibly rather than silently rewriting a past test result.
