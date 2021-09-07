import asyncio

import discord
from discord.ext import commands

from ..classes import ErrorEmbed
from ..util import ban, feedback, support, unban, warns


#checks warns
def check_if_warning_system_setup(ctx):
    if discord.utils.get(ctx.guild.text_channels, topic=warns):
        return True
    else:
        return False

#checks support
def check_if_support_is_setup(ctx):
    if discord.utils.get(ctx.guild.text_channels, topic=support):
        support_channel = True
    else:
        support_channel = False
    return support_channel

#checks ban
def check_if_ban_channel_setup(ctx):
    if discord.utils.get(ctx.guild.text_channels, topic=ban):
        return True
    else:
        return False

#checks unban
def check_if_unban_channel_setup(ctx):
    if discord.utils.get(ctx.guild.text_channels, topic=unban):
        return True
    else:
        return False

#check feedback
def check_if_feedback_system_setup(ctx):
    if discord.utils.get(ctx.guild.text_channels, topic=feedback):
        return True
    else:
        return False

#return warns
def return_warning_channel(ctx = None, guild = None):
    return discord.utils.get(ctx.guild.text_channels if ctx else guild.text_channels, topic=warns)

def return_ban_channel(ctx = None, guild = None):
    return discord.utils.get(ctx.guild.text_channels if ctx else guild.text_channels, topic=ban)

def return_unban_channel(ctx = None, guild = None):
    return discord.utils.get(ctx.guild.text_channels if ctx else guild.text_channels, topic=unban)

def return_feedback_channel(ctx = None, guild = None):
    return discord.utils.get(ctx.guild.text_channels if ctx else guild.text_channels, topic=feedback)

def return_support_channel(ctx = None, guild = None):
    return discord.utils.get(ctx.guild.text_channels if ctx else guild.text_channels, topic=support)



# The permission system of the bot is based on a "just works" basis
# You have permissions and the bot has permissions. If you meet the permissions
# required to execute the command (and the bot does as well) then it goes through
# and you can execute the command.
# Certain permissions signify if the person is a moderator (Manage Server) or an
# admin (Administrator). Having these signify certain bypasses.
# Of course, the owner will always be able to execute commands.

async def check_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(getattr(resolved, name, None) == value for name, value in perms.items())

def has_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_permissions(ctx, perms, check=check)
    return commands.check(pred)

async def check_guild_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    if ctx.guild is None:
        return False

    resolved = ctx.author.guild_permissions
    return check(getattr(resolved, name, None) == value for name, value in perms.items())

def has_guild_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_guild_permissions(ctx, perms, check=check)
    return commands.check(pred)

# These do not take channel overrides into account

def is_mod():
    async def pred(ctx):
        return await check_guild_permissions(ctx, {'manage_guild': True})
    return commands.check(pred)

def is_admin():
    async def pred(ctx):
        return await check_guild_permissions(ctx, {'administrator': True})
    return commands.check(pred)

def mod_or_permissions(**perms):
    perms['manage_guild'] = True
    async def predicate(ctx):
        return await check_guild_permissions(ctx, perms, check=any)
    return commands.check(predicate)

def admin_or_permissions(**perms):
    perms['administrator'] = True
    async def predicate(ctx):
        return await check_guild_permissions(ctx, perms, check=any)
    return commands.check(predicate)

def is_in_guilds(*guild_ids):
    def predicate(ctx):
        guild = ctx.guild
        if guild is None:
            return False
        return guild.id in guild_ids
    return commands.check(predicate)
