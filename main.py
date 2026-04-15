"""
Bot Anti-Spam para Discord
Dependências: pip install discord.py python-dotenv

Lembrando: o código aqui possui mais funções do que as apresentadas no vídeo. 
Dêem uma lida na source ou utilizem uma IA pra facilitar os estudos!

Bora pra cima, purplecoders!
Ass: Franco
"""

import os
import re
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


def parse_guild_int_map(raw_value: str) -> dict:
    mapping = {}
    if not raw_value:
        return mapping

    for item in re.split(r"[;,]", raw_value):
        pair = item.strip()
        if not pair or ":" not in pair:
            continue

        guild_id_str, value_str = pair.split(":", 1)
        guild_id_str = guild_id_str.strip()
        value_str = value_str.strip()
        if not guild_id_str or not value_str:
            continue

        try:
            mapping[int(guild_id_str)] = int(value_str)
        except ValueError:
            print(f"[AVISO] Entrada inválida ignorada em mapa por guild: {pair}")

    return mapping

# ============================================================
# CONFIGURAÇÕES - Editem aqui, purplecoders!
# ============================================================
CONFIG = {
    "token": os.getenv("DISCORD_TOKEN", ""),
    "log_channel_id": int(os.getenv("LOG_CHANNEL_ID", 0) or 0),
    "log_channel_ids": parse_guild_int_map(os.getenv("LOG_CHANNEL_IDS", "")),
    "shame_channel_ids": parse_guild_int_map(os.getenv("SHAME_CHANNEL_IDS", "")),

    # IDs dos cargos isentos. Modo Desenvolvedor > clique direito no cargo > Copiar ID
    "exempt_role_ids": [
        int(i) for i in os.getenv("EXEMPT_ROLE_IDS", "").split(",") if i.strip()
    ],

    # Flood: X mensagens em Y segundos
    "flood_limit": 5,
    "flood_window_sec": 8,

    # Punição fixa: timeout
    "punishment": "timeout",
    # 3 dias = 4320 minutos
    "timeout_minutes": 4320,

    # Score mínimo para considerar spam (0–100)
    "score_threshold": 60,
}

# ============================================================
# PADRÕES DE DETECÇÃO DE TEXTO
# ============================================================
SPAM_PATTERNS = [
    {
        "name": "Convite Discord externo",
        "regex": re.compile(r"discord\.(gg|com/invite)/[a-zA-Z0-9]+", re.I),
        "score": 80,
    },
    {
        "name": "Crypto / NFT / Airdrop",
        "regex": re.compile(
            r"\b(airdrop|nft|free\s*crypto|pump|giveaway.*token|mint\s*now|claim.*token|presale)\b", re.I
        ),
        "score": 70,
    },
    {
        "name": 'Golpe estilo "Elon Musk"',
        "regex": re.compile(
            r"\b(elon\s*musk|elon)\b.{0,60}\b(crypto|bitcoin|btc|eth|token|double|investment)\b", re.I
        ),
        "score": 90,
    },
    {
        "name": "Spam NSFW / Cam",
        "regex": re.compile(
            r"\b(cam\s*girl|camgirl|nsfw|onlyfans|only\s*fans|join.*cam|cam.*discord)\b", re.I
        ),
        "score": 95,
    },
    {
        "name": "Link encurtado suspeito",
        "regex": re.compile(
            r"\b(bit\.ly|tinyurl\.com|t\.co|rb\.gy|cutt\.ly|short\.gg)\b.{0,40}\b(free|earn|join|click)\b",
            re.I,
        ),
        "score": 75,
    },
    {
        "name": "Promessa de dinheiro",
        "regex": re.compile(r"\b(earn|ganhe|ganhar|lucre)\b.{0,30}(\$|USD|BRL|reais)", re.I),
        "score": 65,
    },
]

MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".avi"}
TIMEOUT_COUNTERS_PATH = Path("timeout_counters.json")


# ============================================================
# CONTROLE DE FLOOD + RASTREAMENTO CROSS-CHANNEL
# ============================================================
# { (guild_id, user_id): {"messages": [(channel_id, content, timestamp), ...]} }
flood_tracker: dict = defaultdict(lambda: {"messages": []})
timeout_counters: dict = {}


def load_timeout_counters() -> dict:
    if not TIMEOUT_COUNTERS_PATH.exists():
        return {}

    try:
        with TIMEOUT_COUNTERS_PATH.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[AVISO] Falha ao carregar {TIMEOUT_COUNTERS_PATH}: {exc}")

    return {}


def save_timeout_counters() -> None:
    try:
        with TIMEOUT_COUNTERS_PATH.open("w", encoding="utf-8") as fp:
            json.dump(timeout_counters, fp, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"[ERRO] Falha ao salvar {TIMEOUT_COUNTERS_PATH}: {exc}")


