from __future__ import annotations

import asyncio
import io
import random
from typing import (TYPE_CHECKING, Any, Callable, Generator, Iterable,
                    Optional, TypeVar, Union)

import discord
import TenGiphPy
from discord.ext import commands

from ..classes.converter import MemberID
from .vars import ChannelAndMessageId, Tokens

T = TypeVar('T')


if TYPE_CHECKING:
    from minato_namikaze import MinatoNamikazeBot
    from aiohttp import ClientSession
    from asyncpg import Pool, Connection

class _ContextDBAcquire:
    __slots__ = ('ctx', 'timeout')

    def __init__(self, ctx: Context, timeout: Optional[float]):
        self.ctx: Context = ctx
        self.timeout: Optional[float] = timeout

    def __await__(self) -> Generator[Any, None, Connection]:
        return self.ctx._acquire(self.timeout).__await__()

    async def __aenter__(self) -> Union[Pool, Connection]:
        await self.ctx._acquire(self.timeout)
        return self.ctx.db

    async def __aexit__(self, *args) -> None:
        await self.ctx.release()


class ConfirmationView(discord.ui.View):

    def __init__(self, *, timeout: float, author_id: int, ctx: Context,
                 delete_after: bool) -> None:
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.delete_after: bool = delete_after
        self.author_id: int = author_id
        self.ctx: Context = ctx
        self.message: Optional[discord.Message] = None

    async def interaction_check(self,
                                interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        else:
            await interaction.response.send_message(
                "This confirmation dialog is not for you.", ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        if self.delete_after and self.message:
            await self.message.delete()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button,
                      interaction: discord.Interaction):
        self.value = True
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_message()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button,
                     interaction: discord.Interaction):
        self.value = False
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_message()
        self.stop()


