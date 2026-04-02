# Logs Directory

## Active State (Hot Memory)
Located in `../autoload/`:
- `_state.md` - Current 5 sessions (loaded every session via `/resume-session`)

## Defects
Defect tracking uses **GitHub Issues** with structured labels:
- **Feature**: bare name (e.g., `sync`, `pdf`, `auth`)
- **Type**: bare name (e.g., `defect`, `blocker`, `security`, `cosmetic`)
- **Priority**: bare name (e.g., `critical`, `high`, `medium`, `low`, `parked`)
- **Layer**: colon format (e.g., `layer:data`, `layer:sync`, `layer:presentation`)

## Archives (Cold Storage)
- `state-archive.md` - Sessions 193+, auto-rotated when >5 active in `_state.md`
- `defects-archive.md` - Historical defects from pre-migration local tracking (no longer rotated; retained for historical context only)
- `archive-index.md` - Navigation helper for quick lookup

## Rotation Rules
1. When `_state.md` exceeds 5 sessions:
   - Move oldest entry to `state-archive.md`
   - Update `archive-index.md` with new line numbers