def increment_timeout_count(guild_id: int, user_id: int) -> int:
    key = f"{guild_id}:{user_id}"
    current = int(timeout_counters.get(key, 0)) + 1
    timeout_counters[key] = current
    save_timeout_counters()
    return current


def format_infection_count(count: int) -> str:
    if count == 1:
        return "PRIMEIRA"
    if count == 2:
        return "SEGUNDA"
    if count == 3:
        return "TERCEIRA"
    if count == 4:
        return "QUARTA"
    if count == 5:
        return "QUINTA"
    return f"{count}a"


def get_log_channel_id(guild_id: int) -> int:
    return CONFIG["log_channel_ids"].get(guild_id, CONFIG["log_channel_id"])


def get_shame_channel_id(guild_id: int) -> int:
    return CONFIG["shame_channel_ids"].get(guild_id, 0)


def check_flood(guild_id: int, user_id: int, channel_id: int, content: str) -> tuple:
    now = datetime.now(timezone.utc)
    window = timedelta(seconds=CONFIG["flood_window_sec"])
    data = flood_tracker[(guild_id, user_id)]

    # Remove entradas fora da janela de tempo
    data["messages"] = [
        (ch, c, t) for ch, c, t in data["messages"]
        if now - t < window
    ]
    data["messages"].append((channel_id, content, now))
    msgs = data["messages"]

    # Flood no mesmo canal
    same_channel = [m for m in msgs if m[0] == channel_id]
    duplicates = sum(1 for _, c, _ in same_channel if c == content)

    if duplicates >= 3:
        return True, f"Conteúdo idêntico enviado {duplicates}x no mesmo canal"
    if len(same_channel) >= CONFIG["flood_limit"]:
        return True, f"{len(same_channel)} msgs no mesmo canal em {CONFIG['flood_window_sec']}s"

    # Cross-channel: mesmo conteúdo espalhado em canais diferentes
    channels_used = {ch for ch, _, _ in msgs}
    if len(channels_used) >= 2:
        unique_contents = {c for _, c, _ in msgs}
        if len(unique_contents) <= 2:
            return True, f"Mesmo conteúdo em {len(channels_used)} canais diferentes"

    # Cross-channel: volume alto em 3+ canais em pouco tempo
    if len(channels_used) >= 3 and len(msgs) >= 4:
        return True, f"Spam em {len(channels_used)} canais ({len(msgs)} msgs em {CONFIG['flood_window_sec']}s)"

    return False, ""


# ============================================================
# ANÁLISE DE SPAM
# ============================================================
def analyze_message(message: discord.Message) -> tuple:
    total_score = 0
    reasons = []
    content = message.content

    # Padrões de texto
    for pattern in SPAM_PATTERNS:
        if pattern["regex"].search(content):
            total_score += pattern["score"]
            reasons.append(pattern["name"])

    # @everyone / @here → score máximo direto
    if message.mention_everyone:
        total_score += 100
        reasons.append("Menção @everyone ou @here")

    # 3+ usuários mencionados
    unique_mentions = {m.id for m in message.mentions}
    if len(unique_mentions) >= 3:
        total_score += 70
        reasons.append(f"Múltiplas menções ({len(unique_mentions)} usuários)")

    # 2+ arquivos de mídia → alerta imediato
    media_attachments = [
        a for a in message.attachments
        if any(a.filename.lower().endswith(ext) for ext in MEDIA_EXTENSIONS)
    ]
    if len(media_attachments) >= 2:
        total_score += 80
        reasons.append(f"{len(media_attachments)} arquivos de mídia anexados")

    # Bônus por combinações suspeitas
    has_mention = message.mention_everyone or len(unique_mentions) >= 3
    has_discord_link = bool(re.search(r"discord\.(gg|com/invite)/[a-zA-Z0-9]+", content, re.I))

    if has_mention and has_discord_link:
        total_score += 30
        reasons.append("Combinação: menção + convite Discord")

    if has_mention and len(media_attachments) >= 2:
        total_score += 30
        reasons.append("Combinação: menção + múltiplos anexos")

    if len(media_attachments) >= 2 and has_discord_link:
        total_score += 30
        reasons.append("Combinação: múltiplos anexos + convite Discord")

    return min(total_score, 100), reasons


# ============================================================
# BOT
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


