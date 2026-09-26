#!/bin/bash
COMMIT_MSG="${1:-Update CampusCare codebase}"
git add .
git commit -m "$COMMIT_MSG"
git pull origin main --no-edit
git push origin main
echo "Changes successfully synced to https://github.com/dynamic-cod/CampusCare.git"
