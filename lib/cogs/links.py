from typing import Optional

from discord.ext.commands import Cog, command, cooldown, BucketType
from discord.utils import get

from discord_slash.utils.manage_commands import create_option
from discord_slash import cog_ext, SlashContext

from ..db import db  # pylint: disable=relative-beyond-top-level

import requests
import json

import os
from dotenv import load_dotenv

load_dotenv()

with open("config.json") as config_file:
    config = json.load(config_file)


class Links(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("links")

    async def shorten_link_func(self, ctx, url: str, vanity: Optional[str]):
        ShortLinkAmount = db.records(
            "SELECT ShortLinkAmount FROM users WHERE UserID = ?", ctx.author.id
        )

        homeGuild = self.bot.get_guild(config["homeGuild_id"])  # Support Server ID.
        patreonRole = get(
            homeGuild.roles, id=config["patreonRole_id"]
        )  # Patreon role ID.

        member = []

        # Checks if user is a Patron
        for pledger in homeGuild.members:
            if pledger == ctx.author:
                member = pledger

        if ctx.author in homeGuild.members:
            if patreonRole in member.roles:
                if ShortLinkAmount[0][0] >= 12:
                    await ctx.send("You have too many short links! (12)")
                else:
                    await self.after_check_shorten_link_func(ctx, url, vanity)
            else:
                if ShortLinkAmount[0][0] >= 6:
                    await ctx.send("You have too many short links! (6)")

        else:
            if ShortLinkAmount[0][0] >= 6:
                await ctx.send("You have too many short links! (6)")
            else:
                await self.after_check_shorten_link_func(ctx, url, vanity)

    async def after_check_shorten_link_func(self, ctx, url: str, vanity: Optional[str]):
        ShortLinkAmount = db.records(
            "SELECT ShortLinkAmount FROM users WHERE UserID = ?", ctx.author.id
        )
        try:
            homeGuild = self.bot.get_guild(config["homeGuild_id"])  # Support Server ID.
            patreonRole = get(
                homeGuild.roles, id=config["patreonRole_id"]
            )  # Patreon role ID.

            member = []

            # Checks if user is a Patron
            for pledger in homeGuild.members:
                if pledger == ctx.author:
                    member = pledger

            # If patron, give them access to vanity
            if ctx.author in homeGuild.members:
                if patreonRole in member.roles:
                    linkRequest = {
                        "destination": url,
                        "domain": {"fullName": "doob.link"},
                        "slashtag": vanity,
                    }
                else:
                    linkRequest = {
                        "destination": url,
                        "domain": {"fullName": "doob.link"},
                    }
            # If not, don't.
            else:
                linkRequest = {
                    "destination": url,
                    "domain": {"fullName": "doob.link"},
                }

            requestHeaders = {
                "Content-type": "application/json",
                "apikey": os.environ.get("rebrandly"),
                "workspace": os.environ.get("rebrandly_workspace"),
            }

            r = requests.post(
                "https://api.rebrandly.com/v1/links",
                data=json.dumps(linkRequest),
                headers=requestHeaders,
            )

            if r.status_code == requests.codes.ok:
                link = r.json()
                shortUrl = link["shortUrl"]
                await ctx.send(f"Boom! Shortened: :link: <https://{shortUrl}>")

                db.execute(
                    "UPDATE users SET (ShortLinkAmount) = (?) WHERE UserID = ?",
                    ShortLinkAmount[0][0] + 1,
                    ctx.author.id,
                )
                db.commit()

            elif r.status_code == 403:
                await ctx.send(
                    "Seems like your vanity URL is already being used, try again!"
                )
            else:
                await ctx.send(f"Rebrandly API sent an error :/ ({r.status_code})")

        except UnboundLocalError:
            await ctx.send(
                "You aren't a Patron! You can't use vanities.\nSubscribe to get access ;) <https://patreon.com/doobdev>"
            )

    @command(
        name="link", aliases=["shortenlink"], brief="Shorten a link using doob.link!"
    )
    @cooldown(1, 10, BucketType.user)
    async def shorten_link_command(self, ctx, url: str, vanity: Optional[str]):
        """Vanity URLs are only available to [Patrons](https://patreon.com/doobdev)"""
        await self.shorten_link_func(ctx, url, vanity)

    @cog_ext.cog_slash(
        name="link",
        description="[Patreon Only, for now] Shorten a link using doob.link!",
        options=[
            create_option(
                name="url",
                description="Link you would like to shorten.",
                option_type=3,
                required=True,
            ),
            create_option(
                name="vanity",
                description="[Patreon Only] Vanity link for your short URL",
                option_type=3,
                required=True,
            ),
        ],
    )
    async def shorten_link_slash(self, SlashContext, url: str, vanity: str):
        ctx = SlashContext
        await self.shorten_link_func(ctx, url, vanity)


def setup(bot):
    bot.add_cog(Links(bot))
