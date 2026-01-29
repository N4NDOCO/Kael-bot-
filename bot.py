import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime

# ==========================
# CONFIGURAÇÕES
# ==========================
TOKEN = "SEU_TOKEN_AQUI"  # Substitua pelo seu token real
GUILD_ID = 123456789012345678  # Substitua pelo ID do seu servidor
RELATORIO_CHANNEL = "📊┃relatorio-vendas"
COMPRAR_CHANNEL = "📦┃comprar-contas"
VERIFY_CHANNEL = "✅┃verificar-pagamentos"

CARGOS_AUTORIZADOS = ["Staff", "Mod", "Infuencer", "Farmer", "Entregador"]

VARIACOES_NOMES = {
    "Mikhayas": ["Mikhayas", "mk", "MK", "MIKHAYAS", "Mk", "mikhayas"],
    "N4NDIN": ["N4NDIN", "nandin", "Nandin", "n4ndin", "N4ndin"],
    "Lucas": ["Lucas", "LUCAS", "lucas"],
    "Dionata": ["Dionata", "DIONATA", "dionata"],
    "Ramilson": ["Ramilson","RAMILSON","Rami","RAMI","rami","ramilson"],
    "Kaio": ["Kaio","Caio","KAIO","CAIO","kaio","caio"],
    "Edu": ["Edu","edu","EDU","eduardo","Eduardo","EDUARDO"]
}

# ==========================
# BOT SETUP
# ==========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# ==========================
# FUNÇÕES AUXILIARES
# ==========================
def carregar_json(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def usuario_autorizado(member):
    return any(role.name in CARGOS_AUTORIZADOS for role in member.roles)

def encontrar_nome_variacao(nome_digitado):
    for principal, variacoes in VARIACOES_NOMES.items():
        if nome_digitado.lower() in [v.lower() for v in variacoes]:
            return principal
    return None

def procurar_conta_stock(nome_digitado):
    stock = carregar_json("vendas.json")
    for conta, info in stock.items():
        if nome_digitado.lower() in conta.lower():
            return conta, info
    return None, None

# ==========================
# EVENTO DE INÍCIO
# ==========================
@bot.event
async def on_ready():
    print(f"{bot.user} está online!")
    try:
        await tree.sync(guild=discord.Object(id=GUILD_ID))
        print("Comandos sincronizados com sucesso!")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

# ==========================
# COMANDOS
# ==========================

# /contas - envia contas em DM
@tree.command(name="contas", description="Veja as contas disponíveis", guild=discord.Object(id=GUILD_ID))
async def contas(interaction: discord.Interaction):
    if interaction.channel.name != COMPRAR_CHANNEL:
        await interaction.response.send_message(f"Use este comando no canal correto: {COMPRAR_CHANNEL}", ephemeral=True)
        return

    stock = carregar_json("vendas.json")
    mensagem = "**Contas à venda:**\n\n"
    for nome, info in stock.items():
        emojis = info.get("emoji", "")
        preco = info.get("preco", "Indefinido")
        nivel = info.get("nivel", "Indefinido")
        mensagem += f"• {nome} {emojis}\nLv {nivel} – R${preco}\n\n"

    mensagem += "✅ Contas **100%** seguras\n\n👀 Mande o nome da conta que deseja comprar"
    await interaction.user.send(mensagem)
    await interaction.response.send_message("📩 Confira sua DM com as contas disponíveis!", ephemeral=True)

# /vendas - lucro individual
@tree.command(name="vendas", description="Veja seu lucro diário, médio e mensal", guild=discord.Object(id=GUILD_ID))
async def vendas(interaction: discord.Interaction):
    if not usuario_autorizado(interaction.user):
        await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
        return

    data = carregar_json("relatorio.json")
    nome = encontrar_nome_variacao(interaction.user.name)
    if not nome:
        await interaction.response.send_message("Seu usuário não foi encontrado no sistema.", ephemeral=True)
        return

    info = data.get(nome, {"diaria":0,"media":0,"mensal":0})
    mensagem = f"**{nome}**\nDiária: R${info['diaria']}\nMédia: R${info['media']}\nMensal: R${info['mensal']}"
    await interaction.response.send_message(mensagem, ephemeral=True)

# /relatorio - lucro total da loja
@tree.command(name="relatorio", description="Lucro total da loja", guild=discord.Object(id=GUILD_ID))
async def relatorio(interaction: discord.Interaction):
    if not usuario_autorizado(interaction.user):
        await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
        return

    data = carregar_json("relatorio.json")
    total = sum(v.get("mensal",0) for v in data.values())
    mensagem = f"📜 **World Blox**\n💰 Lucro total: R${total}"
    canal = discord.utils.get(interaction.guild.channels, name=RELATORIO_CHANNEL)
    if canal:
        await canal.send(mensagem)
    await interaction.response.send_message("Relatório enviado no canal de vendas.", ephemeral=True)

# /verify - confirmar pagamento
@tree.command(name="verify", description="Confirmar pagamento de uma conta", guild=discord.Object(id=GUILD_ID))
async def verify(interaction: discord.Interaction, usuario: discord.Member, conta: str):
    if interaction.channel.name != VERIFY_CHANNEL:
        await interaction.response.send_message(f"Use este comando apenas no canal {VERIFY_CHANNEL}.", ephemeral=True)
        return
    if not usuario_autorizado(interaction.user):
        await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
        return

    nome_conta, info = procurar_conta_stock(conta)
    if not nome_conta:
        await interaction.response.send_message("Conta não encontrada ou indisponível.", ephemeral=True)
        return

    # Remove do stock
    stock = carregar_json("vendas.json")
    if nome_conta in stock:
        del stock[nome_conta]
        salvar_json("vendas.json", stock)

    # Atualiza relatorio
    relatorio_data = carregar_json("relatorio.json")
    vendedor_nome = encontrar_nome_variacao(interaction.user.name)
    if vendedor_nome:
        if vendedor_nome not in relatorio_data:
            relatorio_data[vendedor_nome] = {"diaria":0,"media":0,"mensal":0}
        relatorio_data[vendedor_nome]["diaria"] += info.get("preco",0)
        relatorio_data[vendedor_nome]["mensal"] += info.get("preco",0)
        salvar_json("relatorio.json", relatorio_data)

    # Envia conta para o cliente
    await usuario.send(f"✅ Pix caiu boa compra.\n**📦 Sua conta está saindo para a entrega:**\n\nUsuário: {nome_conta}\nSenha: {info.get('senha','---')}\n\n🚨 Caso sua conta possua verificação de 2 etapas, informe um Staff, Entregador ou Farmer.\n\n(Contas) 🚨 Botão de compra se expira")

    await interaction.response.send_message(f"Conta {nome_conta} entregue para {usuario.name}.", ephemeral=True)

# ==========================
# INICIAR BOT
# ==========================
bot.run(TOKEN)
