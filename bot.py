import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
from datetime import datetime

# ================= CONFIGURAÇÕES =================
TOKEN = os.environ.get("TOKEN")  # Token do bot via variável de ambiente
STORE = "World Blox"
ALLOWED_ROLES = ["Staff", "Mod", "Entregador", "Farmer"]
PIX_KEY = "world.blox018@gmail.com"  # PIX único

# Normalização de nomes dos trabalhadores
WORKERS = {
    "n4ndin": "Nandin", "nandin": "Nandin",
    "lucas": "Lucas", "ℒ𝓊𝒸𝒶𝓈 ℒ𝓊𝒾𝓏".lower(): "Lucas",
    "scther541": "Dionata", "dionata": "Dionata",
    "mklon15": "Mikhayas", "mikhayas": "Mikhayas",
    "__xblaster": "Kaio", "kaio": "Kaio",
    "ramixz": "Ramilson", "ramilson": "Ramilson",
    "eduardo": "Eduardo", "edu": "Eduardo"
}

# Produtos
PRODUCTS = {
    "God Human": (20, "📦┃stock-god-human"),
    "Dragon Talon v2 (Evo)": (15, "📦┃stock-dragon-talon"),
    "Sharkman Karatê v2 (Evo)": (15, "📦┃stock-sharkman"),
    "Electric Claw": (10, "📦┃stock-electric-claw"),
    "Level Max (2800)": (8, "📦┃stock-level-max"),
    "100 Milhões de Berries": (20, "📦┃stock-berries"),
    "Fruta no Inv": (12, "📦┃stock-fruta-inv"),
    "Conta Tudo Random": (10, "📦┃stock-random")
}

VERIFY_CHANNEL = "✅┃verificar-pagamentos"
REPORT_CHANNEL = "📊┃relatorio-vendas"

# ================= BOT =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Carregar vendas
if os.path.exists("vendas.json"):
    with open("vendas.json", "r") as f:
        vendas_data = json.load(f)
else:
    vendas_data = {}

# Garantir que todos os trabalhadores existem no JSON
for worker in WORKERS.values():
    if worker not in vendas_data:
        vendas_data[worker] = {"diaria": 0, "total": 0}

def normalize(name: str) -> str:
    return WORKERS.get(name.lower(), name)

def save_vendas():
    with open("vendas.json", "w") as f:
        json.dump(vendas_data, f, indent=4)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.playing,
        name="Vendendo contas | World Blox"
    ))
    await bot.tree.sync()
    daily_reset.start()
    monthly_reset.start()
    print("Kael (Bot) online!")

# ===== COMANDO /contas =====
@bot.tree.command(name="contas", description="Ver contas disponíveis")
async def contas(interaction: discord.Interaction):
    # Primeiro envia apenas instruções de PIX
    pix_message = (
        f"💳 Para comprar qualquer conta, envie o pagamento via PIX:\n"
        f"🔑 Chave PIX: `{PIX_KEY}`\n\n"
        f"Após enviar, peça a um vendedor para verificar o pagamento clicando em **Verify Buying**."
    )
    await interaction.user.send(pix_message)

    # Agora envia embed com contas e botões
    embed = discord.Embed(
        title=f"🏪 {STORE} — Contas Blox Fruits",
        description="Clique no botão da conta que deseja comprar.",
        color=0x9b59b6
    )
    view = View()
    for product, (price, _) in PRODUCTS.items():
        embed.add_field(name=product, value=f"💰 R$ {price}", inline=False)
        view.add_item(Button(label=f"Comprar {product}", style=discord.ButtonStyle.primary, custom_id=f"buy_{product}"))

    await interaction.user.send(embed=embed, view=view)
    await interaction.response.send_message("📩 Te mandei as instruções e contas no privado!", ephemeral=True)

# ===== BOTÃO VERIFY =====
class VerifyView(View):
    def __init__(self, buyer: discord.User, product: str):
        super().__init__(timeout=None)
        self.buyer = buyer
        self.product = product

    @discord.ui.button(label="Verify Buying", style=discord.ButtonStyle.green)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verifica permissão
        if not any(r.name in ALLOWED_ROLES for r in interaction.user.roles):
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

        guild = interaction.guild
        price, channel_name = PRODUCTS[self.product]
        stock_channel = discord.utils.get(guild.text_channels, name=channel_name)

        # Pega primeira conta do stock
        msgs = [m async for m in stock_channel.history(limit=10)]
        if not msgs:
            return await interaction.response.send_message("❌ Sem stock.", ephemeral=True)

        msg = msgs[0]
        lines = msg.content.splitlines()

        upador_raw = lines[0].strip()
        upador = normalize(upador_raw)
        usuario = lines[2].split(":", 1)[1].strip()
        senha = lines[3].split(":", 1)[1].strip()

        # Adiciona valor ao UPADOR (não ao vendedor)
        if upador in vendas_data:
            vendas_data[upador]["diaria"] += price
            vendas_data[upador]["total"] += price
            save_vendas()

        # Remove a conta do stock
        await msg.delete()

        # Envia conta apenas após a verificação
        dm_message = f"""✅ **Compra Concluída — {STORE}**

👤 Usuário: `{usuario}`
🔐 Senha: `{senha}`
"""
        await self.buyer.send(dm_message)

        # Mensagem no canal de verificação
        verify_ch = discord.utils.get(guild.text_channels, name=VERIFY_CHANNEL)
        if verify_ch:
            await verify_ch.send(
                f"📦 **Conta entregue**\nUpador: **{upador}**\nVendedor: **{normalize(interaction.user.name)}**"
            )

        await interaction.response.send_message("✅ Conta entregue com sucesso!", ephemeral=True)

# ===== RESET DIÁRIO =====
@tasks.loop(hours=24)
async def daily_reset():
    for worker in vendas_data:
        vendas_data[worker]["diaria"] = 0
    save_vendas()
    await send_report()

# ===== RESET MENSAL =====
@tasks.loop(hours=24)
async def monthly_reset():
    now = datetime.utcnow()
    if now.day == 1 and now.hour == 0:
        for worker in vendas_data:
            vendas_data[worker]["total"] = 0
        save_vendas()
        await send_report()

# ===== RELATÓRIO =====
async def send_report():
    for guild in bot.guilds:
        ch = discord.utils.get(guild.text_channels, name=REPORT_CHANNEL)
        if ch:
            text = f"📊 **Relatório — {STORE}**\n\n"
            for worker, values in vendas_data.items():
                text += f"**[{worker}]**\nDiária: R$ {values['diaria']}\nTotal: R$ {values['total']}\n\n"
            await ch.send(text)

bot.run(TOKEN)
