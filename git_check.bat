@echo off
cd /d "c:\Users\WATAP\Documents\github\braille-card-and-cylinder-stl-generator"
echo === GIT STATUS === > git_results.txt
git status >> git_results.txt 2>&1
echo. >> git_results.txt
echo === GIT LOG === >> git_results.txt
git log --oneline -5 >> git_results.txt 2>&1
echo. >> git_results.txt
echo === BRANCH INFO === >> git_results.txt
git branch -v >> git_results.txt 2>&1
