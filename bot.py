import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime

# ----- CONFIGURAÇÕES -----
GUILD_ID = 1465477542919016625

CANAIS = {
    "comprar_contas": "📦┃comprar-contas",
    "relatorio_vendas": "📊┃relatorio-vendas",
    "verificar_pagamentos": "✅┃verificar-pagamentos"
}

CARGOS_AUTORIZADOS = ["Vendedor", "Upador"]  # nomes dos cargos que podem usar comandos administrativos

TOKEN = os.environ.get("DISCORD_TOKEN")  # token pelo environment

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# ----- ARQUIVOS -----
VENDAS_FILE = "vendas.json"

# ----- VARIÁVEIS -----
contas_disponiveis = [
    {"nome": "God Human", "tipo": "🥊 Estilos de luta", "lv": "Lv Max (2800)", "preco": 20},
    {"nome": "Dragon Talor v2 (Evo)", "tipo": "🥊 Estilos de luta", "lv": "Lv Max (2800)", "preco": 15},
    {"nome": "Sharkman Karatê v2 (Evo)", "tipo": "🥊 Estilos de luta", "lv": "Lv Max (2800)", "preco": 15},
    {"nome": "Electric Claw", "tipo": "🥊 Estilos de luta", "lv": "Lv Max (2800)", "preco": 10},
    {"nome": "100M Berries", "tipo": "📦 Contas Padrão", "lv": "Lv Max (2800)", "preco": 20},
    {"nome": "Level Max", "tipo": "📦 Contas Padrão", "lv": "Lv Max (2800)", "preco": 8},
    {"nome": "Fruta no Inv", "tipo": "📦 Contas Padrão", "lv": "Lv Max (2800)", "preco": 12},
    {"nome": "Tudo Random", "tipo": "📦 Contas Padrão", "lv": "Aleatória", "preco": 10},
]

# ----- FUNÇÕES AUX -----
def carregar_vendas():
    if not os.path.exists(VENDAS_FILE):
        return {}
    with open(VENDAS_FILE, "r") as f:
        return json.load(f)

def salvar_vendas(data):
    with open(VENDAS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def tem_cargo(member):
    return any(c.name in CARGOS_AUTORIZADOS for c in member.roles)

# ----- BOT EVENTS -----
@bot.event
async def on_ready():
    print(f"{bot.user} está online!")
    print("Servindo o servidor:", GUILD_ID)

# ----- COMANDOS -----
@bot.command()
async def contas(ctx):
    if ctx.guild is None or ctx.guild.id != GUILD_ID:
        return
    dm = await ctx.author.create_dm()
    msg = "**--🥊 Estilos de luta--**\n\n"
    for c in contas_disponiveis:
        msg += f"• {c['nome']}\n{c['lv']} – R${c['preco']}\n\n"
    msg += "✅ Contas **100%** seguras\n\n"
    msg += "👀 Mande o nome da conta que deseja comprar"
    await dm.send(msg)
    await ctx.message.add_reaction("✅")  # feedback rápido

@bot.command()
async def vendas(ctx):
    if ctx.guild is None or ctx.guild.id != GUILD_ID:
        return
    if not tem_cargo(ctx.author):
        await ctx.send("❌ Você não tem permissão.")
        return
    data = carregar_vendas()
    nome = ctx.author.name
    if nome not in data:
        await ctx.send("Nenhum registro encontrado.")
        return
    usuario = data[nome]
    embed = discord.Embed(title=f"{nome}", color=discord.Color.green())
    embed.add_field(name="Diária", value=f"R${usuario['diaria']}", inline=False)
    embed.add_field(name="Média Semanal", value=f"R${usuario.get('media',0)}", inline=False)
    embed.add_field(name="Mensal", value=f"R${usuario['total']}", inline=False)
    canal = discord.utils.get(ctx.guild.channels, name=CANAIS["relatorio_vendas"])
    if canal:
        await canal.send(embed=embed)

@bot.command()
async def relatorio(ctx):
    if ctx.guild is None or ctx.guild.id != GUILD_ID:
        return
    if not tem_cargo(ctx.author):
        await ctx.send("❌ Você não tem permissão.")
        return
    data = carregar_vendas()
    total_loja = sum(user["total"] for user in data.values())
    embed = discord.Embed(title="📜 World Blox", color=discord.Color.gold())
    embed.add_field(name="💰 Lucro total", value=f"R${total_loja}", inline=False)
    canal = discord.utils.get(ctx.guild.channels, name=CANAIS["relatorio_vendas"])
    if canal:
        await canal.send(embed=embed)

@bot.command()
async def verify(ctx, usuario: discord.Member = None, *, conta_nome=None):
    if ctx.guild is None or ctx.guild.id != GUILD_ID:
        return
    if not tem_cargo(ctx.author):
        await ctx.send("❌ Você não tem permissão.")
        return
    if ctx.channel.name != CANAIS["verificar_pagamentos"]:
        await ctx.send("❌ Use este comando no canal correto.")
        return
    if usuario is None or conta_nome is None:
        await ctx.send("❌ Sintaxe: /verify @usuario NomeDaConta")
        return
    # Busca a conta
    conta = next((c for c in contas_disponiveis if c["nome"].lower() == conta_nome.lower()), None)
    if conta is None:
        await ctx.send("❌ Conta não encontrada no stock.")
        return
    await ctx.send(
        f"✅ Pix caiu boa compra.\n"
        f"**📦 Sua conta está saindo para entrega**\n"
        f"{conta['nome']}: {conta['lv']}\n"
        f"Comprador: {usuario.mention}\n"
        f"⏳ Prazo de até 2 Dias\n\n"
        f"🚨 Caso sua conta possua verificação de 2 etapas, informe um Staff, Entregador ou Farmer.\n"
        f"🚨 Botão de compra se expira"
    )
    contas_disponiveis.remove(conta)

# ----- RODA O BOT -----
bot.run(TOKEN)
