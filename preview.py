#!/usr/bin/env python3
"""
preview.py - Preview what your contribution graph will look like.
Simulates push.py's algorithm without touching git or making any commits.

Usage:
    python3 preview.py
"""

import random
from datetime import date, timedelta

import push


# ─── DISPLAY ─────────────────────────────────────────────────────────────────

# Coloured squares matching GitHub's green palette (ANSI 256-colour)
def square(n: int) -> str:
    if n == 0:  return "\033[38;5;238m■\033[0m"   # grey   — no commits
    if n <= 2:  return "\033[38;5;22m■\033[0m"    # dark green
    if n <= 4:  return "\033[38;5;34m■\033[0m"    # medium green
    return              "\033[38;5;46m■\033[0m"   # bright green — 5 commits

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]
DAY_LABELS  = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

# ─────────────────────────────────────────────────────────────────────────────


def simulate() -> dict:
    """Run the algorithm and return {date: commit_count} for the past 365 days."""
    end   = date.today() - timedelta(days=1)
    start = end - timedelta(days=364)

    vacation   = push.build_vacation_set(start, end)
    commits    = {}
    skip_until = None
    day        = start

    while day <= end:
        if day in vacation or (skip_until and day < skip_until):
            commits[day] = 0
        else:
            if push.should_commit(day):
                n = push.pick_commit_count()
                commits[day] = n
                if n > 0 and random.random() < push.BREAK_CHANCE:
                    break_len  = random.randint(push.BREAK_MIN_DAYS, push.BREAK_MAX_DAYS)
                    skip_until = day + timedelta(days=break_len)
            else:
                commits[day] = 0
        day += timedelta(days=1)

    return commits, start, end


def render(commits: dict, start: date, end: date):
    # Align to the Monday on or before start
    grid_start = start - timedelta(days=start.weekday())

    # Build list of weeks (each week is 7 dates, Mon–Sun)
    weeks = []
    d = grid_start
    while d <= end:
        weeks.append([d + timedelta(days=i) for i in range(7)])
        d += timedelta(days=7)

    # Month header — print abbreviated month name at the start of each new month
    header     = "     "
    seen_month = None
    for week in weeks:
        label = "  "
        for d in week:
            if start <= d <= end and d.month != seen_month and d.day <= 7:
                label      = MONTH_NAMES[d.month - 1][:2]
                seen_month = d.month
                break
        header += label
    print(header)

    # Grid — one row per day of the week
    for dow in range(7):
        row = f"{DAY_LABELS[dow]}  "
        for week in weeks:
            d = week[dow]
            if d < start or d > end:
                row += "  "
            else:
                row += square(commits.get(d, 0)) + " "
        print(row)


def stats(commits: dict):
    total  = sum(commits.values())
    active = sum(1 for n in commits.values() if n > 0)
    days   = len(commits)
    avg    = total / active if active else 0.0

    longest = streak = 0
    for n in commits.values():
        if n > 0:
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 0

    pct = int(100 * active / days) if days else 0
    print()
    print(f"  Total commits  : {total}")
    print(f"  Active days    : {active}/{days}  ({pct}%)")
    print(f"  Avg per day    : {avg:.1f}  (on active days only)")
    print(f"  Longest streak : {longest} days")
    print()
    print("  Legend:  \033[38;5;238m■\033[0m none   "
          "\033[38;5;22m■\033[0m 1–2   "
          "\033[38;5;34m■\033[0m 3–4   "
          "\033[38;5;46m■\033[0m 5")
    print()


def main():
    print()
    commits, start, end = simulate()
    render(commits, start, end)
    stats(commits)


if __name__ == "__main__":
    main()
