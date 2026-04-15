# 🛡️ Discord Anti-Spam Bot (Hall of Shame Edition)

Um bot robusto desenvolvido em Python para manter a integridade do seu servidor, combatendo spams de crypto, convites indesejados e comportamentos maliciosos através de uma análise comportamental e de conteúdo.

## 🚀 Funcionalidades

- **Análise de Score:** Sistema de pesos que identifica padrões de golpes (Crypto, NFTs, links encurtados).
- **Detecção de Flood:** Rastreamento cross-channel que impede usuários de espalharem mensagens em vários canais simultaneamente.
- **Justiça Automática:** Aplicação de timeout (castigo) configurável por até 3 dias.
- **Hall of Shame:** Um mural da vergonha persistente que expõe usuários infectados ou mal-intencionados com um toque de humor.

## 🛠️ Pré-requisitos

Antes de começar, você vai precisar do [Python 3.8+](https://www.python.org/) instalado e as seguintes bibliotecas:

```bash
pip install discord.py python-dotenv
```

# ⚙️ Configuração (Obrigatório)
O projeto utiliza variáveis de ambiente para garantir a segurança dos seus tokens e a flexibilidade entre diferentes servidores.

Na raiz do projeto, crie um arquivo chamado .env.

Copie e cole o conteúdo abaixo, preenchendo com as suas informações:
```bash
# CONFIGURE AQUI, PURPLECODERS!

# Token do seu bot (obtenha em https://discord.com/developers/applications)
DISCORD_TOKEN=SEU_TOKEN_DO_BOT_AQUI

# ID do canal onde o bot vai logar as ações de moderação (opcional)
# Para pegar o ID: ative Modo Desenvolvedor no Discord > clique direito no canal > Copiar ID
# formato: guild_id:channel_id,guild_id:channel_id
LOG_CHANNEL_IDS=1111111111111111:22222222222222, 333333333333333:44444444444444

# ID do server:canal onde o bot vai jogar a mensagem do HALL OF SHAME
SHAME_CHANNEL_IDS=1111111111111111:777777777777777, 333333333333333:555555555555555

# Cargos isentos de verificação (separados por vírgula)
# Exemplo: EXEMPT_ROLE_IDS=XXXXXXXXXXXXXXX, YYYYYYYYYYYYYYYYY
EXEMPT_ROLE_IDS=133713371337
```
