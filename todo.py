#!/usr/bin/env python3
"""
╔══════════════════════════════════════╗
║       TODO CLI — Task Manager        ║
║   Persistent · Colorful · Powerful   ║
╚══════════════════════════════════════╝
"""

import json
import os
import sys
import re
from datetime import datetime, date
from pathlib import Path


# ─── ANSI Colors ────────────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"

    @staticmethod
    def supports_color():
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

def c(text, *codes):
    if not C.supports_color():
        return text
    return "".join(codes) + str(text) + C.RESET


# ─── Constants ───────────────────────────────────────────────────────────────

DATA_FILE = Path.home() / ".todo_data.json"
PRIORITIES = {"high": 1, "medium": 2, "low": 3}
PRIORITY_COLORS = {
    "high":   C.RED,
    "medium": C.YELLOW,
    "low":    C.GREEN,
}
PRIORITY_ICONS = {"high": "!!!", "medium": "!!", "low": "!"}
STATUS_ICONS = {"done": "✓", "pending": "○", "in-progress": "◑"}


# ─── Storage ─────────────────────────────────────────────────────────────────

def load_tasks():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_tasks(tasks):
    with open(DATA_FILE, "w") as f:
        json.dump(tasks, f, indent=2)

def next_id(tasks):
    return max((t["id"] for t in tasks), default=0) + 1


# ─── Task helpers ────────────────────────────────────────────────────────────

def make_task(title, priority="medium", due=None, tags=None, note=""):
    return {
        "id":       None,       # assigned on save
        "title":    title.strip(),
        "status":   "pending",
        "priority": priority,
        "due":      due,
        "tags":     tags or [],
        "note":     note,
        "created":  datetime.now().isoformat(timespec="seconds"),
        "completed": None,
    }

def days_until(due_str):
    if not due_str:
        return None
    try:
        d = datetime.strptime(due_str, "%Y-%m-%d").date()
        return (d - date.today()).days
    except ValueError:
        return None

def format_due(due_str):
    delta = days_until(due_str)
    if delta is None:
        return ""
    if delta < 0:
        return c(f"overdue {abs(delta)}d", C.RED, C.BOLD)
    elif delta == 0:
        return c("due today", C.YELLOW, C.BOLD)
    elif delta == 1:
        return c("due tomorrow", C.YELLOW)
    elif delta <= 7:
        return c(f"due in {delta}d", C.CYAN)
    else:
        return c(f"due {due_str}", C.GRAY)

def match_id(tasks, id_):
    for t in tasks:
        if t["id"] == id_:
            return t
    return None


# ─── Display ─────────────────────────────────────────────────────────────────

HEADER = f"""
{c('╔' + '═'*44 + '╗', C.CYAN)}
{c('║', C.CYAN)}  {c('TODO CLI', C.BOLD, C.WHITE)}  {c('—', C.GRAY)} Task Manager           {c('║', C.CYAN)}
{c('╚' + '═'*44 + '╝', C.CYAN)}"""

def print_header():
    print(HEADER)

def print_task(t, index=None, verbose=False):
    sid   = c(f"#{t['id']:>3}", C.GRAY)
    pri   = t["priority"]
    pcol  = PRIORITY_COLORS.get(pri, C.WHITE)
    picon = c(PRIORITY_ICONS.get(pri, ""), pcol)
    st    = t["status"]
    sicon = STATUS_ICONS.get(st, "?")

    if st == "done":
        sdisp = c(sicon, C.GREEN)
        title = c(t["title"], C.DIM)
    elif st == "in-progress":
        sdisp = c(sicon, C.CYAN)
        title = c(t["title"], C.WHITE, C.BOLD)
    else:
        sdisp = c(sicon, C.GRAY)
        title = c(t["title"], C.WHITE)

    due_fmt = format_due(t.get("due"))
    tags_fmt = ""
    if t.get("tags"):
        tags_fmt = " " + " ".join(c(f"#{g}", C.MAGENTA) for g in t["tags"])

    line = f"  {sid} {sdisp} {picon} {title}{tags_fmt}"
    if due_fmt:
        line += f"  {due_fmt}"
    print(line)

    if verbose:
        if t.get("note"):
            print(f"       {c('Note:', C.GRAY)} {t['note']}")
        print(f"       {c('Created:', C.GRAY)} {t['created']}")
        if t.get("completed"):
            print(f"       {c('Completed:', C.GRAY)} {t['completed']}")

