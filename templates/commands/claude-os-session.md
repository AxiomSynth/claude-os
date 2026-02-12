---
name: claude-os-session
description: Intelligent session management with automatic context loading and pattern recognition
---

# Claude OS Session Management

Power-user session workflows that make me smarter with every session.

## Project Name Resolution

Before using any command below, resolve the project name:
1. Read `{cwd}/claude-os-state.json` — use the `project_name` field
2. If no state file, call `mcp__code-forge__list_knowledge_bases` and find the KB ending in `-project_memories` (strip the suffix to get the project name)
3. If no KB found, use the directory name as fallback

## Commands

```
/claude-os-session start [task]     - Start session with context loading
/claude-os-session end              - End session with save prompts
/claude-os-session status           - Current session status
/claude-os-session save [note]      - Quick save to memories during session
/claude-os-session blocker [desc]   - Save blocker to project KB
/claude-os-session pattern [desc]   - Save pattern to project KB
/claude-os-session decision [desc]  - Save decision to project KB
/claude-os-session context          - Search and show relevant context
```

---

## START SESSION

```
/claude-os-session start "redesign appointment dashboard"
```

**Step 1: Start session via MCP**
```
mcp__code-forge__start_session
  project_path: {cwd}
  task: "redesign appointment dashboard"
  branch: (from git branch --show-current)
```

**Step 2: Search Relevant Memories**
```
mcp__code-forge__search_all_knowledge_bases
  query: "{task} recent work"
```

**Step 3: Get Git Context**
```bash
git branch --show-current
git status --short
git log -5 --oneline
```

**Step 4: Show Session Start Summary**

```
Session started: {task}
Branch: {branch}
Project: {project_name}

Context loaded:
  - [relevant memories from search]

Ready to code!
```

---

## END SESSION

```
/claude-os-session end
```

**Step 1: Analyze Work**
```bash
git diff --stat
git log --oneline @{upstream}..HEAD 2>/dev/null || git log --oneline -5
```

**Step 2: Smart Save Prompts**

Review patterns, decisions, and blockers discovered during the session.
Ask the user what to save — each item gets uploaded to the project KB:

```
mcp__code-forge__upload_document
  kb_name: {project_name}-project_memories
  content: "[formatted content]"
  filename: "{type}-{timestamp}.md"
  title: "[title]"
  tags: ["{type}"]
```

**Step 3: End Session via MCP**
```
mcp__code-forge__end_session
  project_path: {cwd}
  one_liner: "Brief summary of what was accomplished"
```

**Step 4: Show Session Summary**

```
Session ended.
Duration: {duration}
Task: {task}
One-liner: {one_liner}
```

---

## STATUS CHECK

```
/claude-os-session status
```

**Call MCP tool:**
```
mcp__code-forge__get_session_status
  project_path: {cwd}
```

**Display result:**
```
Status: {active/inactive}
Task: {last_task}
Project: {project_name}
Started: {started_at}
```

---

## SAVE PATTERN / DECISION / BLOCKER

```
/claude-os-session pattern "Service objects return model on success, error string on fail"
/claude-os-session decision "Use CSS Grid for sidebar layout instead of flexbox"
/claude-os-session blocker "API returning 500 on appointment sync"
```

All three work the same way — upload directly to the project KB:

```
mcp__code-forge__upload_document
  kb_name: {project_name}-project_memories
  content: "# {Type}: {description}\n\n**Date**: {date}\n**Session**: {current_task}"
  filename: "{type}-{timestamp}.md"
  title: "{Type}: {short_description}"
  tags: ["{type}"]
```

**Response:**
```
Saved to {project_name}-project_memories
```

---

## QUICK SAVE

```
/claude-os-session save "Found fix for N+1 query in appointments"
```

```
mcp__code-forge__upload_document
  kb_name: {project_name}-project_memories
  content: "[formatted content with context from session]"
  filename: "quick-save-{timestamp}.md"
  title: "Quick save: {short_description}"
  tags: ["quick_save"]
```

---

## SHOW CONTEXT

```
/claude-os-session context
```

**Step 1: Get session status**
```
mcp__code-forge__get_session_status
  project_path: {cwd}
```

**Step 2: Search for relevant context**
```
mcp__code-forge__search_all_knowledge_bases
  query: "{current_task}"
```

**Step 3: Display loaded context**

```
Project: {project_name}
Task: {current_task}

Relevant memories:
  - [search results]
```

---

## MCP TOOLS REFERENCE

| Tool | Purpose |
|------|---------|
| `start_session` | Begin new session (writes claude-os-state.json) |
| `end_session` | End session (updates claude-os-state.json) |
| `get_session_status` | Quick status check |
| `upload_document` | Save patterns/decisions/blockers to KB |
| `search_all_knowledge_bases` | Search across project KBs for context |

---

## DATA STORAGE

**Session state:** `{cwd}/claude-os-state.json`
- Active/inactive flag, task, branch, project name
- Written by `start_session` and `end_session`

**Learnings:** Project knowledge bases via `upload_document`
- Patterns, decisions, blockers saved directly to KB
- Searchable via `search_all_knowledge_bases`
- No separate session database needed
