# Logs Directory

## Active State (Hot Memory)
Located in `../autoload/`:
- `_state.md` - Current 10 sessions (loaded every session)
- `_defects.md` - Current 15 defects (loaded every session)
- `_tech-stack.md` - Tech reference (loaded every session)

## Archives (Cold Storage)
- `state-archive.md` - Sessions 193+, auto-rotated when >10 active
- `defects-archive.md` - Older defects, auto-rotated when >15 active
- `archive-index.md` - Navigation helper for quick lookup

## Rotation Rules
1. When `_state.md` exceeds 10 sessions:
   - Move oldest entry to `state-archive.md`
   - Update `archive-index.md` with new line numbers

2. When `_defects.md` exceeds 15 entries:
   - Move oldest entries to `defects-archive.md`
   - Update `archive-index.md` with new counts

## Historical Files
- `session-log.md` - Historical record of all sessions (kept by user decision, updated by `/end-session`)