def print_tasks(tasks, title="All tasks", verbose=False, filter_fn=None):
    filtered = [t for t in tasks if filter_fn is None or filter_fn(t)]

    pending    = [t for t in filtered if t["status"] == "pending"]
    inprog     = [t for t in filtered if t["status"] == "in-progress"]
    done       = [t for t in filtered if t["status"] == "done"]

    def sort_key(t):
        return (PRIORITIES.get(t["priority"], 9), t["id"])

    print()
    print(c(f"  {title}", C.BOLD, C.WHITE))
    print(c("  " + "─" * 42, C.GRAY))

    if not filtered:
        print(c("  No tasks found.", C.GRAY))
        print()
        return

    if inprog:
        print(c("  In Progress", C.CYAN, C.BOLD))
        for t in sorted(inprog, key=sort_key):
            print_task(t, verbose=verbose)
        print()

    if pending:
        print(c("  Pending", C.YELLOW, C.BOLD))
        for t in sorted(pending, key=sort_key):
            print_task(t, verbose=verbose)
        print()

    if done:
        print(c("  Completed", C.GREEN, C.BOLD))
        for t in sorted(done, key=sort_key):
            print_task(t, verbose=verbose)
        print()

    total = len(filtered)
    ndone = len(done)
    pct   = int(ndone / total * 100) if total else 0
    bar_w = 20
    filled = int(bar_w * pct / 100)
    bar = c("█" * filled, C.GREEN) + c("░" * (bar_w - filled), C.GRAY)
    print(f"  {bar}  {c(f'{ndone}/{total} done ({pct}%)', C.GRAY)}")
    print()

def print_summary(tasks):
    total    = len(tasks)
    done     = sum(1 for t in tasks if t["status"] == "done")
    inprog   = sum(1 for t in tasks if t["status"] == "in-progress")
    pending  = sum(1 for t in tasks if t["status"] == "pending")
    overdue  = sum(1 for t in tasks if (days_until(t.get("due")) or 1) < 0 and t["status"] != "done")
    today_due= sum(1 for t in tasks if days_until(t.get("due")) == 0 and t["status"] != "done")

    print(c("\n  📊 Summary", C.BOLD, C.WHITE))
    print(c("  " + "─" * 30, C.GRAY))
    print(f"  Total      {c(total, C.WHITE, C.BOLD)}")
    print(f"  Pending    {c(pending, C.YELLOW)}")
    print(f"  In-Progress {c(inprog, C.CYAN)}")
    print(f"  Done       {c(done, C.GREEN)}")
    if overdue:
        print(f"  Overdue    {c(overdue, C.RED, C.BOLD)}")
    if today_due:
        print(f"  Due today  {c(today_due, C.YELLOW, C.BOLD)}")
    print()

def print_help():
    helps = [
        ("add  <title> [opts]",  "Add a new task"),
        ("  -p high|medium|low", "Set priority (default: medium)"),
        ("  -d YYYY-MM-DD",      "Set due date"),
        ("  -t tag1,tag2",       "Add tags"),
        ("  -n 'note text'",     "Add a note"),
        ("",                     ""),
        ("list [opts]",          "List tasks"),
        ("  -s pending|done|in-progress", "Filter by status"),
        ("  -p high|medium|low", "Filter by priority"),
        ("  -t tag",             "Filter by tag"),
        ("  -v",                 "Verbose (show notes & dates)"),
        ("",                     ""),
        ("done <id>",            "Mark task as done"),
        ("start <id>",           "Mark task as in-progress"),
        ("undo <id>",            "Mark task back to pending"),
        ("edit <id> [opts]",     "Edit task (-p, -d, -t, -n, --title)"),
        ("delete <id>",          "Delete a task"),
        ("clear done",           "Remove all completed tasks"),
        ("",                     ""),
        ("show <id>",            "Show task details"),
        ("search <query>",       "Search titles, tags, notes"),
        ("today",                "Tasks due today or overdue"),
        ("stats",                "Show summary statistics"),
        ("help",                 "Show this help"),
        ("quit",                 "Exit the app"),
    ]
    print()
    print(c("  Commands", C.BOLD, C.WHITE))
    print(c("  " + "─" * 44, C.GRAY))
    for cmd, desc in helps:
        if not cmd:
            print()
            continue
        print(f"  {c(cmd, C.CYAN):<42} {c(desc, C.GRAY)}")
    print()


