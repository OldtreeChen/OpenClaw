$ErrorActionPreference = "Stop"

param(
  [string]$Message = ""
)

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "git is not installed."
}

$insideRepo = git rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -ne 0 -or $insideRepo -ne "true") {
  throw "Current directory is not a git repository."
}

$status = git status --porcelain
if (-not $status) {
  Write-Output "No changes to commit."
  exit 0
}

if ([string]::IsNullOrWhiteSpace($Message)) {
  $Message = "Update project files"
}

git add .
git commit -m $Message
git push
