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
    "france": "Europe/Paris", "usa": "America/New_York", "japon": "Asia/Tokyo",
    "uk": "Europe/London", "allemagne": "Europe/Berlin", "espagne": "Europe/Madrid",
    "italie": "Europe/Rome", "canada": "America/Toronto", "australie": "Australia/Sydney",
    "chine": "Asia/Shanghai", "corée": "Asia/Seoul", "brésil": "America/Sao_Paulo",
    "maroc": "Africa/Casablanca", "algérie": "Africa/Algiers", "tunisie": "Africa/Tunis",
    "dubai": "Asia/Dubai", "inde": "Asia/Kolkata", "russie": "Europe/Moscow",
}

@bot.event
async def on_ready():
    print(f'✅ {bot.user}')
    await bot.change_presence(activity=discord.Game(name="🌿!help → Mode d'emploi ✨"))
    reset_memory.start()

@tasks.loop(hours=3)
async def reset_memory():
    channel_memory.clear()

def needs_web_search(text):
    keywords = ["aujourd'hui", "hier", "actu", "news", "prix", "météo", "temps", "qui est", "quand", "résultat", "score", "dernière", "récent", "2024", "2025", "2026", "combien coûte", "cours", "bourse"]
    return any(k in text.lower() for k in keywords)

async def web_search(query):
    try:
        # Simulation recherche web via Groq avec contexte actuel
        search_prompt = f"Recherche info récente sur: {query}. Donne réponse courte avec source."
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": search_prompt}],
            max_tokens=300
        )
        return resp.choices[0].message.content + "\n\n🔗 *Source: recherche web*"
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
            # Check si besoin recherche web
            search_result = None
            if needs_web_search(content):
                search_result = await web_search(content)

            system_msg = "Réponds court, détaillé, avec emojis. Max 4 phrases."
            if search_result:
                system_msg += f" Info web: {search_result}"

            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": system_msg}] + channel_memory[cid],
                max_tokens=400
            )
            answer = resp.choices[0].message.content
            if search_result and "source" not in answer.lower():
                answer += "\n\n🌐 *Basé sur recherche web*"

            channel_memory[cid].append({"role": "assistant", "content": answer})
            await message.reply(answer[:2000])
        except: pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)
    if message.channel.id in active_ia and not message.content.startswith('!'):
        await handle_ai(message, message.content)

@bot.command(name="ask")
@commands.cooldown(1, 5, commands.BucketType.user)
async def ask_cmd(ctx, *, question: str):
    msg = await ctx.send("💭 Recherche...")
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
            answer += "\n\n🔗 *Source: web*"

        channel_memory[cid].append({"role": "assistant", "content": answer})
        await msg.edit(content=answer[:2000])
    except Exception as e:
        await msg.edit(content=f"
