import discord
from discord.ext import commands, tasks
from lib import BackupDatabse,ChannelAndMessageId, Arguments
from DiscordUtils import SuccessEmbed
import shlex, argparse, datetime, os
from random import randint


class BackUp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "Create a backup for your server"
        self.cleanup.start()

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\U0001f4be")
    
    @tasks.loop(hours=1, reconnect=True)
    async def cleanup(self):
        '''Cleans the redunadant and useless backups'''
        async for message in (await self.bot.fetch_channel(ChannelAndMessageId.backup_channel.value)).history(limit=None):
            try:
                await commands.GuildConverter().convert(await self.bot.get_context(message), message.content.strip())
            except (commands.CommandError, commands.BadArgument):
                await message.delete()
                continue
    
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True, manage_channels=True, manage_roles=True)
    @commands.cooldown(2, 60, commands.BucketType.guild)
    async def backup(self, ctx: commands.Context, command=None):
        """Backup releated commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
            return
    
    def save_json(self, filename, data):
        """Atomically saves json file"""
        rnd = randint(1000, 9999)
        path, ext = os.path.splitext(filename)
        tmp_file = "{}-{}.tmp".format(path, rnd)
        self._save_json(tmp_file, data)
        try:
            self._read_json(tmp_file)
        except json.decoder.JSONDecodeError:
            self.logger.exception(
                "Attempted to write file {} but JSON "
                "integrity check on tmp file has failed. "
                "The original file is unaltered."
                "".format(filename)
            )
            return False
        os.replace(tmp_file, filename)
        return True

    @backup.command(aliases=["channelbackup"], usage="[channel.mention | channel.id]")
    async def channellogs(self, ctx, *, channel: Optional[commands.TextChannelConverter, discord.TextChannel] = None):
        """
        Creat a backup of all channel data as json files This might take a long time
        `channel` is partial name or ID of the server you want to backup
        defaults to the server the command was run in
        """
        if channel is None:
            channel = ctx.channel
        guild = ctx.guild
        today = datetime.date.today().strftime("%Y-%m-%d")
        total_msgs = 0
        files_saved = 0
        message_list = []
        try:
            async for message in channel.history(limit=None):
                data = {
                    "timestamp": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "tts": message.tts,
                    "author": {
                        "name": message.author.name,
                        "display_name": message.author.display_name,
                        "discriminator": message.author.discriminator,
                        "id": message.author.id,
                        "bot": message.author.bot,
                    },
                    "content": message.content,
                    "channel": {"name": message.channel.name, "id": message.channel.id},
                    "mention_everyone": message.mention_everyone,
                    "mentions": [
                        {
                            "name": user.name,
                            "display_name": user.display_name,
                            "discriminator": user.discriminator,
                            "id": user.id,
                            "bot": user.bot,
                        }
                        for user in message.mentions
                    ],
                    "channel_mentions": [
                        {"name": channel.name, "id": channel.id}
                        for channel in message.channel_mentions
                    ],
                    "role_mentions": [
                        {"name": role.name, "id": role.id} for role in message.role_mentions
                    ],
                    "id": message.id,
                    "pinned": message.pinned,
                }
                message_list.append(data)
                if message.attachments:
                    for a in message.attachments:
                        files_saved += 1
                        fp = "{}/{}/files/{}-{}".format(
                            str(cog_data_path(self)), guild.name, message.id, a.filename
                        )
                        await a.save(fp)
            total_msgs += len(message_list)
            self.save_json(
                "{}/{}/{}-{}.json".format(
                    str(cog_data_path(self)), guild.name, channel.name, today
                ),
                message_list,
            )
        except discord.Forbidden:
            return
        await channel.send("{} messages saved from {}".format(total_msgs, channel.name))

    @backup.command(aliases=["serverbackup"])
    async def serverlogs(self, ctx):
        """
        Creat a backup of all server data as json files This might take a long time
        """
        guild = ctx.guild
        today = datetime.date.today().strftime("%Y-%m-%d")
        channel = ctx.message.channel
        total_msgs = 0
        files_saved = 0
        for chn in guild.channels:
            # await channel.send("backing up {}".format(chn.name))
            message_list = []
            try:
                async for message in chn.history(limit=None):
                    data = {
                        "timestamp": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "tts": message.tts,
                        "author": {
                            "name": message.author.name,
                            "display_name": message.author.display_name,
                            "discriminator": message.author.discriminator,
                            "id": message.author.id,
                            "bot": message.author.bot,
                        },
                        "content": message.content,
                        "channel": {"name": message.channel.name, "id": message.channel.id},
                        "mention_everyone": message.mention_everyone,
                        "mentions": [
                            {
                                "name": user.name,
                                "display_name": user.display_name,
                                "discriminator": user.discriminator,
                                "id": user.id,
                                "bot": user.bot,
                            }
                            for user in message.mentions
                        ],
                        "channel_mentions": [
                            {"name": channel.name, "id": channel.id}
                            for channel in message.channel_mentions
                        ],
                        "role_mentions": [
                            {"name": role.name, "id": role.id} for role in message.role_mentions
                        ],
                        "id": message.id,
                        "pinned": message.pinned,
                    }
                    message_list.append(data)
                    if message.attachments:
                        for a in message.attachments:
                            files_saved += 1
                            fp = "{}/{}/files/{}-{}".format(
                                str(cog_data_path(self)), guild.name, message.id, a.filename
                            )
                            await a.save(fp)
                total_msgs += len(message_list)
                if len(message_list) == 0:
                    continue
                self.save_json(
                    "{}/{}/{}-{}.json".format(
                        str(cog_data_path(self)), guild.name, chn.name, today
                    ),
                    message_list,
                )
                await channel.send("{} messages saved from {}".format(len(message_list), chn.name))
            except discord.errors.Forbidden:
                await channel.send("0 messages saved from {}".format(chn.name))
                pass
            except AttributeError:
                await channel.send("0 messages saved from {}".format(chn.name))
                pass
        await channel.send("{} messages saved from {}".format(total_msgs, guild.name))


    @backup.command(description="Create backup of the server")
    async def template(self, ctx):
        """
        Create a backup of this guild, (it backups only those channels which is visible to the bot)
        And then dm you the backup code, (Phew keep it safe)
        """
        if not await ctx.prompt(
                "Are you sure that you want to **create a backup** of this guild?",
                author_id=ctx.author.id,
        ):
            return
        backup_code = await BackupDatabse(ctx).create_backup()
        backup_code_reference = await ctx.author.send(
            f":arrow_right:  **BACKUP CODE** : ``{backup_code}``")
        await ctx.send(
            content=f"{ctx.author.mention} check your dm(s) :white_check_mark:",
            embed=SuccessEmbed(
                title="The backup code was generated successfully",
                url=backup_code_reference.jump_url,
            ),
        )

    @backup.command()
    async def get(self, ctx: commands.Context, code: int):
        """Gets the json file which is stored as a backup"""
        backup_code_data_url = await BackupDatabse(ctx).get_backup_data(code)
        if backup_code_data_url is not None:
            await ctx.send(
                content=f"The data for the ``{code}``\n{backup_code_data_url}"
            )
            return
        await ctx.send(
            f"Hey {ctx.author.mention}, \n there is no data associated with **{code}** backup code!"
        )
    
    @backup.command()
    async def delete(self, ctx: commands.Context, *,args):
        """Deletes the backup data if it is there in the database.
        This command has a powerful "command line" syntax. To use this command
        you and the bot must both have Manage Server permission. **-all option is optional.**
        The following options are valid.
        `--id` or `-id`: Array of backup id to delete.
        `--all` or `-all`: To delete all backup(s) of the guild.
        """
        parser = Arguments(add_help=False, allow_abbrev=False)
        parser.add_argument("--id", "-id", action="append_const",const=int)
        parser.add_argument("--all", "-all", action="store_true")
        try:
            args = parser.parse_args(shlex.split(args))
        except Exception as e:
            return await ctx.send(str(e))
        if args.id:
            if len(args.id) <= 0:
                await ctx.send('No Backup Id\'s provided')
                return
            await ctx.send("If any backup(s) with those id exists then it will deleted.")
            for i in args.id:
                await BackupDatabse(ctx).delete_backup_data(int(i))
            return
        if args.all:
            await ctx.send("If any backup(s) of the guild exists then it will be deleted.")
            async for message in (await self.bot.fetch_channel(ChannelAndMessageId.backup_channel.value)).history(limit=None):
                if int(message.content.strip()) == ctx.guild.id:
                    await message.delete()
            return
            
        await ctx.send('No arguments were provided')


def setup(bot):
    bot.add_cog(BackUp(bot))
