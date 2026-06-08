# ═══════════════════════════════════════════════════════════════════
#  PARTIE 1 / 3 — CONFIG · EVENTS · IA
#  ▸ Collez les 3 parties à la suite dans un seul fichier bot.py
#  ▸ Activez "Server Members Intent" dans le portail Discord Developer
# ═══════════════════════════════════════════════════════════════════

import discord, os, random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from discord.ext import commands, tasks
from groq import Groq

# ── CONFIG ──────────────────────────────────────────────────────────
intents                = discord.Intents.default()
intents.message_content = True
intents.members        = True          # ← activer dans le portail Discord

bot         = commands.Bot(command_prefix="!", intents=intents, help_command=None)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TOKEN       = os.getenv("TOKEN")

BOT_COLOR   = 0x2ECC71
BOT_NAME    = "Block2BlockFr"
SUPPORT_URL = "https://discord.gg/SxCbfsErHU"

active_channels : set  = set()
memory          : dict = {}
warnings        : dict = {}   # {guild_id: {user_id: [{reason, by, at}]}}

TZ = {
    "france":    "Europe/Paris",      "paris":    "Europe/Paris",
    "usa":       "America/New_York",  "new york": "America/New_York",
    "japon":     "Asia/Tokyo",        "tokyo":    "Asia/Tokyo",
    "uk":        "Europe/London",     "londres":  "Europe/London",
    "allemagne": "Europe/Berlin",     "espagne":  "Europe/Madrid",
    "italie":    "Europe/Rome",       "canada":   "America/Toronto",
    "australie": "Australia/Sydney",  "chine":    "Asia/Shanghai",
    "corée":     "Asia/Seoul",        "brésil":   "America/Sao_Paulo",
    "maroc":     "Africa/Casablanca", "algérie":  "Africa/Algiers",
    "tunisie":   "Africa/Tunis",      "dubai":    "Asia/Dubai",
    "inde":      "Asia/Kolkata",      "russie":   "Europe/Moscow",
}

# ── HELPER EMBED ────────────────────────────────────────────────────
def mk_embed(title: str, desc: str = "", color: int = BOT_COLOR,
             footer: str = None) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=color,
                      timestamp=datetime.now(timezone.utc))
    e.set_footer(text=footer or BOT_NAME)
    return e

# ── EVENTS ──────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="🌿 !help → Mode d'emploi"))
    reset_loop.start()
    print(f"✅  {bot.user}  |  {len(bot.guilds)} serveur(s)")

@bot.event
async def on_guild_join(guild: discord.Guild):
    """DM clean au propriétaire du serveur lors de l'ajout du bot."""
    try:
        owner = await bot.fetch_user(guild.owner_id)
        e = discord.Embed(
            title="⚒️ Merci de m'avoir installé !",
            description=(
                "Je suis maintenant actif sur ton serveur 🎉\n\n"
                "Si vous souhaitez plus d'infos sur moi, veuillez rejoindre\n"
                "notre Discord ou exécuter la commande `!help` 🎋\n\n"
                "**━━━━━━━━━━━━━━━━━━━━━━━━**\n"
                f"→  **{SUPPORT_URL}**  ←\n"
                "**━━━━━━━━━━━━━━━━━━━━━━━━**"
            ),
            color=BOT_COLOR,
        )
        e.add_field(name="📌 Préfixe",  value="`!`",                         inline=True)
        e.add_field(name="❓ Aide",      value="`!help`",                      inline=True)
        e.add_field(name="🌐 Support",   value=f"[Rejoindre]({SUPPORT_URL})", inline=True)
        e.set_thumbnail(url=bot.user.display_avatar.url)
        e.set_footer(text=BOT_NAME)
        await owner.send(embed=e)
    except (discord.Forbidden, discord.HTTPException):
        pass  # DM désactivés chez le propriétaire

@bot.event
async def on_message(msg: discord.Message):
    if msg.author.bot:
        return
    await bot.process_commands(msg)
    if msg.channel.id in active_channels and not msg.content.startswith("!"):
        cid = msg.channel.id
        memory.setdefault(cid, []).append({"role": "user", "content": msg.content})
        memory[cid] = memory[cid][-20:]
        async with msg.channel.typing():
            answer = await ask_ai(memory[cid], need_web(msg.content))
            memory[cid].append({"role": "assistant", "content": answer})
            await msg.reply(answer[:2000])

