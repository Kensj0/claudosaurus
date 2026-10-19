# Claudosaurus 🦖

**Discord-bot för servern AI-Den.** Den håller listor över medlemmarnas GitHub-repon och skriver veckorapporter för två grupper: AI och Jarri Workspace.

Namnet är en blandning av *Claude* och *dinosaurus*. 🦖

---

## Grupperna

Servern har två kategorier. Varje grupp har samma tre bot-kanaler:

| Kanal | Vad |
|---|---|
| `#claudosaurus` | Skriv här till boten (se nedan). Samarbetare och Kärngruppen. |
| `#repos` | Listan över konton och repon. Boten skriver, människor läser. |
| `#weekly-report` | Veckorapporten. Boten skriver, människor läser. |

**AI:** `#general`, `#ideas` och `Hangout`. Rapporten bygger på repona i AI:s lista och på chatten i `#general` och `#ideas`.

**Jarri Workspace:** `#workspace-core` och `#modules`. Rapporten bygger på repona i Jarris lista och på chatten i de två kanalerna. `#jarri-core` läses aldrig av boten.

---

## Så använder du Claudosaurus

Skriv i gruppens `#claudosaurus`. Boten sätter ✅ när den har tagit emot det.

- **Profil** (`github.com/namn`): kontot läggs in i `#repos` med alla sina publika repon, utan forks.
- **Repo** (`github.com/namn/repo`): bara det repot läggs in under kontot.
- **Anteckning** (vad som helst utan länk): kommer med under "📝 From the team" i nästa veckorapport.

Varje konto får ett eget inlägg i `#repos`, och det uppdateras när nya repon läggs till:

> **Sh0ken** · [github.com/Kensj0](<https://github.com/Kensj0>)
> -# **jarri-workspace-core**: Reusable cognitive workspace substrate for …
> -# **kennystuner**: A free, offline-capable instrument tuner that …

Varje repo visas med en kort beskrivning från GitHub (eller första raden i README). Kontot tillhör den som länkade först.

Om något inte går att läsa (privat repo, fel länk) får meddelandet ⚠️.

---

## Hur det körs

| Workflow | När | Gör |
|---|---|---|
| **Repo-listor** (`directory-sync.yml`) | var 30:e minut | Läser länkarna i de två `#claudosaurus` och uppdaterar `#repos` |
| **Veckosammanfattning** (`weekly-summary.yml`) | måndagar 06:00 UTC, båda grupperna | Postar i respektive `#weekly-report` |

- Inget sparas i en databas. Boten ser vad som är gjort via ✅ och sina egna inlägg.
- Om hemligheten `ANTHROPIC_API_KEY` finns görs en kort AI-sammanfattning av veckan. Utan den postas bara siffrorna.
- Undantag: `EXCLUDE` i `config.py` (just nu `Kensj0/doris`) läggs aldrig in i en lista.

Testa utan att posta:

```bash
python3 directory_sync.py --dry-run
python3 weekly_summary.py --group jarri --dry-run
python3 weekly_summary.py --group ai --dry-run
```

---

## Filer

| Fil | Vad |
|---|---|
| [`config.py`](config.py) | Kanal-ID:n för de två grupperna, och undantagslistan |
| [`directory_sync.py`](directory_sync.py) | Läser länkar och uppdaterar `#repos` |
| [`weekly_summary.py`](weekly_summary.py) | Veckorapporten per grupp (`--group ai` eller `jarri`) |
| [`repo_sync.py`](repo_sync.py) | Hjälpfunktioner för Discord, GitHub och HTTP |
| [`.github/workflows/`](.github/workflows) | De två schemalagda workflowsen |

## Licens

[MIT](LICENSE): fritt att använda, ändra och dela, så länge licenstexten följer med.
