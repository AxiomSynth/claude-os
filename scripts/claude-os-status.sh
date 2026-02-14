#!/bin/bash
# Claude OS session status for ccstatusline custom-command widget
# Receives Claude Code JSON on stdin, reads claude-os-state.json directly

cwd=$(python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null)

if [ -z "$cwd" ]; then
  echo "⏸ no session"
  exit 0
fi

# In a worktree, check main repo for state file too
state_file="$cwd/claude-os-state.json"
if [ ! -f "$state_file" ]; then
  main_repo=$(git -C "$cwd" worktree list --porcelain 2>/dev/null | head -1 | sed 's/^worktree //')
  if [ -n "$main_repo" ] && [ "$main_repo" != "$cwd" ] && [ -f "$main_repo/claude-os-state.json" ]; then
    state_file="$main_repo/claude-os-state.json"
  else
    echo "⏸ no session"
    exit 0
  fi
fi

python3 -c "
import json, sys
try:
    with open('$state_file') as f:
        d = json.load(f)
    if d.get('active'):
        task = (d.get('last_task') or '')[:35]
        print(f'\u26a1 {task}')
    else:
        print('\u23f8 no session')
except:
    print('\u23f8 no session')
" 2>/dev/null
