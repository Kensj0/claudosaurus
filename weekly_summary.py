#!/usr/bin/env python3
"""Claudosaurus: veckosammanfattning av projektforumet.

Går igenom alla inlägg i projektforumet och postar en sammanfattning av senaste
veckan: nya projekt, aktiva diskussioner, GitHub-commits per repo och projekt
som legat stilla länge.

  python3 weekly_summary.py            # postar i sammanfattningskanalen
  python3 weekly_summary.py --dry-run  # skriver bara ut texten

Miljövariabler: DISCORD_TOKEN (krävs), GITHUB_TOKEN (valfri),
FORUM_CHANNEL_ID, SUMMARY_CHANNEL_ID, GUILD_ID (valfria, se README).
"""
import datetime as dt
import os
import re
import sys

from repo_sync import GUILD, FORUM, discord, github

SUMMARY = os.environ.get('SUMMARY_CHANNEL_ID') or '1558441075591487530'   # #veckan
DAYS = 7
QUIET_DAYS = 30
DISCORD_EPOCH = 1420070400000


MONTHS = 'jan feb mar apr maj jun jul aug sep okt nov dec'.split()


def fmt(t):
    return f'{t.day} {MONTHS[t.month - 1]}'


def snowflake_time(sid):
    return dt.datetime.fromtimestamp(((int(sid) >> 22) + DISCORD_EPOCH) / 1000, dt.timezone.utc)


def time_snowflake(t):
    return str(int(t.timestamp() * 1000 - DISCORD_EPOCH) << 22)


def forum_threads():
    threads = [t for t in discord('GET', f'/guilds/{GUILD}/threads/active')['threads'] if t.get('parent_id') == FORUM]
    page = discord('GET', f'/channels/{FORUM}/threads/archived/public?limit=100')
    return threads + page['threads']


def human_messages_since(thread_id, since):
    msgs = discord('GET', f'/channels/{thread_id}/messages?limit=100&after={time_snowflake(since)}')
    return [m for m in msgs if not m['author'].get('bot') and m.get('type', 0) in (0, 19)]


def commits_since(full_name, since):
    """(antal, [titlar]) eller None om repot inte går att se (privat/borttaget)."""
    status, data = github(f"/repos/{full_name}/commits?per_page=100&since={since.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    if status >= 400 or not isinstance(data, list):
        return None
    return len(data), [c['commit']['message'].splitlines()[0][:70] for c in data[:3]]


def last_push(full_name):
    status, data = github(f'/repos/{full_name}')
    if status >= 400:
        return None
    return dt.datetime.fromisoformat(data['pushed_at'].replace('Z', '+00:00'))


def build(now):
    since = now - dt.timedelta(days=DAYS)
    tags = {t['id']: t['name'] for t in discord('GET', f'/channels/{FORUM}')['available_tags']}
    new, discussed, coding, quiet, private = [], [], [], [], []

    for t in forum_threads():
        repo = t['name'].split(' · ')[0].strip()
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
            continue  # mallar och andra inlägg utan ägare/repo
        link = f"<#{t['id']}>"
        status = [tags[x] for x in t.get('applied_tags', []) if x in tags]

        if snowflake_time(t['id']) >= since:
            new.append(link)

        msgs = human_messages_since(t['id'], since) if t.get('last_message_id') and \
            snowflake_time(t['last_message_id']) >= since else []
        if msgs:
            people = len({m['author']['id'] for m in msgs})
            discussed.append((len(msgs), f"{link}: {len(msgs)} meddelanden från {people} person{'er' if people > 1 else ''}"))

        commits = commits_since(repo, since)
        if commits is None:
            private.append(link)
        elif commits[0]:
            n, titles = commits
            lines = f"{link}: **{n}{'+' if n == 100 else ''} commit{'s' if n > 1 else ''}**"
            lines += ''.join(f'\n  › {x}' for x in titles)
            coding.append((n, lines))
        elif '✅ Klart' not in status:
            pushed = last_push(repo)
            if pushed and (now - pushed).days >= QUIET_DAYS:
                quiet.append(f"{link}: senast pushat för {(now - pushed).days} dagar sedan")

    week = now.isocalendar().week
    parts = [f"# 📰 Veckan som gick, vecka {week}",
             f"*{fmt(since)} – {fmt(now)}*"]
    if new:
        parts.append('## 🆕 Nya projekt\n' + '\n'.join(f'• {x}' for x in new))
    if coding:
        parts.append('## 🔨 Kodat på GitHub\n' + '\n'.join(f'• {x}' for _, x in sorted(coding, reverse=True)))
    if discussed:
        parts.append('## 💬 Livligast i trådarna\n' + '\n'.join(f'• {x}' for _, x in sorted(discussed, reverse=True)))
    if not (new or coding or discussed):
        parts.append('😴 Lugn vecka, inget nytt i projekten. Perfekt läge att starta något?')
    if quiet:
        parts.append('## 💤 Står still\n*Behöver de hjälp, eller ska de få taggen ✅ Klart?*\n' +
                     '\n'.join(f'• {x}' for x in quiet))
    if private:
        parts.append(f"-# 🔒 {len(private)} privata repon räknas inte i commits ({', '.join(private)})")
    parts.append('-# Diskutera veckan i en tråd under det här meddelandet 👇')
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
    print(f'Postade {len(messages)} meddelande(n) i #{SUMMARY}')


if __name__ == '__main__':
    main()
