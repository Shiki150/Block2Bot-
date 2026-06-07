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

@bot.event
async def on_ready():
    print(f'✅ Connecté en tant que {bot.user}')
    await bot.change_presence(activity=discord.Game(name="!help pour les commandes"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

    if message.channel.id in active_ia and not message.content.startswith('!'):
        if len(message.content) >= 4:
            async with message.channel.typing():
                try:
                    resp = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": message.content}],
                        max_tokens=700,
                        temperature=0.7
                    )
                    await message.reply(resp.choices[0].message.content[:2000])
                except Exception as e:
                    print(f"Erreur IA auto: {e}")

@bot.command(name="ask")
@commands.cooldown(1, 5, commands.BucketType.user)
async def ask_cmd(ctx, *, question: str):
    msg = await ctx.send("💭 Block2Bot réfléchit...")
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": question}],
            max_tokens=1000,
            temperature=0.7
        )
        await msg.edit(content=resp.choices[0].message.content[:2000])
    except APIConnectionError:
        await msg.edit(content="❌ Groq ne répond pas")
    except AuthenticationError:
        await msg.edit(content="❌ Clé GROQ_API_KEY invalide")
    except RateLimitError:
        await msg.edit(content="⏱️ Rate limit, attends 1 minute")
    except Exception as e:
        await msg.edit(content=f"❌ Erreur: {type(e).__name__}")

@bot.command(name="ia")
@commands.has_permissions(administrator=True)
async def ia_toggle(ctx):
    if ctx.channel.id in active_ia:
        active_ia.remove(ctx.channel.id)
        embed = discord.Embed(description="🔴 **Mode IA désactivé**", color=0xff0000)
    else:
        active_ia.add(ctx.channel.id)
        embed = discord.Embed(description="🟢 **Mode IA activé** - Je réponds à tout", color=0x00ff00)
        embed.set_footer(text="Refais!ia pour désactiver")
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

    if is_admin:
        e = discord.Embed(title="🔧 Commandes Admin + Membres", color=0x5865f2)
        e.add_field(name="🤖 IA (tout le monde)", value="`!ask <question>` - Question à l'IA", inline=False)
        e.add_field(name="⚙️ Admin uniquement", value="`!ia` - Active l'IA auto dans le salon\n`!ping` - Latence\n`!clear <1-100>` - Supprime messages", inline=False)
        e.add_field(name="🎮 Fun (tout le monde)", value="`!coin` `!roll` `!8ball` `!ratio` `!sus` `!pp`", inline=False)
    else:
        e = discord.Embed(title="🎮 Commandes Block2Bot", color=0x57f287)
        e.add_field(name="🤖 IA", value="`!ask <question>` - Pose une question à l'IA Groq", inline=False)
        e.add_field(name="🎲 Fun", value="`!coin` - Pile ou face\n`!roll` - Dé 1-100\n`!8ball <question>` - Boule magique\n`!ratio [@membre]` - Ratio\n`!sus [@membre]` - Taux de sus\n`!pp [@membre]` - Taille", inline=False)

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
        return await ctx.send("❌ `!8ball tu vas réussir?`")
    rep = random.choice(["Oui.", "Non.", "Peut-être.", "C'est certain.", "Jamais.", "Demande plus tard.", "Évidemment."])
    await ctx.send(f"🎱 {rep}")

@bot.command(name="ratio")
async def ratio_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    await ctx.send(f"{target.mention} ratio + L + skill issue")

@bot.command(name="sus")
async def sus_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    pct = random.randint(0, 100)
    await ctx.send(f"📮 {target.mention} est **{pct}%** sus {'😳' if pct > 75 else '✅'}")

@bot.command(name="pp")
async def pp_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    size = random.randint(0, 15)
    await ctx.send(f"📏 {target.mention} : 8{'='*size}D")

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
    print("❌ TOKEN manquant")
else:
    bot.run(TOKEN)
