#!/bin/bash
# Claude OS session status for ccstatusline custom-command widget
# Receives Claude Code JSON on stdin, reads claude-os-state.json directly

cwd=$(python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null)

if [ -z "$cwd" ]; then
  exit 0
fi

state_file="$cwd/claude-os-state.json"

if [ ! -f "$state_file" ]; then
  exit 0
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
    pass
" 2>/dev/null
