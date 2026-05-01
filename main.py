"""
Bot Anti-Spam para Discord
Dependencias: pip install discord.py python-dotenv

Lembrando: o codigo aqui possui mais funcoes do que as apresentadas no video.
Deem uma lida na source ou utilizem uma IA pra facilitar os estudos.

Bora pra cima, purplecoders!
Ass: Franco
"""

import json
import os
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

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
            print(f"[AVISO] Entrada invalida ignorada em mapa por guild: {pair}")

    return mapping


def parse_int_list(raw_value: str) -> list:
    values = []
    if not raw_value:
        return values

    for item in re.split(r"[;,]", raw_value):
        item = item.strip()
        if not item:
            continue
        try:
            number = int(item)
        except ValueError:
            print(f"[AVISO] Valor inteiro invalido ignorado: {item}")
            continue
        if number > 0:
            values.append(number)

    return values


def parse_domain_list(raw_value: str) -> list:
    if not raw_value:
        return []

    domain_pattern = re.compile(r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")
    domains = []
    for item in re.split(r"[;,]", raw_value):
        value = item.strip().lower()
        if not value:
            continue

        # Aceita tanto "dominio.com" quanto entradas acidentais com URL/caminho.
        if value.startswith(("http://", "https://")):
            host = urlparse(value).netloc.lower()
        else:
            host = value.split("/", 1)[0]

        host = host.split(":", 1)[0]
        if host.startswith("www."):
            host = host[4:]

        if host and domain_pattern.fullmatch(host):
            domains.append(host)
        elif host:
            print(f"[AVISO] Dominio inválido ignorado no ALLOWED_DOMAINS: {value}")

    return domains


def parse_bool(raw_value: str, default: bool = False) -> bool:
    if raw_value is None:
        return default
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on", "sim"}


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"https?://\S+", " URL ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def extract_domains(content: str) -> list:
    domain_pattern = re.compile(r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")
    matches = re.findall(r"\S+", content)
    domains = []
    for item in matches:
        value = item.strip("<>[](){}\"'`.,!?;")
        if not value:
            continue

        if value.startswith(("http://", "https://")):
            parsed_value = value
        elif value.startswith("www.") or domain_pattern.fullmatch(value):
            parsed_value = f"http://{value}"
        else:
            continue

        try:
            host = urlparse(parsed_value).netloc.lower()
        except ValueError:
            continue
        if not host:
            continue
        host = host.split(":", 1)[0]
        if host.startswith("www."):
            host = host[4:]
        domains.append(host)
    return domains


def is_allowed_domain(domain: str) -> bool:
    for allowed in CONFIG["allowed_domains"]:
        if domain == allowed or domain.endswith(f".{allowed}"):
            return True
    return False


# ============================================================
# CONFIGURACOES
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
    "flood_limit": int(os.getenv("FLOOD_LIMIT", 5) or 5),
    "flood_window_sec": int(os.getenv("FLOOD_WINDOW_SEC", 8) or 8),

    # Progressao de timeout em minutos (1a, 2a, 3a, ...)
    "timeout_steps_minutes": parse_int_list(os.getenv("TIMEOUT_STEPS_MINUTES", "10,60,1440,4320")) or [4320],

    # Score minimo para considerar spam (0-100)
    "score_threshold": int(os.getenv("SCORE_THRESHOLD", 60) or 60),

    # Similaridade para detectar mensagens quase iguais (0-1)
    "message_similarity_threshold": float(os.getenv("MESSAGE_SIMILARITY_THRESHOLD", 0.9) or 0.9),

    # Links externos
    "external_link_score": int(os.getenv("EXTERNAL_LINK_SCORE", 55) or 55),
    "allow_discord_invites": parse_bool(os.getenv("ALLOW_DISCORD_INVITES", "false"), default=False),
    "allowed_domains": parse_domain_list(
        os.getenv(
            "ALLOWED_DOMAINS",
            "discord.com,discord.gg,discordapp.com,cdn.discordapp.com,media.discordapp.net,tenor.com,media.tenor.com,youtube.com,youtu.be,github.com,docs.python.org",
        )
    ),

    # Raid detection
    "suspicious_account_max_age_days": int(os.getenv("SUSPICIOUS_ACCOUNT_MAX_AGE_DAYS", 14) or 14),
    "raid_window_sec": int(os.getenv("RAID_WINDOW_SEC", 10) or 10),
    "raid_user_threshold": int(os.getenv("RAID_USER_THRESHOLD", 5) or 5),
    "raid_join_grace_sec": int(os.getenv("RAID_JOIN_GRACE_SEC", 900) or 900),
    "raid_cooldown_sec": int(os.getenv("RAID_COOLDOWN_SEC", 30) or 30),
}

# ============================================================
# PADROES DE DETECCAO DE TEXTO
# ============================================================
SPAM_PATTERNS = [
    {
        "key": "discord_invite",
        "name": "Convite Discord externo",
        "regex": re.compile(r"(?:discord\.gg|discord(?:app)?\.com/invite)/[a-zA-Z0-9-]+", re.I),
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
# RASTREAMENTO DE ESTADO
# ============================================================
# { (guild_id, user_id): {"messages": [(channel_id, original, normalized, timestamp), ...]} }
flood_tracker: dict = defaultdict(lambda: {"messages": []})
timeout_counters: dict = {}

# { guild_id: { user_id: {"joined_at": datetime, "suspicious": bool, "age_days": int} } }
recent_join_tracker: dict = defaultdict(dict)

# { guild_id: [(user_id, timestamp, suspicious_recent_join), ...] }
raid_message_tracker: dict = defaultdict(list)
raid_last_alert: dict = {}


# ============================================================
# CONTADOR DE TIMEOUTS
# ============================================================
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


def get_timeout_count(guild_id: int, user_id: int) -> int:
    return int(timeout_counters.get(f"{guild_id}:{user_id}", 0))


def increment_timeout_count(guild_id: int, user_id: int) -> int:
    key = f"{guild_id}:{user_id}"
    current = get_timeout_count(guild_id, user_id) + 1
    timeout_counters[key] = current
    save_timeout_counters()
    return current


def get_timeout_minutes_for_next_infraction(guild_id: int, user_id: int) -> int:
    next_count = get_timeout_count(guild_id, user_id) + 1
    steps = CONFIG["timeout_steps_minutes"]
    index = min(next_count - 1, len(steps) - 1)
    return steps[index]


def format_duration_minutes(total_minutes: int) -> str:
    if total_minutes % 1440 == 0:
        days = total_minutes // 1440
        return f"{days}d"
    if total_minutes % 60 == 0:
        hours = total_minutes // 60
        return f"{hours}h"
    return f"{total_minutes}min"


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


# ============================================================
# CANAIS POR GUILD
# ============================================================
def get_log_channel_id(guild_id: int) -> int:
    return CONFIG["log_channel_ids"].get(guild_id, CONFIG["log_channel_id"])


def get_shame_channel_id(guild_id: int) -> int:
    return CONFIG["shame_channel_ids"].get(guild_id, 0)


# ============================================================
# DETECCAO DE RAID
# ============================================================
def is_suspicious_account(member: discord.Member) -> tuple:
    age_delta = datetime.now(timezone.utc) - member.created_at
    age_days = max(age_delta.days, 0)
    return age_days <= CONFIG["suspicious_account_max_age_days"], age_days


def prune_recent_joins(guild_id: int, now: datetime) -> None:
    grace = CONFIG["raid_join_grace_sec"]
    joins = recent_join_tracker[guild_id]
    stale = [
        user_id
        for user_id, data in joins.items()
        if (now - data["joined_at"]).total_seconds() > grace
    ]
    for user_id in stale:
        joins.pop(user_id, None)


def check_raid_message_activity(guild_id: int, user_id: int) -> tuple:
    now = datetime.now(timezone.utc)
    prune_recent_joins(guild_id, now)

    join_data = recent_join_tracker[guild_id].get(user_id)
    suspicious_recent_join = bool(join_data and join_data.get("suspicious"))

    events = raid_message_tracker[guild_id]
    window_sec = CONFIG["raid_window_sec"]
    events[:] = [e for e in events if (now - e[1]).total_seconds() <= window_sec]
    events.append((user_id, now, suspicious_recent_join))

    suspicious_users = {uid for uid, _, is_suspicious in events if is_suspicious}
    if len(suspicious_users) < CONFIG["raid_user_threshold"]:
        return False, ""

    last_alert = raid_last_alert.get(guild_id)
    if last_alert and (now - last_alert).total_seconds() < CONFIG["raid_cooldown_sec"]:
        return False, ""

    raid_last_alert[guild_id] = now
    return True, (
        f"Raid suspeita: {len(suspicious_users)} contas novas suspeitas enviando mensagens "
        f"em {CONFIG['raid_window_sec']}s"
    )


# ============================================================
# CONTROLE DE FLOOD + MENSAGENS QUASE IGUAIS
# ============================================================
def check_flood(guild_id: int, user_id: int, channel_id: int, content: str, normalized_content: str) -> tuple:
    now = datetime.now(timezone.utc)
    window = timedelta(seconds=CONFIG["flood_window_sec"])
    data = flood_tracker[(guild_id, user_id)]

    # Remove entradas fora da janela de tempo
    data["messages"] = [
        (ch, original, normalized, timestamp)
        for ch, original, normalized, timestamp in data["messages"]
        if now - timestamp < window
    ]
    data["messages"].append((channel_id, content, normalized_content, now))
    msgs = data["messages"]

    # Flood no mesmo canal
    same_channel = [m for m in msgs if m[0] == channel_id]
    duplicates = sum(1 for _, _, normalized, _ in same_channel if normalized == normalized_content and normalized)

    if duplicates >= 3:
        return True, f"Conteudo identico enviado {duplicates}x no mesmo canal"

    similar_count = sum(
        1
        for _, _, previous_normalized, _ in same_channel
        if previous_normalized
        and normalized_content
        and similarity(previous_normalized, normalized_content) >= CONFIG["message_similarity_threshold"]
    )
    if similar_count >= 3:
        return True, f"Mensagens quase iguais ({similar_count}x) no mesmo canal"

    if len(same_channel) >= CONFIG["flood_limit"]:
        return True, f"{len(same_channel)} msgs no mesmo canal em {CONFIG['flood_window_sec']}s"

    # Cross-channel: mesmo conteudo espalhado em canais diferentes
    channels_used = {ch for ch, _, _, _ in msgs}
    if len(channels_used) >= 2:
        unique_contents = {normalized for _, _, normalized, _ in msgs if normalized}
        if len(unique_contents) <= 2:
            return True, f"Mesmo conteudo em {len(channels_used)} canais diferentes"

    # Cross-channel: volume alto em 3+ canais em pouco tempo
    if len(channels_used) >= 3 and len(msgs) >= 4:
        return True, f"Spam em {len(channels_used)} canais ({len(msgs)} msgs em {CONFIG['flood_window_sec']}s)"

    return False, ""


# ============================================================
# ANALISE DE SPAM
# ============================================================
def analyze_message(message: discord.Message, normalized_content: str) -> tuple:
    total_score = 0
    reasons = []
    content = message.content

    # Padroes de texto
    for pattern in SPAM_PATTERNS:
        if pattern.get("key") == "discord_invite" and CONFIG["allow_discord_invites"]:
            continue
        if pattern["regex"].search(content):
            total_score += pattern["score"]
            reasons.append(pattern["name"])

    # Links externos fora da whitelist
    blocked_domains = sorted({domain for domain in extract_domains(content) if not is_allowed_domain(domain)})
    if blocked_domains:
        total_score += CONFIG["external_link_score"]
        preview = ", ".join(blocked_domains[:4])
        suffix = "..." if len(blocked_domains) > 4 else ""
        reasons.append(f"Link externo fora da whitelist: {preview}{suffix}")

    # @everyone / @here -> score maximo direto
    if message.mention_everyone:
        total_score += 100
        reasons.append("Mencao @everyone ou @here")

    # 3+ usuarios mencionados
    unique_mentions = {m.id for m in message.mentions}
    if len(unique_mentions) >= 3:
        total_score += 70
        reasons.append(f"Multiplas mencoes ({len(unique_mentions)} usuarios)")

    # 2+ arquivos de midia -> alerta imediato
    media_attachments = [
        a for a in message.attachments
        if any(a.filename.lower().endswith(ext) for ext in MEDIA_EXTENSIONS)
    ]
    if len(media_attachments) >= 2:
        total_score += 80
        reasons.append(f"{len(media_attachments)} arquivos de midia anexados")

    # Mensagem curta com muitos simbolos apos normalizacao pode indicar tentativa de bypass
    if content and len(content) >= 10 and len(normalized_content) <= max(4, len(content) // 4):
        total_score += 20
        reasons.append("Texto com alta obfuscacao/simbolos")

    # Bonus por combinacoes suspeitas
    has_mention = message.mention_everyone or len(unique_mentions) >= 3
    has_discord_link = bool(re.search(r"(?:discord\.gg|discord(?:app)?\.com/invite)/[a-zA-Z0-9-]+", content, re.I))

    if has_mention and has_discord_link:
        total_score += 30
        reasons.append("Combinacao: mencao + convite Discord")

    if has_mention and len(media_attachments) >= 2:
        total_score += 30
        reasons.append("Combinacao: mencao + multiplos anexos")

    if len(media_attachments) >= 2 and has_discord_link:
        total_score += 30
        reasons.append("Combinacao: multiplos anexos + convite Discord")

    return min(total_score, 100), reasons


# ============================================================
# BOT
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


def get_punish_block_reason(member: discord.Member) -> str:
    me = member.guild.me
    if me is None:
        return "Bot nao encontrado no cache da guild (guild.me=None)."

    if not getattr(me.guild_permissions, "moderate_members", False):
        return "Permissao ausente para timeout: moderate_members"

    if member == member.guild.owner:
        return "Nao e possivel punir o dono do servidor."

    # Regra de hierarquia do Discord: o cargo mais alto do bot precisa estar acima do alvo.
    if me.top_role <= member.top_role:
        return (
            "Hierarquia de cargos invalida "
            f"(cargo bot: {me.top_role.name} <= cargo alvo: {member.top_role.name})."
        )

    return ""


async def punish(member: discord.Member, reason: str, timeout_minutes: int) -> bool:
    block_reason = get_punish_block_reason(member)
    if block_reason:
        print(
            "[AVISO] Bloqueio de punicao | "
            f"guild={member.guild.name} ({member.guild.id}) | "
            f"alvo={member} ({member.id}) | motivo={block_reason}"
        )
        return False

    try:
        until = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
        await member.timeout(until, reason=reason)
        return True
    except discord.Forbidden as exc:
        print(
            "[AVISO] Discord proibiu a punicao | "
            f"guild={member.guild.name} ({member.guild.id}) | "
            f"alvo={member} ({member.id}) | tipo=timeout | erro={exc}"
        )
        return False
    except discord.HTTPException as exc:
        print(
            "[ERRO] Falha HTTP ao punir usuario | "
            f"guild={member.guild.name} ({member.guild.id}) | "
            f"alvo={member} ({member.id}) | tipo=timeout | erro={exc}"
        )
        return False


async def resolve_channel(guild: discord.Guild, channel_id: int):
    channel = guild.get_channel(channel_id)
    if channel:
        return channel

    try:
        return await guild.fetch_channel(channel_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


async def log_action(guild: discord.Guild, message: discord.Message, reasons: list, score: int, timeout_minutes: int):
    log_channel_id = get_log_channel_id(guild.id)
    if not log_channel_id:
        return

    channel = await resolve_channel(guild, log_channel_id)
    if not channel:
        print(f"[AVISO] Nao foi possivel acessar canal de log {log_channel_id} na guild {guild.name} ({guild.id})")
        return

    embed = discord.Embed(
        title="Spam removido",
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Usuario", value=f"{message.author} ({message.author.id})", inline=False)
    embed.add_field(name="Canal", value=message.channel.mention, inline=True)
    embed.add_field(name="Score", value=f"{score}/100", inline=True)
    embed.add_field(name="Timeout aplicado", value=format_duration_minutes(timeout_minutes), inline=True)
    embed.add_field(name="Motivos", value="\n".join(f"- {r}" for r in reasons), inline=False)

    if message.content:
        preview = message.content[:300] + ("..." if len(message.content) > 300 else "")
        embed.add_field(name="Conteudo", value=f"```{preview}```", inline=False)

    if message.attachments:
        attach_list = "\n".join(f"- {a.filename}" for a in message.attachments[:10])
        embed.add_field(name="Anexos", value=attach_list, inline=False)

    try:
        await channel.send(embed=embed)
    except discord.Forbidden as exc:
        print(
            f"[AVISO] Sem permissao para enviar log no canal {log_channel_id} "
            f"na guild {guild.name} ({guild.id}) | erro={exc}"
        )
    except discord.HTTPException as exc:
        print(
            f"[ERRO] Falha HTTP ao enviar log no canal {log_channel_id} "
            f"na guild {guild.name} ({guild.id}) | erro={exc}"
        )


async def send_shame_wall(guild: discord.Guild, member: discord.Member, timeout_count: int, timeout_minutes: int):
    shame_channel_id = get_shame_channel_id(guild.id)
    if not shame_channel_id:
        print(f"[AVISO] Hall of Shame nao configurado para guild {guild.name} ({guild.id})")
        return

    channel = await resolve_channel(guild, shame_channel_id)
    if not channel:
        print(
            f"[AVISO] Nao foi possivel acessar canal do Hall of Shame {shame_channel_id} "
            f"na guild {guild.name} ({guild.id})"
        )
        return

    occurrence = format_infection_count(timeout_count)
    timeout_label = format_duration_minutes(timeout_minutes)

    if timeout_count >= 3:
        description = (
            f"{member.mention} foi infectado pela **{occurrence}** vez!\n"
            "Realmente uma pessoa dedicada, comprometida a baixar tudo e qualquer tipo de coisa que ve na frente!\n"
            "Nos vemos em breve novamente, zumbi roxo."
        )
    else:
        description = (
            f"{member.mention} foi infectado pela **{occurrence}** vez. Colocamos ele em quarentena!\n"
            "Nos vemos em breve, companheiro!\n"
            "Recomendamos formatar o computador e ativar o Windows Defender!"
        )

    embed = discord.Embed(
        title="Hall of Shame",
        description=description,
        color=discord.Color.dark_magenta(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Timeout", value=timeout_label, inline=True)
    embed.add_field(name="Reincidencias", value=str(timeout_count), inline=True)
    embed.set_footer(text=f"Guild: {guild.name}")

    avatar = getattr(member.display_avatar, "url", None)
    if avatar:
        embed.set_thumbnail(url=avatar)

    try:
        await channel.send(content=member.mention, embed=embed)
    except discord.Forbidden as exc:
        # Fallback para servidores sem permissao de Embed Links
        try:
            await channel.send(
                f"Hall of Shame | {member.mention} | reincidencia={timeout_count} | timeout={timeout_label}"
            )
        except (discord.Forbidden, discord.HTTPException):
            print(
                f"[AVISO] Sem permissao para enviar Hall of Shame no canal {shame_channel_id} "
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

    print(f"Bot conectado como {bot.user} ({bot.user.id})")
    print(f"Threshold: {CONFIG['score_threshold']}")
    print(f"Timeout progressivo (min): {CONFIG['timeout_steps_minutes']}")
    if CONFIG["log_channel_ids"]:
        print(f"Canais de log por guild: {len(CONFIG['log_channel_ids'])} configurado(s)")
    elif CONFIG["log_channel_id"]:
        print(f"Canal de log padrao: {CONFIG['log_channel_id']}")
    if CONFIG["shame_channel_ids"]:
        print(f"Canais do Hall por guild: {len(CONFIG['shame_channel_ids'])} configurado(s)")

    for guild in bot.guilds:
        log_channel_id = get_log_channel_id(guild.id)
        shame_channel_id = get_shame_channel_id(guild.id)
        print(
            f"Guild: {guild.name} ({guild.id}) | "
            f"Log: {log_channel_id or 'nao configurado'} | "
            f"Hall: {shame_channel_id or 'nao configurado'}"
        )
    print(f"Contadores de timeout carregados: {len(timeout_counters)} registro(s)")


@bot.event
async def on_member_join(member: discord.Member):
    suspicious, age_days = is_suspicious_account(member)
    recent_join_tracker[member.guild.id][member.id] = {
        "joined_at": datetime.now(timezone.utc),
        "suspicious": suspicious,
        "age_days": age_days,
    }

    if suspicious:
        print(
            f"[RAID] Conta suspeita entrou | guild={member.guild.name} ({member.guild.id}) | "
            f"usuario={member} ({member.id}) | idade_conta={age_days}d"
        )


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    if is_exempt(message.author):
        await bot.process_commands(message)
        return

    normalized_content = normalize_text(message.content)

    # 1) Flood + mensagens quase iguais
    is_flood, flood_reason = check_flood(
        message.guild.id,
        message.author.id,
        message.channel.id,
        message.content,
        normalized_content,
    )

    # 2) Raid por contas suspeitas recentes
    raid_detected, raid_reason = check_raid_message_activity(message.guild.id, message.author.id)

    # 3) Conteudo + anexos + mencoes + links externos
    score, reasons = analyze_message(message, normalized_content)

    if raid_detected:
        reasons.insert(0, f"Raid: {raid_reason}")
        score = max(score, 95)

    spam_detected = raid_detected or is_flood or score >= CONFIG["score_threshold"]

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
                f"{message.author.mention} sua mensagem foi removida por violar as regras do servidor.",
                delete_after=8,
            )
        except discord.Forbidden:
            pass

        timeout_minutes = get_timeout_minutes_for_next_infraction(message.guild.id, message.author.id)
        timeout_applied = await punish(
            message.author,
            reason=f"Spam: {', '.join(reasons)}",
            timeout_minutes=timeout_minutes,
        )

        await log_action(message.guild, message, reasons, score, timeout_minutes)

        if timeout_applied:
            timeout_count = increment_timeout_count(message.guild.id, message.author.id)
            await send_shame_wall(message.guild, message.author, timeout_count, timeout_minutes)

        print(
            f"[SPAM] {message.author} | Score: {score} | Timeout={format_duration_minutes(timeout_minutes)} | {reasons}"
        )
        return

    await bot.process_commands(message)


# ============================================================
# COMANDO DE TESTE (apenas admins)
# ============================================================
@bot.command(name="testspam")
@commands.has_permissions(administrator=True)
async def test_spam(ctx, *, texto: str):
    """Testa se um texto seria detectado. Uso: !testspam <texto>"""
    fake_message = type("FakeMessage", (), {
        "content": texto,
        "mention_everyone": False,
        "mentions": [],
        "attachments": [],
    })()

    normalized = normalize_text(texto)
    score, reasons = analyze_message(fake_message, normalized)
    is_spam = score >= CONFIG["score_threshold"]

    embed = discord.Embed(
        title="Resultado da analise",
        color=discord.Color.red() if is_spam else discord.Color.green(),
    )
    embed.add_field(name="Score", value=f"{score}/100", inline=True)
    embed.add_field(name="E spam?", value="Sim" if is_spam else "Nao", inline=True)
    embed.add_field(
        name="Obs",
        value="Attachments, mencoes, flood e raid sao avaliados melhor em mensagens reais.",
        inline=False,
    )
    if reasons:
        embed.add_field(name="Padroes encontrados", value="\n".join(f"- {r}" for r in reasons), inline=False)
    await ctx.reply(embed=embed)


# ============================================================
# INICIAR
# ============================================================
if __name__ == "__main__":
    token = CONFIG["token"]
    if not token:
        raise ValueError("Defina DISCORD_TOKEN no arquivo .env")
    bot.run(token)
