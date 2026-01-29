import discord
from discord.ext import commands
import json
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# IDs de canais
CANAL_CONTAS = 1465477544445874291
CANAL_VERIFY = 1465657430292697151
CANAL_RELATORIO = 1465657468745941043

# IDs dos stocks
STOCKS = {
    "God Human": 1465679418075643926,
    "Dragon Talor": 1465679812340220069,
    "Sharkman": 1465679631997861990,
    "Electric Claw": 1465679998777032786,
    "100M Berries": 1465680216432050237,
    "Level Max": 1465680124564475935,
    "Fruta no Inv": 1465680280114303165,
    "Tudo Random": 1465680530526834781
}

# Carregar vendas e relatório
with open("vendas.json", "r") as f:
    vendas = json.load(f)

with open("relatorio.json", "r") as f:
    relatorio = json.load(f)

# Contas à venda
contas_disponiveis = {
    "God Human": {"Lv": 2800, "Preço": 20},
    "Dragon Talor v2": {"Lv": 2800, "Preço": 15},
    "Sharkman Karatê v2": {"Lv": 2800, "Preço": 15},
    "Electric Claw": {"Lv": 2800, "Preço": 10},
    "100M Berries": {"Lv": 2800, "Preço": 20},
    "Level Max": {"Lv": 2800, "Preço": 8},
    "Fruta no Inv": {"Lv": 2800, "Preço": 12},
    "Tudo Random": {"Lv": "Aleatória", "Preço": 10}
}

# Stocks iniciais (quantidade)
stocks_quantidade = {nome: 5 for nome in contas_disponiveis}  # exemplo: 5 unidades cada

# Lista de nomes de vendedores
VENDEDORES = ["Mikhayas", "Nandin", "Lucas", "Dionata", "Ramilson", "Kaio", "Edu"]

# /contas envia DM com lista
@bot.slash_command(name="contas", description="Veja as contas disponíveis")
async def contas(interaction: discord.Interaction):
    if interaction.channel.id != CANAL_CONTAS:
        await interaction.response.send_message("Este comando só funciona no canal de compras!", ephemeral=True)
        return

    msg = "**Contas disponíveis:**\n\n"
    for nome, info in contas_disponiveis.items():
        qtd = stocks_quantidade.get(nome, 0)
        msg += f"• {nome}\nLv: {info['Lv']} – R${info['Preço']} | Estoque: {qtd}\n\n"

    msg += "✅ Contas **100%** seguras\n\n"
    msg += "👀 Mande o nome da conta que deseja comprar"

    await interaction.user.send(msg)
    await interaction.response.send_message("💌 Enviei as contas para o seu DM!", ephemeral=True)


# Listener para pegar escolha da conta na DM
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Verifica se é DM
    if isinstance(message.channel, discord.DMChannel):
        escolha = message.content.strip()
        if escolha in contas_disponiveis:
            if stocks_quantidade.get(escolha, 0) > 0:
                stocks_quantidade[escolha] -= 1
                await message.channel.send(
                    f"✅ Conta **{escolha}** vendida!\nUsuário: {message.author}\nPreço: R${contas_disponiveis[escolha]['Preço']}"
                )
                # Aqui você pode atualizar vendas.json se necessário
            else:
                await message.channel.send(f"❌ A conta **{escolha}** não está disponível no momento.")
        else:
            await message.channel.send("❌ Conta não reconhecida. Digite exatamente o nome listado nas contas.")
    await bot.process_commands(message)


# /verify só no canal de verificação
@bot.slash_command(name="verify", description="Verificar pagamento da conta")
async def verify(interaction: discord.Interaction):
    if interaction.channel.id != CANAL_VERIFY:
        await interaction.response.send_message("Este comando só funciona no canal de verificação!", ephemeral=True)
        return

    # Aqui você pode implementar a lógica de verificação de pagamento
    await interaction.response.send_message("Pagamento verificado! Conta liberada.", ephemeral=True)


# /vendas para mostrar lucro do vendedor
@bot.slash_command(name="vendas", description="Mostra lucro do vendedor")
async def vendas_cmd(interaction: discord.Interaction):
    if str(interaction.user.id) not in VENDEDORES:
        await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
        return

    usuario = interaction.user.name
    info = vendas.get(usuario, {"diaria": 0, "total": 0})
    msg = f"**{usuario}**\nDiária: R${info['diaria']}\nTotal: R${info['total']}\nMensal: R${info['total']*30}"  # exemplo
    await interaction.response.send_message(msg)


# /relatorio para mostrar lucro total (somente canal correto)
@bot.slash_command(name="relatorio", description="Mostra lucro total da loja")
async def relatorio_cmd(interaction: discord.Interaction):
    if interaction.channel.id != CANAL_RELATORIO:
        await interaction.response.send_message("❌ Este comando só funciona no canal de relatório!", ephemeral=True)
        return

    total = sum(v['total'] for v in vendas.values())
    msg = f"📜 **World Blox**\n💰 Lucro total: R${total}"
    await interaction.response.send_message(msg)


@bot.event
async def on_ready():
    print(f"{bot.user} está online!")

# Rodar bot
import os
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
