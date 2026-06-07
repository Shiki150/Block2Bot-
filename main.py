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
    "usa": "America/New_York", "new york": "America/New_York", "newyork": "America/New_York",
    "japon": "Asia/Tokyo", "tokyo": "Asia/Tokyo", "japan": "Asia/Tokyo",
    "uk": "Europe/London", "londres": "Europe/London", "london": "Europe/London",
    "allemagne": "Europe/Berlin", "berlin": "Europe/Berlin", "germany": "Europe/Berlin",
    "espagne": "Europe/Madrid", "madrid": "Europe/Madrid", "spain": "Europe/Madrid",
    "italie": "Europe/Rome", "rome": "Europe/Rome", "italy": "Europe/Rome",
    "canada": "America/Toronto", "toronto": "America/Toronto", "montreal": "America/Montreal",
    "australie": "Australia/Sydney", "sydney": "Australia/Sydney",
    "chine": "Asia/Shanghai", "shanghai": "Asia/Shanghai", "beijing": "Asia/Shanghai",
    "corée": "Asia/Seoul", "seoul": "Asia/Seoul", "korea": "Asia/Seoul",
    "brésil": "America/Sao_Paulo", "sao paulo": "America/Sao_Paulo", "brazil": "America/Sao_Paulo",
    "maroc": "Africa/Casablanca", "casablanca": "Africa/Casablanca",
    "algérie": "Africa/Algiers", "alger": "Africa/Algiers", "algeria": "Africa/Algiers",
    "tunisie": "Africa/Tunis", "tunis": "Africa/Tunis",
    "dubai": "Asia/Dubai", "uae": "Asia/Dubai",
    "inde": "Asia/Kolkata", "india": "Asia/Kolkata", "mumbai": "Asia/Kolkata",
    "russie": "Europe/Moscow", "moscou": "Europe/Moscow", "moscow": "Europe/Moscow",
}

@bot.event
async def on_ready():
    print(f'✅ Connecté en tant que {bot.user}')
    await bot.change_presence(activity=discord.Game(name="🌿!help → Mode d'emploi ✨"))
    reset_memory.start()

@tasks.loop(hours=3)
async def reset_memory():
    channel_memory.clear()
    print("🧹 Mémoire reset (3h)")

def needs_web_search(text):
    keywords = ["aujourd'hui", "hier", "actu", "news", "prix", "météo", "temps", "qui est", "quand", "résultat", "score", "dernière", "récent", "2024", "2025", "2026", "combien coûte", "cours", "bourse", "température"]
    return any(k in text.lower() for k in keywords)

async def web_search(query):
    try:
        search_prompt = f"Recherche info récente sur: {query}. Donne réponse courte avec source."
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
                system_msg += f" Info web: {search_result}"

            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": system_msg}] + channel_memory[cid],
                max_tokens=400,
                temperature=0.7
            )
            answer = resp.choices[0].message.content
            if search_result and "source" not in answer.lower():
                answer += "\n\n🌐 Basé sur recherche web"
            channel_memory[cid].append({"role": "assistant", "content": answer})
            await message.reply(answer[:2000])
        except Exception as e:
            print(f"Erreur IA: {e}")

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
            system_msg += f" Utilise cette info: {search_result}"

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
        await msg.edit(content=f"❌ Erreur: {type(e).__name__}")

@bot.command(name="time")
async def time_cmd(ctx, *, pays: str = None):
    if not pays:
        now = datetime.now()
        return await ctx.send(f"⏰ **Heure locale du bot**\n🕐 {now.strftime('%H:%M:%S')}\n📅 {now.strftime('%d/%m/%Y')}\n\n💡 Essaie: `!time france` ou `!time japon`")
    pays_key = pays.lower().strip()
    tz_name = TIMEZONES.get(pays_key)
    if not tz_name:
        return await ctx.send("❌ Pays inconnu\n💡 Exemples: france, usa, japon, uk, canada, australie, maroc, dubai, inde...")
    try:
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
        await ctx.send(f"⏰ **{pays.title()}**\n🕐 {now.strftime('%H:%M:%S')}\n📅 {now.strftime('%d/%m/%Y')}\n🌍 Fuseau: {tz_name}")
    except Exception as e:
        await ctx.send(f"❌ Erreur: {e}")