class Context(commands.Context):
    channel: Union[discord.VoiceChannel, discord.TextChannel, discord.Thread, discord.DMChannel]
    prefix: str
    command: commands.Command[Any, ..., Any]
    bot: MinatoNamikazeBot

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = self.bot.pool
        self._db: Optional[Union[Pool, Connection]] = None

    async def entry_to_code(self, entries):
        width = max(len(a) for a, b in entries)
        output = ["```"]
        for name, entry in entries:
            output.append(f"{name:<{width}}: {entry}")
        output.append("```")
        await self.send("\n".join(output))

    async def indented_entry_to_code(self, entries):
        width = max(len(a) for a, b in entries)
        output = ["```"]
        for name, entry in entries:
            output.append(f"\u200b{name:>{width}}: {entry}")
        output.append("```")
        await self.send("\n".join(output))

    def __repr__(self):
        # we need this for our cache key strategy
        return "<Context>"

    @property
    def session(self):
        return self.bot.session

    @discord.utils.cached_property
    def replied_reference(self):
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    async def disambiguate(self, matches: list[T], entry: Callable[[T], Any]) -> T:
        if len(matches) == 0:
            raise ValueError('No results found.')

        if len(matches) == 1:
            return matches[0]

        await self.send('There are too many matches... Which one did you mean? **Only say the number**.')
        await self.send('\n'.join(f'{index}: {entry(item)}' for index, item in enumerate(matches, 1)))

        def check(m):
            return m.content.isdigit() and m.author.id == self.author.id and m.channel.id == self.channel.id

        await self.release()

        # only give them 3 tries.
        try:
            for i in range(3):
                try:
                    message = await self.bot.wait_for('message', check=check, timeout=30.0)
                except asyncio.TimeoutError:
                    raise ValueError('Took too long. Goodbye.')

                index = int(message.content)
                try:
                    return matches[index - 1]
                except:
                    await self.send(f'Please give me a valid number. {2 - i} tries remaining...')

            raise ValueError('Too many tries. Goodbye.')
        finally:
            await self.acquire()
            pass

    async def prompt(
        self,
        message: str,
        *,
        timeout: float = 60.0,
        delete_after: bool = True,
        reacquire: bool = True,
        author_id: Optional[int] = None,
    ) -> Optional[bool]:
        """An interactive reaction confirmation dialog.
        Parameters
        -----------
        message: str
            The message to show along with the prompt.
        timeout: float
            How long to wait before returning.
        delete_after: bool
            Whether to delete the confirmation message after we're done.
        reacquire: bool
            Whether to release the database connection and then acquire it
            again when we're done.
        author_id: Optional[int]
            The member who should respond to the prompt. Defaults to the author of the
            Context's message.
        Returns
        --------
        Optional[bool]
            ``True`` if explicit confirm,
            ``False`` if explicit deny,
            ``None`` if deny due to timeout
        """

        author_id = author_id or self.author.id
        view = ConfirmationView(
            timeout=timeout,
            delete_after=delete_after,
            ctx=self,
            reacquire=reacquire,
            author_id=author_id,
        )
        view.message = await self.send(message, view=view)
        await view.wait()
        return view.value

    @property
    def db(self) -> Union[Pool, Connection]:
        return self._db if self._db else self.pool

    async def _acquire(self, timeout: Optional[float]) -> Connection:
        if self._db is None:
            self._db = await self.pool.acquire(timeout=timeout)
        return self._db

    def acquire(self, *, timeout=300.0) -> _ContextDBAcquire:
        """Acquires a database connection from the pool. e.g. ::
            async with ctx.acquire():
                await ctx.db.execute(...)
        or: ::
            await ctx.acquire()
            try:
                await ctx.db.execute(...)
            finally:
                await ctx.release()
        """
        return _ContextDBAcquire(self, timeout)

    async def release(self) -> None:
        """Releases the database connection from the pool.
        Useful if needed for "long" interactive commands where
        we want to release the connection and re-acquire later.
        Otherwise, this is called automatically by the bot.
        """
        # from source digging asyncpg source, releasing an already
        # released connection does nothing

        if self._db is not None:
            await self.bot.pool.release(self._db)
            self._db = None

    async def show_help(self, command=None):
        """Shows the help command for the specified command if given.
        If no command is given, then it'll show help for the current
        command.
        """
        cmd = self.bot.get_command("help")
        command = command or self.command.qualified_name
        await self.invoke(cmd, command=command)

    async def safe_send(self, content, *, escape_mentions=True, **kwargs):
        """Same as send except with some safe guards.
        1) If the message is too long then it sends a file with the results instead.
        2) If ``escape_mentions`` is ``True`` then it escapes mentions.
        """
        if escape_mentions:
            content = discord.utils.escape_mentions(content)

        if len(content) > 2000:
            fp = io.BytesIO(content.encode())
            kwargs.pop("file", None)
            return await self.send(file=discord.File(
                fp, filename="message_too_long.txt"),
                **kwargs)
        else:
            return await self.send(content)

    def get_user(self, user: Union[int, discord.Member, MemberID]):
        if isinstance(user, (int, MemberID)):
            user = self.bot.get_user(user)
        return user

    async def get_dm(self, user: Union[int, discord.Member, MemberID]):
        try:
            if isinstance(user, (int, MemberID)):
                user = self.bot.get_or_fetch_member(user, self.guild)
            else:
                user = self.bot.get_or_fetch_member(user.id, self.guild)
        except:
            if isinstance(user, (int, MemberID)):
                user = self.bot.get_user(user)
        return user.dm_channel if user.dm_channel else await user.create_dm()

    def get_roles(self, role: Union[int, discord.Role]):
        if isinstance(role, int):
            role = discord.utils.get(self.guild.roles, id=role)
        return role

    def get_emoji(self, emoji: Union[int, discord.Emoji,
                                     discord.PartialEmoji]):
        if isinstance(emoji, int):
            emoji = discord.utils.get(self.guild.emojis, id=emoji)
        return emoji

    def get_guild(self, guild: Union[int, discord.Guild,
                                     discord.PartialInviteGuild]):
        if isinstance(guild, int):
            guild = self.bot.get_guild(guild)
        return guild

    def get_config_emoji_by_name_or_id(self, emoji: Union[int, str]):
        if isinstance(emoji, str):
            guild1 = self.get_guild(ChannelAndMessageId.server_id.value)
            emoji_model = discord.utils.get(guild1.emojis, name=emoji)
            if not emoji:
                guild2 = self.get_guild(ChannelAndMessageId.server_id2.value)
                emoji_model = discord.utils.get(guild2.emojis, name=emoji)
            return emoji_model
        else:
            return self.bot.get_emoji(emoji)

    def get_config_channel_by_name_or_id(self, channel: Union[int, str]):
        if isinstance(channel, str):
            guild1 = self.get_guild(ChannelAndMessageId.server_id.value)
            channel_model = discord.utils.get(guild1.text_channels,
                                              name=channel)
            if not channel:
                guild2 = self.get_guild(ChannelAndMessageId.server_id2.value)
                channel_model = discord.utils.get(guild2.text_channels,
                                                  name=channel)
            return channel_model
        else:
            return self.bot.get_channel(channel)

    @staticmethod
    def get_random_image_from_tag(tag_name: str) -> Optional[str]:
        tenor_giphy = ["tenor", "giphy"]
        if random.choice(tenor_giphy) == "tenor":
            api_model = TenGiphPy.Tenor(token=Tokens.tenor.value)
            try:
                return api_model.random(str(tag_name.lower()))
            except:
                return
        api_model = TenGiphPy.Giphy(token=Tokens.giphy.value)
        try:
            return api_model.random(str(
                tag_name.lower()))["data"]["images"]["downsized_large"]["url"]
        except:
            return

    @staticmethod
    async def get_random_image_from_tag(tag_name: str) -> Optional[str]:
        tenor_giphy = ["tenor", "giphy"]
        if random.choice(tenor_giphy) == "tenor":
            api_model = TenGiphPy.Tenor(token=Tokens.tenor.value)
            try:
                return await api_model.arandom(str(tag_name.lower()))
            except:
                return
        api_model = TenGiphPy.Giphy(token=Tokens.giphy.value)
        try:
            return (await api_model.arandom(
                tag=str(tag_name.lower())
            ))["data"]["images"]["downsized_large"]["url"]
        except:
            return

    @staticmethod
    def tenor(tag_name: str) -> Optional[str]:
        api_model = TenGiphPy.Tenor(token=Tokens.tenor.value)
        try:
            return api_model.random(str(tag_name.lower()))
        except:
            return

    @staticmethod
    def giphy(tag_name: str) -> Optional[str]:
        api_model = TenGiphPy.Giphy(token=Tokens.giphy.value)
        try:
            return api_model.random(str(
                tag_name.lower()))["data"]["images"]["downsized_large"]["url"]
        except:
            return

    @staticmethod
    async def tenor(tag_name: str) -> Optional[str]:
        api_model = TenGiphPy.Tenor(token=Tokens.tenor.value)
        try:
            return await api_model.arandom(str(tag_name.lower()))
        except:
            return

    @staticmethod
    async def giphy(tag_name: str) -> Optional[str]:
        api_model = TenGiphPy.Giphy(token=Tokens.giphy.value)
        try:
            return (await api_model.arandom(
                tag=str(tag_name.lower())
            ))["data"]["images"]["downsized_large"]["url"]
        except:
            return
    
class GuildContext(Context):
    author: discord.Member
    guild: discord.Guild
    channel: Union[discord.VoiceChannel, discord.TextChannel, discord.Thread]
    me: discord.Member
    prefix: str

