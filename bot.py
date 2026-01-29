import discord
from discord.ext import commands, tasks
import json
import asyncio
import os
from datetime import datetime

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Bot
bot = commands.Bot(command_prefix="/", intents=intents)

# Environment Token
TOKEN = os.environ.get("DISCORD_TOKEN")  # Defina DISCORD_TOKEN nas variáveis de ambiente

# Canais
CHANNEL_COMPRAR = 1465477544445874291
CHANNEL_VERIFY = 1465657430292697151
CHANNEL_RELATORIO = 1465657468745941043

# Stocks por tipo de conta
STOCK_CHANNELS = {
    "God Human": 1465679418075643926,
    "Dragon Talor": 1465679812340220069,
    "Sharkman": 1465679631997861990,
    "Eletric Claw": 1465679998777032786,
    "100M Berries": 1465680216432050237,
    "Level Max": 1465680124564475935,
    "Fruta no Inv": 1465680280114303165,
    "Tudo Random": 1465680530526834781,
}

# Nomes dos vendedores e variações
VENDEDORES = {
    "Mikhayas": ["Mikhayas", "mk", "MK", "MIKHAYAS", "Mk", "mikhayas"],
    "Nandin": ["N4NDIN", "nandin", "Nandin", "n4ndin", "N4ndin"],
    "Lucas": ["Lucas", "LUCAS", "lucas"],
    "Dionata": ["Dionata", "DIONATA", "dionata"],
    "Ramilson": ["Ramilson", "RAMILSON", "Rami", "RAMI", "rami", "ramilson"],
    "Kaio": ["Kaio", "Caio", "KAIO", "CAIO", "kaio", "caio"],
    "Edu": ["Edu", "edu", "EDU", "eduardo", "Eduardo", "EDUARDO"],
}

# Arquivos JSON
VENDAS_FILE = "vendas.json"
RELATORIO_FILE = "relatorio.json"

# Load JSON
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

vendas_data = load_json(VENDAS_FILE)
relatorio_data = load_json(RELATORIO_FILE)

# Reset diário e mensal
@tasks.loop(hours=24)
async def reset_diario():
    for v in vendas_data:
        vendas_data[v]["diaria"] = 0
    save_json(VENDAS_FILE, vendas_data)

@tasks.loop(hours=24)
async def reset_mensal():
    today = datetime.utcnow().day
    if today == 28:
        for v in vendas_data:
            vendas_data[v]["total"] = 0
        relatorio_data["total"] = 0
        save_json(VENDAS_FILE, vendas_data)
        save_json(RELATORIO_FILE, relatorio_data)

@bot.event
async def on_ready():
    print(f"{bot.user} está online!")
    reset_diario.start()
    reset_mensal.start()

# Função para checar cargo
def tem_cargo(member):
    cargos_ids = [id for id in member.roles]  # Aqui você pode especificar os IDs dos cargos permitidos
    return True  # Pode colocar checagem real se quiser

# /contas
@bot.slash_command(name="contas", description="Veja as contas disponíveis")
async def contas(ctx):
    if ctx.channel.id != CHANNEL_COMPRAR:
        return
    contas_msg = """**--🥊 Estilos de luta--**

• God Human
Lv Max (2800) – R$20

• Dragon Talor v2 (Evo)
Lv Max (2800) – R$15

• Sharkman Karatê v2 (Evo)
Lv Max (2800) – R$15

• Eletric Claw
Lv Max (2800) – R$10

**--📦 Contas Padrão--**

• 100M Berries
Lv Max (2800) – R$20

• Level Max
Lv Max (2800) – R$8

• Fruta no Inv
Lv Max (2800) – R$12

• Tudo Random
Aleatória – R$10

✅ Contas **100%** seguras

👀 Mande o nome da conta que deseja comprar"""
    await ctx.author.send(contas_msg)
    await ctx.respond("As contas foram enviadas no privado!", ephemeral=True)

# Função pegar stock
async def pegar_stock(tipo_conta):
    channel_id = STOCK_CHANNELS.get(tipo_conta)
    if not channel_id:
        return None
    channel = bot.get_channel(channel_id)
    mensagens = await channel.history(limit=100).flatten()
    for msg in mensagens:
        if not msg.content.startswith("VENDIDO"):
            return msg
    return None

# /verify
@bot.slash_command(name="verify", description="Verificar pagamento de conta")
async def verify(ctx, tipo_conta: str, usuario: discord.Member):
    if ctx.channel.id != CHANNEL_VERIFY:
        await ctx.respond("Este comando só pode ser usado no canal de verificação.", ephemeral=True)
        return
    if not tem_cargo(ctx.author):
        await ctx.respond("Você não tem permissão.", ephemeral=True)
        return

    stock_msg = await pegar_stock(tipo_conta)
    if not stock_msg:
        await ctx.respond("Não há stock disponível para essa conta.", ephemeral=True)
        return

    # Marca como vendido
    await stock_msg.edit(content="VENDIDO: " + stock_msg.content)
    
    # Atualiza vendas
    for nome, variantes in VENDEDORES.items():
        if any(v in stock_msg.content for v in variantes):
            vendas_data[nome]["diaria"] += int(tipo_conta.split("–R$")[-1])
            vendas_data[nome]["total"] += int(tipo_conta.split("–R$")[-1])
            save_json(VENDAS_FILE, vendas_data)
            break
    relatorio_data["total"] = relatorio_data.get("total", 0) + int(tipo_conta.split("–R$")[-1])
    save_json(RELATORIO_FILE, relatorio_data)

    await usuario.send(f"✅ Pix caiu! Boa compra.\n**📦 Sua conta está saindo para a entrega.**\nPrazo de até 2 Dias.\n\n{stock_msg.content}")

    await ctx.respond(f"Conta {tipo_conta} enviada para {usuario.name}.", ephemeral=True)

# /vendas
@bot.slash_command(name="vendas", description="Ver suas vendas")
async def vendas(ctx):
    if ctx.channel.id != CHANNEL_RELATORIO:
        return
    if not tem_cargo(ctx.author):
        await ctx.respond("Você não tem permissão.", ephemeral=True)
        return
    for nome, variantes in VENDEDORES.items():
        if ctx.author.name in variantes:
            dados = vendas_data.get(nome, {"diaria":0, "total":0})
            media = dados["total"] / 4  # Média semanal aproximada
            msg = f"**{nome}**\nDiária: R${dados['diaria']}\nMédia: R${media}\nMensal: R${dados['total']}"
            await ctx.respond(msg)
            return
    await ctx.respond("Nenhuma venda registrada para você.")

# /relatorio
@bot.slash_command(name="relatorio", description="Lucro total da loja")
async def relatorio(ctx):
    if ctx.channel.id != CHANNEL_RELATORIO:
        return
    if not tem_cargo(ctx.author):
        await ctx.respond("Você não tem permissão.", ephemeral=True)
        return
    total = relatorio_data.get("total", 0)
    await ctx.respond(f"📜 **World Blox**\n💰 Lucro total: R${total}")

bot.run(TOKEN)
