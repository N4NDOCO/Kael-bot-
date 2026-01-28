import discord
from discord.ext import commands, tasks
import json
import datetime

# CONFIGURAÇÕES
TOKEN = "SEU_TOKEN_DO_DISCORD"
PREFIX = "/"
GUILD_ID = 123456789012345678  # ID do seu servidor
CHAT_VERIFICACAO = 987654321098765432  # ID do chat privado de verificação
CHAT_RELATORIO = 876543210987654321  # ID do chat privado de relatório
CARGOS_PERMITIDOS = ["Staff", "Mod", "Influencer", "Farmer", "Entregador"]

bot = commands.Bot(command_prefix=PREFIX, intents=discord.Intents.all())

# ARQUIVOS
STOCK_FILE = "vendas.json"
RELATORIO_FILE = "relatorio.json"

# CARREGAR STOCK
try:
    with open(STOCK_FILE, "r") as f:
        stock = json.load(f)
except:
    stock = []

# CARREGAR RELATÓRIO
try:
    with open(RELATORIO_FILE, "r") as f:
        relatorio = json.load(f)
except:
    relatorio = {}

def save_stock():
    with open(STOCK_FILE, "w") as f:
        json.dump(stock, f, indent=4)

def save_relatorio():
    with open(RELATORIO_FILE, "w") as f:
        json.dump(relatorio, f, indent=4)

def tem_cargo(user):
    return any(role.name in CARGOS_PERMITIDOS for role in user.roles)

def atualizar_relatorio(usuario, valor):
    hoje = datetime.datetime.now().strftime("%Y-%m-%d")
    mes = datetime.datetime.now().strftime("%Y-%m")
    if usuario not in relatorio:
        relatorio[usuario] = {"diaria":0, "total":0, "semanal":0, "ultima_data":hoje, "ultimo_mes":mes}
    # reset diário
    if relatorio[usuario]["ultima_data"] != hoje:
        relatorio[usuario]["diaria"] = 0
        relatorio[usuario]["ultima_data"] = hoje
    # reset mensal
    if relatorio[usuario]["ultimo_mes"] != mes:
        relatorio[usuario]["total"] = 0
        relatorio[usuario]["semanal"] = 0
        relatorio[usuario]["ultimo_mes"] = mes

    relatorio[usuario]["diaria"] += valor
    relatorio[usuario]["total"] += valor
    relatorio[usuario]["semanal"] += valor

    save_relatorio()

# COMANDO /contas
@bot.command()
async def contas(ctx):
    dm = ctx.author
    if not stock:
        await dm.send("🚫 Não há contas disponíveis no momento.")
        return
    msg = "🏪 **World Blox — Contas Blox Fruits**\n\n"
    for conta in stock:
        msg += f"**{conta['nome']}** — R$ {conta['preco']}\n"
    msg += "\n👀 Mande o nome da conta que deseja comprar"
    await dm.send(msg)
    await ctx.message.delete()

# CLIENTE RESPONDE COM NOME DA CONTA
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    # só DM
    if isinstance(message.channel, discord.DMChannel):
        escolha = message.content.strip()
        conta_encontrada = None
        for c in stock:
            if escolha.lower() in c['nome'].lower():
                conta_encontrada = c
                break
        if not conta_encontrada:
            await message.channel.send("🚫 Conta fora de Stock\n⏳ Aguarde ficar disponível")
            return
        # envia PIX e notificação no chat de verificação
        await message.channel.send(f"✅ Conta disponível será enviada pós o pagamento.\n💸 Chave Pix: world.blox018@gmail.com")
        canal = bot.get_channel(CHAT_VERIFICACAO)
        await canal.send(f"📦 Nova compra pendente:\nConta: {conta_encontrada['nome']}\nValor: R$ {conta_encontrada['preco']}\nComprador: {message.author.name}")
        # registra a compra pendente para /verify
        if "pendentes" not in relatorio:
            relatorio["pendentes"] = []
        relatorio["pendentes"].append({
            "usuario": message.author.name,
            "conta": conta_encontrada["nome"],
            "preco": conta_encontrada["preco"],
            "upador": message.author.name  # pode ajustar caso queira outro upador
        })
        save_relatorio()
    await bot.process_commands(message)

# COMANDO /verify
@bot.command()
async def verify(ctx, usuario: str = None):
    if not tem_cargo(ctx.author):
        await ctx.send("❌ Você não tem permissão para usar este comando.")
        return
    # verifica pendentes
    if "pendentes" not in relatorio or not relatorio["pendentes"]:
        await ctx.send("❌ Não há compras pendentes.")
        return
    pendente = None
    for p in relatorio["pendentes"]:
        if usuario is None or p["usuario"].lower() == usuario.lower():
            pendente = p
            break
    if not pendente:
        await ctx.send("❌ Não foi encontrada compra pendente desse usuário.")
        return
    # calcula lucro
    vendedor = ctx.author.name
    upador = pendente["upador"]
    preco = pendente["preco"]
    if vendedor == upador:
        lucro_upador = preco
        lucro_vendedor = 0
    else:
        lucro_upador = preco*0.8
        lucro_vendedor = preco*0.2
    atualizar_relatorio(upador, lucro_upador)
    if lucro_vendedor > 0:
        atualizar_relatorio(vendedor, lucro_vendedor)
    # envia conta
    canal_user = None
    for u in bot.users:
        if u.name == pendente["usuario"]:
            canal_user = u
            break
    if canal_user:
        await canal_user.send(f"✅ Pix caiu boa compra.\n📦 Sua conta está saindo para a entrega.\n⏳ Prazo de até 2 Dias.\n🚨 Caso possua verificação de 2 etapas, informe Staff/Farmer/Entregador.\n\nUsuário: {pendente['usuario']}\nSenha: {pendente['conta']}\n\n(Contas)\n👀 Mande o nome da conta que deseja comprar")
    # remove do stock
    stock[:] = [c for c in stock if c["nome"] != pendente["conta"]]
    save_stock()
    # remove pendente
    relatorio["pendentes"].remove(pendente)
    save_relatorio()
    await ctx.send(f"✅ Compra de {pendente['usuario']} confirmada e conta entregue.")

# COMANDO /vendas
@bot.command()
async def vendas(ctx):
    if not tem_cargo(ctx.author):
        await ctx.send("❌ Você não tem permissão para usar este comando.")
        return
    usuario = ctx.author.name
    if usuario not in relatorio:
        await ctx.send("❌ Nenhum registro encontrado.")
        return
    data = relatorio[usuario]
    await ctx.send(f"**{usuario}**\nDiária: R$ {data['diaria']}\nTotal: R$ {data['total']}\nMédia semanal: R$ {data['semanal']}")

# COMANDO /relatorio
@bot.command()
async def relatorio(ctx):
    if not tem_cargo(ctx.author):
        await ctx.send("❌ Você não tem permissão para usar este comando.")
        return
    total_geral = sum(d["total"] for k,d in relatorio.items() if k != "pendentes")
    await ctx.send(f"📊 Relatório geral da loja:\nTotal de vendas acumuladas: R$ {total_geral}")

bot.run(TOKEN)
