import discord
from discord.ext import commands, tasks
import json
import os

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

# Pegando o token do environment
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = 1465477542919016625  # Seu servidor

# IDs dos canais
CANAL_CONTAS = 1465477544445874291
CANAL_VERIFY = 1465657430292697151
CANAL_VENDAS_RELATORIO = 1465657468745941043

# Stocks
STOCK_CHANNELS = {
    "God Human": 1465679418075643926,
    "Dragon Talor": 1465679812340220069,
    "Sharkman": 1465679631997861990,
    "Electric Claw": 1465679998777032786,
    "100M Berries": 1465680216432050237,
    "Level Max": 1465680124564475935,
    "Fruta no Inv": 1465680280114303165,
    "Tudo Random": 1465680530526834781
}

bot = commands.Bot(command_prefix="!", intents=intents)

# Carregando vendas
if os.path.exists("vendas.json"):
    with open("vendas.json", "r") as f:
        vendas = json.load(f)
else:
    vendas = {
        "Mikhayas": {"diaria": 0, "total": 0},
        "Nandin": {"diaria": 0, "total": 0},
        "Lucas": {"diaria": 0, "total": 0},
        "Dionata": {"diaria": 0, "total": 0},
        "Ramilson": {"diaria": 0, "total": 0},
        "Kaio": {"diaria": 0, "total": 0},
        "Edu": {"diaria": 0, "total": 0}
    }

# Carregando relatório
if os.path.exists("relatorio.json"):
    with open("relatorio.json", "r") as f:
        relatorio = json.load(f)
else:
    relatorio = {"lucro_total": 0}

# Sincroniza comandos de barra
@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"{bot.user} está online!")

# /contas envia DM com contas
@bot.tree.command(name="contas", description="Veja as contas disponíveis", guild=discord.Object(id=GUILD_ID))
async def contas(interaction: discord.Interaction):
    contas_msg = """
**--🥊 Estilos de luta--**

• God Human
Lv Max (2800) – R$20

• Dragon Talor v2 (Evo)
Lv Max (2800) – R$15

• Sharkman Karatê v2 (Evo)
Lv Max (2800) – R$15

• Electric Claw
Lv Max (2800) – R$10

**--📦  Contas Padrão--**

• 100M Berries
Lv Max (2800) – R$20

• Level Max
Lv Max (2800) – R$8

• Fruta no Inv
Lv Max (2800) – R$12

• Tudo Random
Aleatória – R$10

✅ Contas 100% seguras
👀 Mande o nome da conta que deseja comprar
"""
    try:
        await interaction.user.send(contas_msg)
        await interaction.response.send_message("📬 Verifique sua DM!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Não consegui te enviar DM. Ative suas mensagens diretas.", ephemeral=True)

# /vendas mostra lucro do usuário
@bot.tree.command(name="vendas", description="Mostra seu lucro", guild=discord.Object(id=GUILD_ID))
async def vendas_cmd(interaction: discord.Interaction):
    user = interaction.user.name
    if user not in vendas:
        await interaction.response.send_message("Você não tem permissão para usar esse comando.", ephemeral=True)
        return
    info = vendas[user]
    msg = f"""
{user}
Diária: R${info['diaria']}
Média: R${info['total'] / 30:.2f}
Mensal: R${info['total']}
"""
    await interaction.response.send_message(msg, ephemeral=True)

# /relatorio mostra lucro total
@bot.tree.command(name="relatorio", description="Mostra lucro total da loja", guild=discord.Object(id=GUILD_ID))
async def relatorio_cmd(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
        return
    msg = f"📜World Blox\n💰 Lucro total: R${relatorio.get('lucro_total',0)}"
    await interaction.response.send_message(msg)

# Função para atualizar stocks
async def atualizar_stocks():
    for nome, channel_id in STOCK_CHANNELS.items():
        canal = bot.get_channel(channel_id)
        if canal:
            mensagens = []
            async for msg in canal.history(limit=None):
                mensagens.append(msg.content)
            # Você pode processar as contas aqui se precisar

bot.run(TOKEN)
