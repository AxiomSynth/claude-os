---
name: claude-os-session
description: Intelligent session management with automatic context loading and pattern recognition
---

# Claude OS Session Management

Power-user session workflows that make me smarter with every session.

## Commands

```
/claude-os-session start [task]     - Start session with context loading
/claude-os-session end              - End session with save prompts
/claude-os-session status           - Current session status
/claude-os-session save [note]      - Quick save to memories during session
/claude-os-session blocker [desc]   - Track blocker
/claude-os-session pattern [desc]   - Document pattern discovered
/claude-os-session decision [desc]  - Record decision made
/claude-os-session context          - Show loaded context
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

**Step 2: Search Recent Memories**
```
mcp__code-forge__search_knowledge_base
  kb_name: {project}-project_memories
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
═══════════════════════════════════════
🚀 SESSION STARTED
═══════════════════════════════════════

Task: Redesign Appointment Dashboard
Branch: feature/appointment-redesign
Session ID: 42
Started: 2025-10-29 10:30 AM

📚 CONTEXT LOADED (5 memories):
  ✓ Appointment Dashboard Redesign Plan (Oct 28)
  ✓ Current Dashboard Analysis (Oct 28)
  ✓ Bootstrap to Modern Cards Pattern (Oct 25)

🎯 KEY INSIGHTS:
  • 67-page implementation plan ready
  • Zero functionality loss requirement

⚠️  UNRESOLVED BLOCKERS:
  None found ✓

Ready to code! I have full context.
═══════════════════════════════════════
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

**Step 2: Get Current Session Info**
```
mcp__code-forge__get_session_status
  project_path: {cwd}
```

**Step 3: Smart Save Prompts**

Show user what was accomplished and ask what to save:
- Patterns discovered during session
- Decisions made
- Work completed

**Step 4: End Session via MCP**
```
mcp__code-forge__end_session
  project_path: {cwd}
  work_completed: ["Created sidebar navigation", "Converted panels to cards", ...]
  memories_saved: 3
```

> **Note:** This MCP call automatically:
> 1. Saves session to SQLite database (queryable history)
> 2. Updates project statistics (total sessions, avg duration, etc.)
> 3. Exports JSON snapshot to `{project}/claude-os-state.json` (git-trackable)

**Step 5: Show Session Summary**

```
═══════════════════════════════════════
📊 SESSION ENDED
═══════════════════════════════════════

Duration: 2 hours 15 minutes
Task: Redesign Appointment Dashboard

🎨 WORK COMPLETED:
  ✓ Created sidebar navigation component
  ✓ Converted Bootstrap panels to cards
  ✓ Implemented iOS-style toggles

💡 PATTERNS DISCOVERED: 3
🤔 DECISIONS MADE: 2
💾 MEMORIES SAVED: 3

📈 CUMULATIVE STATS:
  Total Sessions: 47
  Total Patterns: 128
  Avg Duration: 98 min

JSON snapshot exported to claude-os-state.json ✓
═══════════════════════════════════════
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
═══════════════════════════════════════
📊 CURRENT SESSION
═══════════════════════════════════════

Status: ACTIVE ✓
Task: Redesign Appointment Dashboard
Duration: 1h 23m
Branch: feature/appointment-redesign

📚 Context Loaded: 5 memories
🎯 Patterns Discovered: 3
⚠️  Active Blockers: 0
🤔 Decisions Made: 2

Last Activity: 3 minutes ago
═══════════════════════════════════════
```

---

## TRACK BLOCKER

```
/claude-os-session blocker "Tekmetric API returning 500 on appointment sync"
```

**Call MCP tool:**
```
mcp__code-forge__add_session_blocker
  project_path: {cwd}
  description: "Tekmetric API returning 500 on appointment sync"
```

**Response:**
```
⚠️  Blocker tracked. Let me search for solutions...

mcp__code-forge__search_knowledge_base
  kb_name: {project}-project_memories
  query: "Tekmetric API 500 error"
```

