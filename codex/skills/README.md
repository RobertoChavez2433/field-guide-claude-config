# Codex Compatibility Skills

These are Codex-facing wrappers around the shared `.claude` workflows.

They exist because Codex cannot register native slash commands from the repo,
but it can follow documented compatibility conventions.

## Supported Compatibility Aliases

- `/resume-session` or `resume session`
- `/end-session` or `end session`
- `/implement <plan>` or `implement <plan>`
- `/writing-plans <spec>` or `writing plans <spec>`
- `/brainstorming` or `brainstorming` or `brainstorm <topic>`
- `/systematic-debugging` or `systematic debugging` or `systematic debug <issue>`
- `/test ...` or `test ...`
- `/audit-config` or `audit config`

## Design Rules

- Update the same `.claude` handoff/state files Claude uses.
- Prefer the same `.claude` artifact directories Claude uses for specs, plans,
  reviews, and checkpoints.
- Tag Codex-authored shared artifacts with `-codex-` in the filename.
- Follow the same no-noise, targeted-context approach.
- Prefer these wrappers first when working in Codex.
- Use the matching `.claude/skills/*/SKILL.md` file as the upstream reference
  when more detail is needed.

## Persona Rule

- When a Claude workflow would dispatch a named agent, Codex should use that
  same agent name as an internal persona or review mode.
- These personas are not slash commands; they are routing and reasoning modes.
