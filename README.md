# Claudosaurus 🦖

**En Discord-bot som skriver veckorapporten för Jarri Workspace.**

Varje måndag postar den en rapport i `#claudosaurus` på servern Jarri Workspace: vad som
hänt i repona (commits och ändrad dokumentation) och i Discord-chatten under de senaste
7 dagarna. Om en AI-nyckel finns görs även en kort sammanfattning av veckan.

Namnet är en blandning av *Claude* och *dinosaurus*. 🦖

---

## Så ser det ut

> # 📰 Jarri Workspace, vecka 43
> *12 okt – 19 okt*
>
> ## 🔨 Code on GitHub
> • **Kensj0/kennystuner**: 3 commits
>   › Fix mic permission
>   › …
>
> ## 📄 Docs changed
> • **Kensj0/kennystuner**: README.md
>
> ## 💬 Discussion
> • #general: 14 messages from 2 persons

*(Påhittat exempel.)*

---

## Vad rapporten läser

| Källa | Vad som tas med |
|---|---|
| GitHub | Commits och ändrade `.md`-filer i repona i listan `REPOS` i `weekly_summary.py` |
| Discord | Meddelanden i alla textkanaler och aktiva forumtrådar, **utom** kategorin 📦 ARCHIVE |

Privata repon syns inte för boten och tas inte med. Arkivet tas inte med alls, så
gamla projekt som inte hör till Jarri hamnar inte i rapporten.

## Hur det körs

- **`weekly-summary.yml`** kör `weekly_summary.py` varje måndag 06:00 UTC, och går att starta
  manuellt under fliken **Actions**.
- Boten skriver bara i `#claudosaurus`. Den läser utan att spara något.
- Om hemligheten `ANTHROPIC_API_KEY` finns skickas veckans text (commits och meddelanden,
  max 20 000 tecken) till Claude API för att skriva sammanfattningen. Utan nyckeln postas
  bara siffrorna.
- Inga beroenden utöver Pythons standardbibliotek.

Testa utan att posta:

```bash
python3 weekly_summary.py --dry-run
```

## Inaktiv: repo-synken

`repo_sync.py` och `repo-sync.yml` lade tidigare in GitHub-länkar från `#lägg-till-repo` i
ett projektforum. Workflowen är avstängd och kanalen är arkiverad. Filerna finns kvar,
eftersom `repo_sync.py` också innehåller hjälpfunktionerna som veckorapporten använder.

---

## Sätt upp egen instans

Du behöver en Discord-server där du är admin, ett GitHub-konto och en Discord-bot.

### 1. Boten i Discord

1. [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** → fliken **Bot** → **Reset Token**. Dela aldrig token.
2. **OAuth2 → URL Generator**: kryssa i `bot` och rättigheterna *View Channels*, *Send Messages*,
   *Read Message History*. Öppna länken och bjud in boten till servern.

### 2. Kanaler

- En kanal för rapporten, t.ex. `#claudosaurus`. Kopiera dess ID (Utvecklarläge på → högerklick → **Kopiera ID**).
- Server-ID:t: högerklicka på servern → **Kopiera ID**.

### 3. GitHub

Forka repot och lägg in under **Settings → Secrets and variables → Actions**:

| Namn | Typ | Beskrivning |
|---|---|---|
| `DISCORD_TOKEN` | secret | Botens token. **Krävs.** |
| `ANTHROPIC_API_KEY` | secret | Ger AI-sammanfattningen. Valfri. |
| `GUILD_ID` | variable | Serverns ID. Standardvärdet är Jarri Workspace-servern. |
| `SUMMARY_CHANNEL_ID` | variable | Kanalen för rapporten. Standardvärdet är `#claudosaurus`. |

Ändra `REPOS` i `weekly_summary.py` till de repon du vill följa. Starta sedan workflowen
**Veckosammanfattning** under **Actions → Run workflow** för att testa.

---

## Filer

| Fil | Vad |
|---|---|
| [`weekly_summary.py`](weekly_summary.py) | Veckorapporten: GitHub, Discord och sammanfattningen |
| [`repo_sync.py`](repo_sync.py) | Hjälpfunktioner (Discord, GitHub, HTTP). Repo-synken är avstängd. |
| [`.github/workflows/weekly-summary.yml`](.github/workflows/weekly-summary.yml) | Kör rapporten måndagar 06:00 UTC |
| [`.github/workflows/repo-sync.yml`](.github/workflows/repo-sync.yml) | Avstängd |

## Licens

[MIT](LICENSE): fritt att använda, ändra och dela, så länge licenstexten följer med.
