import discord
from discord import app_commands
from discord.ext import tasks
import json
import datetime
import os

# ===== CONFIGURAÇÕES =====
TOKEN = os.environ.get("TOKEN")  # variável de ambiente no Koyeb

# IDs dos canais (substitua pelos IDs reais)
CHAT_CONTAS_ID = 123456789012345678
CHAT_RELATORIO_ID = 987654321098765432
CHAT_VERIFY_ID = 112233445566778899

CARGOS_ACESSO = ["Staff", "Mod", "Infuencer", "Farmer", "Entregador"]

STOCK_FILE = "vendas.json"
RELATORIO_FILE = "relatorio.json"

# ===== BOT E INTENTS =====
intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ===== FUNÇÕES AUXILIARES =====
def carregar_stock():
    try:
        with open(STOCK_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def salvar_stock(stock):
    with open(STOCK_FILE, "w") as f:
        json.dump(stock, f, indent=4)

def carregar_relatorio():
    try:
        with open(RELATORIO_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def salvar_relatorio(data):
    with open(RELATORIO_FILE, "w") as f:
        json.dump(data, f, indent=4)

def tem_cargo(member):
    return any(role.name in CARGOS_ACESSO for role in member.roles)

# ===== COMANDOS =====

# /contas → envia lista de contas disponíveis via DM
@tree.command(name="contas", description="Ver as contas disponíveis")
async def contas(interaction: discord.Interaction):
    if interaction.channel.id != CHAT_CONTAS_ID:
        await interaction.response.send_message("🚫 Use este comando no canal correto.", ephemeral=True)
        return
    user = interaction.user
    stock = carregar_stock()
    if not stock:
        await interaction.response.send_message("🚫 Nenhuma conta disponível no momento.", ephemeral=True)
        return

    msg = "📦 Contas disponíveis:\n"
    for nome in stock.keys():
        msg += f"- {nome}\n"
    msg += "\n👀 Mande o nome da conta que deseja comprar."
    await user.send(msg)
    await interaction.response.send_message("✅ Confira suas DMs!", ephemeral=True)

# Evento de DM do usuário para pegar o nome da conta
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if isinstance(message.channel, discord.DMChannel):
        stock = carregar_stock()
        nome_conta = message.content.strip()
        if nome_conta not in stock:
            await message.channel.send("🚫 Conta fora de Stock\n⏳ Aguarde ficar disponível")
            return

        info = stock[nome_conta]
        valor = info.get("valor", "R$0")
        await message.channel.send(
            "✅ Conta disponível será enviada pós o pagamento.\n\n💸 Chave Pix: world.blox018@gmail.com"
        )

        canal_verify = bot.get_channel(CHAT_VERIFY_ID)
        await canal_verify.send(
            f"💰 Conta: {nome_conta}\n"
            f"💵 Valor: {valor}\n"
            f"👤 Comprador: {message.author.mention}\n"
            f"⌛ Aguarde confirmação com `/verify {nome_conta}`"
        )

# /verify → confirmação de pagamento por cargos
@tree.command(name="verify", description="Confirmar pagamento de uma conta")
@app_commands.describe(nome_conta="Nome da conta a verificar")
async def verify(interaction: discord.Interaction, nome_conta: str):
    if interaction.channel.id != CHAT_VERIFY_ID:
        await interaction.response.send_message("🚫 Este comando só pode ser usado no canal de verificação.", ephemeral=True)
        return
    if not tem_cargo(interaction.user):
        await interaction.response.send_message("🚫 Você não tem permissão.", ephemeral=True)
        return
    stock = carregar_stock()
    if nome_conta not in stock:
        await interaction.response.send_message("🚫 Conta não encontrada no stock.", ephemeral=True)
        return
    info = stock.pop(nome_conta)
    salvar_stock(stock)
    conta_info = info.get("dados", "Sem dados")
    await interaction.response.send_message(
        f"✅ Pix caiu, boa compra!\n**📦 Sua conta está saindo para a entrega.**\n⏳ Prazo de até 2 Dias.\n\n"
        f"🚨 Caso sua conta possua verificação de 2 etapas, informe um Staff, Entregador ou Farmer.\n\n"
        f"Conta:\n{conta_info}\n\n(Contas)\n🚨 Botão de compra se expira🚨"
    )

    # Atualiza relatório
    relatorio = carregar_relatorio()
    vendedor = info.get("vendedor", "Desconhecido")
    if vendedor not in relatorio:
        relatorio[vendedor] = {"diaria": 0, "total": 0, "compras": 0}
    relatorio[vendedor]["diaria"] += info.get("lucro", 0)
    relatorio[vendedor]["total"] += info.get("lucro", 0)
    relatorio[vendedor]["compras"] += 1
    salvar_relatorio(relatorio)

# /vendas → relatório individual (apenas para cargos)
@tree.command(name="vendas", description="Relatório de vendas individuais")
async def vendas(interaction: discord.Interaction):
    if not tem_cargo(interaction.user):
        await interaction.response.send_message("🚫 Você não tem permissão.", ephemeral=True)
        return
    relatorio = carregar_relatorio()
    usuario = str(interaction.user)
    dados = relatorio.get(usuario)
    if not dados:
        await interaction.response.send_message("🚫 Nenhuma venda registrada para você.", ephemeral=True)
        return
    media = dados["total"] / max(dados["compras"],1)
    msg = (
        f"**{usuario}**\n"
        f"Diária: R${dados['diaria']}\n"
        f"Média: R${media:.2f}\n"
        f"Mensal: R${dados['total']}\n"
    )
    await interaction.response.send_message(msg, ephemeral=True)

# /relatorio → lucro total loja (apenas para cargos, canal privado)
@tree.command(name="relatorio", description="Lucro total da loja")
async def relatorio(interaction: discord.Interaction):
    if interaction.channel.id != CHAT_RELATORIO_ID:
        await interaction.response.send_message("🚫 Use este comando no canal correto.", ephemeral=True)
        return
    if not tem_cargo(interaction.user):
        await interaction.response.send_message("🚫 Você não tem permissão.", ephemeral=True)
        return
    relatorio = carregar_relatorio()
    lucro_total = sum(d["total"] for d in relatorio.values())
    msg = f"📜 World Blox\n💰 Lucro total: R${lucro_total}"
    await interaction.response.send_message(msg)

# ===== RESETS =====
@tasks.loop(hours=24)
async def reset_diario():
    relatorio = carregar_relatorio()
    for v in relatorio.values():
        v["diaria"] = 0
    salvar_relatorio(relatorio)

@tasks.loop(hours=24)
async def reset_mensal():
    hoje = datetime.datetime.now()
    if hoje.day == 28:
        relatorio = carregar_relatorio()
        for v in relatorio.values():
            v["total"] = 0
            v["compras"] = 0
        salvar_relatorio(relatorio)

# ===== READY =====
@bot.event
async def on_ready():
    await tree.sync()
    print(f"{bot.user} está online!")
    reset_diario.start()
    reset_mensal.start()
