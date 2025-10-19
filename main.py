from dotenv import load_dotenv
import os
import time
import asyncio
import aiohttp
import discord
from discord.ext import commands

# ====== CONFIG / ENV ======
load_dotenv()
TOKEN = os.getenv("TOKEN")
LUMI_WEBHOOK = os.getenv("LUMI_WEBHOOK")          # optional: external events
WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID")  # optional: numeric string

# ====== DISCORD INTENTS ======
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
start_time = time.time()

# ====== UTIL: LUMI WEBHOOK POST (optional) ======
async def lumi_post(event_type: str, data: dict):
    if not LUMI_WEBHOOK:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(LUMI_WEBHOOK, json={"event": event_type, "data": data})
    except Exception as e:
        print(f"[LUMI] Post failed: {e}")

# ====== ON READY ======
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Tending the LUMI Realm"))
    print(f"👻 Ghost_Bot online as {bot.user}")
    await lumi_post("bot_ready", {"bot": str(bot.user)})

# ====== BASIC / FUN ======
@bot.command(help="Check bot is alive.")
async def ping(ctx):
    await ctx.send("👻 Boo! Ghost_Bot is awake and listening across the LUMI network.")

@bot.command(help="Feed the Orb (LUMI flavor).")
async def feed(ctx):
    await ctx.send("✨ You feed the Orb. Faint pulses of light ripple through the LUMI realm...")

@bot.command(help="Dream portal (LUMI flavor).")
async def dream(ctx):
    await ctx.send("💤 You drift into the dream portal — whispers of creation surround you.")

@bot.command(help="Show bot uptime.")
async def uptime(ctx):
    secs = int(time.time() - start_time)
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    pretty = f"{d}d {h}h {m}m {s}s"
    await ctx.send(f"⏱️ Uptime: **{pretty}**")

# ====== SERVER INFO ======
@bot.command(help="Quick server info.")
async def server(ctx):
    g = ctx.guild
    await ctx.send(
        f"🏰 **{g.name}** — Members: **{g.member_count}** | Roles: **{len(g.roles)-1}** | Channels: **{len(g.channels)}**"
    )

# ====== MODERATION (popular essentials) ======
def mod_or_admin():
    return commands.has_permissions(manage_messages=True)

@bot.command(help="Delete the last N messages. (Mod only)")
@mod_or_admin()
async def purge(ctx, count: int):
    count = max(1, min(count, 200))
    await ctx.channel.purge(limit=count + 1)
    m = await ctx.send(f"🧹 Purged **{count}** messages.")
    await asyncio.sleep(3)
    await m.delete()

@bot.command(help="Kick a member. (Mod only)")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked **{member}** — {reason}")

@bot.command(help="Ban a member. (Mod only)")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned **{member}** — {reason}")

@bot.command(help="Timeout a member for N minutes. (Mod only)")
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    duration = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
    try:
        await member.timeout(duration, reason=reason)
        await ctx.send(f"⏳ Timed out **{member}** for **{minutes}m** — {reason}")
    except Exception as e:
        await ctx.send(f"Could not timeout: {e}")

# ====== SIMPLE WARN SYSTEM (in-memory; resets on restart) ======
warnings = {}  # {user_id: [reasons]}
@bot.command(help="Warn a user. (Mod only)")
@mod_or_admin()
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    warnings.setdefault(member.id, []).append(reason)
    await ctx.send(f"⚠️ Warning added for **{member}** — {reason}")

@bot.command(help="Show warnings for a user. (Mod only)")
@mod_or_admin()
async def warnings_of(ctx, member: discord.Member):
    user_warns = warnings.get(member.id, [])
    if not user_warns:
        return await ctx.send(f"✅ **{member}** has no warnings.")
    lines = "\n".join([f"{i+1}. {r}" for i, r in enumerate(user_warns)])
    await ctx.send(f"⚠️ Warnings for **{member}**:\n{lines}")

# ====== WELCOME (optional channel) ======
@bot.event
async def on_member_join(member: discord.Member):
    if WELCOME_CHANNEL_ID and WELCOME_CHANNEL_ID.isdigit():
        ch = member.guild.get_channel(int(WELCOME_CHANNEL_ID))
        if ch:
            try:
                await ch.send(f"🌟 Welcome {member.mention}! Choose your roles below and say hello!")
            except Exception:
                pass
    await lumi_post("member_join", {"user": str(member), "guild": member.guild.name})

# ====== ROLE MENU (priority feature) ======
# Usage (mods only):
#   !rolesetup @Role1 @Role2 @Role3
# or by names:
#   !rolesetup Role One | Role Two | Role Three
#
# Bot will post an embed with a dropdown to add/remove those roles.

class RoleSelect(discord.ui.Select):
    def __init__(self, roles: list[discord.Role]):
        opts = [discord.SelectOption(label=r.name, value=str(r.id)) for r in roles]
        super().__init__(placeholder="Select your roles…", min_values=0, max_values=len(opts), options=opts)
        self.roles = roles

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        chosen_ids = {int(v) for v in self.values}
        to_add, to_remove = [], []
        for r in self.roles:
            if r.id in chosen_ids and r not in member.roles:
                to_add.append(r)
            if r.id not in chosen_ids and r in member.roles:
                to_remove.append(r)
        try:
            if to_add:
                await member.add_roles(*to_add, reason="Self-role menu")
            if to_remove:
                await member.remove_roles(*to_remove, reason="Self-role menu")
            await interaction.response.edit_message(content="✅ Roles updated.", view=self.view)
        except discord.Forbidden:
            await interaction.response.send_message("I’m missing role permissions or role order is above me.", ephemeral=True)

class RoleMenuView(discord.ui.View):
    def __init__(self, roles: list[discord.Role], timeout: int = 0):
        super().__init__(timeout=timeout)
        self.add_item(RoleSelect(roles))

def parse_roles_from_args(ctx: commands.Context, args: str) -> list[discord.Role]:
    # Accept mentions OR a bar-separated list of names.
    roles: list[discord.Role] = []
    if ctx.message.role_mentions:
        for r in ctx.message.role_mentions:
            if r < ctx.guild.me.top_role:
                roles.append(r)
        return roles

    # By names: "Role A | Role B | Role C"
    parts = [p.strip() for p in args.split("|") if p.strip()]
    for name in parts:
        r = discord.utils.get(ctx.guild.roles, name=name)
        if r and r < ctx.guild.me.top_role:
            roles.append(r)
    return roles

@bot.command(help="Create a self-role dropdown. Usage: !rolesetup @Role1 @Role2 …  OR  !rolesetup Role A | Role B")
@commands.has_permissions(manage_roles=True)
async def rolesetup(ctx, *, roles_text: str = ""):
    roles = parse_roles_from_args(ctx, roles_text)
    if not roles:
        return await ctx.send("Provide roles by mention or by name (use `|` between names). Example:\n`!rolesetup @Artists @Coders @Dreamers`\n`!rolesetup Artists | Coders | Dreamers`")
    embed = discord.Embed(
        title="Choose Your Roles",
        description="Use the dropdown to add/remove your roles. You can select multiple.",
        color=discord.Color.purple(),
    )
    view = RoleMenuView(roles)
    await ctx.send(embed=embed, view=view)

# ====== ERROR HANDLER (clean messages) ======
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        return await ctx.send("🚫 You don’t have permission to use that.")
    if isinstance(error, commands.BadArgument):
        return await ctx.send("❓ Bad argument. Try again.")
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"⚠️ Error: {error}")

# ====== RUN ======
if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("TOKEN not set. Add a TOKEN environment variable on Render.")
    bot.run(TOKEN)
