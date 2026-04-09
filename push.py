#!/usr/bin/env python3
"""
push.py - GitHub contribution graph filler
Commits realistic-looking activity to a private repo.

Usage:
    python3 push.py --repo /path/to/repo --backfill   # fill past 365 days
    python3 push.py --repo /path/to/repo              # commit for today (run via cron)
"""

import argparse
import os
import random
import subprocess
from datetime import date, datetime, timedelta


# ─── CONFIG ──────────────────────────────────────────────────────────────────
# Edit anything in this block to change the behaviour.

# Probability (0.0–1.0) that commits happen on each day of the week
# 0 = Monday, 6 = Sunday
DAY_ODDS = {
    0: 0.45,  # Monday
    1: 0.50,  # Tuesday
    2: 0.50,  # Wednesday
    3: 0.45,  # Thursday
    4: 0.40,  # Friday
    5: 0.35,  # Saturday
    6: 0.30,  # Sunday
}

# Weighted commit counts for active days — (count, weight)
# Higher weight = more likely. Max 5 to keep it casual.
COMMIT_WEIGHTS = [
    (1, 40),
    (2, 30),
    (3, 18),
    (4,  8),
    (5,  4),
]

# Commit time window (24-hour)
TIME_START = 10    # earliest possible hour
TIME_END   = 23    # latest possible hour (up to :30)
TIME_MEAN  = 16    # centre of the normal distribution (afternoon/evening)
TIME_STD   = 3     # spread in hours — higher = more variation

# Pool of commit messages to pick from randomly
MESSAGES = [
    "update notes",
    "add log entry",
    "cleanup",
    "progress",
    "wip",
    "fix typo",
    "add reminder",
    "scratch notes",
    "update",
    "minor changes",
    "tidy up",
    "notes",
    "small fix",
    "tweaks",
    "misc",
]

# Fixed vacation blocks during backfill — (month, day, duration_in_days)
# These dates will always be skipped.
VACATION_BLOCKS = [
    (12, 20, 14),   # Christmas / New Year
]

# Extra random vacation blocks dropped in during backfill
RANDOM_VACATION_COUNT    = 2   # how many extra blocks
RANDOM_VACATION_MIN_DAYS = 5   # shortest block length
RANDOM_VACATION_MAX_DAYS = 10  # longest block length

# Consecutive-days-off mechanic
# After any active day, there's a BREAK_CHANCE that coding stops for a few days.
# Minimum break is 2 days (as requested). Raise BREAK_CHANCE for more gaps.
BREAK_CHANCE    = 0.12  # 12% chance of a break after committing
BREAK_MIN_DAYS  = 2     # minimum days off in a break
BREAK_MAX_DAYS  = 6     # maximum days off in a break

# ─────────────────────────────────────────────────────────────────────────────


def git(repo_path, *args, env=None):
    """Run a git command in the given repo path."""
    cmd = ["git", "-C", repo_path] + list(args)
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    result = subprocess.run(cmd, env=full_env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout.strip()


def random_time(day: date) -> datetime:
    """Pick a random time during the day, weighted toward the afternoon/evening."""
    for _ in range(100):
        hour = random.gauss(TIME_MEAN, TIME_STD)
        if TIME_START <= hour < TIME_END:
            minute = random.randint(0, 59)
            return datetime(day.year, day.month, day.day, int(hour), minute)
    # fallback
    return datetime(day.year, day.month, day.day, TIME_MEAN, 0)


def pick_commit_count() -> int:
    counts, weights = zip(*COMMIT_WEIGHTS)
    return random.choices(counts, weights=weights)[0]


def should_commit(day: date) -> bool:
    return random.random() < DAY_ODDS[day.weekday()]


def build_vacation_set(start: date, end: date) -> set:
    """Return a set of dates to skip entirely (vacation / quiet periods)."""
    skip = set()

    # Fixed blocks
    for month, day_of_month, duration in VACATION_BLOCKS:
        for year in range(start.year, end.year + 1):
            try:
                block_start = date(year, month, day_of_month)
            except ValueError:
                continue
            for i in range(duration):
                d = block_start + timedelta(days=i)
                if start <= d <= end:
                    skip.add(d)

    # Random blocks
    available = [
        start + timedelta(days=i)
        for i in range((end - start).days + 1)
        if (start + timedelta(days=i)) not in skip
    ]
    for _ in range(RANDOM_VACATION_COUNT):
        if len(available) < RANDOM_VACATION_MIN_DAYS:
            break
        block_start = random.choice(available)
        duration = random.randint(RANDOM_VACATION_MIN_DAYS, RANDOM_VACATION_MAX_DAYS)
        for i in range(duration):
            skip.add(block_start + timedelta(days=i))

    return skip


def make_commit(repo_path: str, day: date, message: str):
    """Append a line to log.txt and commit with a backdated timestamp."""
    log_file = os.path.join(repo_path, "log.txt")
    commit_time = random_time(day)
    timestamp = commit_time.strftime("%Y-%m-%d %H:%M")

    with open(log_file, "a") as f:
        f.write(f"{timestamp} — {message}\n")

    git(repo_path, "add", "log.txt")

    date_str = commit_time.strftime("%Y-%m-%dT%H:%M:%S")
    git(repo_path, "commit", "-m", message, env={
        "GIT_AUTHOR_DATE":    date_str,
        "GIT_COMMITTER_DATE": date_str,
    })


def process_day(repo_path: str, day: date) -> int:
    """Decide whether to commit for a given day and do it. Returns commit count."""
    if not should_commit(day):
        return 0
    count = pick_commit_count()
    for _ in range(count):
        make_commit(repo_path, day, random.choice(MESSAGES))
    return count


def backfill(repo_path: str):
    """Generate commits across the past 365 days and push."""
    end   = date.today() - timedelta(days=1)
    start = end - timedelta(days=364)
    vacation = build_vacation_set(start, end)

    total = 0
    day = start
    skip_until = None
    while day <= end:
        if day not in vacation:
            if skip_until and day < skip_until:
                pass  # in a break, do nothing
            else:
                n = process_day(repo_path, day)
                total += n
                if n > 0 and random.random() < BREAK_CHANCE:
                    break_len = random.randint(BREAK_MIN_DAYS, BREAK_MAX_DAYS)
                    skip_until = day + timedelta(days=break_len)
        day += timedelta(days=1)

    print(f"Backfill complete: {total} commits over 365 days.")
    print("Pushing...")
    git(repo_path, "push", "origin", "main")
    print("Done.")


def daily(repo_path: str):
    """Commit for today only, then push."""
    today = date.today()
    n = process_day(repo_path, today)
    if n:
        git(repo_path, "push", "origin", "main")
        print(f"Done: {n} commit(s) pushed.")
    else:
        print("No commits today.")


def main():
    parser = argparse.ArgumentParser(description="GitHub contribution filler")
    parser.add_argument("--repo",     required=True,      help="Path to the target git repo")
    parser.add_argument("--backfill", action="store_true", help="Fill the past 365 days")
    args = parser.parse_args()

    repo = os.path.expanduser(args.repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        print(f"Error: '{repo}' is not a git repository.")
        return

    git(repo, "config", "user.email", "cjcoleman267@gmail.com")
    git(repo, "config", "user.name",  "cjcol01")

    if args.backfill:
        backfill(repo)
    else:
        daily(repo)


if __name__ == "__main__":
    main()
