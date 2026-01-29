import discord
from discord.ext import commands, tasks
import json
import datetime
import os
import asyncio

# ===== CONFIGURAÇÕES =====
TOKEN = os.environ.get("TOKEN")  # Pega o token do Koyeb, variável de ambiente

CHAT_CONTAS_ID = 123456789012345678  # canal público de /contas
CHAT_RELATORIO_ID = 987654321098765432  # chat privado de relatório de compras
CHAT_VERIFY_ID = 112233445566778899  # chat privado de verificação

CARGOS_ACESSO = ["Staff", "Mod", "Infuencer", "Farmer", "Entregador"]

STOCK_FILE = "vendas.json"
RELATORIO_FILE = "relatorio.json"

# ===== INTENTS E BOT =====
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

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
@bot.command()
async def contas(ctx):
    if ctx.channel.id != CHAT_CONTAS_ID:
        return
    user = ctx.author
    stock = carregar_stock()
    if not stock:
        await user.send("🚫 Nenhuma conta disponível no momento.")
        return
    msg = "📦 Contas disponíveis:\n"
    for nome in stock.keys():
        msg += f"- {nome}\n"
    msg += "\n👀 Mande o nome da conta que deseja comprar."
    await user.send(msg)

# DM do usuário com o nome da conta
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

        # aviso no chat de verificação
        canal_verify = bot.get_channel(CHAT_VERIFY_ID)
        await canal_verify.send(
            f"💰 Conta: {nome_conta}\n"
            f"💵 Valor: {valor}\n"
            f"👤 Comprador: {message.author.mention}\n"
            f"⌛ Aguarde confirmação com `/verify {nome_conta}`"
        )

    await bot.process_commands(message)

# /verify → confirmação de pagamento por cargos
@bot.command()
async def verify(ctx, nome_conta: str):
    if ctx.channel.id != CHAT_VERIFY_ID:
        return
    if not tem_cargo(ctx.author):
        await ctx.send("🚫 Você não tem permissão para usar este comando.")
        return
    stock = carregar_stock()
    if nome_conta not in stock:
        await ctx.send("🚫 Conta não encontrada no stock.")
        return
    info = stock.pop(nome_conta)
    salvar_stock(stock)
    conta_info = info.get("dados", "Sem dados")
    await ctx.send(
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

# /vendas → relatório individual
@bot.command()
async def vendas(ctx):
    if not tem_cargo(ctx.author):
        await ctx.send("🚫 Você não tem permissão para usar este comando.")
        return
    relatorio = carregar_relatorio()
    usuario = str(ctx.author)
    dados = relatorio.get(usuario)
    if not dados:
        await ctx.send("🚫 Nenhuma venda registrada para você.")
        return
    media = dados["total"] / max(dados["compras"],1)
    msg = (
        f"**{usuario}**\n"
        f"Diária: R${dados['diaria']}\n"
        f"Média: R${media:.2f}\n"
        f"Mensal: R${dados['total']}\n"
    )
    await ctx.send(msg)

# /relatorio → lucro total loja
@bot.command()
async def relatorio(ctx):
    if ctx.channel.id != CHAT_RELATORIO_ID:
        return
    if not tem_cargo(ctx.author):
        await ctx.send("🚫 Você não tem permissão para usar este comando.")
        return
    relatorio = carregar_relatorio()
    lucro_total = sum(d["total"] for d in relatorio.values())
    msg = f"📜 World Blox\n💰 Lucro total: R${lucro_total}"
    await ctx.send(msg)

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

# ===== ON READY =====
@bot.event
async def on_ready():
    print(f"{bot.user} está online!")
    reset_diario.start()
    reset_mensal.start()

# ===== RUN =====
bot.run(TOKEN)
