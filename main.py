import discord
import os
from discord.ext import commands
from groq import Groq, APIConnectionError, RateLimitError, AuthenticationError

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
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
        await msg.edit(content="❌ Connection error : Groq répond pas. Réessaie dans 1 min.")
    except AuthenticationError:
        await msg.edit(content="❌ Clé Groq invalide. Check `GROQ_API_KEY` sur Railway.")
    except RateLimitError:
        await msg.edit(content="⏱️ Trop de requêtes. Attends 1 min.")
    except Exception as e:
        await msg.edit(content=f"❌ Erreur : `{type(e).__name__}`")
        print(f"Erreur: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏱️ Attends {error.retry_after:.1f}s")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Utilise : `!ask ton message`")

bot.run(os.getenv("TOKEN")) 