def get_punish_block_reason(member: discord.Member, punishment: str) -> str:
    me = member.guild.me
    if me is None:
        return "Bot não encontrado no cache da guild (guild.me=None)."

    permissions_needed = {
        "timeout": ["moderate_members"],
    }
    needed = permissions_needed.get(punishment, [])
    missing = [perm for perm in needed if not getattr(me.guild_permissions, perm, False)]
    if missing:
        return f"Permissões ausentes para {punishment}: {', '.join(missing)}"

    if member == member.guild.owner:
        return "Não é possível punir o dono do servidor."

    # Regra de hierarquia do Discord: o cargo mais alto do bot precisa estar acima do alvo.
    if me.top_role <= member.top_role:
        return (
            "Hierarquia de cargos inválida "
            f"(cargo bot: {me.top_role.name} <= cargo alvo: {member.top_role.name})."
        )

    return ""


async def punish(member: discord.Member, reason: str) -> bool:
    punishment = "timeout"

    block_reason = get_punish_block_reason(member, punishment)
    if block_reason:
        print(
            "[AVISO] Bloqueio de punição | "
            f"guild={member.guild.name} ({member.guild.id}) | "
            f"alvo={member} ({member.id}) | motivo={block_reason}"
        )
        return False

    try:
        until = datetime.now(timezone.utc) + timedelta(minutes=CONFIG["timeout_minutes"])
        await member.timeout(until, reason=reason)
        return True
    except discord.Forbidden as exc:
        print(
            "[AVISO] Discord proibiu a punição | "
            f"guild={member.guild.name} ({member.guild.id}) | "
            f"alvo={member} ({member.id}) | tipo={punishment} | erro={exc}"
        )
        return False
    except discord.HTTPException as exc:
        print(
            "[ERRO] Falha HTTP ao punir usuário | "
            f"guild={member.guild.name} ({member.guild.id}) | "
            f"alvo={member} ({member.id}) | tipo={punishment} | erro={exc}"
        )
        return False


