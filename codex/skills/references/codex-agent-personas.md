# Codex Agent Personas

Use the same agent names Claude uses, but treat them as Codex internal personas
or review modes rather than literal Claude-dispatched subagents.

## Implementation Personas

| Persona | Use For | Primary Signals |
|---------|---------|-----------------|
| `frontend-flutter-specialist-agent` | presentation-layer Flutter work | `lib/**/presentation/**`, screens, widgets, providers, UX |
| `backend-data-layer-agent` | repositories, models, datasources, schema-adjacent app logic | `lib/**/data/**`, `lib/core/database/**` |
| `backend-supabase-agent` | sync, Supabase, SQL, storage, RLS | `lib/features/sync/**`, `supabase/**` |
| `auth-agent` | auth flows, sessions, password reset, deep links | `lib/features/auth/**` |
| `pdf-agent` | OCR, extraction, PDF generation, template handling | `lib/features/pdf/**` |

Persona-specific references:

- `frontend-flutter-specialist-agent` -> `.codex/skills/references/interface-design.md`
- `pdf-agent` -> `.codex/skills/references/pdf-processing.md`

## Review Personas

| Persona | Use For | Output Focus |
|---------|---------|--------------|
| `code-review-agent` | architecture and quality review | correctness, maintainability, performance, DRY/KISS/YAGNI |
| `security-agent` | security review | auth, authorization, data exposure, validation, tenant boundaries |
| `qa-testing-agent` | test/debug review | reproduction quality, test coverage, debugging rigor |

## Routing Rules

- Feature-specific personas take priority over generic layer personas.
- If a phase spans multiple domains, either:
  - split the work by persona if file ownership is clean, or
  - use a general implementation pass while still applying persona checklists.
- Tests and integration checks should still use the relevant domain persona plus
  `qa-testing-agent` review where appropriate.

## Shared Context Rules

For any persona-driven pass:

1. Load only the smallest relevant feature context from `.claude/`.
2. Read any relevant GitHub issues or issue references before editing or reviewing.
3. Apply the same shared rules Claude would use for that domain.
4. Update the same shared `.claude` handoff files at session end.

## Shared Artifact Naming

When Codex creates artifacts in shared `.claude` directories, include
`-codex-` in the filename:

- spec: `YYYY-MM-DD-<topic>-codex-spec.md`
- plan: `YYYY-MM-DD-<topic>-codex-plan.md`
- review: `YYYY-MM-DD-<topic>-codex-review.md` or
  `YYYY-MM-DD-<topic>-codex/`
- checkpoint: `implement-codex-checkpoint.json`
