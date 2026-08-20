# Quick-launch deployment acceptance script (automates deploy/DEPLOY.md section 4).
# Usage (on server or locally):
#   pwsh -File deploy/verify.ps1
#   pwsh -File deploy/verify.ps1 -BaseUrl http://127.0.0.1:8080
param(
  [string]$BaseUrl = 'http://127.0.0.1:8080'
)
$ErrorActionPreference = 'Stop'
$script:failures = @()
function Check([string]$name, [scriptblock]$step) {
  try {
    & $step | Out-Null
    Write-Host "[PASS] $name"
  } catch {
    Write-Host "[FAIL] $name : $($_.Exception.Message)"
    $script:failures += $name
  }
}
$player = 'deploy-check-' + (Get-Random)
Check 'health /api/health' {
  $h = Invoke-RestMethod -Uri "$BaseUrl/api/health" -TimeoutSec 15
  if ($h.status -ne 'ok') { throw 'status != ok' }
}
Check 'story first node (SYSTEM INITIALIZING...)' {
  $v = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/story/advance" -Body (@{ session_id = $null; player_id = $player } | ConvertTo-Json) -ContentType 'application/json' -TimeoutSec 30
  if ($v.node.kind -ne 'line' -or $v.node.text -ne 'SYSTEM INITIALIZING...') { throw "unexpected first node: $($v.node | ConvertTo-Json -Compress)" }
}
Check 'scene-boundary AUTO save (postgres)' {
  $s = Invoke-RestMethod -Uri "$BaseUrl/api/saves?player_id=$player" -TimeoutSec 15
  if ($null -eq $s.auto) { throw 'auto save missing' }
}
Check 'static asset /char/deepseek/pic/deepseek_main.png' {
  $r = Invoke-WebRequest -Uri "$BaseUrl/char/deepseek/pic/deepseek_main.png" -UseBasicParsing -TimeoutSec 20
  if ($r.StatusCode -ne 200) { throw "HTTP $($r.StatusCode)" }
}
Check 'frontend page /' {
  $r = Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing -TimeoutSec 20
  if ($r.StatusCode -ne 200) { throw "HTTP $($r.StatusCode)" }
}
if ($script:failures.Count -gt 0) {
  Write-Host "`nACCEPTANCE FAILED: $($script:failures -join ', ')"
  exit 1
}
Write-Host "`nAll acceptance checks passed. Run the browser walkthrough per DEPLOY.md 4.4 to finish."
