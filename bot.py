import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
from datetime import datetime

# -------------------- CONFIG --------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# Token
TOKEN = os.environ.get("DISCORD_TOKEN")  # defina DISCORD_TOKEN nas variáveis de ambiente

# IDs de canais
CHANNEL_COMPRAR = 1465477544445874291
CHANNEL_VERIFY = 1465657430292697151
CHANNEL_RELATORIO = 1465657468745941043

# Stocks por tipo de conta
STOCK_CHANNELS = {
    "God Human": 1465679418075643926,
    "Dragon Talor": 1465679812340220069,
    "Sharkman": 1465679631997861990,
    "Electric Claw": 1465679998777032786,
    "100M Berries": 1465680216432050237,
    "Level Max": 1465680124564475935,
    "Fruta no Inv": 1465680280114303165,
    "Tudo Random": 1465680530526834781,
}

# Vendedores e variações de nomes
VENDEDORES = {
    "Mikhayas": ["Mikhayas","mk","MK","MIKHAYAS","Mk","mikhayas"],
    "Nandin": ["N4NDIN","nandin","Nandin","n4ndin","N4ndin"],
    "Lucas": ["Lucas","LUCAS","lucas"],
    "Dionata": ["Dionata","DIONATA","dionata"],
    "Ramilson": ["Ramilson","RAMILSON","Rami","RAMI","rami","ramilson"],
    "Kaio": ["Kaio","Caio","KAIO","CAIO","kaio","caio"],
    "Edu": ["Edu","edu","EDU","eduardo","Eduardo","EDUARDO"],
}

# Arquivos JSON
VENDAS_FILE = "vendas.json"
RELATORIO_FILE = "relatorio.json"

# -------------------- FUNÇÕES AUX --------------------
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file,"r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file,"w") as f:
        json.dump(data, f, indent=4)

vendas_data = load_json(VENDAS_FILE)
relatorio_data = load_json(RELATORIO_FILE)

def tem_cargo(member):
    # Aqui você coloca IDs dos cargos permitidos
    return True

# -------------------- RESET DIÁRIO/MENSAL --------------------
@tasks.loop(hours=24)
async def reset_diario():
    for v in vendas_data:
        vendas_data[v]["diaria"] = 0
    save_json(VENDAS_FILE, vendas_data)

@tasks.loop(hours=24)
async def reset_mensal():
    if datetime.utcnow().day == 28:
        for v in vendas_data:
            vendas_data[v]["total"] = 0
        relatorio_data["total"] = 0
        save_json(VENDAS_FILE, vendas_data)
        save_json(RELATORIO_FILE, relatorio_data)

# -------------------- ON READY --------------------
@bot.event
async def on_ready():
    print(f"{bot.user} está online!")
    reset_diario.start()
    reset_mensal.start()
    await tree.sync()

# -------------------- FUNÇÃO STOCK --------------------
async def pegar_stock(tipo_conta):
    """Retorna primeira mensagem disponível do stock"""
    channel_id = STOCK_CHANNELS.get(tipo_conta)
    if not channel_id:
        return None
    channel = bot.get_channel(channel_id)
    mensagens = await channel.history(limit=100).flatten()
    for msg in mensagens:
        if not msg.content.startswith("VENDIDO"):
            return msg
    return None

async def contar_stock(tipo_conta):
    channel_id = STOCK_CHANNELS.get(tipo_conta)
    if not channel_id:
        return 0
    channel = bot.get_channel(channel_id)
    mensagens = await channel.history(limit=100).flatten()
    count = sum(1 for msg in mensagens if not msg.content.startswith("VENDIDO"))
    return count

# -------------------- COMANDOS --------------------

