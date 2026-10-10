#!/usr/bin/env python3
"""Claudosaurus: lägger in GitHub-repon i forumet #projekt.

Läser nya meddelanden i #lägg-till-repo. För varje GitHub-länk:
  github.com/namn/repo  -> ett forum-inlägg för repot
  github.com/namn       -> ett inlägg per publikt repo (ej forks), nyast först
Redan inlagda repon (samma ägare/repo i titeln) hoppas över.
Behandlade meddelanden får en reaktion (✅/⚠️) och ett svar.

Miljövariabler: DISCORD_TOKEN (krävs), GITHUB_TOKEN (valfri, högre rate limit),
GUILD_ID, INBOX_CHANNEL_ID, FORUM_CHANNEL_ID, MAX_PER_USER_LINK (valfria, se README).
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Standardvärden = AI Gruppen. Sätt egna via miljövariabler för din server.
GUILD = os.environ.get('GUILD_ID') or '1558416177175470122'
INBOX = os.environ.get('INBOX_CHANNEL_ID') or '1558428805608116313'   # #lägg-till-repo
FORUM = os.environ.get('FORUM_CHANNEL_ID') or '1558439433861075015'   # #projekt-intern
MAX_PER_USER_LINK = int(os.environ.get('MAX_PER_USER_LINK') or 15)
DONE, FAIL = '✅', '⚠️'

DISCORD = 'https://discord.com/api/v10'
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    path = os.path.expanduser('~/.config/discord-bot/token')
    DISCORD_TOKEN = open(path).read().strip() if os.path.exists(path) else sys.exit('DISCORD_TOKEN saknas')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

LINK = re.compile(r'github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))(?:/([A-Za-z0-9._-]+))?', re.I)
NOT_USERS = {'orgs', 'settings', 'topics', 'explore', 'marketplace', 'features', 'about', 'login', 'sponsors'}


def http(method, url, headers, body=None):
    data = json.dumps(body).encode() if body is not None else None
    for _ in range(6):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        if data:
            req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            if e.code == 429:
                time.sleep(json.loads(raw).get('retry_after', 1) + 0.2)
                continue
            return e.code, (json.loads(raw) if raw else None)
    return 429, None


def discord(method, path, body=None):
    status, data = http(method, DISCORD + path, {
        'Authorization': 'Bot ' + DISCORD_TOKEN,
        'User-Agent': 'Claudosaurus (https://github.com/Kensj0, 1.0)',
    }, body)
    if status >= 400:
        raise RuntimeError(f'Discord {method} {path}: {status} {data}')
    return data


def github(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'Claudosaurus'}
    if GITHUB_TOKEN:
        headers['Authorization'] = 'Bearer ' + GITHUB_TOKEN
    return http('GET', 'https://api.github.com' + path, headers)


def existing_repos():
    """ägare/repo (gemener) för alla inlägg i forumet, aktiva och arkiverade."""
    titles = [t['name'] for t in discord('GET', f'/guilds/{GUILD}/threads/active')['threads']
              if t.get('parent_id') == FORUM]
    before = None
    while True:
        q = '?limit=100' + (f'&before={urllib.parse.quote(before)}' if before else '')
        page = discord('GET', f'/channels/{FORUM}/threads/archived/public{q}')
        titles += [t['name'] for t in page['threads']]
        if not page.get('has_more') or not page['threads']:
            break
        before = page['threads'][-1]['thread_metadata']['archive_timestamp']
    return {t.split(' · ')[0].strip().lower() for t in titles}


def pick_tags(repo, tag_ids):
    text = ' '.join([repo.get('description') or '', repo.get('name') or '', *repo.get('topics', [])]).lower()
    words = set(re.findall(r'[a-zåäö0-9+-]+', text))
    lang = (repo.get('language') or '').lower()
    tags = ['✅ Klart' if repo.get('archived') else '🚧 Pågår']
    if words & {'ai', 'llm', 'gpt', 'claude', 'openai', 'chatbot', 'ml', 'agent', 'anthropic', 'gemini'}:
        tags.append('🤖 AI')
    if words & {'game', 'games', 'spel', 'godot', 'unity', 'pygame'}:
        tags.append('🎮 Spel')
    if lang in {'kotlin', 'swift', 'dart', 'objective-c'} or words & {'android', 'ios', 'flutter', 'react-native', 'expo'}:
        tags.append('📱 Mobilapp')
    if repo.get('homepage') or lang in {'typescript', 'javascript', 'html', 'vue', 'svelte', 'css', 'astro'}:
        tags.append('🌐 Webbapp')
    if words & {'cli', 'tool', 'tools', 'verktyg', 'script', 'scripts', 'extension', 'plugin'}:
        tags.append('🧰 Verktyg')
    if len(tags) == 1:
        tags.append('🧪 Experiment')
    return [tag_ids[t] for t in tags[:5] if t in tag_ids]


def create_post(repo, added_by, tag_ids):
    full = repo['full_name']
    desc = (repo.get('description') or '').strip()
    title = f"{full} · {desc or repo.get('language') or 'Nytt projekt'}"
    if len(title) > 100:
        title = title[:99].rstrip() + '…'
    stack = ', '.join(x for x in [repo.get('language'), *repo.get('topics', [])[:6]] if x)
    lines = [
        f"**Vad:** {desc or '_Ingen beskrivning än, skriv gärna en rad i tråden!_'}",
        f"**Repo:** <{repo['html_url']}>",
    ]
    if repo.get('homepage'):
        lines.append(f"**Live:** <{repo['homepage']}>")
    lines += [
        f"**Ägare:** [{repo['owner']['login']}](<{repo['owner']['html_url']}>) · tillagd av <@{added_by}>",
        f"**Stack/verktyg:** {stack or '–'}",
        f"**Senast uppdaterad:** {repo['pushed_at'][:10]} · ⭐ {repo.get('stargazers_count', 0)}",
        '',
        '_Ägaren: berätta gärna mer i tråden, vad är nästa steg och söker du hjälp?_',
    ]
    t = discord('POST', f'/channels/{FORUM}/threads', {
        'name': title,
        'applied_tags': pick_tags(repo, tag_ids),
        'message': {'content': '\n'.join(lines), 'allowed_mentions': {'parse': []}},
    })
    return t['id']


def repos_for_link(owner, name):
    """Returnerar (repon, felmeddelande)."""
    if name:
        name = re.sub(r'\.git$', '', name)
        status, repo = github(f'/repos/{owner}/{name}')
        if status == 404:
            return [], f'Hittar inte `{owner}/{name}`. Är repot privat? Bara publika repon kan läggas in automatiskt.'
        if status >= 400:
            return [], f'GitHub svarade {status} för `{owner}/{name}`, försöker igen nästa körning.'
        return [repo], None
    status, repos = github(f'/users/{owner}/repos?per_page=100&sort=pushed')
    if status == 404:
        return [], f'Hittar ingen GitHub-användare som heter `{owner}`.'
    if status >= 400:
        return [], f'GitHub svarade {status} för `{owner}`, försöker igen nästa körning.'
    return [r for r in repos if not r['fork']], None


def handle(msg, have, tag_ids):
    links = []
    for owner, name in LINK.findall(msg['content']):
        if owner.lower() in NOT_USERS:
            continue
        key = (owner.lower(), (name or '').lower())
        if key not in [(o.lower(), (n or '').lower()) for o, n in links]:
            links.append((owner, name))
    if not links:
        return FAIL, 'Hittade ingen GitHub-länk. Skicka t.ex. `https://github.com/namn/repo` eller `https://github.com/namn`.'

    added, skipped, notes = [], [], []
    for owner, name in links:
        repos, err = repos_for_link(owner, name)
        if err:
            notes.append(err)
            continue
        new = [r for r in repos if r['full_name'].lower() not in have]
        skipped += [r['full_name'] for r in repos if r['full_name'].lower() in have and r['full_name'] not in skipped]
        if not name and len(new) > MAX_PER_USER_LINK:
            notes.append(f'`{owner}` har {len(new)} nya repon. Jag lade in de {MAX_PER_USER_LINK} senast uppdaterade. '
                         'Skicka direktlänkar för fler.')
            new = new[:MAX_PER_USER_LINK]
        for repo in new:
            tid = create_post(repo, msg['author']['id'], tag_ids)
            have.add(repo['full_name'].lower())
            added.append(f'<#{tid}>')

    parts = []
    if added:
        parts.append(f"🦖 Lade in {len(added)} repo{'n' if len(added) > 1 else ''} i <#{FORUM}>: " + ' '.join(added))
    if skipped:
        parts.append('Fanns redan: ' + ', '.join(f'`{s}`' for s in skipped[:10]) + (' …' if len(skipped) > 10 else ''))
    parts += notes
    ok = bool(added or skipped) and not any('försöker igen' in n for n in notes)
    retry = any('försöker igen' in n for n in notes)
    if retry and not added:
        return None, None  # lämna obehandlat, nästa körning tar det
    return (DONE if ok else FAIL), '\n'.join(parts)[:1900]


def main():
    me = discord('GET', '/users/@me')['id']
    msgs = discord('GET', f'/channels/{INBOX}/messages?limit=50')
    todo = [m for m in reversed(msgs)
            if m['author']['id'] != me and not m['author'].get('bot') and m.get('type', 0) in (0, 19)
            and not any(r.get('me') for r in m.get('reactions', []))]
    if not todo:
        print('Inget nytt.')
        return
    have = existing_repos()
    tag_ids = {t['name']: t['id'] for t in discord('GET', f'/channels/{FORUM}')['available_tags']}
    for m in todo:
        emoji, reply = handle(m, have, tag_ids)
        if emoji is None:
            print('Skjuter upp', m['id'])
            continue
        discord('POST', f'/channels/{INBOX}/messages', {
            'content': reply,
            'message_reference': {'message_id': m['id'], 'fail_if_not_exists': False},
            'allowed_mentions': {'parse': []},
        })
        discord('PUT', f"/channels/{INBOX}/messages/{m['id']}/reactions/{urllib.parse.quote(emoji)}/@me")
        print(emoji, m['id'], reply.splitlines()[0] if reply else '')


if __name__ == '__main__':
    main()
