import discord
import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from discord.ext import commands, tasks
from groq import Groq

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TOKEN = os.getenv("TOKEN")

active_ia = set()
channel_memory = {}

TIMEZONES = {
    "france": "Europe/Paris", "paris": "Europe/Paris",
    "usa": "America/New_York", "new york": "America/New_York",
    "japon": "Asia/Tokyo", "tokyo": "Asia/Tokyo", "japan": "Asia/Tokyo",
    "uk": "Europe/London", "londres": "Europe/London",
    "allemagne": "Europe/Berlin", "berlin": "Europe/Berlin",
    "espagne": "Europe/Madrid", "madrid": "Europe/Madrid",
    "italie": "Europe/Rome", "rome": "Europe/Rome",
    "canada": "America/Toronto", "toronto": "America/Toronto",
    "australie": "Australia/Sydney", "sydney": "Australia/Sydney",
    "chine": "Asia/Shanghai", "shanghai": "Asia/Shanghai",
    "corée": "Asia/Seoul", "seoul": "Asia/Seoul",
    "brésil": "America/Sao_Paulo", "brazil": "America/Sao_Paulo",
    "maroc": "Africa/Casablanca", "casablanca": "Africa/Casablanca",
    "algérie": "Africa/Algiers", "alger": "Africa/Algiers",
    "tunisie": "Africa/Tunis", "tunis": "Africa/Tunis",
    "dubai": "Asia/Dubai", "uae": "Asia/Dubai",
    "inde": "Asia/Kolkata", "india": "Asia/Kolkata",
    "russie": "Europe/Moscow", "moscou": "Europe/Moscow",
}

@bot.event
async def on_ready():
    print(f'✅ {bot.user}')
    await bot.change_presence(activity=discord.Game(name="🌿!help → Mode d'emploi ✨"))
    reset_memory.start()

@tasks.loop(hours=3)
async def reset_memory():
    channel_memory.clear()
    print("🧹 Mémoire reset (3h)")

def needs_web_search(text):
    keywords = ["aujourd'hui", "hier", "actu", "news", "prix", "météo", "temps", "qui est", "quand", "résultat", "score", "dernière", "récent", "2024", "2025", "2026", "combien", "cours", "bourse"]
    return any(k in text.lower() for k in keywords)

async def web_search(query):
    try:
        search_prompt = f"Donne info récente sur: {query}. Réponse courte avec source."
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": search_prompt}],
            max_tokens=300
        )
        return resp.choices[0].message.content + "\n\n🔗 Source: recherche web"
    except:
        return None

async def handle_ai(message, content):
    cid = message.channel.id
    if cid not in channel_memory:
        channel_memory[cid] = []
    channel_memory[cid].append({"role": "user", "content": content})
    channel_memory[cid] = channel_memory[cid][-20:]

    async with message.channel.typing():
        try:
            search_result = None
            if needs_web_search(content):
                search_result = await web_search(content)

            system_msg = "Réponds court, détaillé, avec emojis. Max 4 phrases."
            if search_result:
                system_msg += f" Info: {search_result}"

            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": system_msg}] + channel_memory[cid],
                max_tokens=400
            )
            answer = resp.choices[0].message.content
            if search_result and "source" not in answer.lower():
                answer += "\n\n🌐 Basé sur recherche web"
            channel_memory[cid].append({"role": "assistant", "content": answer})
            await message.reply(answer[:2000])
        except: pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)
    if message.channel.id in active_ia and not message.content.startswith('!'):
        if len(message.content) >= 3:
            await handle_ai(message, message.content)
            @bot.command(name="ask")
@commands.cooldown(1, 5, commands.BucketType.user)
async def ask_cmd(ctx, *, question: str):
    msg = await ctx.send("💭")
    cid = ctx.channel.id
    if cid not in channel_memory:
        channel_memory[cid] = []
    channel_memory[cid].append({"role": "user", "content": question})
    channel_memory[cid] = channel_memory[cid][-20:]

    try:
        search_result = None
        if needs_web_search(question):
            await msg.edit(content="🌐 Recherche web...")
            search_result = await web_search(question)

        system_msg = "Réponds court, détaillé, avec emojis. Max 4 phrases."
        if search_result:
            system_msg += f" Utilise: {search_result}"

        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_msg}] + channel_memory[cid],
            max_tokens=400
        )
        answer = resp.choices[0].message.content
        if search_result:
            answer += "\n\n🔗 Source: web"
        channel_memory[cid].append({"role": "assistant", "content": answer})
        await msg.edit(content=answer[:2000])
    except Exception as e:
        await msg.edit(content=f"❌ {type(e).__name__}")

