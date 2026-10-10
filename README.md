# Claudosaurus 🦖

**En Discord-bot som gör om GitHub-länkar till snygga projektinlägg.**

Någon klistrar in en länk till ett repo i Discord. Några minuter senare finns ett
inlägg i serverns projektforum med namn, beskrivning, länkar, språk och taggar.
Ingen behöver fylla i något för hand, och ingen server behöver vara igång dygnet runt.

Byggd för [AI Gruppen](#om-ai-gruppen), en Discord-server där vänner bygger saker
tillsammans med AI (”vibe coding”), men går att använda på vilken server som helst.

---

## Så ser det ut

**1. Någon skriver i `#lägg-till-repo`:**

> https://github.com/kompis/recept-ai

**2. Claudosaurus svarar (inom ~10 minuter):**

> 🦖 Lade in 1 repo i #projekt: **kompis/recept-ai · AI som föreslår middag från det som finns i kylen**

…och sätter ✅ på meddelandet.

**3. I forumet `#projekt` finns ett nytt inlägg:**

> **kompis/recept-ai · AI som föreslår middag från det som finns i kylen** &nbsp; `🚧 Pågår` `🤖 AI` `🌐 Webbapp`
>
> **Vad:** AI som föreslår middag från det som finns i kylen
> **Repo:** https://github.com/kompis/recept-ai
> **Live:** https://recept-ai.vercel.app
> **Ägare:** kompis · tillagd av @kompis
> **Stack/verktyg:** TypeScript, nextjs, openai
> **Senast uppdaterad:** 2026-10-08 · ⭐ 4

*(Påhittat exempel.)*

Du kan också länka till en **användare** (`https://github.com/namn`). Då läggs
alla hens publika repon in, högst 15 åt gången.

---

## Hur det fungerar

```
  Discord                         GitHub Actions (var 10:e min)             GitHub API
 ┌──────────────────┐   läser    ┌──────────────────────────┐   hämtar    ┌───────────┐
 │ #lägg-till-repo  │ ─────────▶ │      repo_sync.py        │ ──────────▶ │ repo-info │
 │  (länkar)        │ ◀───────── │                          │ ◀────────── └───────────┘
 └──────────────────┘ ✅ + svar  │ 1. nya meddelanden?      │
 ┌──────────────────┐            │ 2. hitta GitHub-länkar   │
 │ #projekt (forum) │ ◀───────── │ 3. hoppa över dubbletter │
 │  ett inlägg/repo │  skapar    │ 4. skapa forum-inlägg    │
 └──────────────────┘            └──────────────────────────┘
```

- **Ingen server.** Boten är inte ”online” hela tiden. Ett litet Python-skript körs
  var 10:e minut av GitHub Actions, gör sitt jobb och stängs av. Gratis i publika repon.
- **Inget minne.** Skriptet sparar ingen databas. Det vet vad som är gjort genom att
  titta på Discord själv:
  - Ett meddelande med botens ✅ eller ⚠️ är redan behandlat.
  - Ett repo vars `ägare/repo` redan står i en forumtitel finns redan.
- **Inga beroenden.** Bara Pythons standardbibliotek, ingen `pip install`.

### Taggar

Varje inlägg får en status-tagg och 1–4 typ-taggar som gissas från repots språk,
ämnen (topics), beskrivning och hemsida:

| Tagg | Sätts när… |
|---|---|
| 🚧 Pågår / ✅ Klart | repot är aktivt / arkiverat på GitHub |
| 🤖 AI | ord som *ai, llm, gpt, claude, openai, agent* förekommer |
| 🌐 Webbapp | repot har en hemsida, eller språket är JS/TS/HTML/Vue/Svelte… |
| 📱 Mobilapp | Kotlin/Swift/Dart, eller *android, ios, flutter, expo* |
| 🎮 Spel | *game, spel, godot, unity, pygame* |
| 🧰 Verktyg | *cli, tool, script, extension, plugin* |
| 🧪 Experiment | inget annat passade |

Taggarna måste finnas i forumet med exakt de namnen. Taggar som saknas hoppas över.

### Vad som läggs in och inte

| ✅ Läggs in | ❌ Läggs inte in |
|---|---|
| Publika repon | Privata repon (GitHub visar dem inte utan inloggning) |
| Arkiverade repon (som ✅ Klart) | Forks, vid länk till en användare |
| | Repon som redan har ett inlägg |

---

## Kör den på din egen server

Du behöver: en Discord-server där du är admin, ett GitHub-konto och ~15 minuter.

### 1. Skapa boten i Discord

1. Gå till [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**.
2. Fliken **Bot** → **Reset Token** → kopiera token. *Dela den aldrig. Den är botens lösenord.*
3. Slå på **Message Content Intent** på samma sida (annars kan boten inte läsa länkarna).
4. **OAuth2 → URL Generator**: kryssa i `bot`, och under rättigheter:
   *View Channels, Send Messages, Read Message History, Add Reactions,
   Create Public Threads, Send Messages in Threads*.
   Öppna länken som skapas och bjud in boten till din server.

### 2. Förbered servern

1. Skapa en **textkanal** för länkar, t.ex. `#lägg-till-repo`.
2. Skapa en **forumkanal** för projekten, t.ex. `#projekt`, och lägg till taggarna
   från [tabellen ovan](#taggar) (de du vill ha).
3. Slå på **Utvecklarläge** (Användarinställningar → Avancerat). Högerklicka sedan
   på servern och de två kanalerna → **Kopiera ID**.

### 3. Sätt upp GitHub

1. **Forka** det här repot (eller kopiera filerna till ett eget **publikt** repo).
2. I ditt repo: **Settings → Secrets and variables → Actions**
   - Fliken **Secrets** → `DISCORD_TOKEN` = bot-token från steg 1.
   - Fliken **Variables** → `GUILD_ID`, `INBOX_CHANNEL_ID`, `FORUM_CHANNEL_ID` = ID:na från steg 2.
3. Fliken **Actions** → aktivera workflows → **Lägg in repon från Discord** → **Run workflow**.

Klart! Klistra in en länk i din kanal och vänta.

### Inställningar

| Namn | Typ | Beskrivning |
|---|---|---|
| `DISCORD_TOKEN` | secret | Botens token. **Krävs.** |
| `GUILD_ID` | variable | Serverns ID |
| `INBOX_CHANNEL_ID` | variable | Kanalen där länkar klistras in |
| `FORUM_CHANNEL_ID` | variable | Forumet där inläggen skapas |
| `MAX_PER_USER_LINK` | variable | Max antal repon per användarlänk (standard 15) |

Utan variablerna används AI Gruppens ID:n, vilket bara fungerar för den servern.

### Köra lokalt

```bash
export DISCORD_TOKEN=...      # eller lägg token i ~/.config/discord-bot/token
export GUILD_ID=... INBOX_CHANNEL_ID=... FORUM_CHANNEL_ID=...
python3 repo_sync.py
```

Skriver `Inget nytt.` om det inte fanns något att göra.

---

## Vanliga frågor

**Varför tar det upp till 10 minuter?**
GitHub Actions kan som tätast köra var 5:e minut, och schemat är ibland försenat
när GitHub har mycket att göra. Direkta svar kräver en bot som körs dygnet runt på
en server. Det här är gratisvarianten utan underhåll.

**Jobbet har slutat köra?**
GitHub pausar schemalagda workflows i repon som inte haft någon aktivitet på 60
dagar. Gå till **Actions** och klicka **Enable workflow**.

**Kan medlemmar ändra sitt inlägg?**
Inlägget skapas av boten, så medlemmar kan inte redigera första meddelandet eller
taggarna (bara moderatorer kan). Skriv uppdateringar som svar i tråden i stället.

**Läser boten allt i servern?**
Nej. Den läser bara de 50 senaste meddelandena i *en* kanal (länkkanalen) och
skriver bara där och i forumet.

---

## Filer

| Fil | Vad |
|---|---|
| [`repo_sync.py`](repo_sync.py) | Hela logiken, ~220 rader Python utan beroenden |
| [`.github/workflows/repo-sync.yml`](.github/workflows/repo-sync.yml) | Schemat som kör skriptet var 10:e minut |

## Om AI Gruppen

En liten Discord-server där vänner bygger appar och verktyg tillsammans med hjälp av
AI-assistenter som Claude Code och ChatGPT. Claudosaurus håller ordning på
projekten. Namnet är en blandning av *Claude* och *dinosaurus*. 🦖
