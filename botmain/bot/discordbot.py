import os
import time
from os.path import join
from pathlib import Path

import aiozaneapi
import async_cleverbot as ac
import discord
import mystbin
from asyncdagpi import Client
from discord.ext import commands
from discord.ext.buttons import Paginator
from os.path import join

from help import Help

class Page(Paginator):
    async def teardown(self):
        try:
            await self.page.clear_reactions()
        except discord.HTTPException:
            pass
intents = discord.Intents.all()
intents.members = True
intents.reactions = True
intents.guilds = True

TOKEN = 'Nzc5NTU5ODIxMTYyMzE1Nzg3.X7iTqA.PEmxShgoueoJgaE6BvQatCCT4XM'
topastoken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3OTU1OTgyMTE2MjMxNTc4NyIsImJvdCI6dHJ1ZSwiaWF0IjoxNjEyODcxOTczfQ.dtqLmmqI5Ktp3xxaNyj-G-zat071kveqrraKQJFBKkk'

bot = commands.Bot(command_prefix=commands.when_mentioned_or(')'), intents=intents, help_command=Help(),  allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),case_insensitive=True,description="Hi I am **Minato Namikaze**, Yondaime Hokage")
bot.mystbin_client = mystbin.Client()
bot.version = "1"
hce = bot.get_command("help")
hce.hidden = True
chatbottoken = open("chat.txt", "a+").read()
bot.topken = f"{topastoken}"
bot.chatbot = ac.Cleverbot(f"{chatbottoken}")
bot.se = aiozaneapi.Client('MTE=.89SNKEEIaYvNsGhO0g0UMs0tIEarF7q9SmPgyR73jwT2ne23')
bot.dagpi = Client('slKkwVI9wgMORv8ytee3nwRKzx9rPvLoK53F2JwLw9TU0VI4naEZ0RFuZPqFeOyY')
bot.start_time = time.time()
bot.thresholds = (10, 25, 50, 100)
bot.DEFAULT_GIF_LIST_PATH = Path(__file__).resolve(strict=True).parent / join('discord_bot_images')


# Events
@bot.event
async def on_ready():
    for filename in os.listdir(Path(__file__).resolve(strict=True).parent / join('cogs')):
        if filename.endswith('.py'):
            bot.load_extension(f'cogs.{filename[:-3]}')
    await bot.change_presence(activity=discord.Streaming(name="Naruto", url="https://gogoanime.so/naruto-episode-31"))
    print('My Ready is Body')

#on join send message event
@bot.event
async def on_guild_join(guild):
    await guild.system_channel.send(f'Hello ** {guild.name}**! I am **Dhruva Shaw bot**!!! do **) help** or **{bot.user.mention} help** for commands!')



@bot.listen()
async def on_message(message):
    if message.author.bot or message.author == bot.user:
        return
    if "fuck" in message.content.lower():
        await message.channel.send(f'Fuck off!!! <@{message.author.id}>')
        await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    guild = ctx.guild
    if isinstance(error, commands.CommandOnCooldown):
        e1 = discord.Embed(title="Command Error!", description=f"`{error}`")
        e1.set_footer(text=f"{ctx.author.name}")
        await ctx.channel.send(embed=e1)
    elif isinstance(error, commands.CommandNotFound):
        e2 = discord.Embed(title="Command Error!", description=f"`{error}`")
        e2.set_footer(text=f"{ctx.author.name}")
        await ctx.channel.send(embed=e2)
    elif isinstance(error, commands.MissingPermissions):
        e3 = discord.Embed(title="Command Error!", description=f"`{error}`")
        e3.set_footer(text=f"{ctx.author.name}")
        await ctx.channel.send(embed=e3)
    elif isinstance(error, commands.MissingRequiredArgument):
        e4 = discord.Embed(title="Command Error!", description=f"`{error}`")
        e4.set_footer(text=f"{ctx.author.name}")
        await ctx.channel.send(embed=e4)
    elif isinstance(error, commands.CommandInvokeError):
        haha = ctx.author.avatar_url
        e7 = discord.Embed(title="Oh no green you fucked up", description=f"`{error}`")
        e7.add_field(name="Command Caused By?", value=f"{ctx.command}")
        e7.add_field(name="By?", value=f"ID : {ctx.author.id}, Name : {ctx.author.name}")
        e7.set_thumbnail(url=f"{haha}")
        e7.set_footer(text=f"{ctx.author.name}")
        await ctx.channel.send(embed=e7)
    else:
        haaha = ctx.author.avatar_url
        e9 = discord.Embed(title="Oh no green you fucked up", description=f"`{error}`")
        e9.add_field(name="Command Caused By?", value=f"{ctx.command}")
        e9.add_field(name="By?", value=f"ID : {ctx.author.id}, Name : {ctx.author.name}")
        e9.set_thumbnail(url=f"{haaha}")
        e9.set_footer(text=f"{ctx.author.name}")
        await ctx.channel.send(embed=e9)

bot.run(TOKEN)
