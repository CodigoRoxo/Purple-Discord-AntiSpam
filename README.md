<p align="center">
  <img src="./logo/antispam.png" alt="Purple AntiSpam Logo" width="200">
</p>

# Purple AntiSpam

Bot anti-spam para Discord com foco em moderacao automatica, deteccao comportamental e configuração simples por `.env`.

O projeto comecou como um anti-spam baseado em score, flood e algumas regras de texto. A versao atual evoluiu para um sistema mais robusto com:

- punicao progressiva por reincidencia
- deteccao de mensagens quase iguais
- whitelist de links externos
- bloqueio opcional de convites do Discord
- deteccao basica de raid com contas suspeitas
- log de moderacao por servidor
- Hall of Shame por servidor com reincidencia e fallback

## O que o bot faz

- analisa texto, mencoes, anexos e links
- detecta flood no mesmo canal
- detecta cross-channel spam
- detecta mensagens quase iguais apos normalizacao
- aumenta score para links externos fora da whitelist
- bloqueia convites de servidor Discord quando configurado
- aplica timeout progressivo por usuario e por guild
- registra reincidencias em `timeout_counters.json`
- envia log em canal especifico por servidor
- envia mensagem/embed no Hall of Shame por servidor
- observa entrada de contas novas para ajudar na deteccao de raid
- possui comando `!testspam` para testes rapidos

## Comparacao: versao anterior vs versao atual

### Versao anterior

- score fixo por regex
- flood basico
- cross-channel basico
- timeout fixo
- um fluxo mais simples de log e moderacao

### Versao atual

- punicao progressiva por reincidencia
- timeout separado por guild + usuario
- normalizacao de texto para reduzir bypass com simbolos/variacoes
- comparacao de similaridade para mensagens quase iguais
- whitelist configuravel para links externos
- convites Discord controlados por flag separada
- suporte melhor a links de GIF/CDN do Discord e Tenor
- raid detection com contas novas suspeitas enviando mensagens em janela curta
- Hall of Shame com embed, reincidencia e fallback para texto simples
- configuracao multi-servidor para logs e Hall of Shame

## Estrutura do projeto

- [main.py](main.py) - codigo principal do bot
- [FEATURES.md](FEATURES.md) - resumo das features mais recentes
- [requirements.txt](requirements.txt) - dependencias Python
- [discloud.config](discloud.config) - exemplo de deploy na Discloud
- `timeout_counters.json` - persistencia de reincidencias (para controle de reincidência)

## Requisitos

- Python 3.10+
- Um bot criado no Discord Developer Portal
- Intents habilitados no portal:
  - `Message Content Intent`
  - `Server Members Intent`

## Dependencias

Instale com:

```bash
pip install -r requirements.txt
```

Pacotes atuais:

- `discord.py`
- `python-dotenv`

## Como usar

### 1. Clone o repositorio ou faça download da source 2.0

### 2. Configure o `.env`

Crie ou edite o arquivo `renomeie.env` para `.env` com os IDs e parametros do seu servidor.

Exemplo:

```env
DISCORD_TOKEN=SEU_TOKEN_AQUI

LOG_CHANNEL_IDS=1397673828221718638:1493565123363737621
SHAME_CHANNEL_IDS=1397673828221718638:1493582480824074243

EXEMPT_ROLE_IDS=1437831725920161993

FLOOD_LIMIT=5
FLOOD_WINDOW_SEC=8
TIMEOUT_STEPS_MINUTES=10,60,1440,4320
SCORE_THRESHOLD=60
MESSAGE_SIMILARITY_THRESHOLD=0.90

EXTERNAL_LINK_SCORE=55
ALLOW_DISCORD_INVITES=false
ALLOWED_DOMAINS=discord.com,discord.gg,discordapp.com,cdn.discordapp.com,media.discordapp.net,tenor.com,media.tenor.com,youtube.com,youtu.be,github.com,docs.python.org

SUSPICIOUS_ACCOUNT_MAX_AGE_DAYS=14
RAID_WINDOW_SEC=10
RAID_USER_THRESHOLD=5
RAID_JOIN_GRACE_SEC=900
RAID_COOLDOWN_SEC=30
```

### 3. Execute o bot

```bash
python main.py
```

## Variaveis de ambiente

### Basicas

- `DISCORD_TOKEN`: token do bot
- `LOG_CHANNEL_ID`: canal de log padrao opcional
- `LOG_CHANNEL_IDS`: canais de log por guild no formato `guild_id:channel_id`
- `SHAME_CHANNEL_IDS`: canais do Hall por guild no formato `guild_id:channel_id`
- `EXEMPT_ROLE_IDS`: cargos isentos separados por virgula

### Anti-spam e flood