# ─── Argument parsing helpers ─────────────────────────────────────────────────

def parse_opts(args):
    """Simple flag parser returning (positional_tokens, opts_dict)."""
    opts = {}
    pos  = []
    i    = 0
    while i < len(args):
        a = args[i]
        if a in ("-p", "--priority") and i + 1 < len(args):
            opts["priority"] = args[i+1].lower(); i += 2
        elif a in ("-d", "--due") and i + 1 < len(args):
            opts["due"] = args[i+1]; i += 2
        elif a in ("-t", "--tags") and i + 1 < len(args):
            opts["tags"] = [g.strip() for g in args[i+1].split(",") if g.strip()]; i += 2
        elif a in ("-n", "--note") and i + 1 < len(args):
            opts["note"] = args[i+1]; i += 2
        elif a == "--title" and i + 1 < len(args):
            opts["title"] = args[i+1]; i += 2
        elif a == "-v":
            opts["verbose"] = True; i += 1
        elif a in ("-s", "--status") and i + 1 < len(args):
            opts["status"] = args[i+1].lower(); i += 2
        else:
            pos.append(a); i += 1
    return pos, opts

def validate_priority(p):
    if p not in PRIORITIES:
        print(c(f"  ✗ Unknown priority '{p}'. Use: high, medium, low", C.RED))
        return False
    return True

def validate_date(d):
    if d is None:
        return True
    try:
        datetime.strptime(d, "%Y-%m-%d")
        return True
    except ValueError:
        print(c(f"  ✗ Invalid date '{d}'. Use YYYY-MM-DD format.", C.RED))
        return False


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_add(tasks, args):
    pos, opts = parse_opts(args)
    title = " ".join(pos).strip()
    if not title:
        print(c("  ✗ Please provide a task title.", C.RED))
        return

    pri  = opts.get("priority", "medium")
    due  = opts.get("due")
    tags = opts.get("tags", [])
    note = opts.get("note", "")

    if not validate_priority(pri): return
    if not validate_date(due): return

    t = make_task(title, pri, due, tags, note)
    t["id"] = next_id(tasks)
    tasks.append(t)
    save_tasks(tasks)

    print(c(f"\n  ✓ Added", C.GREEN) + f" #{t['id']} {c(title, C.WHITE, C.BOLD)}")
    print(f"    Priority: {c(pri, PRIORITY_COLORS[pri])}"
          + (f"  Due: {due}" if due else "")
          + (f"  Tags: {', '.join(tags)}" if tags else ""))
    print()

def cmd_list(tasks, args):
    pos, opts = parse_opts(args)
    stat   = opts.get("status")
    pri    = opts.get("priority")
    tag    = opts.get("tags", [None])[0] if isinstance(opts.get("tags"), list) else None
    if not tag and pos:
        tag = pos[0]
    verbose = opts.get("verbose", False)

    filters = []
    title_parts = ["Tasks"]
    if stat:
        filters.append(lambda t, s=stat: t["status"] == s)
        title_parts.append(stat)
    if pri:
        if not validate_priority(pri): return
        filters.append(lambda t, p=pri: t["priority"] == p)
        title_parts.append(pri + " priority")
    if tag:
        filters.append(lambda t, g=tag: g in t.get("tags", []))
        title_parts.append(f"#{tag}")

    filter_fn = (lambda t: all(f(t) for f in filters)) if filters else None
    print_tasks(tasks, " · ".join(title_parts), verbose=verbose, filter_fn=filter_fn)