@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignorer les commandes inconnues silencieusement
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=mk_embed("❌ Permission refusée",
            "Tu n'as pas les droits pour cette commande.", 0xE74C3C))
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(embed=mk_embed("❌ Droits insuffisants",
            "Je n'ai pas les permissions nécessaires pour faire ça.", 0xE74C3C))
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(embed=mk_embed("❌ Membre introuvable",
            "Ce membre n'est pas sur le serveur.", 0xE74C3C))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=mk_embed("❌ Argument manquant",
            "Utilisation incorrecte. Tape `!help` pour voir les commandes.", 0xE74C3C))
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=mk_embed("⏱️ Cooldown",
            f"Attends **{error.retry_after:.1f}s** avant de réessayer.", 0xE67E22))
    elif isinstance(error, commands.BadArgument):
        await ctx.send(embed=mk_embed("❌ Argument invalide",
            "Mauvais argument. Tape `!help` pour plus d'infos.", 0xE74C3C))

# ── IA ──────────────────────────────────────────────────────────────
@tasks.loop(hours=3)
async def reset_loop():
    memory.clear()
    print("🔄 Mémoire IA réinitialisée.")

def need_web(q: str) -> bool:
    kw = ["aujourd'hui", "actu", "prix", "météo", "score", "2024", "2025",
          "2026", "combien", "qui est", "maintenant", "récent", "dernière"]
    return any(k in q.lower() for k in kw)

async def ask_ai(messages: list, with_web: bool = False) -> str:
    sys_p = ("Tu es un assistant Discord utile et sympathique francophone. "
             "Réponds en 3 phrases max avec des emojis.")
    if with_web:
        sys_p += " Cite tes sources si possible."
    r = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": sys_p}] + messages,
        max_tokens=400,
    )
    return r.choices[0].message.content

@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def ask(ctx: commands.Context, *, question: str):
    msg = await ctx.send(embed=mk_embed("💭 Réflexion...", "L'IA analyse ta question..."))
    cid = ctx.channel.id
    memory.setdefault(cid, []).append({"role": "user", "content": question})
    memory[cid] = memory[cid][-20:]
    if need_web(question):
        await msg.edit(embed=mk_embed("🌐 Recherche en cours...", "Accès au web..."))
    answer = await ask_ai(memory[cid], need_web(question))
    if need_web(question):
        answer += "\n\n🔗 *Source : recherche web*"
    memory[cid].append({"role": "assistant", "content": answer})
    await msg.edit(embed=mk_embed("🤖 Réponse IA", answer[:4000],
                                  footer=f"Question de {ctx.author.display_name}"))

@bot.command()
@commands.has_permissions(administrator=True)
async def ia(ctx: commands.Context):
    cid = ctx.channel.id
    if cid in active_channels:
        active_channels.discard(cid)
        memory.pop(cid, None)
        await ctx.send(embed=mk_embed("🔴 IA Désactivée",
            "L'IA ne répond plus automatiquement ici. Mémoire effacée.", 0xE74C3C))
    else:
        active_channels.add(cid)
        memory[cid] = []
        await ctx.send(embed=mk_embed("🟢 IA Activée",
            "L'IA répond automatiquement à tous les messages dans ce salon.\n"
            "📝 Mémoire : 20 messages  |  🌐 Web auto  |  🔄 Reset toutes les 3h"))
        # ═══════════════════════════════════════════════════════════════════
#  PARTIE 2 / 3 — MODÉRATION
#  ▸ À coller APRÈS la partie 1 dans bot.py
# ═══════════════════════════════════════════════════════════════════

@bot.command()
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "Aucune raison fournie"):
    if member == ctx.author:
        return await ctx.send(embed=mk_embed("❌ Erreur",
            "Tu ne peux pas te kick toi-même.", 0xE74C3C))
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send(embed=mk_embed("❌ Hiérarchie des rôles",
            "Tu ne peux pas kick un membre avec un rôle ≥ au tien.", 0xE74C3C))
    try:
        await member.send(embed=mk_embed("👢 Tu as été expulsé",
            f"**Serveur :** {ctx.guild.name}\n**Raison :** {reason}\n"
            f"**Par :** {ctx.author}", 0xE67E22))
    except (discord.Forbidden, discord.HTTPException):
        pass
    await member.kick(reason=f"{ctx.author} : {reason}")
    await ctx.send(embed=mk_embed("👢 Membre expulsé",
        f"**Membre :** {member.mention}\n**Raison :** {reason}\n"
        f"**Modérateur :** {ctx.author.mention}", 0xE67E22))

