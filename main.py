import discord, os, random, asyncio
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from discord.ext import commands, tasks
from groq import Groq

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot             = commands.Bot(command_prefix="!", intents=intents, help_command=None)
groq_client     = Groq(api_key=os.getenv("GROQ_API_KEY"))
TOKEN           = os.getenv("TOKEN")
BOT_COLOR       = 0x2ECC71
BOT_NAME        = "Block2BlockFr™"
SUPPORT_URL     = "https://discord.gg/SxCbfsErHU"
B2B_SERVER_NAME = "✦Block2BlockFr✦"
LANG            = "fr"

active_channels:   set  = set()
memory:            dict = {}
warnings:          dict = {}
counting_channels: dict = {}

TZ = {
    "france": "Europe/Paris",       "paris":     "Europe/Paris",
    "usa":    "America/New_York",   "new york":  "America/New_York",
    "japon":  "Asia/Tokyo",         "tokyo":     "Asia/Tokyo",
    "uk":     "Europe/London",      "londres":   "Europe/London",
    "allemagne": "Europe/Berlin",   "espagne":   "Europe/Madrid",
    "italie": "Europe/Rome",        "canada":    "America/Toronto",
    "australie":"Australia/Sydney", "chine":     "Asia/Shanghai",
    "corée":  "Asia/Seoul",         "brésil":    "America/Sao_Paulo",
    "maroc":  "Africa/Casablanca",  "algérie":   "Africa/Algiers",
    "tunisie":"Africa/Tunis",       "dubai":     "Asia/Dubai",
    "inde":   "Asia/Kolkata",       "russie":    "Europe/Moscow",
}

S = {
    "fr": {
        "ia_on":    "🟢 IA Activée",    "ia_on_d":   "L'IA répond automatiquement ici.\n🔄 Reset toutes les 3h",
        "ia_off":   "🔴 IA Désactivée", "ia_off_d":  "L'IA ne répond plus dans ce salon.",
        "think":    "💭 Réflexion...",  "think_d":   "L'IA analyse ta question...",
        "search":   "🌐 Recherche...", "search_d":  "Accès au web en cours...",
        "src":      "\n\n🔗 *Source : recherche web*",
        "resp":     "🤖 Réponse IA",   "by":        "Question de",
        "lang_ok":  "🌍 Langue → **Français** 🇫🇷", "lang_same": "Le bot est déjà en français !",
    },
    "en": {
        "ia_on":    "🟢 AI Enabled",   "ia_on_d":   "AI responds automatically here.\n🔄 Reset every 3h",
        "ia_off":   "🔴 AI Disabled",  "ia_off_d":  "AI no longer responds in this channel.",
        "think":    "💭 Thinking...",  "think_d":   "AI is analyzing your question...",
        "search":   "🌐 Searching...", "search_d":  "Accessing the web...",
        "src":      "\n\n🔗 *Source: web search*",
        "resp":     "🤖 AI Response",  "by":        "Question by",
        "lang_ok":  "🌍 Language → **English** 🇬🇧", "lang_same": "Bot is already in English!",
    }
}

def tr(k):
    return S[LANG].get(k, S["fr"].get(k, k))

def mk_embed(title, desc="", color=BOT_COLOR, footer=None):
    e = discord.Embed(title=title, description=desc, color=color,
                      timestamp=datetime.now(timezone.utc))
    e.set_footer(text=footer or BOT_NAME)
    return e

def is_mod(ctx):
    return any([
        ctx.author.guild_permissions.kick_members,
        ctx.author.guild_permissions.ban_members,
        ctx.author.guild_permissions.manage_messages,
        ctx.author.guild_permissions.moderate_members,
        ctx.author.guild_permissions.administrator,
    ])

def get_ticket_count():
    os.makedirs("data", exist_ok=True)
    try:
        with open("data/ticket_count.txt", "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0

def increment_ticket_count():
    count = get_ticket_count() + 1
    with open("data/ticket_count.txt", "w") as f:
        f.write(str(count))
    return count

@bot.before_invoke
async def auto_delete(ctx):
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(TicketActionView())
    await bot.change_presence(activity=discord.Game(name="⚒️ | Block2BlockFr™"))
    if not reset_loop.is_running():
        reset_loop.start()
    print(f"✅ {bot.user} · {len(bot.guilds)} serveur(s)")

@bot.event
async def on_guild_join(guild):
    try:
        owner = await bot.fetch_user(guild.owner_id)
        e = discord.Embed(
            title="⚒️ Merci de m'avoir installé !",
            description=(
                f"Bonjour **{owner.display_name}** 👋\n\n"
                f"Je viens d'être ajouté sur **{guild.name}** et je suis prêt !\n\n"
                "Utilise `!help` pour voir toutes mes commandes,\n"
                f"ou rejoins notre Discord pour plus d'infos 🎋\n\n"
                f"**→ {SUPPORT_URL} ←**"
            ),
            color=BOT_COLOR
        )
        e.add_field(name="📌 Préfixe", value="`!`", inline=True)
        e.add_field(name="❓ Aide",    value="`!help`", inline=True)
        e.add_field(name="🌐 Support", value=f"[Rejoindre]({SUPPORT_URL})", inline=True)
        e.set_thumbnail(url=bot.user.display_avatar.url)
        e.set_footer(text="Block2BlockFr™")
        await owner.send(embed=e)
    except (discord.Forbidden, discord.HTTPException):
        pass

CODED_BY_KW = [
    "qui t'a codé", "qui t'as codé", "who coded you", "qui t'as fait",
    "qui t'a fait", "qui t'a créé", "qui t'as créé", "ton créateur", "who made you",
]

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return
    if any(kw in msg.content.lower() for kw in CODED_BY_KW):
        await msg.reply("✨ J'ai été Codé par Shiki ⚒️")
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
    if msg.channel.id in counting_channels and not msg.content.startswith("!"):
        uid = msg.author.id
        counting_channels[msg.channel.id][uid] = counting_channels[msg.channel.id].get(uid, 0) + 1

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass
    pairs = {
        commands.MissingPermissions:      ("❌ Permission refusée",   "Tu n'as pas les droits pour cette commande."),
        commands.BotMissingPermissions:   ("❌ Droits insuffisants",  "Je n'ai pas les permissions nécessaires."),
        commands.MemberNotFound:          ("❌ Membre introuvable",   "Ce membre n'existe pas sur ce serveur."),
        commands.MissingRequiredArgument: ("❌ Argument manquant",    "Usage incorrect — tape `!help`."),
        commands.BadArgument:             ("❌ Argument invalide",    "Mauvais argument — tape `!help`."),
    }
    for exc, (title, desc) in pairs.items():
        if isinstance(error, exc):
            return await ctx.send(embed=mk_embed(title, desc, 0xE74C3C), delete_after=6)
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=mk_embed("⏱️ Cooldown",
            f"Attends `{error.retry_after:.1f}s`.", 0xE67E22), delete_after=5)

