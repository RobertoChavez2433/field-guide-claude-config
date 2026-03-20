$base = 'C:/Users/rseba/Projects/Field_Guide_App'
$expected = @(
    "$base/lib/core/driver/test_photo_service.dart",
    "$base/lib/core/driver/driver_server.dart",
    "$base/lib/main_driver.dart",
    "$base/tools/prune-test-results.ps1",
    "$base/.claude/test-flows/registry.md",
    "$base/.claude/skills/test/SKILL.md",
    "$base/.claude/agents/test-wave-agent.md"
)
foreach ($f in $expected) {
    if (Test-Path $f) { Write-Host "OK: $f" } else { Write-Host "MISSING: $f" }
}

Write-Host ""
Write-Host "--- Dead code check ---"
$dead = @(
    "$base/.claude/test_results/flow_registry.md",
    "$base/.claude/skills/test/references/adb-commands.md",
    "$base/.claude/skills/test/references/uiautomator-parsing.md"
)
foreach ($f in $dead) {
    if (Test-Path $f) { Write-Host "STILL EXISTS (delete failed): $f" } else { Write-Host "DELETED: $f" }
}