async def log_action(guild: discord.Guild, message: discord.Message, reasons: list, score: int):
    log_channel_id = get_log_channel_id(guild.id)
    if not log_channel_id:
        return

    channel = guild.get_channel(log_channel_id)
    if not channel:
        try:
            channel = await guild.fetch_channel(log_channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
            print(
                f"[AVISO] Não foi possível acessar canal de log {log_channel_id} "
                f"na guild {guild.name} ({guild.id}) | erro={exc}"
            )
            return

    if not channel:
        print(f"[AVISO] Canal de log {log_channel_id} não encontrado na guild {guild.name} ({guild.id})")
        return

    embed = discord.Embed(
        title="🚫 Spam removido",
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Usuário", value=f"{message.author} (`{message.author.id}`)", inline=False)
    embed.add_field(name="Canal", value=message.channel.mention, inline=True)
    embed.add_field(name="Score", value=f"{score}/100", inline=True)
    embed.add_field(name="Motivos", value="\n".join(f"• {r}" for r in reasons), inline=False)

    if message.content:
        preview = message.content[:300] + ("..." if len(message.content) > 300 else "")
        embed.add_field(name="Conteúdo", value=f"```{preview}```", inline=False)

    if message.attachments:
        attach_list = "\n".join(f"• {a.filename}" for a in message.attachments[:10])
        embed.add_field(name="Anexos", value=attach_list, inline=False)

    embed.set_footer(text=f"Punição: {CONFIG['punishment']}")
    try:
        await channel.send(embed=embed)
    except discord.Forbidden as exc:
        print(
            f"[AVISO] Sem permissão para enviar log no canal {log_channel_id} "
            f"na guild {guild.name} ({guild.id}) | erro={exc}"
        )
    except discord.HTTPException as exc:
        print(
            f"[ERRO] Falha HTTP ao enviar log no canal {log_channel_id} "
            f"na guild {guild.name} ({guild.id}) | erro={exc}"
        )


async def send_shame_wall(guild: discord.Guild, member: discord.Member, timeout_count: int):
    shame_channel_id = get_shame_channel_id(guild.id)
    if not shame_channel_id:
        print(f"[AVISO] Hall of Shame não configurado para guild {guild.name} ({guild.id})")
        return

    channel = guild.get_channel(shame_channel_id)
    if not channel:
        try:
            channel = await guild.fetch_channel(shame_channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
            print(
                f"[AVISO] Não foi possível acessar canal do Hall of Shame {shame_channel_id} "
                f"na guild {guild.name} ({guild.id}) | erro={exc}"
            )
            return

    if not channel:
        print(f"[AVISO] Canal do mural {shame_channel_id} não encontrado na guild {guild.name} ({guild.id})")
        return

    occurrence = format_infection_count(timeout_count)
    if timeout_count >= 2:
        shame_text = (
            "⚡ **Hall of Shame** ⚡\n"
            f"{member.mention} foi infectado pela **{occurrence}** vez!\n"
            "Realmente uma pessoa dedicada, comprometida a baixar tudo e qualquer tipo de coisa que vê na frente!\n"
            "Nos vemos em breve novamente, zumbi roxo."
        )
    else:
        shame_text = (
            "⚡ **Hall of Shame** ⚡\n"
            f"{member.mention} foi infectado pela **{occurrence}** vez. Colocamos ele em quarentena! 💀\n"
            "Nos vemos em breve, companheiro!\n"
            "Recomendamos formatar o computador e ativar o Windows Defender! 💜⚡"
        )
    try:
        await channel.send(shame_text)
    except discord.Forbidden as exc:
        print(
            f"[AVISO] Sem permissão para enviar Hall of Shame no canal {shame_channel_id} "
            f"na guild {guild.name} ({guild.id}) | erro={exc}"
        )
    except discord.HTTPException as exc:
        print(
            f"[ERRO] Falha HTTP ao enviar Hall of Shame no canal {shame_channel_id} "
            f"na guild {guild.name} ({guild.id}) | erro={exc}"
        )


def is_exempt(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    member_role_ids = {r.id for r in member.roles}
    return bool(member_role_ids & set(CONFIG["exempt_role_ids"]))


@bot.event
async def on_ready():
    global timeout_counters
    timeout_counters = load_timeout_counters()

    print(f"✅ Bot conectado como {bot.user} ({bot.user.id})")
    print(f"   Punição: {CONFIG['punishment']} | Threshold: {CONFIG['score_threshold']}")
    if CONFIG["log_channel_ids"]:
        print(f"   Canais de log por guild: {len(CONFIG['log_channel_ids'])} configurado(s)")
    elif CONFIG["log_channel_id"]:
        print(f"   Canal de log padrão: {CONFIG['log_channel_id']}")
    if CONFIG["shame_channel_ids"]:
        print(f"   Canais do mural por guild: {len(CONFIG['shame_channel_ids'])} configurado(s)")

    for guild in bot.guilds:
        log_channel_id = get_log_channel_id(guild.id)
        shame_channel_id = get_shame_channel_id(guild.id)
        print(
            f"   Guild: {guild.name} ({guild.id}) | "
            f"Log: {log_channel_id or 'não configurado'} | "
            f"Mural: {shame_channel_id or 'não configurado'}"
        )
    print(f"   Contadores de timeout carregados: {len(timeout_counters)} registro(s)")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    if is_exempt(message.author):
        await bot.process_commands(message)
        return

    # 1. Flood + cross-channel
    is_flood, flood_reason = check_flood(
        message.guild.id, message.author.id, message.channel.id, message.content
    )

    # 2. Conteúdo + attachments + menções
    score, reasons = analyze_message(message)

    spam_detected = is_flood or score >= CONFIG["score_threshold"]

    if spam_detected:
        if is_flood:
            reasons.insert(0, f"Flood: {flood_reason}")
            score = max(score, 85)

        try:
            await message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass

        try:
            await message.channel.send(
                f"⚠️ {message.author.mention} Sua mensagem foi removida por violar as regras do servidor.",
                delete_after=8,
            )
        except discord.Forbidden:
            pass

        timeout_applied = await punish(message.author, reason=f"Spam: {', '.join(reasons)}")
        await log_action(message.guild, message, reasons, score)
        if timeout_applied:
            timeout_count = increment_timeout_count(message.guild.id, message.author.id)
            await send_shame_wall(message.guild, message.author, timeout_count)
        print(f"[SPAM] {message.author} | Score: {score} | {reasons}")
        return

    await bot.process_commands(message)


# ============================================================
# COMANDO DE TESTE (apenas admins)
# ============================================================
@bot.command(name="testspam")
@commands.has_permissions(administrator=True)
async def test_spam(ctx, *, texto: str):
    """Testa se um texto seria detectado. Uso: !testspam <texto>"""
    total_score = 0
    reasons = []
    for pattern in SPAM_PATTERNS:
        if pattern["regex"].search(texto):
            total_score += pattern["score"]
            reasons.append(pattern["name"])
    score = min(total_score, 100)
    is_spam = score >= CONFIG["score_threshold"]

    embed = discord.Embed(
        title="🔍 Resultado da análise",
        color=discord.Color.red() if is_spam else discord.Color.green(),
    )
    embed.add_field(name="Score", value=f"{score}/100", inline=True)
    embed.add_field(name="É spam?", value="Sim ✅" if is_spam else "Não ❌", inline=True)
    embed.add_field(
        name="Obs",
        value="Attachments, menções e cross-channel só são analisados em mensagens reais.",
        inline=False,
    )
    if reasons:
        embed.add_field(name="Padrões encontrados", value="\n".join(f"• {r}" for r in reasons), inline=False)
    await ctx.reply(embed=embed)


# ============================================================
# INICIAR
# ============================================================
if __name__ == "__main__":
    token = CONFIG["token"]
    if not token:
        raise ValueError("Defina DISCORD_TOKEN no arquivo .env")
    bot.run(token)