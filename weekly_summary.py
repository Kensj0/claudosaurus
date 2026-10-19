#!/usr/bin/env python3
"""Claudosaurus: weekly report for Jarri Workspace.

Posts once a week in #claudosaurus: commits in the Jarri repos and activity
in #core and #modules over the last 7 days.

  python3 weekly_summary.py            # posts to #claudosaurus
  python3 weekly_summary.py --dry-run  # prints the text only

Environment variables (optional, see README): CORE_CHANNEL_ID, MODULES_CHANNEL_ID,
SUMMARY_CHANNEL_ID, GITHUB_TOKEN, DISCORD_TOKEN.
"""
import datetime as dt
import os
import sys

from repo_sync import discord, github

CORE = os.environ.get('CORE_CHANNEL_ID') or '1561799039987622063'      # #core
MODULES = os.environ.get('MODULES_CHANNEL_ID') or '1561799041635848259'  # #modules
SUMMARY = os.environ.get('SUMMARY_CHANNEL_ID') or '1561799044194631680'  # #claudosaurus
REPOS = ['TorMatzAndren/jarri-workspace-core', 'Kensj0/jarri-workspace-core', 'Kensj0/jarri-apps']
DAYS = 7
DISCORD_EPOCH = 1420070400000
MONTHS = 'jan feb mar apr may jun jul aug sep oct nov dec'.split()


def fmt(t):
    return f'{t.day} {MONTHS[t.month - 1]}'


def time_snowflake(t):
    return str(int(t.timestamp() * 1000 - DISCORD_EPOCH) << 22)


def commits_since(full_name, since):
    """List of commit titles, or None if the repo can't be read (private or removed)."""
    status, data = github(f"/repos/{full_name}/commits?per_page=100&since={since.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    if status >= 400 or not isinstance(data, list):
        return None
    return [c['commit']['message'].splitlines()[0][:70] for c in data]


def channel_activity(channel_id, since):
    """(messages, people) from humans in the channel since the given time."""
    msgs = discord('GET', f'/channels/{channel_id}/messages?limit=100&after={time_snowflake(since)}')
    human = [m for m in msgs if not m['author'].get('bot') and m.get('type', 0) in (0, 19)]
    return len(human), len({m['author']['id'] for m in human})


def build(now):
    since = now - dt.timedelta(days=DAYS)
    week = now.isocalendar().week
    parts = [f'# 📰 Jarri Workspace, week {week}', f'*{fmt(since)} – {fmt(now)}*']

    coding, private = [], []
    for repo in REPOS:
        titles = commits_since(repo, since)
        if titles is None:
            private.append(repo)
        elif titles:
            coding.append(f"• **{repo}**: {len(titles)}{'+' if len(titles) == 100 else ''} commit{'s' if len(titles) > 1 else ''}"
                          + ''.join(f'\n  › {t}' for t in titles[:3]))
    if coding:
        parts.append('## 🔨 Code on GitHub\n' + '\n'.join(coding))

    talk = []
    for name, cid in (('#core', CORE), ('#modules', MODULES)):
        count, people = channel_activity(cid, since)
        if count:
            talk.append(f"• {name}: {count} message{'s' if count > 1 else ''} from {people} person{'s' if people > 1 else ''}")
    if talk:
        parts.append('## 💬 Discussion\n' + '\n'.join(talk))

    if not (coding or talk):
        parts.append('😴 Quiet week. Nothing new in the repos, #core or #modules.')
    if private:
        parts.append(f"-# 🔒 Not visible to the bot, so not counted: {', '.join(private)}")
    return parts


def chunks(parts, limit=1900):
    out, cur = [], ''
    for p in parts:
        if cur and len(cur) + len(p) + 2 > limit:
            out.append(cur)
            cur = ''
        cur = f'{cur}\n\n{p}' if cur else p
    return out + [cur] if cur else out


def main():
    now = dt.datetime.now(dt.timezone.utc)
    messages = chunks(build(now))
    if '--dry-run' in sys.argv:
        print('\n---\n'.join(messages))
        return
    for text in messages:
        discord('POST', f'/channels/{SUMMARY}/messages', {'content': text, 'allowed_mentions': {'parse': []}})
    print(f'Posted {len(messages)} message(s) in #claudosaurus')


if __name__ == '__main__':
    main()
