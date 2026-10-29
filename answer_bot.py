"""Svarar direkt i #claudosaurus: frågor, chatthistorik, repoförklaringar och admin-ändringar.

Körs som tjänst på servern (systemd-användartjänsten claudosaurus-answer).
Miljövariabler: DISCORD_TOKEN och ANTHROPIC_API_KEY.
Läser och citerar bara offentliga kanaler i GROUPS, aldrig #jarri-core eller låsta kanaler.
GitHub-länkar utan fråga hanteras fortfarande av directory_sync.py.
"""
import asyncio
import collections
import datetime as dt
import json
import os
import re
import time
import urllib.request

import anthropic
import discord

from config import GROUPS, JARRI_CORE

ANSWER_CHANNELS = {int(group['claudosaurus']) for group in GROUPS.values()}
CHAT_CHANNELS = {int(channel) for group in GROUPS.values() for channel in group['chat']}
READABLE = (ANSWER_CHANNELS | CHAT_CHANNELS) - {int(JARRI_CORE)}
KERNGRUPPEN = 1558439231842418783  # 👑 Kärngruppen, den enda som får ge admin-kommandon
ADMIN_LOG = os.environ.get('ADMIN_LOG', 'admin-log.jsonl')
MODEL = 'claude-haiku-5-5'
MAX_PER_HOUR = 20
PENDING_SECONDS = 600
HISTORY_WORDS = ('igår', 'sa ', 'sade', 'bestämdes', 'historik', 'senast', 'vad hände')
SYSTEM = (
    'Du är Claudosaurus, boten för Discord-servern AI-Den. Svara kort på svenska i neutral ton. '
    'Ändringar i servern görs bara efter ett ja från Kärngruppen. '
    'Du citerar bara från underlag du fått i meddelandet. Om underlaget saknas: säg det.'
)
ACTION_PROMPT = (
    'Du omvandlar en begäran från en admin till JSON och svarar bara med JSON. '
    'Tillåtna actions: "channel_topic" (ny kanalbeskrivning) och "post_text" (text att skriva). '
    'Format: {"action": "...", "channels": ["kanal-ID", ...], "text": "..."}. '
    'Välj kanal-ID:n bara från listan Kanaler. Två kanaler med samma namn skiljs åt med kategorin. '
    'Om begäran saknar en ny text, sätt "text" till "". '
    'Om begäran inte passar: {"action": "none"}.'
)
REPO_LINK = re.compile(r'github\.com/([\w.-]+)/([\w.-]+)')

recent = collections.deque()
pending = {}  # kanal-id -> föreslagen ändring som väntar på "ja"
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


def is_public(channel):
    return channel.permissions_for(channel.guild.default_role).view_channel


def log_action(message, action, target, result):
    entry = {
        'time': dt.datetime.now(dt.timezone.utc).isoformat(),
        'by': str(message.author), 'by_id': message.author.id,
        'action': action, 'target': str(target), 'target_id': target.id, 'result': result,
    }
    with open(ADMIN_LOG, 'a', encoding='utf-8') as log:
        log.write(json.dumps(entry, ensure_ascii=False) + '\n')


def ask(system, content, max_tokens=500):
    result = ai.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                messages=[{'role': 'user', 'content': content}])
    return ''.join(block.text for block in result.content if block.type == 'text')


async def chat_context(limit=30):
    lines = []
    for channel_id in READABLE:
        channel = client.get_channel(channel_id)
        if channel is None or not is_public(channel):
            continue
        try:
            async for message in channel.history(limit=limit):
                if not message.author.bot and message.content:
                    lines.append((message.created_at, f'#{channel.name} {message.author.display_name}: {message.content[:300]}'))
        except discord.Forbidden:
            continue
    lines.sort()
    return '\n'.join(line for _, line in lines)[-12000:]


