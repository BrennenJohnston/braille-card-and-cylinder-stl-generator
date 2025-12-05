# Git push script
Write-Host "Starting git operations..."
git status
Write-Host "---"
git add -A
Write-Host "Files staged"
git commit -m "Update cylinder geometry, HTML templates, and worker scripts"
Write-Host "---"
git push origin HEAD
Write-Host "Done!"