@bot.command(name="time")
async def time_cmd(ctx, *, pays: str = None):
    if not pays:
        now = datetime.now()
        return await ctx.send(f"⏰ **Heure locale**\n🕐 {now.strftime('%H:%M:%S')}\n📅 {now.strftime('%d/%m/%Y')}")
    pays_key = pays.lower().strip()
    tz_name = TIMEZONES.get(pays_key)
    if not tz_name:
        return await ctx.send("❌ Pays inconnu. Essaie: france, usa, japon, uk, maroc, dubai, canada...")
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    await ctx.send(f"⏰ **{pays.title()}**\n🕐 {now.strftime('%H:%M:%S')}\n📅 {now.strftime('%d/%m/%Y')}\n🌍 {tz_name}")

@bot.command(name="ia")
@commands.has_permissions(administrator=True)
async def ia_toggle(ctx):
    cid = ctx.channel.id
    if cid in active_ia:
        active_ia.remove(cid)
        channel_memory.pop(cid, None)
        embed = discord.Embed(title="🔴 IA désactivée", description="Mémoire effacée ✅", color=0xff0000)
    else:
        active_ia.add(cid)
        channel_memory[cid] = []
        embed = discord.Embed(title="🟢 IA activée", description="Mémoire + recherche web • Reset 3h", color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command(name="ping")
@commands.has_permissions(administrator=True)
async def ping_cmd(ctx):
    await ctx.send(f"🏓 {round(bot.latency*1000)}ms")

@bot.command(name="clear")
@commands.has_permissions(administrator=True, manage_messages=True)
async def clear_cmd(ctx, amount: int = 5):
    if not 1 <= amount <= 100:
        return await ctx.send("❌ 1-100")
    deleted = await ctx.channel.purge(limit=amount+1)
    await ctx.send(f"✅ {len(deleted)-1} supprimés", delete_after=3)

@bot.command(name="help")
async def help_cmd(ctx):
    is_admin = ctx.author.guild_permissions.administrator
    e = discord.Embed(title="📖 Mode d'emploi Block2Bot", color=0x5865f2, description="Toutes les commandes")

    e.add_field(name="🤖 IA INTELLIGENTE", value="`!ask <question>`\n→ Pose une question\n→ Mémoire du salon activée\n→ Recherche web auto pour actu/prix/météo\n→ Donne les sources", inline=False)

    if is_admin:
        e.add_field(name="🧠 COMMANDES ADMIN", value="`!ia`\n→ Active mode auto-réponse dans le salon\n→ Répond à TOUS les messages\n→ Avec mémoire + web\n→ Refaire!ia = stop + efface mémoire\n\n`!ping`\n→ Latence du bot\n\n`!clear <1-100>`\n→ Supprime messages", inline=False)

    e.add_field(name="🌍 UTILITAIRES", value="`!time <pays>`\n→ Heure exacte d'un pays\n→ Exemples: `!time france`, `!time japon`, `!time usa`, `!time maroc`, `!time dubai`\n→ Sans pays = heure locale", inline=False)

    e.add_field(name="🎮 FUN", value="`!coin` → Pile ou face\n`!roll` → 1-100\n`!8ball <question>` → Oui/non\n`!ratio [@user]` → Ratio\n`!sus [@user]` → % sus", inline=False)

    e.set_footer(text="💾 Mémoire reset toutes les 3 heures automatiquement")
    await ctx.send(embed=e)

@bot.command(name="coin")
async def coin_cmd(ctx):
    await ctx.send(f"🪙 **{random.choice(['Pile','Face'])}**")

@bot.command(name="roll")
async def roll_cmd(ctx):
    await ctx.send(f"🎲 **{random.randint(1,100)}**")

@bot.command(name="8ball")
async def ball_cmd(ctx, *, q=None):
    if not q:
        return await ctx.send("❌!8ball ta question")
    await ctx.send(f"🎱 {random.choice(['Oui 👍','Non 👎','Peut-être 🤔','C\'est sûr ✅','Jamais ❌'])}")

@bot.command(name="ratio")
async def ratio_cmd(ctx, m: discord.Member = None):
    await ctx.send(f"{(m or ctx.author).mention} ratio + L 📉")

@bot.command(name="sus")
async def sus_cmd(ctx, m: discord.Member = None):
    t = m or ctx.author
    p = random.randint(0,100)
    await ctx.send(f"📮 {t.mention} est **{p}%** sus {'😳' if p>75 else '😇'}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏱️ Attends {error.retry_after:.1f}s", delete_after=3)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Admin uniquement", delete_after=3)
    elif isinstance(error, commands.CommandNotFound):
        return

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ TOKEN manquant")
