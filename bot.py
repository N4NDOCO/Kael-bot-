import discord
from discord.ext import commands
import json
import os
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

VENDAS_FILE = "vendas.json"
CANAL_RELATORIO = "📊┃relatorio-vendas"
COMISSAO_PERCENT = 0.20

CARGOS_PERMITIDOS = [
    "Staff",
    "Mod",
    "Influencer",
    "Farmer",
    "Entregador"
]

# ================= UTIL =================
def carregar_vendas():
    if not os.path.exists(VENDAS_FILE):
        return []
    with open(VENDAS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_vendas(vendas):
    with open(VENDAS_FILE, "w", encoding="utf-8") as f:
        json.dump(vendas, f, indent=4, ensure_ascii=False)

def tem_permissao(member: discord.Member):
    return any(cargo.name in CARGOS_PERMITIDOS for cargo in member.roles)

# ================= EVENT =================
@bot.event
async def on_ready():
    print(f"🤖 Bot online como {bot.user}")

# ================= CONTAS (LIVRE) =================
@bot.command(name="contas")
async def contas(ctx):
    embed = discord.Embed(
        title="🏪 Contas Disponíveis",
        description="Entre em contato com a equipe para comprar.",
        color=discord.Color.gold()
    )

    embed.add_field(name="God Human", value="R$ 20", inline=False)
    embed.add_field(name="Dragon Talon v2", value="R$ 15", inline=False)
    embed.add_field(name="Sharkman v2", value="R$ 15", inline=False)
    embed.add_field(name="Electric Claw", value="R$ 10", inline=False)
    embed.add_field(name="Level Max (2800)", value="R$ 8", inline=False)

    await ctx.author.send(embed=embed)
    await ctx.send("📩 Te mandei as contas no privado!")

# ================= REGISTRAR VENDA =================
@bot.command(name="venda")
async def venda(ctx, *, dados: str):
    if not tem_permissao(ctx.author):
        await ctx.send("❌ Você não tem permissão para usar este comando.")
        return

    try:
        partes = [p.strip() for p in dados.split("|")]
        conta = partes[0]
        preco = float(partes[1])
        vendedor = partes[2]

        comissao = round(preco * COMISSAO_PERCENT, 2)
        lucro = round(preco - comissao, 2)

    except Exception:
        await ctx.send("❌ Use: `/venda Conta | PREÇO | @Vendedor`")
        return

    venda_data = {
        "conta": conta,
        "preco": preco,
        "vendedor": vendedor,
        "comissao": comissao,
        "lucro": lucro,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    vendas = carregar_vendas()
    vendas.append(venda_data)
    salvar_vendas(vendas)

    canal = discord.utils.get(ctx.guild.text_channels, name=CANAL_RELATORIO)
    if canal:
        embed = discord.Embed(title="💰 Venda Registrada", color=discord.Color.green())
        embed.add_field(name="📦 Conta", value=conta, inline=False)
        embed.add_field(name="💵 Preço", value=f"R$ {preco}", inline=True)
        embed.add_field(name="👤 Vendedor", value=vendedor, inline=True)
        embed.add_field(name="💸 Comissão (20%)", value=f"R$ {comissao}", inline=True)
        embed.add_field(name="📈 Lucro", value=f"R$ {lucro}", inline=True)
        await canal.send(embed=embed)

    await ctx.send("✅ Venda registrada com sucesso!")

# ================= COMISSÃO =================
@bot.command(name="comissao")
async def comissao(ctx, *, vendedor: str):
    if not tem_permissao(ctx.author):
        await ctx.send("❌ Você não tem permissão para usar este comando.")
        return

    vendas = carregar_vendas()
    total_vendas = 0
    total_comissao = 0
    total_valor = 0

    for v in vendas:
        if vendedor.lower() in v["vendedor"].lower():
            total_vendas += 1
            total_comissao += v["comissao"]
            total_valor += v["preco"]

    if total_vendas == 0:
        await ctx.send("❌ Nenhuma venda encontrada.")
        return

    embed = discord.Embed(title="💸 Comissão do Vendedor", color=discord.Color.blue())
    embed.add_field(name="👤 Vendedor", value=vendedor, inline=False)
    embed.add_field(name="📦 Vendas", value=total_vendas, inline=True)
    embed.add_field(name="💵 Total Vendido", value=f"R$ {total_valor}", inline=True)
    embed.add_field(name="💰 Comissão", value=f"R$ {round(total_comissao,2)}", inline=True)

    await ctx.send(embed=embed)

# ================= RELATÓRIO =================
@bot.command(name="relatorio")
async def relatorio(ctx):
    if not tem_permissao(ctx.author):
        await ctx.send("❌ Você não tem permissão para usar este comando.")
        return

    vendas = carregar_vendas()
    if not vendas:
        await ctx.send("❌ Nenhuma venda registrada.")
        return

    faturamento = sum(v["preco"] for v in vendas)
    total_comissao = sum(v["comissao"] for v in vendas)
    lucro = sum(v["lucro"] for v in vendas)

    embed = discord.Embed(title="📊 Relatório Geral", color=discord.Color.purple())
    embed.add_field(name="📦 Vendas", value=len(vendas), inline=False)
    embed.add_field(name="💵 Faturamento", value=f"R$ {round(faturamento,2)}", inline=True)
    embed.add_field(name="💸 Comissões", value=f"R$ {round(total_comissao,2)}", inline=True)
    embed.add_field(name="📈 Lucro", value=f"R$ {round(lucro,2)}", inline=True)

    await ctx.send(embed=embed)

# ================= START =================
bot.run(TOKEN)
