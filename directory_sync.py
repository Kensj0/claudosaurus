#!/usr/bin/env python3
"""Claudosaurus: keeps each group's #repos list in sync with links posted in its #claudosaurus.

  github.com/user        -> adds the user with all their public repos (no forks)
  github.com/user/repo   -> adds that repo under the user
  anything else          -> left alone, it is a note for the weekly report

Each handled message gets ✅, a link that can't be read gets ⚠️. Entries are one
message per GitHub account, edited in place when repos are added.

  python3 directory_sync.py            # updates the lists
  python3 directory_sync.py --dry-run  # prints what would be posted, changes nothing
"""
import base64
import re
import sys
import urllib.parse

from config import GROUPS, EXCLUDE
from repo_sync import discord, github

LINK = re.compile(r'github\.com/([\w.-]+)(?:/([\w.-]+))?', re.I)
OK, FAIL = '✅', '⚠️'
MAX = 1950  # Discord limit is 2000
DRY = '--dry-run' in sys.argv


def author_name(m):
    return m['author'].get('global_name') or m['author']['username']


def clean(text, limit=90):
    text = re.sub(r'!\[.*?\]\(.*?\)|\[(.*?)\]\(.*?\)|<[^>]+>|[`*_]', lambda x: x.group(1) or '', text).strip()
    return (text[:limit - 1] + '…') if len(text) > limit else text


def summary(full):
    """GitHub description, or the first real line of the README."""
    status, repo = github(f'/repos/{full}')
    if status < 400 and repo.get('description'):
        return clean(repo['description'])
    status, readme = github(f'/repos/{full}/readme')
    if status >= 400:
        return ''
    for line in base64.b64decode(readme['content']).decode('utf-8', 'replace').splitlines():
        line = line.strip()
        if line and not line.startswith(('#', '![', '<', '[!', '---', '|', '[')):
            return clean(line)
    return ''


def user_repos(login):
    """Public, non-fork repos of a user, as (name, summary)."""
    status, data = github(f'/users/{login}/repos?per_page=100&type=owner&sort=pushed')
    if status >= 400 or not isinstance(data, list):
        return None
    return [(r['name'], summary(r['full_name'])) for r in data
            if not r['fork'] and r['full_name'] not in EXCLUDE]


def entries(channel_id):
    """Existing entries as {login: (message_id, name, [(repo, summary)])}, read from the bot's own messages."""
    out = {}
    for m in discord('GET', f'/channels/{channel_id}/messages?limit=100'):
        if not m['author'].get('bot'):
            continue
        head, *rest = m['content'].splitlines()
        login = re.search(r'github\.com/([\w.-]+)', head)
        name = re.match(r'\*\*(.+?)\*\*', head)
        if not login or not name:
            continue
        repos = []
        for line in rest:
            hit = re.match(r'-# \*\*(.+?)\*\*: ?(.*)', line)
            if hit:
                repos.append((hit.group(1), hit.group(2)))
        out[login.group(1).lower()] = (m['id'], name.group(1), repos)
    return out


def render(login, name, repos):
    lines = [f'**{name}** · [github.com/{login}](<https://github.com/{login}>)']
    shown = []
    for repo, text in repos:
        line = f'-# **{repo}**: {text}' if text else f'-# **{repo}**'
        if len('\n'.join(lines + shown + [line])) + 12 > MAX:
            break
        shown.append(line)
    rest = len(repos) - len(shown)
    if rest:
        shown.append(f'-# +{rest} more')
    return '\n'.join(lines + shown)


def save(channel_id, login, name, repos, existing):
    content = render(login, name, repos)
    if DRY:
        print(f'[{channel_id}] {content}\n')
        return
    if existing:
        discord('PATCH', f'/channels/{channel_id}/messages/{existing[0]}', {'content': content, 'allowed_mentions': {'parse': []}})
    else:
        discord('POST', f'/channels/{channel_id}/messages', {'content': content, 'allowed_mentions': {'parse': []}})


def react(channel_id, message_id, emoji):
    if not DRY:
        discord('PUT', f'/channels/{channel_id}/messages/{message_id}/reactions/{urllib.parse.quote(emoji)}/@me')


def add_user(channel_id, login, name, known):
    repos = user_repos(login)
    if repos is None:
        return False
    current = known.get(login.lower())
    save(channel_id, login, current[1] if current else name, repos, current)
    return True


def add_repo(channel_id, login, repo, name, known):
    full = f'{login}/{repo}'
    if full in EXCLUDE:
        return False
    status, _ = github(f'/repos/{full}')
    if status >= 400:
        return False
    current = known.get(login.lower())
    repos = dict(current[2]) if current else {}
    repos[repo] = summary(full)
    save(channel_id, login, current[1] if current else name, list(repos.items()), current)
    return True


def sync(group):
    cfg = GROUPS[group]
    ch, repos_ch = cfg['claudosaurus'], cfg['repos']
    known = entries(repos_ch)
    for m in reversed(discord('GET', f'/channels/{ch}/messages?limit=50')):
        if m['author'].get('bot') or any(r['me'] and r['emoji']['name'] in (OK, FAIL) for r in m.get('reactions', [])):
            continue
        links = list(LINK.finditer(m['content']))
        if not links:
            continue  # en anteckning, den ligger kvar för veckorapporten
        name = author_name(m)
        results = []
        for hit in links:
            login, repo = hit.group(1), hit.group(2)
            if repo:
                results.append(add_repo(repos_ch, login, repo, name, known))
            else:
                results.append(add_user(repos_ch, login, name, known))
            known = entries(repos_ch)
        react(ch, m['id'], OK if all(results) else FAIL)


if __name__ == '__main__':
    for group in GROUPS:
        sync(group)
    print('klart', 'DRY' if DRY else '')