@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "Aucune raison fournie"):
    if member == ctx.author:
        return await ctx.send(embed=mk_embed("❌ Erreur",
            "Tu ne peux pas te ban toi-même.", 0xE74C3C))
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send(embed=mk_embed("❌ Hiérarchie des rôles",
            "Tu ne peux pas ban un membre avec un rôle ≥ au tien.", 0xE74C3C))
    try:
        await member.send(embed=mk_embed("🔨 Tu as été banni",
            f"**Serveur :** {ctx.guild.name}\n**Raison :** {reason}\n"
            f"**Par :** {ctx.author}", 0xE74C3C))
    except (discord.Forbidden, discord.HTTPException):
        pass
    await member.ban(reason=f"{ctx.author} : {reason}", delete_message_days=0)
    await ctx.send(embed=mk_embed("🔨 Membre banni",
        f"**Membre :** {member.mention}\n**Raison :** {reason}\n"
        f"**Modérateur :** {ctx.author.mention}", 0xE74C3C))

@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def unban(ctx: commands.Context, *, user_input: str):
    """Usage : !unban <ID Discord>  ou  !unban NomUtilisateur"""
    bans   = [entry async for entry in ctx.guild.bans()]
    target = None
    if user_input.isdigit():
        target = next((e.user for e in bans if e.user.id == int(user_input)), None)
    if not target:
        target = next((e.user for e in bans
                       if str(e.user) == user_input or e.user.name == user_input), None)
    if not target:
        return await ctx.send(embed=mk_embed("❌ Introuvable",
            "Utilisateur non trouvé dans la liste des bannis.\n"
            "Utilise l'**ID Discord** ou le nom exact.", 0xE74C3C))
    await ctx.guild.unban(target, reason=str(ctx.author))
    await ctx.send(embed=mk_embed("✅ Membre débanni",
        f"**Membre :** {target}\n**Modérateur :** {ctx.author.mention}"))

@bot.command()
@commands.has_permissions(manage_roles=True)
@commands.bot_has_permissions(manage_roles=True)
async def mute(ctx: commands.Context, member: discord.Member, *, reason: str = "Aucune raison fournie"):
    if member == ctx.author:
        return await ctx.send(embed=mk_embed("❌ Erreur",
            "Tu ne peux pas te mute toi-même.", 0xE74C3C))
    # Récupérer ou créer le rôle "Muted" automatiquement
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted",
            reason="Rôle créé automatiquement par le bot")
        for ch in ctx.guild.channels:
            try:
                await ch.set_permissions(muted_role,
                    send_messages=False, add_reactions=False, speak=False)
            except discord.Forbidden:
                pass
    if muted_role in member.roles:
        return await ctx.send(embed=mk_embed("⚠️ Déjà muté",
            f"{member.mention} est déjà muté.", 0xE67E22))
    await member.add_roles(muted_role, reason=f"{ctx.author} : {reason}")
    try:
        await member.send(embed=mk_embed("🔇 Tu as été muté",
            f"**Serveur :** {ctx.guild.name}\n**Raison :** {reason}", 0xE74C3C))
    except (discord.Forbidden, discord.HTTPException):
        pass
    await ctx.send(embed=mk_embed("🔇 Membre muté",
        f"**Membre :** {member.mention}\n**Raison :** {reason}\n"
        f"**Modérateur :** {ctx.author.mention}", 0xE67E22))