---

## DOCUMENT PATTERN

```
/claude-os-session pattern "Service objects return model on success, error string on fail"
```

**Call MCP tool:**
```
mcp__code-forge__add_session_pattern
  project_path: {cwd}
  description: "Service objects return model on success, error string on fail"
```

**Response:**
```
✓ Pattern recorded for this session.
  I'll remember this for future service object work!
```

---

## RECORD DECISION

```
/claude-os-session decision "Use CSS Grid for sidebar layout instead of flexbox"
```

**Call MCP tool:**
```
mcp__code-forge__add_session_decision
  project_path: {cwd}
  description: "Use CSS Grid for sidebar layout instead of flexbox"
```

**Response:**
```
✓ Decision recorded.
  This will be saved when the session ends.
```

---

## QUICK SAVE

```
/claude-os-session save "Found fix for N+1 query in appointments"
```

**Step 1: Save to knowledge base**
```
mcp__code-forge__upload_document
  kb_name: {project}-project_memories
  content: "Found fix for N+1 query in appointments"
  filename: "quick-save-{timestamp}.md"
  title: "Quick save: Found fix for N+1 query..."
  tags: ["quick_save"]
```

**Step 2: Track in session**
```
mcp__code-forge__add_session_decision
  project_path: {cwd}
  description: "Saved memory: Found fix for N+1 query..."
```

**Response:**
```
✓ Saved to {project}-project_memories
  I'll remember this for future reference!
```

---

## SHOW CONTEXT

```
/claude-os-session context
```

**Step 1: Get session state**
```
mcp__code-forge__get_session_state
  project_path: {cwd}
```

**Step 2: Display loaded context**

```
═══════════════════════════════════════
📚 SESSION CONTEXT
═══════════════════════════════════════

📂 Project: sieve-calendar
🎯 Task: SIE-20: Enrich error messaging

📖 LOADED MEMORIES (5):
  • Error handling patterns (Oct 28)
  • API response structure (Oct 25)
  • User feedback guidelines (Oct 20)

💡 PATTERNS AVAILABLE:
  • Service object error returns
  • Flash message formatting

🤔 DECISIONS THIS SESSION:
  • Use CSS Grid for layout
  • Standardize error codes

⚠️  BLOCKERS:
  None ✓
═══════════════════════════════════════
```

---

## CROSS-PROJECT QUERIES

These work without an active session:

**List all recent sessions:**
```
mcp__code-forge__list_all_sessions
  limit: 20
```

**Show all unresolved blockers:**
```
mcp__code-forge__list_all_blockers
  unresolved_only: true
```

**Show patterns across projects:**
```
mcp__code-forge__list_all_patterns
  limit: 50
```

**Global statistics:**
```
mcp__code-forge__get_global_session_stats
```

---

## DATA STORAGE

**Primary:** SQLite database (`data/claude-os.db`)
- Full session history (all sessions, all projects)
- Queryable across projects
- Statistics and preferences
- Updated in real-time by all MCP tools

**Secondary:** JSON export (`{project}/claude-os-state.json`)
- **Automatically exported** when `end_session` is called
- Git-trackable snapshot (commit with your project)
- Contains: last session summary, cumulative stats, preferences
- No manual action required - handled by the MCP server

---

## MCP TOOLS REFERENCE

| Tool | Purpose |
|------|---------|
| `start_session` | Begin new session |
| `end_session` | End session, update stats |
| `get_session_state` | Full state with history |
| `get_session_status` | Quick status summary |
| `add_session_blocker` | Track blocker |
| `add_session_pattern` | Record pattern |
| `add_session_decision` | Record decision |
| `upload_document` | Save to knowledge base (used by `save`) |
| `list_all_sessions` | Sessions across projects |
| `list_all_blockers` | Blockers across projects |
| `list_all_patterns` | Patterns across projects |
| `get_global_session_stats` | Aggregated stats |

---

**This is the power-user workflow. Let's build something amazing!** 🚀
