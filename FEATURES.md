# Evolucoes do AntiSpam

## 1) Punicao progressiva
- O timeout agora e progressivo por reincidencia (guild + usuario).
- Configuracao via `TIMEOUT_STEPS_MINUTES`.
- Exemplo: `10,60,1440,4320` (10 min, 1h, 1d, 3d).

## 2) Normalizacao e mensagens quase iguais
- O bot normaliza texto (minusculo, sem acentos, sem simbolos extras).
- Detecta repeticao por similaridade com limiar configuravel.
- Configuracao via `MESSAGE_SIMILARITY_THRESHOLD` (padrao `0.9`).

## 3) Links externos com whitelist
- Extrai dominios da mensagem e compara com whitelist.
- Dominio fora da whitelist aumenta score de risco.
- Convites do Discord podem ser controlados separadamente por flag.
- Configuracoes:
  - `ALLOWED_DOMAINS`
  - `EXTERNAL_LINK_SCORE`
  - `ALLOW_DISCORD_INVITES`

## 4) Raid detection
- Marca conta suspeita quando entra (conta muito nova).
- Se 5 contas suspeitas recentes enviarem mensagens em menos de 10s, ativa alerta de raid na deteccao.
- Configuracoes:
  - `SUSPICIOUS_ACCOUNT_MAX_AGE_DAYS`
  - `RAID_WINDOW_SEC`
  - `RAID_USER_THRESHOLD`
  - `RAID_JOIN_GRACE_SEC`
  - `RAID_COOLDOWN_SEC`

## 5) Hall of Shame (embed + fallback)
- Hall agora tenta enviar embed com contexto de reincidencia e tempo de timeout.
- Se o servidor bloquear embed, o bot faz fallback para mensagem simples.
- Configuracao por guild via `SHAME_CHANNEL_IDS` no formato `guild_id:channel_id`.

## Novas variaveis de ambiente (resumo)
- `TIMEOUT_STEPS_MINUTES=10,60,1440,4320`
- `MESSAGE_SIMILARITY_THRESHOLD=0.9`
- `ALLOWED_DOMAINS=discord.com,discord.gg,youtube.com,youtu.be,github.com`
- `EXTERNAL_LINK_SCORE=55`
- `ALLOW_DISCORD_INVITES=false`
- `SUSPICIOUS_ACCOUNT_MAX_AGE_DAYS=14`
- `RAID_WINDOW_SEC=10`
- `RAID_USER_THRESHOLD=5`
- `RAID_JOIN_GRACE_SEC=900`
- `RAID_COOLDOWN_SEC=30`