@bot.command(name="ia")
@commands.has_permissions(administrator=True)
async def ia_toggle(ctx):
    cid = ctx.channel.id
    if cid in active_ia:
        active_ia.remove(cid)
        channel_memory.pop(cid, None)
        embed = discord.Embed(title="🔴 Mode IA désactivé", description="La mémoire de conversation a été **supprimée** ✅", color=0xff0000)
    else:
        active_ia.add(cid)
        channel_memory[cid] = []
        embed = discord.Embed(title="🟢 Mode IA activé", description="Je réponds à tous les messages avec mémoire 🧠\nRecherche web auto pour actu\nReset automatique toutes les 3h", color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command(name="ping")
@commands.has_permissions(administrator=True)
async def ping_cmd(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

@bot.command(name="clear")
@commands.has_permissions(administrator=True, manage_messages=True)
async def clear_cmd(ctx, amount: int = 5):
    if amount < 1 or amount > 100:
        return await ctx.send("❌ Nombre entre 1 et 100")
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ {len(deleted)-1} messages supprimés", delete_after=3)

@bot.command(name="help")
async def help_cmd(ctx):
    is_admin = ctx.author.guild_permissions.administrator
    e = discord.Embed(title="📖 Mode d'emploi Block2Bot", color=0x5865f2, description="Voici toutes les commandes disponibles")

    e.add_field(name="🤖 IA INTELLIGENTE", value="`!ask <question>`\n→ Pose une question à l'IA\n→ Elle se souvient de la conversation du salon\n→ Recherche web automatique pour actu, prix, météo, scores\n→ Donne les sources quand c'est du web", inline=False)

    if is_admin:
        e.add_field(name="🧠 COMMANDES ADMIN", value="`!ia`\n→ Active/désactive le mode conversation auto\n→ Quand activé: je réponds à TOUS les messages sans!ask\n→ Avec mémoire complète + recherche web\n→ Refaire!ia = désactive et efface mémoire\n\n`!ping`\n→ Affiche la latence\n\n`!clear <nombre>`\n→ Supprime 1 à 100 messages", inline=False)

    e.add_field(name="🌍 UTILITAIRES", value="`!time <pays>`\n→ Donne l'heure exacte d'un pays\n→ Exemples: `!time france`, `!time japon`, `!time usa`, `!time maroc`, `!time dubai`\n→ Sans argument: heure locale du bot", inline=False)

    e.add_field(name="🎮 COMMANDES FUN", value="`!coin` → Pile ou face 🪙\n`!roll` → Nombre aléatoire 1-100 🎲\n`!8ball <question>` → Boule magique 🎱\n`!ratio [@membre]` → Ratio classique\n`!sus [@membre]` → Calcule ton taux de suspicion", inline=False)

    e.set_footer(text="💾 Mémoire partagée par salon • Reset auto toutes les 3 heures")
    await ctx.send(embed=e)

@bot.command(name="coin")
async def coin_cmd(ctx):
    await ctx.send(f"🪙 **{random.choice(['Pile', 'Face'])}**")

@bot.command(name="roll")
async def roll_cmd(ctx):
    await ctx.send(f"🎲 Tu as fait **{random.randint(1, 100)}**")

@bot.command(name="8ball")
async def ball_cmd(ctx, *, question: str = None):
    if not question:
        return await ctx.send("❌ Pose une question: `!8ball je vais réussir?`")
    rep = random.choice(["Oui 👍", "Non 👎", "Peut-être 🤔", "C'est certain ✅", "Jamais ❌", "Demande plus tard ⏳", "Évidemment 😏"])
    await ctx.send(f"🎱 {rep}")

@bot.command(name="ratio")
async def ratio_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"{target.mention} ratio + L + skill issue 📉")

@bot.command(name="sus")
async def sus_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    pct = random.randint(0, 100)
    emoji = '😳' if pct > 75 else '😇' if pct < 25 else '🤨'
    await ctx.send(f"📮 {target.mention} est **{pct}%** sus {emoji}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏱️ Attends {error.retry_after:.1f}s", delete_after=5)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Réservé aux administrateurs", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Argument manquant", delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        print(f"Erreur: {error}")

if not TOKEN:
    print("❌ ERREUR: Variable TOKEN manquante sur Railway")
else:
    bot.run(TOKEN)
