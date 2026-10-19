#!/usr/bin/env python3
"""Claudosaurus: weekly report for Jarri Workspace.

Posts once a week in #claudosaurus: what happened in the Jarri repos (commits and
changed docs) and in the Discord server (messages), last 7 days. If ANTHROPIC_API_KEY
is set, a short summary is written from that material. Only the repos in REPOS are
read, and archived channels are skipped, so nothing from other projects is included.

  python3 weekly_summary.py            # posts to #claudosaurus
  python3 weekly_summary.py --dry-run  # prints the text only

Environment variables (optional, see README): SUMMARY_CHANNEL_ID, GITHUB_TOKEN,
DISCORD_TOKEN, ANTHROPIC_API_KEY.
"""
import datetime as dt
import os
import sys

from repo_sync import GUILD, discord, github, http

SUMMARY = os.environ.get('SUMMARY_CHANNEL_ID') or '1561799044194631680'  # #claudosaurus
ARCHIVE = '1561799036967718973'  # 📦 ARCHIVE, skipped completely
REPOS = [
    'TorMatzAndren/jarri-workspace-core',
    'Kensj0/jarri-workspace-core',
    'Kensj0/jarri-apps',   # private: not visible to the bot until made public or given a token
    'Kensj0/kennystuner',  # the tuner module
    'Kensj0/claudosaurus',
]
TEXT_TYPES = (0, 5, 15)  # text, announcement, forum
DAYS = 7
MAX_CHARS = 20000  # cap on text sent to the summary model
MODEL = 'claude-sonnet-5-5'
DISCORD_EPOCH = 1420070400000
MONTHS = 'jan feb mar apr may jun jul aug sep oct nov dec'.split()


def fmt(t):
    return f'{t.day} {MONTHS[t.month - 1]}'


def time_snowflake(t):
    return str(int(t.timestamp() * 1000 - DISCORD_EPOCH) << 22)


def commits_since(full_name, since):
    """Commit shas and titles since the given time, empty if the repo can't be read."""
    status, data = github(f"/repos/{full_name}/commits?per_page=100&since={since.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    if status >= 400 or not isinstance(data, list):
        return []
    return [(c['sha'], c['commit']['message'].splitlines()[0][:70]) for c in data]


def changed_docs(full_name, sha):
    """Markdown files changed in one commit."""
    status, data = github(f'/repos/{full_name}/commits/{sha}')
    if status >= 400:
        return []
    return [f['filename'] for f in data.get('files', []) if f['filename'].lower().endswith('.md')]


def messages_since(channel_id, since):
    msgs = discord('GET', f'/channels/{channel_id}/messages?limit=100&after={time_snowflake(since)}')
    return [m for m in msgs if not m['author'].get('bot') and m.get('type', 0) in (0, 19)]


def places():
    """Text channels, forums and active threads outside the archive, as (name, id)."""
    chans = discord('GET', f'/guilds/{GUILD}/channels')
    archived = {c['id'] for c in chans if c.get('parent_id') == ARCHIVE} | {ARCHIVE}
    names = {c['id']: c['name'] for c in chans}
    out = [(c['name'], c['id']) for c in chans if c['type'] in TEXT_TYPES and c['id'] not in archived]
    threads = discord('GET', f'/guilds/{GUILD}/threads/active')['threads']
    out += [(f"{names.get(t['parent_id'], '?')} / {t['name']}", t['id'])
            for t in threads if t.get('parent_id') not in archived]
    return out


def summarize(material):
    """Short English summary from the week's material, or None without an API key."""
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        return None
    prompt = ("You write the weekly report for the Discord server of Jarri Workspace, an open-source desktop app "
              "and its modules. From the material below (commits, changed docs, Discord messages from the last "
              "7 days), write at most 6 short bullets in English: what was built, decisions taken, open questions. "
              "Use only what is in the material. If the week was quiet, say so in one line.\n\n" + material)
    status, data = http('POST', 'https://api.anthropic.com/v1/messages', {
        'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json',
    }, {'model': MODEL, 'max_tokens': 700, 'messages': [{'role': 'user', 'content': prompt}]})
    if status >= 400:
        raise RuntimeError(f'Anthropic API: {status} {data}')
    return data['content'][0]['text'].strip()


def build(now):
    since = now - dt.timedelta(days=DAYS)
    parts = [f'# 📰 Jarri Workspace, week {now.isocalendar().week}', f'*{fmt(since)} – {fmt(now)}*']
    material = []

    coding, docs = [], []
    for repo in REPOS:
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
    for name, cid in places():
        msgs = messages_since(cid, since)
        if not msgs:
            continue
        people = len({m['author']['id'] for m in msgs})
        talk.append(f"• #{name}: {len(msgs)} message{'s' if len(msgs) > 1 else ''} from {people} person{'s' if people > 1 else ''}")
        material.append(f'[#{name}] ' + ' | '.join(f"{m['author']['username']}: {m['content'][:300]}" for m in msgs))
    if talk:
        parts.append('## 💬 Discussion\n' + '\n'.join(talk))

    text = '\n\n'.join(material)[:MAX_CHARS]
    summary = summarize(text) if text else None
    if summary:
        parts.insert(2, '## 🧭 Summary\n' + summary)
    if not (coding or talk):
        parts.append('😴 Quiet week. Nothing new in the repos or the server.')
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
