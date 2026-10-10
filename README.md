# Claudosaurus 🦖

Discord-bot för AI Gruppen, en server för vibe coding med vänner.

## Repo-sync

`repo_sync.py` körs var 10:e minut via GitHub Actions. Den läser nya meddelanden i
`#lägg-till-repo` och skapar ett inlägg i forumet `#projekt` för varje GitHub-länk:

- `github.com/namn/repo` lägger in det repot
- `github.com/namn` lägger in användarens publika repon (inte forks, högst 15 per länk)

Repon som redan finns (samma `ägare/repo` i titeln) hoppas över. Behandlade meddelanden
får ✅ eller ⚠️ och ett svar.

### Setup

1. Lägg bot-token som repo-secret `DISCORD_TOKEN` (Settings → Secrets and variables → Actions).
2. Kör manuellt första gången: Actions → "Lägg in repon från Discord" → Run workflow.

Lokalt: `python3 repo_sync.py` (läser token från `~/.config/discord-bot/token`).

Obs: GitHub pausar schemalagda jobb i repon utan aktivitet på 60 dagar. Klicka "Enable
workflow" under Actions om det händer.
