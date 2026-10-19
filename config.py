"""Kanal-ID:n för AI-Den. Skapade av admin/ai_den_structure.py."""

GROUPS = {
    'ai': {
        'name': 'AI',
        'chat': ['1561826453824471141', '1561819818259390507'],  # #general (AI), #ideas
        'claudosaurus': '1561819821287547030',
        'repos': '1561819826169839681',
        'weekly': '1561819823279702017',
    },
    'jarri': {
        'name': 'Jarri Workspace',
        'chat': ['1558416178597330944', '1561799039987622063', '1561799041635848259'],  # #general (Jarri), #workspace-core, #modules
        'claudosaurus': '1561799044194631680',
        'repos': '1561819833631375500',
        'weekly': '1561819829709574207',
    },
}

JARRI_CORE = '1561803926867804225'  # #jarri-core: Core Group only, never read or reported

# Repon som aldrig läggs in i listorna, även om någon länkar dem (t.ex. privat/Dalvolt-relaterat)
EXCLUDE = {'Kensj0/doris'}

# Jarri-relaterade repon. Allt annat hamnar i AI:s lista. Forks läggs aldrig in via profil.
JARRI_REPOS = {
    'TorMatzAndren/jarri-workspace-core',
    'TorMatzAndren/ChronoGit',
    'TorMatzAndren/Jarri-Benchmark',
    'TorMatzAndren/jarri-codex-handoff',
    'Kensj0/jarri-workspace-core',
    'Kensj0/kennystuner',
}

# Konton som hela listan byggs från, och hur de visas
ACCOUNTS = ['TorMatzAndren', 'Kensj0']
NAMES = {'TorMatzAndren': 'Dretski', 'Kensj0': 'Sh0ken'}