@bot.command()
@commands.has_permissions(manage_roles=True)
@commands.bot_has_permissions(manage_roles=True)
async def unmute(ctx: commands.Context, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role or muted_role not in member.roles:
        return await ctx.send(embed=mk_embed("⚠️ Pas muté",
            f"{member.mention} n'est pas muté.", 0xE67E22))
    await member.remove_roles(muted_role, reason=str(ctx.author))
    await ctx.send(embed=mk_embed("🔊 Membre démuté",
        f"**Membre :** {member.mention}\n**Modérateur :** {ctx.author.mention}"))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx: commands.Context, member: discord.Member, *, reason: str = "Aucune raison fournie"):
    gid, uid = str(ctx.guild.id), str(member.id)
    warnings.setdefault(gid, {}).setdefault(uid, []).append({
        "reason": reason,
        "by":     str(ctx.author),
        "at":     datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M"),
    })
    count = len(warnings[gid][uid])
    try:
        await member.send(embed=mk_embed("⚠️ Tu as reçu un avertissement",
            f"**Serveur :** {ctx.guild.name}\n**Raison :** {reason}\n"
            f"**Total warns :** {count}", 0xE67E22))
    except (discord.Forbidden, discord.HTTPException):
        pass
    await ctx.send(embed=mk_embed("⚠️ Avertissement émis",
        f"**Membre :** {member.mention}\n**Raison :** {reason}\n"
        f"**Modérateur :** {ctx.author.mention}\n**Total warns :** `{count}`", 0xE67E22))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warns(ctx: commands.Context, member: discord.Member):
    gid, uid = str(ctx.guild.id), str(member.id)
    w_list   = warnings.get(gid, {}).get(uid, [])
    if not w_list:
        return await ctx.send(embed=mk_embed("✅ Aucun avertissement",
            f"{member.mention} n'a aucun warn enregistré."))
    desc = "\n".join(
        f"**{i+1}.** {w['reason']} — *par {w['by']}* — `{w['at']}`"
        for i, w in enumerate(w_list)
    )
    await ctx.send(embed=mk_embed(f"⚠️ Warns de {member.display_name}", desc, 0xE67E22))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clearwarn(ctx: commands.Context, member: discord.Member):
    gid, uid = str(ctx.guild.id), str(member.id)
    if gid in warnings and uid in warnings[gid]:
        warnings[gid].pop(uid)
    await ctx.send(embed=mk_embed("✅ Warns effacés",
        f"Tous les avertissements de {member.mention} ont été supprimés.\n"
        f"**Modérateur :** {ctx.author.mention}"))

@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def slowmode(ctx: commands.Context, seconds: int = 0):
    if not 0 <= seconds <= 21600:
        return await ctx.send(embed=mk_embed("❌ Valeur invalide",
            "Délai entre **0** et **21 600** secondes.", 0xE74C3C))
    await ctx.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        await ctx.send(embed=mk_embed("✅ Slowmode désactivé", f"Salon : {ctx.channel.mention}"))
    else:
        await ctx.send(embed=mk_embed("⏱️ Slowmode activé",
            f"**Salon :** {ctx.channel.mention}\n**Délai :** `{seconds}s`"))

@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def lock(ctx: commands.Context):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(embed=mk_embed("🔒 Salon verrouillé",
        f"{ctx.channel.mention} est maintenant fermé.\n"
        f"**Modérateur :** {ctx.author.mention}", 0xE74C3C))

@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def unlock(ctx: commands.Context):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(embed=mk_embed("🔓 Salon déverrouillé",
        f"{ctx.channel.mention} est de nouveau ouvert.\n"
        f"**Modérateur :** {ctx.author.mention}"))
    # ═══════════════════════════════════════════════════════════════════
#  PARTIE 3 / 3 — UTILITAIRES · FUN · HELP · LANCEMENT
#  ▸ À coller APRÈS la partie 2 dans bot.py
# ═══════════════════════════════════════════════════════════════════

# ── UTILITAIRES ─────────────────────────────────────────────────────

@bot.command()
async def time(ctx: commands.Context, *, pays: str = None):
    if not pays:
        now = datetime.now(ZoneInfo("Europe/Paris"))
        return await ctx.send(embed=mk_embed("⏰ Heure locale",
            f"🇫🇷 **France** — `{now.strftime('%H:%M:%S')}` | {now.strftime('%d/%m/%Y')}"))
    tz = TZ.get(pays.lower())
    if not tz:
        dispo = "`, `".join(sorted(TZ.keys()))
        return await ctx.send(embed=mk_embed("❌ Pays inconnu",
            f"Pays disponibles :\n`{dispo}`", 0xE74C3C))
    now = datetime.now(ZoneInfo(tz))
    await ctx.send(embed=mk_embed("⏰ Heure mondiale",
        f"🌍 **{pays.title()}** — `{now.strftime('%H:%M:%S')}` | {now.strftime('%d/%m/%Y')}"))

