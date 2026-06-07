import discord
import os
from discord.ext import commands
from groq import Groq
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = Flask('')
@app.route('/')
def home():
    return "Block2Bot est en ligne"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def ask(ctx, *, question):
    msg = await ctx.send("Block2Bot réfléchit...")
    try:
        r = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": question}]
        )
        await msg.edit(content=r.choices[0].message.content[:2000])
    except Exception as e:
        await msg.edit(content=f"Erreur: {e}")

Thread(target=run_flask).start()
bot.run(os.getenv("DISCORD_TOKEN"))
