"""Svarar direkt på frågor i de två #claudosaurus-kanalerna.

Körs som tjänst på servern (systemd-användartjänsten claudosaurus-answer).
Miljövariabler: DISCORD_TOKEN och ANTHROPIC_API_KEY. Svarar aldrig i #jarri-core.
GitHub-länkar hanteras fortfarande av directory_sync.py, så de hoppas över här.
"""
import asyncio
import collections
import time

import anthropic
import discord

from config import GROUPS

ANSWER_CHANNELS = {int(group['claudosaurus']) for group in GROUPS.values()}
MODEL = 'claude-haiku-5-5'
MAX_PER_HOUR = 20
SYSTEM = (
    'Du är Claudosaurus, boten för Discord-servern AI-Den. Svara kort på svenska i neutral ton. '
    'Du kan inte ändra något i servern och inte ta bort användare. '
    'Om någon ber om en ändring: säg att admin-kommandon kommer senare.'
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


@client.event
async def on_ready():
    print(f'inloggad som {client.user}', flush=True)


@client.event
async def on_message(message):
    if message.author.bot or message.channel.id not in ANSWER_CHANNELS:
        return
    text = message.content.strip()
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
    import os
    client.run(os.environ['DISCORD_TOKEN'])
