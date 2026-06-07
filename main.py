import discord
import os
from discord.ext import commands
from openai import OpenAI

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def ask(ctx, *, question):
    msg = await ctx.send("Block2Bot réfléchit...")
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question}]
        )
        await msg.edit(content=r.choices[0].message.content[:2000])
    except Exception as e:
        await msg.edit(content=f"Erreur: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