def _set_status(tasks, args, new_status):
    if not args:
        print(c("  ✗ Provide a task ID.", C.RED))
        return
    try:
        id_ = int(args[0])
    except ValueError:
        print(c("  ✗ ID must be a number.", C.RED)); return

    t = match_id(tasks, id_)
    if not t:
        print(c(f"  ✗ Task #{id_} not found.", C.RED)); return

    old = t["status"]
    t["status"] = new_status
    if new_status == "done":
        t["completed"] = datetime.now().isoformat(timespec="seconds")
    elif old == "done":
        t["completed"] = None
    save_tasks(tasks)

    icons = {"done": ("✓", C.GREEN), "in-progress": ("◑", C.CYAN), "pending": ("○", C.YELLOW)}
    icon, col = icons[new_status]
    print(c(f"\n  {icon} #{id_} marked as {new_status}", col))
    print()

def cmd_done(tasks, args):      _set_status(tasks, args, "done")
def cmd_start(tasks, args):     _set_status(tasks, args, "in-progress")
def cmd_undo(tasks, args):      _set_status(tasks, args, "pending")

def cmd_delete(tasks, args):
    if not args:
        print(c("  ✗ Provide a task ID.", C.RED)); return
    try:
        id_ = int(args[0])
    except ValueError:
        print(c("  ✗ ID must be a number.", C.RED)); return

    t = match_id(tasks, id_)
    if not t:
        print(c(f"  ✗ Task #{id_} not found.", C.RED)); return

    confirm = input(c(f"  Delete #{id_} '{t['title']}'? (y/N) ", C.YELLOW)).strip().lower()
    if confirm == "y":
        tasks.remove(t)
        save_tasks(tasks)
        print(c(f"  ✓ Deleted #{id_}", C.GREEN))
    else:
        print(c("  Cancelled.", C.GRAY))
    print()

def cmd_edit(tasks, args):
    if not args:
        print(c("  ✗ Provide a task ID.", C.RED)); return
    try:
        id_ = int(args[0])
    except ValueError:
        print(c("  ✗ ID must be a number.", C.RED)); return

    t = match_id(tasks, id_)
    if not t:
        print(c(f"  ✗ Task #{id_} not found.", C.RED)); return

    _, opts = parse_opts(args[1:])

    if "title" in opts:    t["title"]    = opts["title"]
    if "priority" in opts:
        if not validate_priority(opts["priority"]): return
        t["priority"] = opts["priority"]
    if "due" in opts:
        if not validate_date(opts["due"]): return
        t["due"] = opts["due"]
    if "tags" in opts:     t["tags"]     = opts["tags"]
    if "note" in opts:     t["note"]     = opts["note"]

    if not opts:
        print(c("  Nothing to update. Use -p, -d, -t, -n, --title", C.GRAY))
        return

    save_tasks(tasks)
    print(c(f"\n  ✓ Updated #{id_}", C.GREEN))
    print_task(t, verbose=True)
    print()

def cmd_show(tasks, args):
    if not args:
        print(c("  ✗ Provide a task ID.", C.RED)); return
    try:
        id_ = int(args[0])
    except ValueError:
        print(c("  ✗ ID must be a number.", C.RED)); return
    t = match_id(tasks, id_)
    if not t:
        print(c(f"  ✗ Task #{id_} not found.", C.RED)); return
    print()
    print_task(t, verbose=True)
    print()

def cmd_search(tasks, args):
    if not args:
        print(c("  ✗ Provide a search query.", C.RED)); return
    q = " ".join(args).lower()
    def matches(t):
        return (q in t["title"].lower()
                or any(q in g for g in t.get("tags", []))
                or q in t.get("note", "").lower())
    print_tasks(tasks, f"Search: '{q}'", filter_fn=matches)

def cmd_today(tasks, args):
    def is_urgent(t):
        if t["status"] == "done": return False
        d = days_until(t.get("due"))
        return d is not None and d <= 0
    print_tasks(tasks, "Today & Overdue", filter_fn=is_urgent)

def cmd_clear_done(tasks, args):
    done = [t for t in tasks if t["status"] == "done"]
    if not done:
        print(c("\n  No completed tasks to clear.\n", C.GRAY)); return
    confirm = input(c(f"  Remove {len(done)} completed task(s)? (y/N) ", C.YELLOW)).strip().lower()
    if confirm == "y":
        tasks[:] = [t for t in tasks if t["status"] != "done"]
        save_tasks(tasks)
        print(c(f"  ✓ Cleared {len(done)} completed task(s).", C.GREEN))
    else:
        print(c("  Cancelled.", C.GRAY))
    print()