@tasks.loop(hours=3)
async def reset_loop():
    memory.clear()

def need_web(q):
    kw = ["aujourd'hui", "actu", "prix", "météo", "score", "2024", "2025",
          "2026", "combien", "qui est", "maintenant", "récent"]
    return any(k in q.lower() for k in kw)

async def ask_ai(messages, with_web=False):
    lang_instr = "Respond in English." if LANG == "en" else "Réponds en français."
    sys_p = (f"Tu es un assistant Discord utile et sympathique. {lang_instr} "
             "Réponds en 3 phrases max avec des emojis.")
    if with_web:
        sys_p += " Cite tes sources si possible."
    r = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": sys_p}] + messages,
        max_tokens=400
    )
    return r.choices[0].message.content

@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def ask(ctx, *, question: str):
    msg = await ctx.send(embed=mk_embed(tr("think"), tr("think_d")))
    cid = ctx.channel.id
    memory.setdefault(cid, []).append({"role": "user", "content": question})
    memory[cid] = memory[cid][-20:]
    if need_web(question):
        await msg.edit(embed=mk_embed(tr("search"), tr("search_d")))
    answer = await ask_ai(memory[cid], need_web(question))
    if need_web(question):
        answer += tr("src")
    memory[cid].append({"role": "assistant", "content": answer})
    await msg.edit(embed=mk_embed(tr("resp"), answer[:4000],
                                  footer=f"{tr('by')} {ctx.author.display_name}"))

@bot.command()
@commands.has_permissions(administrator=True)
async def ia(ctx):
    cid = ctx.channel.id
    if cid in active_channels:
        active_channels.discard(cid)
        memory.pop(cid, None)
        await ctx.send(embed=mk_embed(tr("ia_off"), tr("ia_off_d"), 0xE74C3C), delete_after=5)
    else:
        active_channels.add(cid)
        memory[cid] = []
        await ctx.send(embed=mk_embed(tr("ia_on"), tr("ia_on_d")))
        claimed_tickets: dict = {}

