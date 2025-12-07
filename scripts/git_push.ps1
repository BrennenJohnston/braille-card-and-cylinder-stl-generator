# Git push script (PowerShell 5+ compatible)
$ErrorActionPreference = "Stop"

Write-Host "Starting git operations..."

# Show current status for context
git status
Write-Host "---"

# Stage everything
git add -A
Write-Host "Files staged"

# Commit only when there are staged changes
if (-not (git diff --cached --quiet)) {
    git commit -m "Auto: update worktree"
} else {
    Write-Host "Nothing to commit"
}

Write-Host "---"

# Push current branch
$branch = git symbolic-ref --short HEAD
git push origin $branch

Write-Host "Done!"