- `FLOOD_LIMIT`: quantidade de mensagens para flood
- `FLOOD_WINDOW_SEC`: janela de tempo do flood
- `SCORE_THRESHOLD`: score minimo para punicao
- `MESSAGE_SIMILARITY_THRESHOLD`: limiar de similaridade de mensagens

### Punicao progressiva

- `TIMEOUT_STEPS_MINUTES`: lista de timeouts por reincidencia

Exemplo:

- `10,60,1440,4320`
  - 1a infracao: 10 min
  - 2a infracao: 1h
  - 3a infracao: 1d
  - 4a em diante: 3d

### Links

- `EXTERNAL_LINK_SCORE`: score adicionado para dominios fora da whitelist
- `ALLOWED_DOMAINS`: dominios liberados
- `ALLOW_DISCORD_INVITES`: `true` permite convites Discord; `false` bloqueia `discord.gg`, `discord.com/invite` e `discordapp.com/invite`

### Raid detection

- `SUSPICIOUS_ACCOUNT_MAX_AGE_DAYS`: idade maxima de conta para ser considerada suspeita
- `RAID_WINDOW_SEC`: janela de observacao das mensagens
- `RAID_USER_THRESHOLD`: quantidade de usuarios suspeitos para disparar alerta
- `RAID_JOIN_GRACE_SEC`: por quanto tempo apos entrar a conta conta como "join recente"
- `RAID_COOLDOWN_SEC`: cooldown entre alertas de raid

## Como a punicao funciona

1. O bot analisa a mensagem.
2. Soma score com base em regex, links, mencoes, anexos e comportamento.
3. Verifica flood, similaridade e raid.
4. Se a mensagem for considerada spam:
   - tenta remover a mensagem
   - envia aviso temporario no canal
   - calcula o proximo timeout progressivo
   - aplica timeout se tiver permissao e hierarquia suficientes
   - registra log no canal configurado
   - incrementa reincidencia
   - envia no Hall of Shame

## Hall of Shame

O Hall of Shame funciona por guild e envia:

- embed com mencao do usuario
- quantidade de reincidencias
- duracao do timeout aplicado

Se o bot nao puder enviar embed, ele tenta fallback para texto simples.

Se nao estiver enviando, verifique:

- `SHAME_CHANNEL_IDS`
- permissao de `View Channel`
- permissao de `Send Messages`
- permissao de `Embed Links`

## Logs de moderacao

Os logs mostram:

- usuario punido
- canal da mensagem
- score
- motivos
- timeout aplicado
- conteudo e anexos, quando existirem

## Convites Discord vs links gerais

O projeto separa duas coisas:

- links externos em geral
- convites de servidor Discord

Isso permite um comportamento mais fino:

- liberar GIFs e links comuns
- bloquear especificamente convites de servidor

Exemplo de links que podem ser permitidos na whitelist:

- `cdn.discordapp.com`
- `media.discordapp.net`
- `tenor.com`
- `media.tenor.com`

Exemplo de convites que podem ser bloqueados com `ALLOW_DISCORD_INVITES=false`:

- `https://discord.gg/abc123`
- `https://discord.com/invite/abc123`
- `https://discordapp.com/invite/abc123`

## Raid detection

O detector observa duas etapas:

1. entrada de conta suspeita
2. sequencia de mensagens de varias contas suspeitas em janela curta

Atualmente, ele considera raid quando varias contas novas suspeitas entram e pelo menos `RAID_USER_THRESHOLD` delas enviam mensagens em `RAID_WINDOW_SEC` segundos.

## Comando de teste

Use:

```text
!testspam seu texto aqui
```

Esse comando ajuda a validar score e padroes de texto sem precisar disparar uma punicao real.

## Permissoes necessarias do bot

- `View Channels`
- `Send Messages`
- `Manage Messages`
- `Moderate Members`
- `Read Message History`
- `Embed Links`

Importante:

- o cargo do bot precisa estar acima do cargo do usuario que sera punido

## Deploy na Discloud

O projeto ja possui [discloud.config](discloud.config) com:

- `TYPE=bot`
- `MAIN=main.py`
- `START=python main.py`

Fluxo basico:

1. envie os arquivos do projeto
2. confirme se o `.env` esta configurado
3. suba a aplicacao na Discloud

## Arquivos de estado

- `timeout_counters.json`: armazena reincidencias por `guild_id:user_id`

Isso significa que o mesmo usuario pode ter contadores diferentes em servidores diferentes.

## Melhorias recentes documentadas

As atualizacoes mais recentes tambem estao resumidas em [FEATURES.md](FEATURES.md).

## Observacoes de seguranca

- nao publique seu `.env`
- nao exponha o token do bot no GitHub
- se o token tiver sido exposto, regenere imediatamente no Discord Developer Portal
