import discord
import urllib.parse
import json
import re
from pprint import pprint
from discord.ext import commands
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType

import neffyWiki

client = commands.Bot(command_prefix="!")

buttonClickHandlers = {}

command, info = neffyWiki.setup(client)
buttonClickHandlers[command] = info

@client.event
async def on_ready():
    DiscordComponents(client)
    print(f'Logged in as {client.user}')

@client.command()
async def glossary(ctx, *args):
    await ctx.send('<https://glossary.infil.net/?t=' + urllib.parse.quote(' '.join(args)) + '>')

@client.event
async def on_button_click(res):

    try:
        args = json.loads(res.component.id)
    except ValueError as e:
        await invalidButtonCommand(res)
        return
    buttonCommand = args.pop(0)
    version = args.pop(0)

    if buttonCommand in buttonClickHandlers:

        buttonVersion = buttonClickHandlers[buttonCommand]['version']
        buttonHandler = buttonClickHandlers[buttonCommand]['buttonClickHandler']

        if version == buttonVersion:
            await buttonHandler(res, args)
        else:
            await invalidButtonCommand(res)
    else:
        await invalidButtonCommand(res)

async def invalidButtonCommand(res):
    await res.respond(type=InteractionType.ChannelMessageWithSource, content="Error: Invalid input (Most likely the bot has been updated since the button you clicked was made")

client.run('<token>')