class TicketModal(discord.ui.Modal, title="Nouveau ticket"):
    raison = discord.ui.TextInput(
        label="Raison du ticket",
        placeholder="Décris ta demande...",
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild  = interaction.guild
        user   = interaction.user
        cat    = discord.utils.get(guild.categories, name="🎫 Tickets")
        if cat:
            for ch in cat.text_channels:
                if ch.topic == str(user.id):
                    return await interaction.response.send_message(
                        embed=mk_embed("❌ Ticket existant",
                            f"Tu as déjà un ticket ouvert : {ch.mention}", 0xE74C3C),
                        ephemeral=True
                    )
        if not cat:
            cat = await guild.create_category("🎫 Tickets")
        num    = increment_ticket_count()
        pseudo = user.display_name.lower().replace(" ", "-")
        name   = f"ticket-{num}-{pseudo}"
        staff  = discord.utils.get(guild.roles, name=" Staff ")
        ow = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user:               discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me:           discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        if staff:
            ow[staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        chan = await guild.create_text_channel(name, category=cat, overwrites=ow, topic=str(user.id))
        demandes = discord.utils.get(guild.text_channels, name="demandes-de-ticket")
        if demandes:
            ping = staff.mention if staff else "@Staff"
            await demandes.send(f"🎫 Nouveau ticket créé par {user.mention} : {chan.mention} — {ping}")
        e = discord.Embed(
            title=f"🎫 Ticket #{num}",
            description=(
                f"**👤 Demandé par :** {user.mention}\n"
                f"**📋 Raison :** {self.raison.value}\n"
                f"**📊 Statut :** En attente"
            ),
            color=0xE67E22,
            timestamp=datetime.now(timezone.utc)
        )
        e.set_footer(text=BOT_NAME)
        await chan.send(content=user.mention, embed=e, view=TicketActionView())
        await interaction.response.send_message(
            embed=mk_embed("✅ Ticket créé !", f"Ton ticket a été ouvert : {chan.mention}"),
            ephemeral=True
        )


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Créer un ticket", style=discord.ButtonStyle.success, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())


class TicketActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Claim le ticket", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff = discord.utils.get(interaction.guild.roles, name=" Staff ")
        if not staff or staff not in interaction.user.roles:
            return await interaction.response.send_message(
                embed=mk_embed("❌ Accès refusé", "Seul le staff peut claim un ticket.", 0xE74C3C),
                ephemeral=True
            )
        cid = interaction.channel.id
        if cid in claimed_tickets:
            return await interaction.response.send_message(
                embed=mk_embed("❌ Déjà claim",
                    f"Ce ticket est déjà pris en charge par {claimed_tickets[cid]}.", 0xE74C3C),
                ephemeral=True
            )
        claimed_tickets[cid] = interaction.user.mention
        og = interaction.message
        if og.embeds:
            old = og.embeds[0]
            new = discord.Embed(
                title=old.title,
                description=(
                    (old.description or "") +
                    f"\n**🔒 Claim par :** {interaction.user.mention}\n"
                    f"**📊 Statut :** Pris en charge"
                ),
                color=0x2ECC71,
                timestamp=datetime.now(timezone.utc)
            )
            new.set_footer(text=BOT_NAME)
            await og.edit(embed=new)
        await interaction.response.send_message(
            f"✅ {interaction.user.mention} a pris en charge ce ticket."
        )

    @discord.ui.button(label="🗑️ Fermer le ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff    = discord.utils.get(interaction.guild.roles, name=" Staff ")
        chan     = interaction.channel
        is_auth  = chan.topic and str(interaction.user.id) == chan.topic
        is_staff = staff and staff in interaction.user.roles
        if not is_auth and not is_staff:
            return await interaction.response.send_message(
                embed=mk_embed("❌ Accès refusé", "Tu ne peux pas fermer ce ticket.", 0xE74C3C),
                ephemeral=True
            )
        await interaction.response.send_message("🗑️ Fermeture du ticket dans 5 secondes...")
        claimed_tickets.pop(chan.id, None)
        await asyncio.sleep(5)
        await chan.delete(reason=f"Ticket fermé par {interaction.user}")


    @bot.command()
    @commands.has_permissions(administrator=True)
    async def ticketsetup(ctx):
        e = discord.Embed(
        title="🎫 **Aide • Tickets**",
        description=(
            "Besoin d'aide? Ouvre un ticket ci-dessous.\n\n"
            "**📋 Fonctionnement :**\n"
            "> 1️⃣ Clique sur `Créer un ticket`\n"
            "> 2️⃣ Indique la raison de ta demande\n"
            "> 3️⃣ Un salon privé sera créé pour toi\n\n"
            "**⚠️ Règles importantes :**\n"
            "> • Pas de spam de ticket\n"
            "> • Une seule mention admin MAX sauf si discussion sur le ticket\n"
            "> • Les demandes de rôle sont interdites sauf si gagné dans giveaways\n"
            "> • Pas de tickets troll\n"
            "> • Pas de tickets inutiles\n"
            "> • Pas de tickets dont la réponse est dans le règlement\n\n"
            "> ⚠️ Le non-respect de ces règles peut entraîner un avertissement ou autre sanction.\n\n"
            "**🔒 Confidentialité :** Seul toi et le staff verront le ticket."
        ),
        color=0x3498db,
        timestamp=datetime.now(timezone.utc)
    )
    e.set_footer(text=BOT_NAME)
    await ctx.send(embed=e, view=TicketView())
@bot.command()
@commands.has_permissions(kick_members=True
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "Aucune raison fournie"):
    if member == ctx.author:
        return await ctx.send(embed=mk_embed("❌ Erreur", "Tu ne peux pas te kick toi-même.", 0xE74C3C), delete_after=5)
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send(embed=mk_embed("❌ Hiérarchie", "Ce membre a un rôle ≥ au tien.", 0xE74C3C), delete_after=5)
    try:
        await member.send(embed=mk_embed("👢 Tu as été expulsé",
            f"**Serveur :** {ctx.guild.name}\n**Raison :** {reason}", 0xE67E22))
    except (discord.Forbidden, discord.HTTPException):
        pass
    await member.kick(reason=f"{ctx.author} : {reason}")
    await ctx.send(embed=mk_embed("👢 Membre expulsé",
        f"**Membre :** {member.mention}\n**Raison :** {reason}\n**Par :** {ctx.author.mention}", 0xE67E22))

@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "Aucune raison fournie"):
    if member == ctx.author:
        return await ctx.send(embed=mk_embed("❌ Erreur", "Tu ne peux pas te ban toi-même.", 0xE74C3C), delete_after=5)
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send(embed=mk_embed("❌ Hiérarchie", "Ce membre a un rôle ≥ au tien.", 0xE74C3C), delete_after=5)
    try:
        await member.send(embed=mk_embed("🔨 Tu as été banni",
            f"**Serveur :** {ctx.guild.name}\n**Raison :** {reason}", 0xE74C3C))
    except (discord.Forbidden, discord.HTTPException):
        pass
    await member.ban(reason=f"{ctx.author} : {reason}", delete_message_days=0)
    await ctx.send(embed=mk_embed("🔨 Membre banni",
        f"**Membre :** {member.mention}\n**Raison :** {reason}\n**Par :** {ctx.author.mention}", 0xE74C3C))

@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def unban(ctx, *, user_input: str):
    bans = [entry async for entry in ctx.guild.bans()]
    target = None
    if user_input.isdigit():
        target = next((e.user for e in bans if e.user.id == int(user_input)), None)
    if not target:
        target = next((e.user for e in bans
            if str(e.user) == user_input or e.user.name == user_input), None)
    if not target:
        return await ctx.send(embed=mk_embed("❌ Introuvable",
            "Utilisateur non trouvé.\nUtilise son **ID Discord** ou son **nom exact**.",
            0xE74C3C), delete_after=6)
    await ctx.guild.unban(target, reason=str(ctx.author))
    await ctx.send(embed=mk_embed("✅ Débanni", f"**Membre :** {target}\n**Par :** {ctx.author.mention}"))

@bot.command()
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def exclure(ctx, member: discord.Member, duree: int = 10, *, reason: str = "Aucune raison fournie"):
    if member == ctx.author:
        return await ctx.send(embed=mk_embed("❌ Erreur", "Tu ne peux pas t'exclure toi-même.", 0xE74C3C), delete_after=5)
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send(embed=mk_embed("❌ Hiérarchie", "Ce membre a un rôle ≥ au tien.", 0xE74C3C), delete_after=5)
    if not 1 <= duree <= 40320:
        return await ctx.send(embed=mk_embed("❌ Durée invalide",
            "Entre **1** et **40 320** minutes (28 jours max).", 0xE74C3C), delete_after=5)
    until = discord.utils.utcnow() + timedelta(minutes=duree)
    await member.timeout(until, reason=f"{ctx.author} : {reason}")
    try:
        await member.send(embed=mk_embed("🔇 Tu as été exclu temporairement",
            f"**Serveur :** {ctx.guild.name}\n**Durée :** {duree} min\n**Raison :** {reason}", 0xE74C3C))
    except (discord.Forbidden, discord.HTTPException):
        pass
    await ctx.send(embed=mk_embed("🔇 Exclusion appliquée",
        f"**Membre :** {member.mention}\n**Durée :** `{duree} min`\n"
        f"**Raison :** {reason}\n**Par :** {ctx.author.mention}", 0xE67E22))

@bot.command()
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
async def unexclure(ctx, member: discord.Member):
    await member.timeout(None, reason=str(ctx.author))
    await ctx.send(embed=mk_embed("🔊 Exclusion levée",
        f"**Membre :** {member.mention}\n**Par :** {ctx.author.mention}"))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason: str = "Aucune raison fournie"):
    gid, uid = str(ctx.guild.id), str(member.id)
    warnings.setdefault(gid, {}).setdefault(uid, []).append({
        "reason": reason, "by": str(ctx.author),
        "at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    })
    count = len(warnings[gid][uid])
    try:
        await member.send(embed=mk_embed("⚠️ Avertissement reçu",
            f"**Serveur :** {ctx.guild.name}\n**Raison :** {reason}\n**Total :** {count}", 0xE67E22))
    except (discord.Forbidden, discord.HTTPException):
        pass
    await ctx.send(embed=mk_embed("⚠️ Warn émis",
        f"**Membre :** {member.mention}\n**Raison :** {reason}\n"
        f"**Par :** {ctx.author.mention}\n**Total :** `{count}`", 0xE67E22))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warns(ctx, member: discord.Member):
    gid, uid = str(ctx.guild.id), str(member.id)
    w_list = warnings.get(gid, {}).get(uid, [])
    if not w_list:
        return await ctx.send(embed=mk_embed("✅ Aucun warn", f"{member.mention} n'a aucun avertissement."))
    desc = "\n".join(f"`{i+1}.` {w['reason']} — *{w['by']}* — `{w['at']}`" for i, w in enumerate(w_list))
    await ctx.send(embed=mk_embed(f"⚠️ Warns — {member.display_name}", desc, 0xE67E22))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clearwarn(ctx, member: discord.Member):
    gid, uid = str(ctx.guild.id), str(member.id)
    if gid in warnings and uid in warnings[gid]:
        warnings[gid].pop(uid)
    await ctx.send(embed=mk_embed("✅ Warns effacés",
        f"Avertissements de {member.mention} supprimés.\n**Par :** {ctx.author.mention}"))

@bot.command()
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def clear(ctx, n: int = 5):
    if not 1 <= n <= 100:
        return await ctx.send(embed=mk_embed("❌ Invalide", "Entre **1** et **100** messages.", 0xE74C3C), delete_after=5)
    deleted = await ctx.channel.purge(limit=n)
    await ctx.send(embed=mk_embed("🧹 Nettoyé",
        f"**{len(deleted)}** message(s) supprimé(s)\n**Par :** {ctx.author.mention}"), delete_after=4)

@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 0):
    if not 0 <= seconds <= 21600:
        return await ctx.send(embed=mk_embed("❌ Invalide", "Entre **0** et **21 600** secondes.", 0xE74C3C), delete_after=5)
    await ctx.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        await ctx.send(embed=mk_embed("✅ Slowmode désactivé", f"{ctx.channel.mention}"))
    else:
        await ctx.send(embed=mk_embed("⏱️ Slowmode activé", f"**Salon :** {ctx.channel.mention} → `{seconds}s`"))

@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(embed=mk_embed("🔒 Salon verrouillé",
        f"{ctx.channel.mention} est en lecture seule.\n**Par :** {ctx.author.mention}", 0xE74C3C))

@bot.command()
@commands.has_permissions(manage_channels=True)
@commands.bot_has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(embed=mk_embed("🔓 Salon déverrouillé",
        f"{ctx.channel.mention} est de nouveau ouvert.\n**Par :** {ctx.author.mention}"))

@bot.command()
@commands.has_permissions(administrator=True)
async def announce(ctx, channel: discord.TextChannel, *, message: str):
    e = discord.Embed(description=message, color=BOT_COLOR, timestamp=datetime.now(timezone.utc))
    e.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    e.set_footer(text=f"Annonce par {ctx.author.display_name} · {BOT_NAME}")
    await channel.send(embed=e)
    await ctx.send(embed=mk_embed("✅ Annonce envoyée", f"Message posté dans {channel.mention}"), delete_after=4)

@bot.command()
@commands.has_permissions(manage_nicknames=True)
@commands.bot_has_permissions(manage_nicknames=True)
async def setnick(ctx, member: discord.Member, *, pseudo: str):
    old = member.display_name
    await member.edit(nick=pseudo, reason=str(ctx.author))
    await ctx.send(embed=mk_embed("✏️ Pseudo modifié",
        f"**Membre :** {member.mention}\n**Avant :** `{old}`\n**Après :** `{pseudo}`\n**Par :** {ctx.author.mention}"))

@bot.command()
@commands.has_permissions(administrator=True)
async def serveurs(ctx):
    if ctx.guild.name != B2B_SERVER_NAME:
        return await ctx.send(embed=mk_embed("❌ Accès refusé",
            f"Cette commande est exclusivement disponible sur **{B2B_SERVER_NAME}**.",
            0xE74C3C), delete_after=6)
    loading = await ctx.send(embed=mk_embed("🔍 Chargement...",
        f"Récupération de **{len(bot.guilds)}** serveur(s) en cours..."))
    lines = []
    for guild in bot.guilds:
        invite_url = "`—`"
        for channel in guild.text_channels:
            try:
                invite = await channel.create_invite(max_age=0, max_uses=0, unique=False)
                invite_url = invite.url
                break
            except (discord.Forbidden, discord.HTTPException):
                continue
        try:
            owner = await bot.fetch_user(guild.owner_id)
            owner_str = f"{owner.name} · `{owner.id}`"
        except (discord.NotFound, discord.HTTPException):
            owner_str = f"`{guild.owner_id}`"
        lines.append(
            f"**{guild.name}** · `{guild.id}`\n"
            f"👑 {owner_str}\n"
            f"👥 `{guild.member_count}` membres\n"
            f"🔗 {invite_url}"
        )
    await loading.delete()
    desc = "\n\n".join(lines) if lines else "Aucun serveur trouvé."
    chunks = [desc[i:i+3900] for i in range(0, len(desc), 3900)]
    for idx, chunk in enumerate(chunks):
        title = f"🌐 Serveurs du bot — {len(bot.guilds)} au total" if idx == 0 else "🌐 Serveurs (suite)"
        await ctx.send(embed=mk_embed(title, chunk, footer=f"Demandé par {ctx.author.display_name} · {BOT_NAME}"))
@bot.command(name="supercounter")
@commands.has_permissions(administrator=True)
async def supercounter(ctx):
    cid = ctx.channel.id
    if cid in counting_channels:
        return await ctx.send(embed=mk_embed("⚠️ Comptage déjà actif",
            f"Un comptage est déjà en cours dans {ctx.channel.mention}.\nUtilise `!stopcount` pour l'arrêter.",
            0xE67E22), delete_after=6)
    counting_channels[cid] = {}
    await ctx.send(embed=mk_embed("📊 Comptage démarré !",
        f"Je compte maintenant les messages dans {ctx.channel.mention}.\n\n"
        "**➜** `!stopcount` — Arrêter et afficher le classement\n"
        "**➜** `!counter` — Aide du système",
        footer=f"Démarré par {ctx.author.display_name} · {BOT_NAME}"))

@bot.command(name="stopcount")
@commands.has_permissions(administrator=True)
async def stopcount(ctx):
    cid = ctx.channel.id
    if cid not in counting_channels:
        return await ctx.send(embed=mk_embed("❌ Aucun comptage actif",
            "Aucun comptage n'est en cours ici.\nUtilise `!supercounter` pour en démarrer un.",
            0xE74C3C), delete_after=6)
    counts = counting_channels.pop(cid)
    if not counts:
        return await ctx.send(embed=mk_embed("📊 Résultats",
            "Aucun message enregistré pendant le comptage.", 0xE67E22))
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:15]
    medals = ["🥇", "🥈", "🥉"] + [f"`{i+1}.`" for i in range(3, 15)]
    lines = []
    for i, (uid, count) in enumerate(sorted_counts):
        member = ctx.guild.get_member(uid)
        name   = member.display_name if member else "Membre introuvable"
        lines.append(f"{medals[i]} **{name}** — `{count}` msg")
    winner_extra = ""
    winner = ctx.guild.get_member(sorted_counts[0][0]) if sorted_counts else None
    if winner:
        super_role = discord.utils.get(ctx.guild.roles, name="Super Counter")
        if super_role:
            for m in super_role.members:
                try:
                    await m.remove_roles(super_role, reason="SuperCounter — nouveau gagnant")
                except (discord.Forbidden, discord.HTTPException):
                    pass
            try:
                await winner.add_roles(super_role, reason="SuperCounter — gagnant du comptage")
                winner_extra = f"\n\n🏆 {winner.mention} remporte {super_role.mention} !"
            except (discord.Forbidden, discord.HTTPException):
                winner_extra = f"\n\n🏆 Gagnant : {winner.mention}"
        else:
            winner_extra = f"\n\n🏆 Gagnant : {winner.mention}"
    await ctx.send(embed=mk_embed("📊 Classement final",
        "\n".join(lines) + winner_extra,
        footer=f"Arrêté par {ctx.author.display_name} · {BOT_NAME}"))

@bot.command(name="counter")
async def counter_help(ctx):
    e = discord.Embed(title="📊 SuperCounter — Aide",
        description="Système de comptage de messages par salon",
        color=BOT_COLOR, timestamp=datetime.now(timezone.utc))
    e.add_field(name="🟢 !supercounter", value="Démarre le comptage dans ce salon *(admin)*",           inline=False)
    e.add_field(name="🔴 !stopcount",    value="Arrête le comptage et affiche le top 15 *(admin)*",     inline=False)
    e.add_field(name="❓ !counter",      value="Affiche cette page d'aide",                             inline=False)
    e.add_field(name="ℹ️ Fonctionnement",
        value="Le comptage est lié au salon où `!supercounter` est lancé.\n"
              "Les commandes `!...` ne sont pas comptées.\n"
              "Le gagnant reçoit le rôle **@Super Counter** 🎖️\n"
              "L'ancien gagnant perd le rôle automatiquement au prochain `!stopcount`", inline=False)
    e.set_footer(text=f"Block2BlockFr™ · {ctx.author.display_name}")
    await ctx.send(embed=e)

@bot.command(name="time")
async def time_cmd(ctx, *, pays: str = None):
    if not pays:
        now = datetime.now(ZoneInfo("Europe/Paris"))
        return await ctx.send(embed=mk_embed("⏰ Heure — France",
            f"`{now.strftime('%H:%M:%S')}` · {now.strftime('%d/%m/%Y')}"))
    tz = TZ.get(pays.lower())
    if not tz:
        return await ctx.send(embed=mk_embed("❌ Pays inconnu",
            "Essaie : `france`, `usa`, `japon`, `uk`, `maroc`...", 0xE74C3C), delete_after=6)
    now = datetime.now(ZoneInfo(tz))
    await ctx.send(embed=mk_embed(f"⏰ Heure — {pays.title()}",
        f"`{now.strftime('%H:%M:%S')}` · {now.strftime('%d/%m/%Y')}"))

@bot.command()
async def ping(ctx):
    ms    = round(bot.latency * 1000)
    color = 0x2ECC71 if ms < 100 else (0xE67E22 if ms < 200 else 0xE74C3C)
    icon  = "🟢" if ms < 100 else ("🟡" if ms < 200 else "🔴")
    await ctx.send(embed=mk_embed(f"{icon} Ping", f"`{ms} ms`", color))

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    m      = member or ctx.author
    roles  = [r.mention for r in m.roles[1:]]
    r_str  = " ".join(roles[:8]) if roles else "`Aucun`"
    joined = m.joined_at.strftime("%d/%m/%Y") if m.joined_at else "—"
    e = mk_embed(f"👤 {m.display_name}",
        f"**Mention :** {m.mention}\n**ID :** `{m.id}`\n"
        f"**A rejoint :** {joined}\n"
        f"**Compte créé :** {m.created_at.strftime('%d/%m/%Y')}\n"
        f"**Rôles :** {r_str}")
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def serverinfo(ctx):
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
async def avatar(ctx, member: discord.Member = None):
    m = member or ctx.author
    e = mk_embed(f"🖼️ Avatar — {m.display_name}")
    e.set_image(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def botinfo(ctx):
    total = sum(g.member_count for g in bot.guilds)
    e = mk_embed("🤖 Block2Bot — Infos",
        f"**Équipe :** Block2BlockFr™\n"
        f"**Serveurs :** `{len(bot.guilds)}`\n"
        f"**Membres totaux :** `{total}`\n"
        f"**Ping :** `{round(bot.latency * 1000)}ms`\n"
        f"**Langue :** `{'Français 🇫🇷' if LANG == 'fr' else 'English 🇬🇧'}`\n"
        f"**Support :** [Rejoindre]({SUPPORT_URL})")
    e.set_thumbnail(url=bot.user.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
@commands.bot_has_permissions(add_reactions=True)
async def poll(ctx, *, question: str):
    e = mk_embed("📊 Sondage", f"**{question}**\n\n👍 **Pour** · 👎 **Contre**",
                 footer=f"Sondage de {ctx.author.display_name} · {BOT_NAME}")
    msg = await ctx.send(embed=e)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command()
async def roleinfo(ctx, role: discord.Role):
    perms = ", ".join(p.replace("_", " ").title() for p, v in role.permissions if v)[:500] or "Aucune"
    e = mk_embed(f"🏷️ Rôle — {role.name}",
        f"**ID :** `{role.id}`\n**Couleur :** `{role.color}`\n"
        f"**Membres :** `{len(role.members)}`\n"
        f"**Mentionnable :** `{'Oui' if role.mentionable else 'Non'}`\n"
        f"**Permissions :** {perms}",
        color=role.color.value or BOT_COLOR)
    await ctx.send(embed=e)

BALL = [
    "🟢 Oui, absolument !", "🟢 Sans aucun doute.", "🟢 C'est certain !", "🟢 Compte là-dessus.",
    "🟡 Peut-être...", "🟡 Difficile à dire.", "🟡 Concentre-toi et redemande.",
    "🔴 Non, je ne pense pas.", "🔴 Mes sources disent non.", "🔴 Très peu probable.",
]
COMPLIMENTS = [
    "Tu es vraiment incroyable ! 🌟", "Le serveur est bien mieux avec toi 💫",
    "Tu es une source d'inspiration ✨", "Ta présence illumine ce Discord 🌸",
    "Tu es quelqu'un de vraiment formidable 🎉", "On a de la chance de t'avoir ici 🍀",
]

@bot.command()
async def coin(ctx):
    await ctx.send(embed=mk_embed("🪙 Pile ou Face", random.choice(["🪙 **Pile**", "🪙 **Face**"])))

@bot.command()
async def roll(ctx, maximum: int = 100):
    if maximum < 2:
        return await ctx.send(embed=mk_embed("❌ Erreur", "Le max doit être ≥ `2`.", 0xE74C3C), delete_after=5)
    await ctx.send(embed=mk_embed("🎲 Dé lancé", f"Résultat : **{random.randint(1, maximum)}** *(1 – {maximum})*"))

@bot.command(name="8ball")
async def _8ball(ctx, *, question: str = None):
    if not question:
        return await ctx.send(embed=mk_embed("❌ Question manquante", "Usage : `!8ball <question>`", 0xE74C3C), delete_after=5)
    await ctx.send(embed=mk_embed("🎱 8-Ball", f"**❓ {question}**\n\n{random.choice(BALL)}"))

@bot.command()
async def ratio(ctx, member: discord.Member = None):
    await ctx.send(embed=mk_embed("📊 Ratio", f"{(member or ctx.author).mention} s'est fait ratio 💀"))

@bot.command()
async def sus(ctx, member: discord.Member = None):
    t = member or ctx.author
    pct = random.randint(0, 100)
    c   = 0xE74C3C if pct > 70 else (0xE67E22 if pct > 40 else 0x2ECC71)
    await ctx.send(embed=mk_embed("📡 Sus Meter", f"{t.mention} → **{pct}% sus** 🔍", c))

@bot.command()
async def pp(ctx, member: discord.Member = None):
    t    = member or ctx.author
    size = random.randint(0, 20)
    await ctx.send(embed=mk_embed("📏 PP Meter", f"{t.mention}\n`8{'=' * size}D` — `{size} cm`"))

@bot.command()
async def mock(ctx, *, text: str = None):
    if not text:
        return await ctx.send(embed=mk_embed("❌ Texte manquant", "Usage : `!mock <texte>`", 0xE74C3C), delete_after=5)
    await ctx.send(embed=mk_embed("🤪 Mock",
        "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text))))

@bot.command()
async def choose(ctx, *, options: str = None):
    if not options or "|" not in options:
        return await ctx.send(embed=mk_embed("❌ Erreur", "Usage : `!choose opt1 | opt2 | opt3`", 0xE74C3C), delete_after=5)
    choices = [o.strip() for o in options.split("|") if o.strip()]
    if len(choices) < 2:
        return await ctx.send(embed=mk_embed("❌ Erreur", "Donne au moins **2 options** séparées par `|`", 0xE74C3C), delete_after=5)
    await ctx.send(embed=mk_embed("🎯 Choix", f"J'ai choisi → **{random.choice(choices)}** 🎲"))

@bot.command()
async def love(ctx, member: discord.Member = None):
    if not member:
        return await ctx.send(embed=mk_embed("❌ Membre manquant", "Usage : `!love @membre`", 0xE74C3C), delete_after=5)
    pct = random.randint(0, 100)
    bar = "❤️" * (pct // 10) + "🖤" * (10 - pct // 10)
    c   = 0xE74C3C if pct >= 70 else (0xE67E22 if pct >= 40 else 0x95A5A6)
    await ctx.send(embed=mk_embed("💘 Love Meter",
        f"{ctx.author.mention} 💕 {member.mention}\n\n{bar}\n\n**{pct}% compatible** 💌", c))

@bot.command()
async def compliment(ctx, member: discord.Member = None):
    t = member or ctx.author
    await ctx.send(embed=mk_embed("🌟 Compliment", f"{t.mention} — {random.choice(COMPLIMENTS)}", 0xF39C12))

@bot.command(name="boten")
async def bot_en(ctx):
    global LANG
    if LANG == "en":
        return await ctx.send(embed=mk_embed("🌍 Language", tr("lang_same"), 0xE67E22), delete_after=4)
    LANG = "en"
    await ctx.send(embed=mk_embed("🌍 Language", tr("lang_ok")))

@bot.command(name="botfr")
async def bot_fr(ctx):
    global LANG
    if LANG == "fr":
        return await ctx.send(embed=mk_embed("🌍 Langue", tr("lang_same"), 0xE67E22), delete_after=4)
    LANG = "fr"
    await ctx.send(embed=mk_embed("🌍 Langue", tr("lang_ok")))
@bot.command(name="help")
async def help_cmd(ctx):
    if LANG == "en":
        e = discord.Embed(title="📖 Block2Bot",
            description=f"Prefix: `!`  ·  [Support Server]({SUPPORT_URL})",
            color=BOT_COLOR, timestamp=datetime.now(timezone.utc))
        e.set_thumbnail(url=bot.user.display_avatar.url)
        e.add_field(name="🤖 AI",         inline=False, value="`!ask <question>` — Ask the AI\n`!ia` — Auto-reply *(admin)*")
        e.add_field(name="🎮 Fun",         inline=False, value="`!helpfun` — All fun commands")
        e.add_field(name="🌍 Utilities",   inline=False, value="`!helputil` — All utility commands")
        if is_mod(ctx):
            e.add_field(name="🛡️ Moderation", inline=False, value="`!helpmodo` — All staff commands")
        e.add_field(name="🌐 Language",    inline=False, value="`!botfr` — Passer en Français 🇫🇷")
    else:
        e = discord.Embed(title="📖 Block2Bot",
            description=f"Préfixe : `!`  ·  [Serveur Support]({SUPPORT_URL})",
            color=BOT_COLOR, timestamp=datetime.now(timezone.utc))
        e.set_thumbnail(url=bot.user.display_avatar.url)
        e.add_field(name="🤖 IA",          inline=False, value="`!ask <question>` — Poser une question à l'IA\n`!ia` — Mode auto *(admin)*")
        e.add_field(name="🎮 Fun",          inline=False, value="`!helpfun` — Toutes les commandes fun")
        e.add_field(name="🌍 Utilitaires",  inline=False, value="`!helputil` — Tous les utilitaires")
        if is_mod(ctx):
            e.add_field(name="🛡️ Modération", inline=False, value="`!helpmodo` — Toutes les commandes staff")
        e.add_field(name="🌐 Langue",       inline=False, value="`!boten` — Switch to English 🇬🇧")
    e.set_footer(text=f"Block2BlockFr™  ·  {ctx.author.display_name}")
    await ctx.send(embed=e)

@bot.command(name="helpfun")
async def help_fun(ctx):
    if LANG == "en":
        e = discord.Embed(title="🎮 Fun Commands", color=BOT_COLOR, timestamp=datetime.now(timezone.utc))
        e.add_field(name="🪙 !coin",                  value="Flip a coin — Heads or Tails",           inline=False)
        e.add_field(name="🎲 !roll [max]",            value="Random number 1–max (default 100)",       inline=False)
        e.add_field(name="🎱 !8ball <question>",      value="Ask the magic 8-Ball 🔮",                inline=False)
        e.add_field(name="📊 !ratio [@member]",       value="Someone just got ratio'd 💀",             inline=False)
        e.add_field(name="📡 !sus [@member]",         value="Impostor percentage detector 🔍",         inline=False)
        e.add_field(name="📏 !pp [@member]",          value="PP size meter",                           inline=False)
        e.add_field(name="🤪 !mock <text>",           value="tUrNs YoUr TeXt InTo ThIs",              inline=False)
        e.add_field(name="🎯 !choose A | B | C",     value="Let the bot pick between your options",   inline=False)
        e.add_field(name="💘 !love @member",          value="Calculate love compatibility %",           inline=False)
        e.add_field(name="🌟 !compliment [@member]", value="Send a wholesome compliment",              inline=False)
    else:
        e = discord.Embed(title="🎮 Commandes Fun", color=BOT_COLOR, timestamp=datetime.now(timezone.utc))
        e.add_field(name="🪙 !coin",                  value="Pile ou face — à toi de jouer !",              inline=False)
        e.add_field(name="🎲 !roll [max]",            value="Nombre aléatoire 1–max (défaut 100)",          inline=False)
        e.add_field(name="🎱 !8ball <question>",      value="Pose une question à la boule magique 🔮",      inline=False)
        e.add_field(name="📊 !ratio [@membre]",       value="Quelqu'un vient de se faire ratio 💀",         inline=False)
        e.add_field(name="📡 !sus [@membre]",         value="Détecte ton pourcentage d'imposteur 🔍",       inline=False)
        e.add_field(name="📏 !pp [@membre]",          value="Mesureur de baguette 🥖",                     inline=False)
        e.add_field(name="🤪 !mock <texte>",          value="tRaNsFoRmE n'ImPoRtE qUeL tExTe",             inline=False)
        e.add_field(name="🎯 !choose A | B | C",     value="Le bot choisit entre plusieurs options",        inline=False)
        e.add_field(name="💘 !love @membre",          value="Calcule la compatibilité amoureuse 💌",        inline=False)
        e.add_field(name="🌟 !compliment [@membre]", value="Envoie un joli compliment à un membre",         inline=False)
    e.set_footer(text=f"Block2BlockFr™  ·  {ctx.author.display_name}")
    await ctx.send(embed=e)

@bot.command(name="helputil")
async def help_util(ctx):
    if LANG == "en":
        e = discord.Embed(title="🌍 Utility Commands", color=BOT_COLOR, timestamp=datetime.now(timezone.utc))
        e.add_field(name="🤖 !ask <question>",    value="Ask the AI — memory + auto web search",          inline=False)
        e.add_field(name="🟢/🔴 !ia",            value="Toggle AI auto-reply in channel *(admin)*",       inline=False)
        e.add_field(name="🏓 !ping",              value="Bot latency — 🟢 good · 🟡 ok · 🔴 bad",       inline=False)
        e.add_field(name="⏰ !time [country]",    value="Current time — france, usa, japan, uk...",        inline=False)
        e.add_field(name="👤 !userinfo [@member]",value="Member info — ID, roles, join & creation dates", inline=False)
        e.add_field(name="🏰 !serverinfo",        value="Server stats — members, channels, roles, owner", inline=False)
        e.add_field(name="🖼️ !avatar [@member]", value="View a member's avatar in full resolution",       inline=False)
        e.add_field(name="🤖 !botinfo",           value="Bot stats — servers, members, ping, language",   inline=False)
        e.add_field(name="📊 !poll <question>",   value="Create a quick 👍/👎 vote in this channel",     inline=False)
        e.add_field(name="🏷️ !roleinfo @role",    value="Role details — color, members, permissions",     inline=False)
        e.add_field(name="🌐 !boten / !botfr",    value="Switch bot language between English and French", inline=False)
    else:
        e = discord.Embed(title="🌍 Commandes Utilitaires", color=BOT_COLOR, timestamp=datetime.now(timezone.utc))
        e.add_field(name="🤖 !ask <question>",   value="Pose une question à l'IA — mémoire + web auto",       inline=False)
        e.add_field(name="🟢/🔴 !ia",           value="Active/désactive l'IA automatique dans le salon *(admin)*", inline=False)
        e.add_field(name="🏓 !ping",             value="Latence du bot — 🟢 bon · 🟡 moyen · 🔴 mauvais",    inline=False)
        e.add_field(name="⏰ !time [pays]",       value="Heure actuelle — france, usa, japon, uk, maroc...",   inline=False)
        e.add_field(name="👤 !userinfo [@membre]",value="Infos membre — ID, rôles, dates de rejointe et création", inline=False)
        e.add_field(name="🏰 !serverinfo",       value="Stats du serveur — membres, salons, rôles, proprio",  inline=False)
        e.add_field(name="🖼️ !avatar [@membre]", value="Voir l'avatar d'un membre en pleine résolution",       inline=False)
        e.add_field(name="🤖 !botinfo",          value="Stats du bot — serveurs, membres, ping, langue",       inline=False)
        e.add_field(name="📊 !poll <question>",  value="Créer un vote rapide 👍/👎 dans le salon",            inline=False)
        e.add_field(name="🏷️ !roleinfo @rôle",   value="Détails d'un rôle — couleur, membres, permissions",   inline=False)
        e.add_field(name="🌐 !boten / !botfr",   value="Changer la langue du bot (français / anglais)",        inline=False)
    e.set_footer(text=f"Block2BlockFr™  ·  {ctx.author.display_name}")
    await ctx.send(embed=e)

@bot.command(name="helpmodo")
async def help_modo(ctx):
    if not is_mod(ctx):
        return await ctx.send(embed=mk_embed("❌ Accès refusé",
            "Ces commandes sont réservées aux modérateurs.", 0xE74C3C), delete_after=5)
    if LANG == "en":
        e = discord.Embed(title="🛡️ Moderation Commands", description="Staff-only commands",
                          color=0xE74C3C, timestamp=datetime.now(timezone.utc))
        e.add_field(name="👢 !kick @member [reason]",          value="Kick a member from the server",                    inline=False)
        e.add_field(name="🔨 !ban @member [reason]",           value="Permanently ban a member",                         inline=False)
        e.add_field(name="✅ !unban <ID or name>",             value="Unban a member from the ban list",                 inline=False)
        e.add_field(name="🔇 !exclure @member [min] [reason]",value="Timeout a member — default 10 min, max 28 days",  inline=False)
        e.add_field(name="🔊 !unexclure @member",             value="Remove a member's timeout immediately",             inline=False)
        e.add_field(name="⚠️ !warn @member [reason]",         value="Issue a warning — DM automatically sent",          inline=False)
        e.add_field(name="📋 !warns @member",                 value="View the full warning history of a member",         inline=False)
        e.add_field(name="🗑️ !clearwarn @member",             value="Erase all warnings from a member",                 inline=False)
        e.add_field(name="🧹 !clear [n]",                     value="Bulk delete 1 to 100 messages",                    inline=False)
        e.add_field(name="⏱️ !slowmode [seconds]",            value="Set channel slowmode — 0 to disable",              inline=False)
        e.add_field(name="🔒 !lock / 🔓 !unlock",            value="Lock or unlock the channel",                       inline=False)
        e.add_field(name="📢 !announce #channel <msg>",       value="Send a clean embed announcement *(admin)*",        inline=False)
        e.add_field(name="✏️ !setnick @member <nick>",        value="Change a member's server nickname",                inline=False)
        e.add_field(name="🌐 !serveurs",                      value="List all servers where the bot is present *(B2B admin only)*", inline=False)
        e.add_field(name="🎫 !ticketsetup",                   value="Deploy the support ticket panel in this channel *(admin)*", inline=False)
    else:
        e = discord.Embed(title="🛡️ Commandes Modération", description="Réservées au staff",
                          color=0xE74C3C, timestamp=datetime.now(timezone.utc))
        e.add_field(name="👢 !kick @membre [raison]",          value="Expulser un membre du serveur",                        inline=False)
        e.add_field(name="🔨 !ban @membre [raison]",           value="Bannir définitivement un membre",                      inline=False)
        e.add_field(name="✅ !unban <ID ou nom>",              value="Débannir un membre de la liste des bannis",             inline=False)
        e.add_field(name="🔇 !exclure @membre [min] [raison]",value="Exclure temporairement — défaut 10 min, max 28 jours", inline=False)
        e.add_field(name="🔊 !unexclure @membre",             value="Retirer l'exclusion d'un membre immédiatement",         inline=False)
        e.add_field(name="⚠️ !warn @membre [raison]",         value="Avertir un membre — DM envoyé automatiquement",        inline=False)
        e.add_field(name="📋 !warns @membre",                 value="Voir l'historique complet des avertissements d'un membre", inline=False)
        e.add_field(name="🗑️ !clearwarn @membre",             value="Effacer tous les avertissements d'un membre",           inline=False)
        e.add_field(name="🧹 !clear [n]",                     value="Supprimer de 1 à 100 messages en masse",               inline=False)
        e.add_field(name="⏱️ !slowmode [secondes]",           value="Définir le slowmode du salon — 0 pour désactiver",     inline=False)
        e.add_field(name="🔒 !lock / 🔓 !unlock",            value="Verrouiller ou déverrouiller le salon",                inline=False)
        e.add_field(name="📢 !announce #salon <message>",     value="Envoyer une annonce propre en embed *(admin)*",        inline=False)
        e.add_field(name="✏️ !setnick @membre <pseudo>",      value="Modifier le pseudo serveur d'un membre",               inline=False)
        e.add_field(name="🌐 !serveurs",                      value="Lister tous les serveurs où le bot est présent *(admin B2B only)*", inline=False)
        e.add_field(name="🎫 !ticketsetup",                   value="Déployer le panneau de support tickets dans ce salon *(admin)*", inline=False)
    e.set_footer(text=f"Block2BlockFr™  ·  {ctx.author.display_name}")
    await ctx.send(embed=e)

bot.run(TOKEN)