@bot.command()
async def ping(ctx: commands.Context):
    ms    = round(bot.latency * 1000)
    color = 0x2ECC71 if ms < 100 else (0xE67E22 if ms < 200 else 0xE74C3C)
    icon  = "🟢" if ms < 100 else ("🟡" if ms < 200 else "🔴")
    await ctx.send(embed=mk_embed(f"{icon} Latence", f"`{ms} ms`", color))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx: commands.Context, n: int = 5):
    if not 1 <= n <= 100:
        return await ctx.send(embed=mk_embed("❌ Valeur invalide",
            "Choisis un nombre entre **1** et **100**.", 0xE74C3C))
    deleted = await ctx.channel.purge(limit=n + 1)
    await ctx.send(embed=mk_embed("🧹 Messages supprimés",
        f"**{len(deleted) - 1}** message(s) effacé(s) dans {ctx.channel.mention}\n"
        f"**Modérateur :** {ctx.author.mention}"), delete_after=4)

@bot.command()
async def userinfo(ctx: commands.Context, member: discord.Member = None):
    m      = member or ctx.author
    roles  = [r.mention for r in m.roles[1:]]
    r_str  = " ".join(roles[:8]) if roles else "`Aucun`"
    joined = m.joined_at.strftime("%d/%m/%Y") if m.joined_at else "N/A"
    e = mk_embed(f"👤 {m.display_name}",
        f"**Mention :** {m.mention}\n"
        f"**ID :** `{m.id}`\n"
        f"**A rejoint le :** {joined}\n"
        f"**Compte créé le :** {m.created_at.strftime('%d/%m/%Y')}\n"
        f"**Rôles :** {r_str}")
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def serverinfo(ctx: commands.Context):
    g = ctx.guild
    e = mk_embed(f"🏰 {g.name}",
        f"**Propriétaire :** {g.owner.mention}\n"
        f"**Membres :** `{g.member_count}`\n"
        f"**Salons texte :** `{len(g.text_channels)}`\n"
        f"**Salons vocaux :** `{len(g.voice_channels)}`\n"
        f"**Rôles :** `{len(g.roles)}`\n"
        f"**Créé le :** {g.created_at.strftime('%d/%m/%Y')}")
    if g.icon:
        e.set_thumbnail(url=g.icon.url)
    await ctx.send(embed=e)

@bot.command()
async def avatar(ctx: commands.Context, member: discord.Member = None):
    m = member or ctx.author
    e = mk_embed(f"🖼️ Avatar — {m.display_name}")
    e.set_image(url=m.display_avatar.url)
    await ctx.send(embed=e)

# ── FUN ─────────────────────────────────────────────────────────────
BALL = [
    "🟢 Oui, absolument !", "🟢 Sans aucun doute.", "🟢 C'est certain !",
    "🟢 Compte là-dessus.", "🟡 Peut-être...",       "🟡 Difficile à dire.",
    "🟡 Concentre-toi et redemande.",                "🔴 Non, je ne pense pas.",
    "🔴 Mes sources disent non.",                    "🔴 Très peu probable.",
]

@bot.command()
async def coin(ctx: commands.Context):
    await ctx.send(embed=mk_embed("🪙 Pile ou Face",
        random.choice(["🪙 **Pile**", "🪙 **Face**"])))

@bot.command()
async def roll(ctx: commands.Context, maximum: int = 100):
    if maximum < 2:
        return await ctx.send(embed=mk_embed("❌ Erreur",
            "Le maximum doit être au moins `2`.", 0xE74C3C))
    n = random.randint(1, maximum)
    await ctx.send(embed=mk_embed("🎲 Lancer de dé",
        f"Résultat : **{n}** *(entre 1 et {maximum})*"))

@bot.command(name="8ball")
async def _8ball(ctx: commands.Context, *, question: str = None):
    if not question:
        return await ctx.send(embed=mk_embed("❌ Question manquante",
            "Usage : `!8ball <question>`", 0xE74C3C))
    await ctx.send(embed=mk_embed("🎱 8Ball",
        f"**❓ {question}**\n\n{random.choice(BALL)}"))