# /contas
@tree.command(name="contas", description="Veja as contas disponíveis")
async def contas(interaction: discord.Interaction):
    if interaction.channel.id != CHANNEL_COMPRAR:
        await interaction.response.send_message("Este comando só funciona no canal correto.", ephemeral=True)
        return
    
    # Monta mensagem com stock dinâmico
    msg = "**--🥊 Estilos de luta--**\n\n"
    for conta in ["God Human","Dragon Talor","Sharkman","Electric Claw"]:
        qtd = await contar_stock(conta)
        preco = {"God Human":20,"Dragon Talor":15,"Sharkman":15,"Electric Claw":10}[conta]
        msg += f"• {conta} (Disponíveis: {qtd}) – R${preco}\n"
    
    msg += "\n**--📦 Contas Padrão--**\n\n"
    for conta in ["100M Berries","Level Max","Fruta no Inv","Tudo Random"]:
        qtd = await contar_stock(conta)
        preco = {"100M Berries":20,"Level Max":8,"Fruta no Inv":12,"Tudo Random":10}[conta]
        msg += f"• {conta} (Disponíveis: {qtd}) – R${preco}\n"

    msg += "\n✅ Contas 100% seguras\n\n👀 Mande o nome da conta que deseja comprar"
    await interaction.user.send(msg)
    await interaction.response.send_message("As contas foram enviadas no privado!", ephemeral=True)

# /verify
@tree.command(name="verify", description="Verificar pagamento de conta")
@app_commands.describe(tipo_conta="Tipo da conta", usuario="Usuário comprador")
async def verify(interaction: discord.Interaction, tipo_conta: str, usuario: discord.Member):
    if interaction.channel.id != CHANNEL_VERIFY:
        await interaction.response.send_message("Este comando só pode ser usado no canal de verificação.", ephemeral=True)
        return
    if not tem_cargo(interaction.user):
        await interaction.response.send_message("Você não tem permissão.", ephemeral=True)
        return

    stock_msg = await pegar_stock(tipo_conta)
    if not stock_msg:
        await interaction.response.send_message("Não há stock disponível para essa conta.", ephemeral=True)
        return

    await stock_msg.edit(content="VENDIDO: " + stock_msg.content)

    # Atualiza vendas
    valor = {"God Human":20,"Dragon Talor":15,"Sharkman":15,"Electric Claw":10,
             "100M Berries":20,"Level Max":8,"Fruta no Inv":12,"Tudo Random":10}.get(tipo_conta,0)
    
    for nome, variantes in VENDEDORES.items():
        if any(v in stock_msg.content for v in variantes):
            vendas_data[nome]["diaria"] += valor
            vendas_data[nome]["total"] += valor
            save_json(VENDAS_FILE, vendas_data)
            break

    relatorio_data["total"] = relatorio_data.get("total",0) + valor
    save_json(RELATORIO_FILE, relatorio_data)

    await usuario.send(f"✅ Pagamento recebido! Sua conta está saindo para entrega:\n\n{stock_msg.content}")
    await interaction.response.send_message(f"Conta {tipo_conta} enviada para {usuario.name}.", ephemeral=True)

# /vendas
@tree.command(name="vendas", description="Ver suas vendas")
async def vendas(interaction: discord.Interaction):
    if interaction.channel.id != CHANNEL_RELATORIO:
        return
    if not tem_cargo(interaction.user):
        await interaction.response.send_message("Você não tem permissão.", ephemeral=True)
        return
    for nome, variantes in VENDEDORES.items():
        if interaction.user.name in variantes:
            dados = vendas_data.get(nome, {"diaria":0,"total":0})
            media = dados["total"]/4
            msg = f"**{nome}**\nDiária: R${dados['diaria']}\nMédia: R${media}\nMensal: R${dados['total']}"
            await interaction.response.send_message(msg)
            return
    await interaction.response.send_message("Nenhuma venda registrada para você.")

# /relatorio
@tree.command(name="relatorio", description="Lucro total da loja")
async def relatorio(interaction: discord.Interaction):
    if interaction.channel.id != CHANNEL_RELATORIO:
        return
    if not tem_cargo(interaction.user):
        await interaction.response.send_message("Você não tem permissão.", ephemeral=True)
        return
    total = relatorio_data.get("total",0)
    await interaction.response.send_message(f"📜 **World Blox**\n💰 Lucro total: R${total}")

# -------------------- RUN --------------------
bot.run(TOKEN)
