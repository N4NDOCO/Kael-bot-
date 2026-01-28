import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import os
from datetime import datetime, timedelta

# ================= CONFIGURAÇÕES =================
TOKEN = os.environ["TOKEN"]  # Pegando do Koyeb
STORE = "World Blox"
ALLOWED_ROLES = ["Staff", "Mod", "Influencer", "Farmer", "Entregador"]

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

# ================= PIX =================
PIX_KEYS = {
    "Nandin": "85996242996",
    "Lucas": "85991202668",
    "Eduardo": "world.blox018@gmail.com"
}

# ================= PRODUTOS =================
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

# ================= GANHOS =================
daily_earnings = {}   # Reset diário
total_earnings = {}   # Reset mensal
daily_reset = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
monthly_reset = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32)

def normalize(name: str) -> str:
    return WORKERS.get(name.lower(), name)

def has_role(member, allowed_roles):
    return any(role.name in allowed_roles for role in member.roles)

# ================= EVENTOS =================
@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.playing, name=f"Vendendo contas | {STORE}")
    )
    await bot.tree.sync()
    daily_report.start()
    print(f"{bot.user} online!")

# ================= COMANDOS =================
@bot.tree.command(name="contas", description="Ver contas disponíveis")
async def contas(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"🏪 {STORE} — Contas Blox Fruits",
        description="Clique no botão da conta que deseja comprar.",
        color=0x9b59b6
    )
    for p, (price, _) in PRODUCTS.items():
        embed.add_field(name=p, value=f"💰 R$ {price}", inline=False)

    view = View()
    for product in PRODUCTS:
        view.add_item(Button(label=product, style=discord.ButtonStyle.primary, custom_id=f"buy_{product}"))

    await interaction.user.send(embed=embed, view=view)
    await interaction.response.send_message("📩 Te mandei as contas no privado!", ephemeral=True)

# ================= BOTÃO VERIFY =================
class VerifyView(View):
    def __init__(self, buyer: discord.User, product: str, seller: discord.Member):
        super().__init__(timeout=None)
        self.buyer = buyer
        self.product = product
        self.seller = seller

    @discord.ui.button(label="Verify Buying", style=discord.ButtonStyle.green)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_role(interaction.user, ALLOWED_ROLES):
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

        guild = interaction.guild
        price, channel_name = PRODUCTS[self.product]
        stock_channel = discord.utils.get(guild.text_channels, name=channel_name)

        msgs = [m async for m in stock_channel.history(limit=10)]
        if not msgs:
            return await interaction.response.send_message("❌ Sem stock.", ephemeral=True)

        msg = msgs[0]
        lines = msg.content.splitlines()

        upador_raw = lines[0].strip()
        upador = normalize(upador_raw)
        usuario = lines[2].split(":", 1)[1].strip()
        senha = lines[3].split(":", 1)[1].strip()
        pix_upador = PIX_KEYS.get(upador, None)

        # Atualiza ganhos do upador
        daily_earnings[upador] = daily_earnings.get(upador, 0) + price
        total_earnings[upador] = total_earnings.get(upador, 0) + price

        # Comissão do vendedor
        seller_name = normalize(self.seller.name)
        comissao = price * 0.2
        daily_earnings[seller_name] = daily_earnings.get(seller_name, 0) + comissao
        total_earnings[seller_name] = total_earnings.get(seller_name, 0) + comissao

        await msg.delete()

        dm_message = f"""✅ **Compra Concluída — {STORE}**

👤 Usuário: `{usuario}`
🔐 Senha: `{senha}`
💳 Pagamento via PIX: `{pix_upador}`
"""
        await self.buyer.send(dm_message)

        verify_ch = discord.utils.get(guild.text_channels, name=VERIFY_CHANNEL)
        if verify_ch:
            await verify_ch.send(
                f"📦 **Conta entregue**\nUpador: **{upador}**\nVendedor: **{seller_name}**\nProduto: {self.product}\nPreço: {price}\nComissão Vendedor: {comissao:.2f}"
            )

        await interaction.response.send_message("✅ Conta entregue com sucesso!", ephemeral=True)

# ================= RELATÓRIOS =================
@bot.tree.command(name="venda", description="Ver vendas diárias e totais")
async def venda(interaction: discord.Interaction):
    if not has_role(interaction.user, ALLOWED_ROLES):
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    text = f"📊 **Relatório Diário — {STORE}**\n\n"
    for p in daily_earnings:
        text += f"**{p}**\nDiária: R$ {daily_earnings[p]:.2f}\nTotal: R$ {total_earnings.get(p,0):.2f}\n\n"
    ch = discord.utils.get(interaction.guild.text_channels, name=REPORT_CHANNEL)
    if ch:
        await ch.send(text)
    await interaction.response.send_message("✅ Relatório enviado!", ephemeral=True)

# ================= TAREFA DIÁRIA =================
@tasks.loop(minutes=1)
async def daily_report():
    global daily_reset, monthly_reset
    now = datetime.utcnow()
    if now >= daily_reset:
        for k in daily_earnings:
            daily_earnings[k] = 0
        daily_reset += timedelta(days=1)

    if now >= monthly_reset:
        for k in total_earnings:
            total_earnings[k] = 0
        monthly_reset += timedelta(days=32)

bot.run(TOKEN)
