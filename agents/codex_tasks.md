# Codex Tasks

Use this file as the task contract for AI-assisted QA and DevOps work in this repository.

## QA Agent

Goal:
Keep runtime behavior covered by tests before production deployment.

Tasks:
1. Inspect the current route and tool surface.
2. Add or update tests for changed behavior.
3. Run `npm test`.
4. If tests fail, fix code or tests conservatively.
5. Summarize remaining risks.

Constraints:
- Do not remove production safeguards.
- Prefer small, reviewable patches.
- If behavior is ambiguous, preserve existing runtime behavior unless the user explicitly requests a change.

## Docs Agent

Goal:
Keep operator and system documentation aligned with the live service.

Tasks:
1. Review runtime endpoints, LINE commands, and deployment assumptions.
2. Run `npm run docs:generate`.
3. Update any handwritten docs that are now stale.

Constraints:
- Keep generated docs in `docs/`.
- Do not claim features are automated if they still require secrets, approvals, or external setup.

## CI Agent

Goal:
Keep the GitHub Actions pipeline healthy and reviewable.

Tasks:
1. Run `npm run ci:check`.
2. Investigate failing tests or stale generated docs.
3. Update workflows only when they match repository behavior.
4. Require secrets for deploy actions instead of hardcoding credentials.

Constraints:
- Production deploys must stay gated behind repository secrets.
- Prefer pull requests over direct production mutation.
