import discord
from discord.ext import commands, tasks
import json
from datetime import datetime, timedelta

# ---------- CONFIGURAÇÕES ----------
TOKEN = "SEU_TOKEN_AQUI"

CANAL_COMPRAS = "comprar-contas"
CANAL_RELATORIO = "relatorio-vendas"
CANAL_VERIFY = "verificar-pagamentos"

CARGOS_AUTORIZADOS = ["Staff", "Mod", "Infuencer", "Farmer", "Entregador"]

STOCK_FILE = "stock.json"
VENDAS_FILE = "vendas.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# ---------- FUNÇÕES DE SUPORTE ----------
def carregar_json(nome_arquivo):
    with open(nome_arquivo, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_json(nome_arquivo, data):
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def usuario_autorizado(member):
    return any(cargo.name in CARGOS_AUTORIZADOS for cargo in member.roles)

# ---------- COMANDOS ----------
@bot.command()
async def contas(ctx):
    if ctx.channel.name != CANAL_COMPRAS:
        return
    user = ctx.author
    stock = carregar_json(STOCK_FILE)
    mensagem = "**📦 Contas disponíveis:**\n\n"
    for nome, dados in stock.items():
        if dados["comprador"] is None:
            mensagem += f"{dados['detalhes']}\n\n👀 Mande o nome da conta que deseja comprar\n\n"
    try:
        await user.send(mensagem)
        await ctx.send(f"✅ {user.mention}, verifique suas DMs para ver as contas disponíveis.")
    except discord.Forbidden:
        await ctx.send(f"❌ {user.mention}, não consegui enviar DM. Ative suas mensagens privadas.")

@bot.command()
async def vendas(ctx):
    if not usuario_autorizado(ctx.author):
        return await ctx.send("❌ Você não tem permissão para usar esse comando.")
    vendas = carregar_json(VENDAS_FILE)
    nome = ctx.author.name
    if nome not in vendas:
        return await ctx.send("❌ Seu nome não está registrado.")
    diaria = vendas[nome]["diaria"]
    total = vendas[nome]["total"]
    # Média semanal simples: total / 4
    media = round(total / 4, 2)
    await ctx.send(
        f"**{nome}**\nDiária: R${diaria}\nMédia Semanal: R${media}\nMensal: R${total}"
    )

@bot.command()
async def relatorio(ctx):
    if ctx.channel.name != CANAL_RELATORIO:
        return
    if not usuario_autorizado(ctx.author):
        return await ctx.send("❌ Você não tem permissão para usar esse comando.")
    vendas = carregar_json(VENDAS_FILE)
    total_geral = sum(dados["total"] for dados in vendas.values())
    await ctx.send(f"📜 **World Blox**\n💰 Lucro total: R${total_geral}")

@bot.command()
async def verify(ctx, nome_conta):
    if ctx.channel.name != CANAL_VERIFY:
        return
    if not usuario_autorizado(ctx.author):
        return await ctx.send("❌ Você não tem permissão para usar esse comando.")
    stock = carregar_json(STOCK_FILE)
    vendas = carregar_json(VENDAS_FILE)

    if nome_conta not in stock or stock[nome_conta]["comprador"] is None:
        return await ctx.send("🚫 Conta não disponível ou não foi selecionada pelo comprador.")

    comprador = stock[nome_conta]["comprador"]
    valor = stock[nome_conta]["valor"]
    upador = stock[nome_conta]["upador"]

    # Atualizar ganhos
    vendedor_nome = ctx.author.name
    if vendedor_nome != upador:
        vendedor_valor = round(valor * 0.2, 2)
        upador_valor = round(valor * 0.8, 2)
        if vendedor_nome in vendas:
            vendas[vendedor_nome]["diaria"] += vendedor_valor
            vendas[vendedor_nome]["total"] += vendedor_valor
        if upador in vendas:
            vendas[upador]["diaria"] += upador_valor
            vendas[upador]["total"] += upador_valor
    else:
        if vendedor_nome in vendas:
            vendas[vendedor_nome]["diaria"] += valor
            vendas[vendedor_nome]["total"] += valor

    # Mandar conta pro comprador
    user = ctx.guild.get_member_named(comprador)
    if user:
        await user.send(
            f"✅ Pix caiu, boa compra.\n**📦 Sua conta está saindo para a entrega.**\n⏳ Prazo de até 2 Dias.\n\nConta: {stock[nome_conta]['detalhes']}\n\n🚨 Caso sua conta possua verificação de 2 etapas, informe um Staff, Entregador ou Farmer.\n\n(Contas)"
        )

    # Remover stock
    stock[nome_conta]["comprador"] = None
    stock[nome_conta]["upador"] = None

    salvar_json(STOCK_FILE, stock)
    salvar_json(VENDAS_FILE, vendas)
    await ctx.send(f"✅ Conta **{nome_conta}** entregue com sucesso a {comprador}.")

# ---------- TAREFAS AUTOMÁTICAS ----------
# Reset diário das vendas
@tasks.loop(hours=24)
async def reset_diario():
    vendas = carregar_json(VENDAS_FILE)
    for dados in vendas.values():
        dados["diaria"] = 0
    salvar_json(VENDAS_FILE, vendas)

# Reset mensal
@tasks.loop(hours=24)
async def reset_mensal():
    hoje = datetime.now()
    if hoje.day == 28:
        vendas = carregar_json(VENDAS_FILE)
        for dados in vendas.values():
            dados["total"] = 0
        salvar_json(VENDAS_FILE, vendas)

# ---------- EVENTOS ----------
@bot.event
async def on_ready():
    print(f"{bot.user} está online!")
    reset_diario.start()
    reset_mensal.start()

bot.run(TOKEN)
