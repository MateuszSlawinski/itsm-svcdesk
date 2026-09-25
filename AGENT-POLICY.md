# Agent policy

- Bash: Shell execution can alter the workspace or leak credentials, so reviews use read-only repository tools instead.
- WebFetch: External network retrieval is unnecessary for this local contract and could expose project context.
- Browser: Browser automation can transmit data or mutate remote state, so it is prohibited for repository review.
