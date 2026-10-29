#!/usr/bin/env python3
"""Claudosaurus: weekly report for one group in AI-Den (ai or jarri).

Posts in the group's #weekly-report: commits and changed docs in the repos listed in the
group's #repos, Discord activity in the group's chat channels, notes people wrote in the
group's #claudosaurus, and a short AI summary if ANTHROPIC_API_KEY is set.

  python3 weekly_summary.py --group jarri            # posts
  python3 weekly_summary.py --group ai --dry-run     # prints the text only
"""
import base64
import datetime as dt
import os
import re
import sys

from config import GROUPS, JARRI_CORE
from directory_sync import LINK, entries
from repo_sync import GUILD, discord, github, http

DAYS = 7
MAX_CHARS = 20000  # cap on text sent to the summary model
MODEL = 'claude-haiku-5-5'
DISCORD_EPOCH = 1420070400000
MONTHS = 'jan feb mar apr may jun jul aug sep oct nov dec'.split()
DRY = '--dry-run' in sys.argv


def fmt(t):
    return f'{t.day} {MONTHS[t.month - 1]}'


def time_snowflake(t):
    return str(int(t.timestamp() * 1000 - DISCORD_EPOCH) << 22)


def repos_in(group):
    """Full repo names listed in the group's #repos. The Jarri list is the Jarri repos."""
    out = []
    for login, (_, _, repos) in entries(GROUPS[group]['repos']).items():
        out += [f'{login}/{name}' for name, _ in repos]
    return out


def commits_since(full, since):
    status, data = github(f"/repos/{full}/commits?per_page=100&since={since.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    if status >= 400 or not isinstance(data, list):
        return []
    return [(c['sha'], c['commit']['message'].splitlines()[0][:70]) for c in data]


def changed_docs(full, sha):
    status, data = github(f'/repos/{full}/commits/{sha}')
    if status >= 400:
        return []
    return [f['filename'] for f in data.get('files', []) if f['filename'].lower().endswith('.md')]


def messages_since(channel_id, since):
    msgs = discord('GET', f'/channels/{channel_id}/messages?limit=100&after={time_snowflake(since)}')
    return [m for m in msgs if not m['author'].get('bot') and m.get('type', 0) in (0, 19)]


def summarize(material):
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        return None
    prompt = ("You write the weekly report for a group in the Discord server AI-Den. The group works on the "
              "material below (commits, changed docs, Discord messages and notes from the last 7 days). Write at "
              "most 6 short bullets in English: what was built, decisions taken, open questions. Use only what "
              "is in the material. If the week was quiet, say so in one line.\n\n" + material)
    status, data = http('POST', 'https://api.anthropic.com/v1/messages', {
        'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json',
    }, {'model': MODEL, 'max_tokens': 700, 'messages': [{'role': 'user', 'content': prompt}]})
    if status >= 400:
        raise RuntimeError(f'Anthropic API: {status} {data}')
    return data['content'][0]['text'].strip()


def build(group, now):
    cfg = GROUPS[group]
    since = now - dt.timedelta(days=DAYS)
    parts = [f"# 📰 {cfg['name']}, week {now.isocalendar().week}", f'*{fmt(since)} – {fmt(now)}*']
    material = []

    jarri_repos = set(repos_in('jarri'))
    repos = [r for r in repos_in(group) if r not in jarri_repos or group == 'jarri']
    coding, docs = [], []
    for repo in repos:
        commits = commits_since(repo, since)
        if not commits:
            continue
        coding.append(f"• **{repo}**: {len(commits)}{'+' if len(commits) == 100 else ''} commit{'s' if len(commits) > 1 else ''}"
                      + ''.join(f'\n  › {title}' for _, title in commits[:3]))
        material.append(f"[{repo}] commits: " + '; '.join(title for _, title in commits))
        files = sorted({f for sha, _ in commits[:20] for f in changed_docs(repo, sha)})
        if files:
            docs.append(f"• **{repo}**: " + ', '.join(files[:8]))
    if coding:
        parts.append('## 🔨 Code on GitHub\n' + '\n'.join(coding))
    if docs:
        parts.append('## 📄 Docs changed\n' + '\n'.join(docs))

    talk = []
    for cid in cfg['chat']:
        if cid == JARRI_CORE:
            continue
        msgs = messages_since(cid, since)
        if not msgs:
            continue
        name = next(c['name'] for c in discord('GET', f'/guilds/{GUILD}/channels') if c['id'] == cid)
        people = len({m['author']['id'] for m in msgs})
        talk.append(f"• #{name}: {len(msgs)} message{'s' if len(msgs) > 1 else ''} from {people} person{'s' if people > 1 else ''}")
        material.append(f'[#{name}] ' + ' | '.join(f"{m['author']['username']}: {m['content'][:300]}" for m in msgs))
    if talk:
        parts.append('## 💬 Discussion\n' + '\n'.join(talk))

    notes = [m for m in messages_since(cfg['claudosaurus'], since) if not LINK.search(m['content'])]
    if notes:
        parts.append('## 📝 From the team\n' + '\n'.join(f"• {m['content'][:300]}" for m in notes))
        material.append('[notes] ' + ' | '.join(m['content'][:300] for m in notes))

    text = '\n\n'.join(material)[:MAX_CHARS]
    summary = summarize(text) if text else None
    if summary:
        parts.insert(2, '## 🧭 Summary\n' + summary)
    if not (coding or talk or notes):
        parts.append('😴 Quiet week. Nothing new in the repos or the chat.')
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
    group = sys.argv[sys.argv.index('--group') + 1]
    now = dt.datetime.now(dt.timezone.utc)
    messages = chunks(build(group, now))
    if DRY:
        print('\n---\n'.join(messages))
        return
    for text in messages:
        discord('POST', f"/channels/{GROUPS[group]['weekly']}/messages", {'content': text, 'allowed_mentions': {'parse': []}})
    print(f"Posted {len(messages)} message(s) in {GROUPS[group]['name']} #weekly-report")


if __name__ == '__main__':
    main()
