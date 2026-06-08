import discord
import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from discord.ext import commands, tasks
from groq import Groq

# CONFIG
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TOKEN = os.getenv("TOKEN")

# Mémoire
active_channels = set()
memory = {}

# Timezones
TZ = {
    "france": "Europe/Paris", "paris": "Europe/Paris",
    "usa": "America/New_York", "new york": "America/New_York",
    "japon": "Asia/Tokyo", "tokyo": "Asia/Tokyo",
    "uk": "Europe/London", "londres": "Europe/London",
    "allemagne": "Europe/Berlin", "espagne": "Europe/Madrid",
    "italie": "Europe/Rome", "canada": "America/Toronto",
    "australie": "Australia/Sydney", "chine": "Asia/Shanghai",
    "corée": "Asia/Seoul", "brésil": "America/Sao_Paulo",
    "maroc": "Africa/Casablanca", "algérie": "Africa/Algiers",
    "tunisie": "Africa/Tunis", "dubai": "Asia/Dubai",
    "inde": "Asia/Kolkata", "russie": "Europe/Moscow"
}

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="🌿!help → Mode d'emploi"))
    reset_loop.start()
    print(f"✅ {bot.user} connecté")

@tasks.loop(hours=3)
async def reset_loop():
    memory.clear()
    print("Memory reset")

def need_web(q):
    words = ["aujourd'hui", "actu", "prix", "météo", "score", "2024", "2025", "2026", "combien", "qui est"]
    return any(w in q.lower() for w in words)

async def ask_ai(messages, with_web=False):
    system = "Réponds en 3 phrases max, clair, avec emojis."
    if with_web:
        system += " Cite tes sources."
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=400
    )
    return resp.choices[0].message.content

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return
    await bot.process_commands(msg)

    if msg.channel.id in active_channels and not msg.content.startswith("!"):
        cid = msg.channel.id
        memory.setdefault(cid, []).append({"role": "user", "content": msg.content})
        memory[cid] = memory[cid][-20:]

        async with msg.channel.typing():
            answer = await ask_ai(memory[cid], need_web(msg.content))
            memory[cid].append({"role": "assistant", "content": answer})
            await msg.reply(answer[:2000])

@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def ask(ctx, *, question):
    msg = await ctx.send("💭")
    cid = ctx.channel.id
    memory.setdefault(cid, []).append({"role": "user", "content": question})
    memory[cid] = memory[cid][-20:]

    if need_web(question):
        await msg.edit(content="🌐 Recherche...")

    answer = await ask_ai(memory[cid], need_web(question))
    if need_web(question):
        answer += "\n\n🔗 Source: web"

    memory[cid].append({"role": "assistant", "content": answer})
    await msg.edit(content=answer[:2000])

@bot.command()
@commands.has_permissions(administrator=True)
async def ia(ctx):
    cid = ctx.channel.id
    if cid in active_channels:
        active_channels.remove(cid)
        memory.pop(cid, None)
        await ctx.send("🔴 IA désactivée - mémoire effacée")
    else:
        active_channels.add(cid)
        memory[cid] = []
        await ctx.send("🟢 IA activée - mémoire + web (reset 3h)")

@bot.command()
async def time(ctx, *, pays=None):
    if not pays:
        now = datetime.now()
        return await ctx.send(f"⏰ {now.strftime('%H:%M:%S')} - {now.strftime('%d/%m/%Y')}")

    tz = TZ.get(pays.lower())
    if not tz:
        return await ctx.send("Pays inconnu. Essaie: france, usa, japon, uk, maroc...")

    now = datetime.now(ZoneInfo(tz))
    await ctx.send(f"⏰ **{pays.title()}** {now.strftime('%H:%M:%S')}")

@bot.command()
async def help(ctx):
    admin = ctx.author.guild_permissions.administrator
    txt = "**📖 COMMANDES**\n\n"
    txt += "**🤖 IA**\n`!ask question` → IA avec mémoire + recherche web\n\n"
    if admin:
        txt += "**⚙️ ADMIN**\n`!ia` → mode auto\n`!clear 10` → supprime\n`!ping` → latence\n\n"
    txt += "**🌍 UTILE**\n`!time france` → heure pays\n\n"
    txt += "**🎮 FUN**\n`!coin` `!roll` `!8ball` `!ratio` `!sus`"
    await ctx.send(txt)

@bot.command()
async def coin(ctx):
    await ctx.send(random.choice(["Pile", "Face"]))

@bot.command()
async def roll(ctx):
    await ctx.send(str(random.randint(1, 100)))

@bot.command()
async def ping(ctx):
    await ctx.send(f"{round(bot.latency*1000)}ms")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, n: int = 5):
    await ctx.channel.purge(limit=n+1)
    await ctx.send(f"✅ {n} supprimés", delete_after=2)

@bot.command(name="8ball")
async def _8ball(ctx, *, q=None):
    await ctx.send(random.choice(["Oui 👍", "Non 👎", "Peut-être"]))

@bot.command()
async def ratio(ctx, m: discord.Member = None):
    await ctx.send(f"{(m or ctx.author).mention} ratio")

@bot.command()
async def sus(ctx, m: discord.Member = None):
    await ctx.send(f"{(m or ctx.author).mention} {random.randint(0,100)}% sus")

bot.run(TOKEN)
