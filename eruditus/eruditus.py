import traceback
import logging
import sys
import os

import discord
from discord import Guild
from discord.ext import commands
from discord.ext.commands import Bot

from discord_slash import SlashCommand, SlashContext

import aiohttp
import pymongo

from lib.util import setup_database, setup_logger

from config import (
    MONGODB_URI,
    DBNAME_PREFIX,
    CONFIG_COLLECTION,
)

# Setup logging
logger = setup_logger(logging.INFO)

# MongoDB handle
mongo = pymongo.MongoClient(MONGODB_URI)

# Setup bot
bot = Bot(command_prefix="!", description="Eruditus - CTF helper bot")
slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True)


@bot.event
async def on_ready() -> None:
    for guild in bot.guilds:
        # Setup guild database if it wasn't already
        if not mongo[f"{DBNAME_PREFIX}-{guild.id}"][CONFIG_COLLECTION].find_one():
            await setup_database(mongo, guild)
        logger.info(f"{bot.user} connected to {guild}")
    await bot.change_presence(activity=discord.Game(name="/help"))


@bot.event
async def on_guild_join(guild: Guild) -> None:
    """Set up a database for the newly joined guild."""
    await setup_database(mongo, guild)
    logger.info(f"{bot.user} joined {guild}!")


@bot.event
async def on_guild_remove(guild: Guild) -> None:
    """Delete the database for the guild we just left."""
    mongo.drop_database(f"{DBNAME_PREFIX}-{guild.id}")
    logger.info(f"{bot.user} left {guild}.")


@bot.event
async def on_slash_command_error(ctx: SlashContext, err: Exception) -> None:
    """Handle exceptions."""
    if isinstance(err, commands.errors.CommandNotFound):
        pass
    elif isinstance(err, discord.errors.NotFound):
        pass
    elif isinstance(err, discord.errors.Forbidden):
        await ctx.send("Forbidden.")
    elif isinstance(err, commands.errors.MissingPermissions):
        await ctx.send("Permission denied.")
    elif isinstance(err, commands.errors.BotMissingPermissions):
        await ctx.send("I don't have enough privileges to perform this action :(")
    elif isinstance(err, commands.errors.NoPrivateMessage):
        await ctx.send("This command can't be used in DM.")
    elif isinstance(err, aiohttp.ClientError):
        await ctx.send("HTTP Client error.")
    else:
        await ctx.send("❌ An error has occured")
        traceback.print_exception(type(err), err, err.__traceback__, file=sys.stderr)


if __name__ == "__main__":
    for task in os.listdir("tasks"):
        task = task.strip(".py")
        bot.load_extension(f"tasks.{task}")
        logger.info(f"Loaded task: {task}")
    for ext in os.listdir("cogs"):
        bot.load_extension(f"cogs.{ext}.{ext}")
        logger.info(f"Loaded extension: {ext}")

    bot.run(os.getenv("DISCORD_TOKEN"))
