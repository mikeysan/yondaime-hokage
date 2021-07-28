import os
from pathlib import Path
from typing import List

import dotenv

with open(os.path.join(Path(__file__).resolve().parent.parent, 'text', 'insult.txt')) as f:
    insults: List[str] = list(map(lambda a: a.strip(' ').strip(
        '\n').strip('\'').strip('"').strip('\\'), f.read().split(',')))

dotenv_file = Path(__file__).resolve(
).parent.parent.parent.parent.parent.parent / ".env"


def token_get(tokenname):
    if os.path.isfile(dotenv_file):
        dotenv.load_dotenv(dotenv_file)
    return os.environ.get(tokenname, 'False').strip('\n')


website = token_get('WEBSITE')
github = token_get('GITHUB')

statcord = token_get('STATCORD')
dagpi = token_get('DAGPI')

dblst = token_get('DISCORDBOTLIST')
discordbotsgg = token_get('DISCORDBOTSGG')
topken = token_get('TOPGG')
bfd = token_get('BOTSFORDISCORD')
botlist = token_get('BOTLISTSPACE')  # discordlistspace
discordboats = token_get('DISCORDBOATS')
voidbot = token_get('VOIDBOT')
fateslist = token_get('FATESLIST')
bladebot = token_get('BLADEBOT')
spacebot = token_get('SPACEBOT')
discordlabs = token_get('DISCORDLABS')

version = token_get('VERSION')

chatbot = token_get('CHATBOTTOKEN')


warns = 'Warning of the server members will be logged here.'
support = 'This channel will be used as a support channel for this server.'
ban = 'This channel will be used to log the server bans.'
unban = 'Unbans of the server will be logged here.'
feedback = 'This channel will be used to log the feedbacks given by members.'