def cmd_stats(tasks, args):
    print_summary(tasks)

    if not tasks:
        return

    # Priority breakdown
    print(c("  Priority breakdown", C.BOLD, C.WHITE))
    print(c("  " + "─" * 30, C.GRAY))
    for p in ("high", "medium", "low"):
        pts = [t for t in tasks if t["priority"] == p]
        done = sum(1 for t in pts if t["status"] == "done")
        bar = c("█" * len(pts), PRIORITY_COLORS[p]) + c("░" * (10 - min(len(pts), 10)), C.GRAY)
        print(f"  {c(p.capitalize(), PRIORITY_COLORS[p]):<20} {bar}  {len(pts)} ({done} done)")
    print()

    # Tags cloud
    all_tags = {}
    for t in tasks:
        for g in t.get("tags", []):
            all_tags[g] = all_tags.get(g, 0) + 1
    if all_tags:
        print(c("  Tags", C.BOLD, C.WHITE))
        print(c("  " + "─" * 30, C.GRAY))
        for tag, count in sorted(all_tags.items(), key=lambda x: -x[1]):
            print(f"  {c('#'+tag, C.MAGENTA)}  {c(count, C.GRAY)} task(s)")
        print()


# ─── REPL ────────────────────────────────────────────────────────────────────

COMMANDS = {
    "add":    cmd_add,
    "list":   cmd_list,
    "ls":     cmd_list,
    "done":   cmd_done,
    "complete": cmd_done,
    "start":  cmd_start,
    "undo":   cmd_undo,
    "delete": cmd_delete,
    "del":    cmd_delete,
    "rm":     cmd_delete,
    "edit":   cmd_edit,
    "show":   cmd_show,
    "search": cmd_search,
    "find":   cmd_search,
    "today":  cmd_today,
    "stats":  cmd_stats,
    "summary": cmd_stats,
    "help":   lambda t, a: print_help(),
    "?":      lambda t, a: print_help(),
    "clear done": None,   # handled specially
}

def run_repl():
    tasks = load_tasks()
    print_header()
    print_summary(tasks)
    print(c("  Type 'help' for commands or 'quit' to exit.\n", C.GRAY))

    while True:
        try:
            raw = input(c("  ❯ ", C.CYAN, C.BOLD)).strip()
        except (EOFError, KeyboardInterrupt):
            print(c("\n\n  Goodbye! ✓\n", C.GREEN))
            break

        if not raw:
            continue

        # Reload tasks each loop (supports external edits)
        tasks = load_tasks()

        parts = raw.split()
        cmd   = parts[0].lower()
        args  = parts[1:]

        # Special: multi-word commands
        if cmd == "clear" and args and args[0] == "done":
            cmd_clear_done(tasks, [])
            continue

        if cmd in ("quit", "exit", "q", "bye"):
            print(c("\n  Goodbye! ✓\n", C.GREEN))
            break

        if cmd in COMMANDS and COMMANDS[cmd] is not None:
            COMMANDS[cmd](tasks, args)
        else:
            print(c(f"\n  ✗ Unknown command '{cmd}'. Type 'help' for commands.\n", C.RED))


# ─── CLI entry-point (non-interactive) ───────────────────────────────────────

def run_cli():
    """Run a single command from the command line: python todo.py add 'task' -p high"""
    tasks = load_tasks()
    args  = sys.argv[1:]
    if not args:
        run_repl()
        return

    cmd  = args[0].lower()
    rest = args[1:]

    if cmd in ("quit","exit","q"):
        return
    if cmd in ("clear",) and rest and rest[0] == "done":
        cmd_clear_done(tasks, [])
    elif cmd in COMMANDS and COMMANDS[cmd] is not None:
        COMMANDS[cmd](tasks, rest)
    else:
        print(c(f"\n  ✗ Unknown command '{cmd}'.\n", C.RED))
        print_help()


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single command mode
        run_cli()
    else:
        # Interactive REPL mode
        run_repl()
