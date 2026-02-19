# Springfield Fixture Regeneration: Upstream Stage-Trace Scorecard

Date: 2026-02-18

## Objective And Scope

- Perform an upstream-first diagnosis after Springfield fixture regeneration.
- Anchor conclusions to observed stage-trace output and fixture artifacts.
- Identify earliest degradation points, not only final checksum failure.
- Scope is analysis only; no production code changes.

## Exact Commands Run And Exit Codes

1. Command:
```powershell
flutter test test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart --plain-name "Print stage-by-stage scorecard vs ground truth"
```
Exit code: `0`

2. Command:
```powershell
$path='test/features/pdf/extraction/fixtures/springfield_parsed_items.json'; $base = (git show "HEAD:$path" | Out-String) | ConvertFrom-Json; $post = Get-Content -Raw $path | ConvertFrom-Json; function ItemRow($obj,$n,$label){ $it=$obj.items | Where-Object { $_.item_number -eq "$n" } | Select-Object -First 1; [pscustomobject]@{snapshot=$label; item_number=$n; unit_price=$it.unit_price; bid_amount=$it.bid_amount; raw_unit_price=$it.raw_unit_price; raw_bid_amount=$it.raw_bid_amount} }; $out=@(); $out += [pscustomobject]@{snapshot='baseline_HEAD'; total_items=$base.items.Count; null_unit_price=(($base.items | Where-Object { $null -eq $_.unit_price }).Count); null_bid_amount=(($base.items | Where-Object { $null -eq $_.bid_amount }).Count)}; $out += ItemRow $base 58 'baseline_HEAD'; $out += ItemRow $base 111 'baseline_HEAD'; $out += [pscustomobject]@{snapshot='post_regen_worktree'; total_items=$post.items.Count; null_unit_price=(($post.items | Where-Object { $null -eq $_.unit_price }).Count); null_bid_amount=(($post.items | Where-Object { $null -eq $_.bid_amount }).Count)}; $out += ItemRow $post 58 'post_regen_worktree'; $out += ItemRow $post 111 'post_regen_worktree'; $out | ConvertTo-Json -Depth 4
```
Exit code: `0`

3. Command:
```powershell
$path='test/features/pdf/extraction/fixtures/springfield_processed_items.json'; $base = (git show "HEAD:$path" | Out-String) | ConvertFrom-Json; $post = Get-Content -Raw $path | ConvertFrom-Json; function ItemRow($obj,$n,$label){ $it=$obj.items | Where-Object { $_.item_number -eq "$n" } | Select-Object -First 1; [pscustomobject]@{snapshot=$label; item_number=$n; unit_price=$it.unit_price; bid_amount=$it.bid_amount; raw_unit_price=$it.raw_unit_price; raw_bid_amount=$it.raw_bid_amount} }; $out=@(); $out += [pscustomobject]@{snapshot='baseline_HEAD'; total_items=$base.items.Count; null_unit_price=(($base.items | Where-Object { $null -eq $_.unit_price }).Count)}; $out += ItemRow $base 58 'baseline_HEAD'; $out += ItemRow $base 111 'baseline_HEAD'; $out += [pscustomobject]@{snapshot='post_regen_worktree'; total_items=$post.items.Count; null_unit_price=(($post.items | Where-Object { $null -eq $_.unit_price }).Count)}; $out += ItemRow $post 58 'post_regen_worktree'; $out += ItemRow $post 111 'post_regen_worktree'; $out | ConvertTo-Json -Depth 4
```
Exit code: `0`

4. Command:
```powershell
$path='test/features/pdf/extraction/fixtures/springfield_quality_report.json'; $base = (git show "HEAD:$path" | Out-String) | ConvertFrom-Json; $post = Get-Content -Raw $path | ConvertFrom-Json; @([pscustomobject]@{snapshot='baseline_HEAD'; overall_score=[double]$base.overall_score}, [pscustomobject]@{snapshot='post_regen_worktree'; overall_score=[double]$post.overall_score}) | ConvertTo-Json
```
Exit code: `0`

