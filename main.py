import discord
import os
import random
import asyncio
from datetime import datetime
from discord.ext import commands, tasks
from groq import Groq

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TOKEN = os.getenv("TOKEN")

active_ia = set()
channel_memory = {}

@bot.event
async def on_ready():
    print(f'✅ {bot.user}')
    activity = discord.Game(name="❤ Block2BlockFr™ ⚒\n🌿!help → Mode D'emploi ✨")
    await bot.change_presence(activity=activity)
    reset_memory.start()

@tasks.loop(hours=3)
async def reset_memory():
    channel_memory.clear()
    print("🧹 Mémoire reset (3h)")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

    if message.channel.id in active_ia and not message.content.startswith('!'):
        await handle_ai(message, message.content)

async def handle_ai(message, content):
    cid = message.channel.id
    if cid not in channel_memory:
        channel_memory[cid] = []

    channel_memory[cid].append({"role": "user", "content": content})
    channel_memory[cid] = channel_memory[cid][-20:]

    async with message.channel.typing():
        try:
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": "Tu réponds de façon courte, claire et détaillée. Utilise des emojis. Max 4 phrases."}] + channel_memory[cid],
                max_tokens=400,
                temperature=0.7
            )
            answer = resp.choices[0].message.content
            channel_memory[cid].append({"role": "assistant", "content": answer})
            await message.reply(answer[:2000])
        except Exception as e:
            print(e)

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
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Réponds court, détaillé, avec emojis. Max 4 phrases."}] + channel_memory[cid],
            max_tokens=400
        )
        answer = resp.choices[0].message.content
        channel_memory[cid].append({"role": "assistant", "content": answer})
        await msg.edit(content=answer[:2000])
    except Exception as e:
        await msg.edit(content=f"❌ {type(e).__name__}")

@bot.command(name="ia")
@commands.has_permissions(administrator=True)
async def ia_toggle(ctx):
    cid = ctx.channel.id
    if cid in active_ia:
        active_ia.remove(cid)
        channel_memory.pop(cid, None)
        embed = discord.Embed(title="🔴 Mode IA désactivé", description="Mémoire effacée ✅", color=0xff0000)
    else:
        active_ia.add(cid)
        channel_memory[cid] = []
        embed = discord.Embed(title="🟢 Mode IA activé", description="Je réponds à tout avec mémoire 🧠\nReset auto toutes les 3h", color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command(name="time")
async def time_cmd(ctx):
    now = datetime.now()
    await ctx.send(f"⏰ **{now.strftime('%H:%M:%S')}**\n📅 {now.strftime('%d/%m/%Y')}")

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
    e = discord.Embed(title="📖 Mode d'emploi Block2Bot", color=0x5865f2)

    e.add_field(
        name="🤖 IA INTELLIGENTE",
        value="`!ask <question>`\n→ Pose une question à l'IA\n→ Elle se souvient de la conversation du salon\n→ Ex: `!ask c'est quoi un trou noir?`\n→ Cooldown 5s",
        inline=False
    )

    if is_admin:
        e.add_field(
            name="🧠!ia (ADMIN)",
            value="→ Active le mode où je réponds à TOUS les messages sans!ask\n→ Avec mémoire complète de la discussion\n→ Reset automatique toutes les 3 heures\n→ Refaire!ia = désactive + efface mémoire",
            inline=False
        )
        e.add_field(
            name="⚙️ MODÉRATION",
            value="`!ping` → Test la latence\n`!clear <1-100>` → Supprime des messages",
            inline=False
        )

    e.add_field(
        name="🎮 FUN",
        value="`!coin` → Pile ou face 🪙\n`!roll` → Nombre 1-100 🎲\n`!8ball <question>` → Boule magique 🎱\n`!time` → Heure et date actuelle ⏰\n`!ratio [@user]` → Ratio classique\n`!sus [@user]` → Test de suspicion",
        inline=False
    )

    e.set_footer(text="Mémoire partagée par salon • Reset 3h")
    await ctx.send(embed=e)

@bot.command(name="coin")
async def coin_cmd(ctx):
    await ctx.send(f"🪙 **{random.choice(['Pile','Face'])}**")

@bot.command(name="roll")
async def roll_cmd(ctx):
    await ctx.send(f"🎲 **{random.randint(1,100)}**")

@bot.command(name="8ball")
async def ball_cmd(ctx, *, q=None):
    if not q: return await ctx.send("❌!8ball ta question")
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
        await ctx.send(f"⏱️ {error.retry_after:.1f}s", delete_after=3)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Admin uniquement", delete_after=3)

if TOKEN:
    bot.run(TOKEN)
