# Codex Compatibility Skills

These are Codex-facing wrappers around the shared `.claude` workflows.

## Supported Aliases

- `/resume-session` or `resume session`
- `/end-session` or `end session`
- `/implement <plan>` or `implement <plan>`
- `/writing-plans <spec>` or `writing plans <spec>`
- `/brainstorming` or `brainstorming` or `brainstorm <topic>`
- `/tailor <spec>` or `tailor <spec>`
- `/systematic-debugging` or `systematic debugging` or `systematic debug <issue>`
- `/test ...` or `test ...`
- `/audit-docs` or `audit docs`
- legacy alias: `/audit-config` or `audit config`

## Design Rules

- Update the same shared `.claude` state and handoff files when appropriate.
- Store new Codex-authored plans in `.codex/plans/`.
- Tag shared Codex-authored artifacts with `-codex-` when they live under
  `.claude/`.
- Keep wrappers short and push detail to the upstream `.claude` skill only when
  needed.
- Prefer these wrappers first when working in Codex.

## Persona Rule

When a Claude workflow would dispatch a named agent, Codex should use that same
agent name as a review or routing persona. Generic implementation work stays
generic unless a live agent actually exists.
