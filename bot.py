import discord
from discord.ext import commands, tasks
import json
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# IDs dos canais
CANAIS = {
    "contas": 1465477544445874291,
    "verify": 1465657430292697151,
    "relatorio_vendas": 1465657468745941043,
    "stocks": {
        "God Human": 1465679418075643926,
        "Dragon Talor": 1465679812340220069,
        "Sharkman": 1465679631997861990,
        "Electric Claw": 1465679998777032786,
        "100M Berries": 1465680216432050237,
        "Level Max": 1465680124564475935,
        "Fruta no Inv": 1465680280114303165,
        "Tudo Random": 1465680530526834781
    }
}

# Vendedores e variações
VENDEDORES = {
    "Mikhayas": ["mk","MK","MIKHAYAS","Mk","mikhayas"],
    "N4NDIN": ["nandin","Nandin","n4ndin","N4ndin"],
    "Lucas": ["LUCAS","lucas"],
    "Dionata": ["DIONATA","dionata"],
    "Ramilson": ["RAMILSON","Rami","RAMI","rami","ramilson"],
    "Kaio": ["Caio","KAIO","CAIO","kaio","caio"],
    "Edu": ["edu","EDU","eduardo","Eduardo","EDUARDO"]
}

# Carregar JSONs
def carregar_json(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)
    with open(file, "r") as f:
        return json.load(f)

vendas = carregar_json("vendas.json")
relatorio = carregar_json("relatorio.json")

# Stocks em memória
stocks = {}
for nome, cid in CANAIS["stocks"].items():
    stocks[nome] = []  # Vai carregar cada mensagem do stock

async def atualizar_stocks():
    for nome, cid in CANAIS["stocks"].items():
        canal = bot.get_channel(cid)
        if canal:
            messages = await canal.history(limit=None).flatten()
            stocks[nome] = []
            for msg in messages:
                # Assumimos o formato: Nome: xxxxx | Usuário: xxxx | Senha: yyyy
                stocks[nome].append(msg.content)

# Evento quando bot está pronto
@bot.event
async def on_ready():
    await atualizar_stocks()
    print(f"{bot.user} está online!")
    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

# -----------------------
# COMANDO /contas
# -----------------------
@bot.tree.command(name="contas", description="Veja as contas disponíveis")
async def contas(interaction: discord.Interaction):
    if interaction.channel.id != CANAIS["contas"]:
        await interaction.response.send_message("Use este comando no canal correto.", ephemeral=True)
        return

    msg = "**Contas disponíveis:**\n\n**--🥊 Estilos de luta--**\n"
    for nome in ["God Human","Dragon Talor","Sharkman","Electric Claw"]:
        q = len(stocks[nome])
        preco = {"God Human":20,"Dragon Talor":15,"Sharkman":15,"Electric Claw":10}[nome]
        msg += f"• {nome} (Disponíveis: {q}) – R${preco}\n"

    msg += "\n**--📦 Contas Padrão--**\n"
    for nome in ["100M Berries","Level Max","Fruta no Inv","Tudo Random"]:
        q = len(stocks[nome])
        preco = {"100M Berries":20,"Level Max":8,"Fruta no Inv":12,"Tudo Random":10}[nome]
        msg += f"• {nome} (Disponíveis: {q}) – R${preco}\n"

    msg += "\n✅ Contas 100% seguras\n👀 Mande o nome da conta que deseja comprar."

    await interaction.response.send_message(msg, ephemeral=True)

# -----------------------
# COMANDO /verify
# -----------------------
@bot.tree.command(name="verify", description="Verifica pagamento do cliente")
async def verify(interaction: discord.Interaction, conta: str, usuario: discord.Member):
    if interaction.channel.id != CANAIS["verify"]:
        await interaction.response.send_message("Use este comando no canal correto.", ephemeral=True)
        return

    # Verifica se a conta existe no stock
    if conta not in stocks or len(stocks[conta]) == 0:
        await interaction.response.send_message("Conta não disponível.", ephemeral=True)
        return

    dados_conta = stocks[conta].pop(0)  # Remove do stock
    # Atualiza canal stock (apaga mensagem correspondente)
    canal = bot.get_channel(CANAIS["stocks"][conta])
    async for msg in canal.history(limit=None):
        if msg.content == dados_conta:
            await msg.delete()
            break

    # Envia DM para cliente
    try:
        await usuario.send(f"Sua conta {conta} foi entregue!\n{dados_conta}")
        await interaction.response.send_message(f"Conta entregue para {usuario.display_name}", ephemeral=True)
    except:
        await interaction.response.send_message("Não foi possível enviar DM para o usuário.", ephemeral=True)

    # Atualiza vendas
    vendedor = interaction.user.display_name
    if vendedor not in vendas:
        vendas[vendedor] = {"diaria":0,"total":0}
    vendas[vendedor]["diaria"] += 1
    vendas[vendedor]["total"] += 1
    with open("vendas.json","w") as f:
        json.dump(vendas,f,indent=4)

    # Atualiza relatorio
    relatorio["lucro_total"] = relatorio.get("lucro_total",0) + 1
    with open("relatorio.json","w") as f:
        json.dump(relatorio,f,indent=4)

# -----------------------
# COMANDO /vendas
# -----------------------
@bot.tree.command(name="vendas", description="Mostra suas vendas")
async def vendas_cmd(interaction: discord.Interaction):
    if interaction.channel.id != CANAIS["relatorio_vendas"]:
        await interaction.response.send_message("Use este comando no canal correto.", ephemeral=True)
        return

    vendedor = interaction.user.display_name
    if vendedor not in vendas:
        await interaction.response.send_message("Você ainda não tem vendas registradas.", ephemeral=True)
        return

    data = vendas[vendedor]
    msg = f"**{vendedor}**\nDiária: {data['diaria']}\nTotal: {data['total']}"
    await interaction.response.send_message(msg, ephemeral=True)

# -----------------------
# COMANDO /relatorio
# -----------------------
@bot.tree.command(name="relatorio", description="Mostra o lucro total da loja")
async def relatorio_cmd(interaction: discord.Interaction):
    if interaction.channel.id != CANAIS["relatorio_vendas"]:
        await interaction.response.send_message("Use este comando no canal correto.", ephemeral=True)
        return

    total = relatorio.get("lucro_total",0)
    await interaction.response.send_message(f"📜World Blox\n💰 Lucro total: {total}", ephemeral=True)

# -----------------------
# RODAR O BOT
# -----------------------
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