def readme(owner, repo):
    request = urllib.request.Request(
        f'https://api.github.com/repos/{owner}/{repo}/readme',
        headers={'Accept': 'application/vnd.github.raw', 'User-Agent': 'claudosaurus'},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode('utf-8')[:8000]


def channel_list(guild):
    return '\n'.join(
        f'{channel.id} #{channel.name} (kategori: {channel.category.name if channel.category else "ingen"})'
        for channel in guild.text_channels if channel.id in READABLE
    )


async def propose(message, request):
    prompt_input = f'Kanaler:\n{channel_list(message.guild)}\n\nBegäran: {request}'
    raw = await asyncio.to_thread(ask, ACTION_PROMPT, prompt_input, 300)
    try:
        proposal = json.loads(raw[raw.index('{'):raw.rindex('}') + 1])
    except ValueError:
        await message.reply('Jag förstod inte vad som ska ändras.', mention_author=False)
        return
    if proposal.get('action') not in ('channel_topic', 'post_text'):
        await message.reply('Den ändringen kan jag inte göra.', mention_author=False)
        return
    text = proposal.get('text', '').strip()[:2000]
    if not text:
        await message.reply('Skriv den nya texten också, efter ett kolon. Exempel: '
                            '`uppdatera beskrivningen i ai-kanalen: Här diskuterar vi AI.`',
                            mention_author=False)
        return
    ids = [int(value) for value in proposal.get('channels', []) if str(value).isdigit()]
    channels = [client.get_channel(channel_id) for channel_id in ids if channel_id in READABLE]
    channels = [channel for channel in channels if channel is not None]
    if not channels or len(channels) != len(ids):
        await message.reply('Hittar inte alla kanalerna. Säg vilka kanaler det gäller, med namn och grupp.',
                            mention_author=False)
        return
    pending[message.channel.id] = {
        'action': proposal['action'], 'channel_ids': [channel.id for channel in channels], 'text': text,
        'expires': time.time() + PENDING_SECONDS,
    }
    names = ', '.join(f'#{channel.name}' for channel in channels)
    await message.reply(
        f'Föreslagen ändring: {proposal["action"]} i {names}:\n> {text}\n'
        'En Kärngruppen-medlem svarar **ja** för att köra. Gäller i 10 minuter.',
        mention_author=False, allowed_mentions=discord.AllowedMentions.none(),
    )


async def run_pending(message, change):
    for channel_id in change['channel_ids']:
        channel = client.get_channel(channel_id)
        if change['action'] == 'channel_topic':
            await channel.edit(topic=change['text'], reason=f'Ändrad av {message.author} via Claudosaurus')
        else:
            await channel.send(change['text'], allowed_mentions=discord.AllowedMentions.none())
        log_action(message, change['action'], channel, 'ok')
    await message.reply('Klart.', mention_author=False)


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
    lowered = text.lower()
    if lowered == 'ja' and is_core(message.author):
        change = pending.pop(message.channel.id, None)
        if change and change['expires'] > time.time():
            await run_pending(message, change)
        return
    if lowered.startswith('kicka'):
        if not is_core(message.author):
            await message.reply('Bara Kärngruppen kan ge admin-kommandon.', mention_author=False)
            return
        await handle_kick(message)
        return
    if lowered.startswith(('ändra', 'uppdatera', 'skriv i')):
        if not is_core(message.author):
            await message.reply('Bara Kärngruppen kan ge ändringar.', mention_author=False)
            return
        if allowed():
            await propose(message, text)
        return
    mentioned = client.user in message.mentions
    if not (mentioned or '?' in text):
        return
    link = REPO_LINK.search(text)
    if link and not mentioned and '?' not in text:
        return  # vanliga repo-länkar hanteras av directory_sync
    if not allowed():
        await message.reply('Jag har nått gränsen för svar den här timmen. Försök igen senare.',
                            mention_author=False)
        return
    question = text.replace(f'<@{client.user.id}>', '').strip() or text
    try:
        if link:
            body = await asyncio.to_thread(readme, link.group(1), link.group(2))
            answer = await asyncio.to_thread(
                ask, SYSTEM, f'README för {link.group(1)}/{link.group(2)}:\n{body}\n\nFråga: {question}')
        elif any(word in lowered for word in HISTORY_WORDS):
            context = await chat_context()
            answer = await asyncio.to_thread(
                ask, SYSTEM, f'Offentlig chatt (senaste):\n{context}\n\nFråga: {question}')
        else:
            answer = await asyncio.to_thread(ask, SYSTEM, question)
    except Exception as error:
        print(f'svar misslyckades: {error}', flush=True)
        return
    await message.reply(answer[:1900] or 'Jag fick inget svar.', mention_author=False,
                        allowed_mentions=discord.AllowedMentions.none())


if __name__ == '__main__':
    client.run(os.environ['DISCORD_TOKEN'])