@bot.command()
async def ratio(ctx: commands.Context, member: discord.Member = None):
    t = member or ctx.author
    await ctx.send(embed=mk_embed("📊 Ratio", f"{t.mention} s'est fait **ratio** 💀"))

@bot.command()
async def sus(ctx: commands.Context, member: discord.Member = None):
    t   = member or ctx.author
    pct = random.randint(0, 100)
    c   = 0xE74C3C if pct > 70 else (0xE67E22 if pct > 40 else 0x2ECC71)
    await ctx.send(embed=mk_embed("📡 Impostor Meter",
        f"{t.mention} est **{pct}%** sus 🔍", c))

@bot.command()
async def pp(ctx: commands.Context, member: discord.Member = None):
    t    = member or ctx.author
    size = random.randint(0, 20)
    await ctx.send(embed=mk_embed("📏 PP Meter",
        f"{t.mention}\n`8{'=' * size}D` — `{size} cm`"))

# ── HELP ────────────────────────────────────────────────────────────
@bot.command()
async def help(ctx: commands.Context):
    is_admin = ctx.author.guild_permissions.administrator
    is_mod   = (ctx.author.guild_permissions.kick_members
                or ctx.author.guild_permissions.ban_members
                or ctx.author.guild_permissions.manage_messages
                or ctx.author.guild_permissions.manage_roles)

    e = discord.Embed(
        title="📖 Block2BlockFr — Aide complète",
        description=f"Préfixe : `!`  ·  [Serveur de support]({SUPPORT_URL})",
        color=BOT_COLOR,
        timestamp=datetime.now(timezone.utc),
    )
    e.set_thumbnail(url=bot.user.display_avatar.url)
    e.add_field(name="🤖 Intelligence Artificielle", inline=False, value=(
        "`!ask <question>` — Pose une question à l'IA (mémoire + web auto)\n"
        "`!ia` — Active / désactive l'IA automatique *(admin)*"
    ))
    e.add_field(name="🌍 Utilitaires", inline=False, value=(
        "`!time [pays]` — Heure locale ou d'un pays (france, usa, japon...)\n"
        "`!ping` — Latence du bot\n"
        "`!userinfo [@membre]` — Informations sur un membre\n"
        "`!serverinfo` — Informations sur le serveur\n"
        "`!avatar [@membre]` — Voir l'avatar d'un membre en grand"
    ))
    e.add_field(name="🎮 Fun", inline=False, value=(
        "`!coin` — Pile ou face 🪙\n"
        "`!roll [max]` — Nombre aléatoire (défaut : 1–100)\n"
        "`!8ball <question>` — Boule magique 🎱\n"
        "`!ratio [@membre]` — Ratio 💀\n"
        "`!sus [@membre]` — Détecteur d'imposteur\n"
        "`!pp [@membre]` — PP Meter 📏"
    ))
    if is_mod or is_admin:
        e.add_field(name="🛡️ Modération *(modérateurs uniquement)*", inline=False, value=(
            "`!kick @membre [raison]` — Expulser un membre\n"
            "`!ban @membre [raison]` — Bannir un membre\n"
            "`!unban <ID ou Nom>` — Débannir un membre\n"
            "`!mute @membre [raison]` — Rendre muet *(crée le rôle Muted si absent)*\n"
            "`!unmute @membre` — Retirer le mute\n"
            "`!warn @membre [raison]` — Avertir un membre\n"
            "`!warns @membre` — Voir la liste des avertissements\n"
            "`!clearwarn @membre` — Effacer tous les avertissements\n"
            "`!clear [n]` — Supprimer jusqu'à 100 messages\n"
            "`!slowmode [secondes]` — Définir le slowmode (0 = désactiver)\n"
            "`!lock` — Verrouiller le salon (lecture seule)\n"
            "`!unlock` — Déverrouiller le salon"
        ))
    e.set_footer(text=f"{BOT_NAME}  ·  Demandé par {ctx.author.display_name}")
    await ctx.send(embed=e)

# ── LANCEMENT ───────────────────────────────────────────────────────
bot.run(TOKEN)
