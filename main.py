import discord
import os
from discord.ext import commands
from groq import Groq, APIConnectionError, RateLimitError, AuthenticationError

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

STAFF_ROLE = "Staff"
active_ia_channels = set()

def is_staff():
    async def predicate(ctx):
        return discord.utils.get(ctx.author.roles, name=STAFF_ROLE) is not None
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Game(name="!ask |!ia pour mode auto"))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if message.channel.id in active_ia_channels and not message.content.startswith('!'):
        if len(message.content) > 3:
            async with message.channel.typing():
                try:
                    r = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": message.content}],
                        max_tokens=600,
                        timeout=15
                    )
                    await message.reply(r.choices[0].message.content[:2000])
                except Exception:
                    pass

@bot.command()
@is_staff()
@commands.cooldown(1, 5, commands.BucketType.user)
async def ask(ctx, *, question):
    msg = await ctx.send("Block2Bot réfléchit...")
    try:
        r = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": question}],
            max_tokens=800,
            timeout=20
        )
        await msg.edit(content=r.choices[0].message.content[:2000])
    except APIConnectionError:
        await msg.edit(content="❌ Groq répond pas. Réessaie dans 1 min.")
    except AuthenticationError:
        await msg.edit(content="❌ Clé Groq invalide.")
    except RateLimitError:
        await msg.edit(content="⏱️ Trop de requêtes. Attends 1 min.")
    except Exception as e:
        await msg.edit(content=f"❌ Erreur : {type(e).__name__}")

@bot.command()
@is_staff()
async def ia(ctx):
    if ctx.channel.id in active_ia_channels:
        active_ia_channels.remove(ctx.channel.id)
        await ctx.send("🔴 Mode IA désactivé dans ce salon. Utilisez!ask pour parler à l'IA.")
    else:
        active_ia_channels.add(ctx.channel.id)
        await ctx.send("🟢 Mode IA activé! Je réponds à tous les messages de ce salon. Refais!ia pour désactiver.")

@bot.command()
@is_staff()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")

@bot.command()
@is_staff()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    if amount > 50:
        await ctx.send("❌ Max 50 messages d'un coup")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ {len(deleted)-1} messages supprimés", delete_after=3)

@bot.command()
@is_staff()
async def help(ctx):
    embed = discord.Embed(title="Commandes Staff Block2Bot", color=0xff0000)
    embed.add_field(name="!ask <question>", value="Pose une question à l'IA", inline=False)
    embed.add_field(name="!ia", value="Active/désactive l'IA auto dans le salon", inline=False)
    embed.add_field(name="!ping", value="Affiche la latence", inline=False)
    embed.add_field(name="!clear <nombre>", value="Supprime des messages", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def mhelp(ctx):
    embed = discord.Embed(title="Commandes Membres", color=0x00ff00)
    embed.add_field(name="!coin", value="Pile ou face", inline=False)
    embed.add_field(name="!roll", value="Lance un dé 1-100", inline=False)
    embed.add_field(name="!8ball <question>", value="Boule magique", inline=False)
    embed.add_field(name="!ratio", value="Ratio automatique", inline=False)
    embed.add_field(name="!sus", value="T'es sus ou pas", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def coin(ctx):
    import random
    result = random.choice(["Pile", "Face"])
    await ctx.send(f"🪙 {result}")

@bot.command()
async def roll(ctx):
    import random
    await ctx.send(f"🎲 Tu as fait {random.randint(1, 100)}")

@bot.command()
async def ratio(ctx):
    await ctx.send(f"{ctx.author.mention} ratio + L + skill issue")

@bot.command()
async def sus(ctx):
    import random
    taux = random.randint(0, 100)
    await ctx.send(f"📮 {ctx.author.mention} est {taux}% sus 😳")

@bot.command(name="8ball")
async def eightball(ctx, *, question):
    import random
    reponses = ["Oui.", "Non.", "Peut-être.", "Jamais.", "Demande plus tard.", "C'est certain.", "J'en doute."]
    await ctx.send(f"🎱 {random.choice(reponses)}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏱️ Attends {error.retry_after:.1f}s")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ T'as pas la perm pour ça")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("❌ Commande réservée au staff")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Argument manquant. Fais!mhelp ou!help")
    else:
        await ctx.send(f"❌ Erreur : {str(error)[:1500]}")

bot.run(os.getenv("TOKEN"))