## Artifact Paths / Log Paths

- Stage-trace test: `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`
- Stage 18 parsed snapshot: `test/features/pdf/extraction/fixtures/springfield_parsed_items.json`
- Stage 23 dedupe snapshot: `test/features/pdf/extraction/fixtures/springfield_post_deduplicate.json`
- Stage 24 processed snapshot: `test/features/pdf/extraction/fixtures/springfield_processed_items.json`
- Quality snapshot: `test/features/pdf/extraction/fixtures/springfield_quality_report.json`
- Log source: command stdout from the test run above (no separate persisted log file was created).

## Baseline Vs Post-Regeneration Fixture Stats

### Stage 18 (`springfield_parsed_items.json`, HEAD vs worktree)

- Total items: `131` -> `131`
- Null `unit_price`: `28` -> `24`
- Null `bid_amount`: `28` -> `24`
- Item `58`:
  - Baseline: `unit_price=null`, `bid_amount=null`, `raw_unit_price="| $537.20"`, `raw_bid_amount="| $10,206.80"`
  - Post-regeneration: `unit_price=537.2`, `bid_amount=null`, `raw_unit_price="$537.20"`, `raw_bid_amount="| $10,206.80"`
- Item `111`:
  - Baseline: `unit_price=null`, `bid_amount=null`, `raw_unit_price=""`, `raw_bid_amount=""`
  - Post-regeneration: `unit_price=null`, `bid_amount=5179.3`, `raw_unit_price="| $739.90"`, `raw_bid_amount="$5,179.30"`

Key observed remnants after regeneration:
- Raw pipe still present in item `58` `raw_bid_amount`.
- Raw pipe still present in item `111` `raw_unit_price`.
- Null `unit_price` count is `24` at Stage 18.

### Stage 24 (`springfield_processed_items.json`, HEAD vs worktree)

- Total items: `130` -> `130`
- Null `unit_price`: `13` -> `11`

## Pipeline Scorecard Summary

From the stage-trace run:

- Totals: `41 OK / 8 LOW / 1 BUG`
- First BUG stage: `25` (`Checksum` fail)
- Stage 16 (`Cell Extraction`) coverage:
  - `Col: price = 122/138`
  - `Col: amount = 123/138`
- Stage 18 (`Row Parsing`) coverage:
  - `w/ unit_price = 107/131`
  - `w/ bid_amount = 107/131`
  - `Total $` mismatch (`$7,315,328.73` vs expected `$7,882,926.73`, delta `$567,598.00`)
- Stage 23 (`Post-Deduplicate`): `131 -> 130`
- Quality score: `0.905`

## Earliest Upstream Degradation Stages

- Earliest structural shortfall appears at Stage 16 (`Cell Extraction`) where price/amount column coverage drops to `122/138` and `123/138`.
- Earliest status degradation (`LOW`) appears at Stage 18 (`Row Parsing`) with `107/131` coverage for both `unit_price` and `bid_amount`, plus total-dollar mismatch.
- Final hard failure (`BUG`) appears at Stage 25 checksum validation.

## Where To Debug Next (Furthest Upstream)

1. Stage 16 cell extraction for price/amount columns:
   - Investigate why 15-16 of 138 rows are missing one or both monetary cells before parsing.
   - Focus on row-to-column assignment and split-row behavior around monetary columns.
2. Raw token sanitation before Stage 18 numeric parsing:
   - Explicitly handle leading pipe remnants (`|`) in money fields.
   - Confirm item `58 raw_bid_amount` and item `111 raw_unit_price` normalize cleanly before parse.
3. Re-run stage-trace scorecard after Stage 16/normalization fixes:
   - Verify Stage 18 rises above `107/131`.
   - Verify checksum passes at Stage 25.

## Explicit Edit Note

- No production code was edited in this analysis.
