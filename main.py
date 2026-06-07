import discord
import os
import random
from discord.ext import commands
from groq import Groq, APIConnectionError, RateLimitError, AuthenticationError

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TOKEN = os.getenv("TOKEN")

active_ia = set()
channel_memory = {} # {channel_id: [{"role":"user","content":"..."},...]}

@bot.event
async def on_ready():
    print(f'✅ Connecté en tant que {bot.user}')
    await bot.change_presence(activity=discord.Game(name="!help"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

    if message.channel.id in active_ia and not message.content.startswith('!'):
        if len(message.content) >= 3:
            channel_id = message.channel.id

            # Initialise la mémoire si besoin
            if channel_id not in channel_memory:
                channel_memory[channel_id] = []

            # Ajoute le message utilisateur à la mémoire
            channel_memory[channel_id].append({"role": "user", "content": message.content})

            # Garde seulement les 10 derniers messages pour pas exploser le quota
            if len(channel_memory[channel_id]) > 20:
                channel_memory[channel_id] = channel_memory[channel_id][-20:]

            async with message.channel.typing():
                try:
                    resp = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=channel_memory[channel_id],
                        max_tokens=800,
                        temperature=0.7
                    )
                    answer = resp.choices[0].message.content
                    channel_memory[channel_id].append({"role": "assistant", "content": answer})
                    await message.reply(answer[:2000])
                except Exception as e:
                    print(f"Erreur IA: {e}")
                    await message.reply("❌ Erreur IA")

@bot.command(name="ask")
@commands.cooldown(1, 5, commands.BucketType.user)
async def ask_cmd(ctx, *, question: str):
    msg = await ctx.send("💭 Je réfléchis...")
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": question}],
            max_tokens=1000
        )
        await msg.edit(content=resp.choices[0].message.content[:2000])
    except Exception as e:
        await msg.edit(content=f"❌ {type(e).__name__}")

@bot.command(name="ia")
@commands.has_permissions(administrator=True)
async def ia_toggle(ctx):
    channel_id = ctx.channel.id

    if channel_id in active_ia:
        active_ia.remove(channel_id)
        # SUPPRESSION DE LA MÉMOIRE
        if channel_id in channel_memory:
            del channel_memory[channel_id]
        embed = discord.Embed(
            title="🔴 Mode IA désactivé",
            description="La mémoire de conversation a été **supprimée**.",
            color=0xff0000
        )
    else:
        active_ia.add(channel_id)
        channel_memory[channel_id] = [] # Initialise mémoire vide
        embed = discord.Embed(
            title="🟢 Mode IA activé avec MÉMOIRE",
            description="Je réponds à tous les messages **et je me souviens** de la conversation.\nRefais `!ia` pour désactiver et effacer la mémoire.",
            color=0x00ff00
        )
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

    e = discord.Embed(
        title="📖 Aide Block2Bot",
        description="Voici toutes les commandes disponibles",
        color=0x5865f2
    )

    # Commandes IA
    e.add_field(
        name="🤖 COMMANDES IA",
        value="`!ask <question>`\n→ Pose une question ponctuelle à l'IA Groq Llama 3.1\n→ Accessible à tout le monde\n→ Exemple: `!ask explique moi les trous noirs`\n→ Cooldown: 5 secondes",
        inline=False
    )

    if is_admin:
        e.add_field(
            name="🧠!ia (ADMIN)",
            value="→ Active/désactive le mode conversation automatique\n→ Quand activé: le bot répond à **tous** les messages du salon\n→ **AVEC MÉMOIRE**: il se souvient des 10 derniers échanges\n→ Quand désactivé: la mémoire est **supprimée**\n→ Exemple: `!ia` dans #général",
            inline=False
        )
        e.add_field(
            name="⚙️ OUTILS ADMIN",
            value="`!ping`\n→ Affiche la latence du bot en millisecondes\n\n`!clear <nombre>`\n→ Supprime les derniers messages (1 à 100)\n→ Exemple: `!clear 20`",
            inline=False
        )

    # Commandes fun
    e.add_field(
        name="🎮 COMMANDES FUN",
        value="`!coin` → Pile ou face aléatoire\n`!roll` → Lance un dé de 1 à 100\n`!8ball <question>` → Boule magique (oui/non)\n`!ratio [@membre]` → Ratio automatique\n`!sus [@membre]` → Calcule ton taux de 'sus' 0-100%\n`!pp [@membre]` → Mesure... autre chose",
        inline=False
    )

    e.set_footer(text="Admin détecté" if is_admin else "Membre - certaines commandes sont cachées")
    await ctx.send(embed=e)

# Commandes fun
@bot.command(name="coin")
async def coin_cmd(ctx):
    await ctx.send(f"🪙 **{random.choice(['Pile','Face'])}**")

@bot.command(name="roll")
async def roll_cmd(ctx):
    await ctx.send(f"🎲 **{random.randint(1,100)}**")

@bot.command(name="8ball")
async def ball_cmd(ctx, *, q=None):
    if not q: return await ctx.send("❌ `!8ball vais-je réussir?`")
    await ctx.send(f"🎱 {random.choice(['Oui.','Non.','Peut-être.','C\'est certain.','Jamais.'])}")

@bot.command(name="ratio")
async def ratio_cmd(ctx, m: discord.Member = None):
    await ctx.send(f"{(m or ctx.author).mention} ratio + L")

@bot.command(name="sus")
async def sus_cmd(ctx, m: discord.Member = None):
    t = m or ctx.author
    await ctx.send(f"📮 {t.mention} est **{random.randint(0,100)}%** sus")

@bot.command(name="pp")
async def pp_cmd(ctx, m: discord.Member = None):
    t = m or ctx.author
    await ctx.send(f"📏 {t.mention} : 8{'='*random.randint(0,15)}D")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏱️ Attends {error.retry_after:.1f}s", delete_after=4)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Admin uniquement", delete_after=4)

if TOKEN:
    bot.run(TOKEN)
