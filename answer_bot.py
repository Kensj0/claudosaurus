"""Svarar direkt på frågor i de två #claudosaurus-kanalerna.

Körs som tjänst på servern (systemd-användartjänsten claudosaurus-answer).
Miljövariabler: DISCORD_TOKEN och ANTHROPIC_API_KEY. Svarar aldrig i #jarri-core.
GitHub-länkar hanteras fortfarande av directory_sync.py, så de hoppas över här.
"""
import asyncio
import collections
import datetime as dt
import json
import os
import time

import anthropic
import discord

from config import GROUPS

ANSWER_CHANNELS = {int(group['claudosaurus']) for group in GROUPS.values()}
KERNGRUPPEN = 1558439231842418783  # 👑 Kärngruppen, den enda som får ge admin-kommandon
ADMIN_LOG = os.environ.get('ADMIN_LOG', 'admin-log.jsonl')
MODEL = 'claude-haiku-5-5'
MAX_PER_HOUR = 20
SYSTEM = (
    'Du är Claudosaurus, boten för Discord-servern AI-Den. Svara kort på svenska i neutral ton. '
    'Du kan inte ändra något i servern på egen hand. '
    'Admin-kommandon som kicka ges bara av Kärngruppen.'
)

recent = collections.deque()
ai = anthropic.Anthropic()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


def allowed():
    now = time.time()
    while recent and now - recent[0] > 3600:
        recent.popleft()
    if len(recent) >= MAX_PER_HOUR:
        return False
    recent.append(now)
    return True


def is_core(member):
    return any(role.id == KERNGRUPPEN for role in member.roles)


def log_action(message, action, target, result):
    entry = {
        'time': dt.datetime.now(dt.timezone.utc).isoformat(),
        'by': str(message.author), 'by_id': message.author.id,
        'action': action, 'target': str(target), 'target_id': target.id, 'result': result,
    }
    with open(ADMIN_LOG, 'a', encoding='utf-8') as log:
        log.write(json.dumps(entry, ensure_ascii=False) + '\n')


async def handle_kick(message):
    targets = [member for member in message.mentions if member.id != client.user.id]
    if not targets:
        await message.reply('Skriv vem som ska kickas, till exempel: kicka @namn', mention_author=False)
        return
    lines = []
    for target in targets:
        if target.bot or is_core(target):
            lines.append(f'{target.display_name}: kickas inte (bot eller Kärngruppen).')
            log_action(message, 'kick', target, 'nekad')
            continue
        try:
            await target.kick(reason=f'Kickad av {message.author} via Claudosaurus')
            lines.append(f'{target.display_name}: kickad.')
            log_action(message, 'kick', target, 'ok')
        except discord.Forbidden:
            lines.append(f'{target.display_name}: boten saknar behörighet att kicka.')
            log_action(message, 'kick', target, 'saknar behörighet')
    await message.reply('\n'.join(lines), mention_author=False,
                        allowed_mentions=discord.AllowedMentions.none())


@client.event
async def on_ready():
    print(f'inloggad som {client.user}', flush=True)


@client.event
async def on_message(message):
    if message.author.bot or message.channel.id not in ANSWER_CHANNELS:
        return
    text = message.content.strip()
    if text.lower().startswith('kicka'):
        if not is_core(message.author):
            await message.reply('Bara Kärngruppen kan ge admin-kommandon.', mention_author=False)
            return
        await handle_kick(message)
        return
    mentioned = client.user in message.mentions
    if not (mentioned or '?' in text) or 'github.com/' in text:
        return
    if not allowed():
        await message.reply('Jag har nått gränsen för svar den här timmen. Försök igen senare.',
                            mention_author=False)
        return
    question = text.replace(f'<@{client.user.id}>', '').strip() or text
    try:
        result = await asyncio.to_thread(
            ai.messages.create, model=MODEL, max_tokens=500, system=SYSTEM,
            messages=[{'role': 'user', 'content': question}],
        )
    except Exception as error:
        print(f'svar misslyckades: {error}', flush=True)
        return
    answer = ''.join(block.text for block in result.content if block.type == 'text')[:1900]
    await message.reply(answer or 'Jag fick inget svar.', mention_author=False,
                        allowed_mentions=discord.AllowedMentions.none())


if __name__ == '__main__':
    client.run(os.environ['DISCORD_TOKEN'])
