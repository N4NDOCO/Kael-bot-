import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
from datetime import datetime, timedelta
import os

# ================= CONFIGURAÇÕES =================
TOKEN = os.environ.get("TOKEN")  # Coloque seu token no Koyeb env vars
STORE = "World Blox"
ALLOWED_ROLES = ["Staff", "Mod", "Influencer", "Farmer", "Entregador"]

# ================= TRABALHADORES / UPADORES =================
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
PIX_KEY = "world.blox018@gmail.com"  # PIX da loja

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
daily_earnings = {}   # Reseta todo dia
total_earnings = {}   # Reseta todo mês
store_total = 0       # Total da loja (soma de todos os vendedores/upadores)

daily_reset = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
monthly_reset = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32)

def normalize(name: str) -> str:
    return WORKERS.get(name.lower(), name)

def has_role(member, allowed_roles):
    return any(role.name in allowed_roles for role in member.roles)

# ================= EVENTO DE READY =================
@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.playing, name=f"Vendendo contas | {STORE}")
    )
    await bot.tree.sync()
    daily_report.start()
    print(f"{bot.user} online!")

# ================= COMANDO /CONTAS =================
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

# ================= BOTÃO DE COMPRA =================
class PurchaseView(View):
    def __init__(self, buyer: discord.User, product: str):
        super().__init__(timeout=None)
        self.buyer = buyer
        self.product = product

    @discord.ui.button(label="Comprar", style=discord.ButtonStyle.green)
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "📦 Verificando conta em Stock\n⏰ Aguarde um momento...", ephemeral=True
        )

        await self.buyer.send(
            f"✅ Conta disponível será enviada pós pagamento.\n💸 Chave Pix: {PIX_KEY}"
        )

        # Cria botão de verificação no canal VERIFY_CHANNEL
        guild = interaction.guild
        verify_ch = discord.utils.get(guild.text_channels, name=VERIFY_CHANNEL)
        if verify_ch:
            view = VerifyView(buyer=self.buyer, product=self.product, seller=interaction.user)
            await verify_ch.send(
                content=f"💰 Pedido de verificação para **{self.product}** do usuário {self.buyer.mention}",
                view=view
            )

# ================= BOTÃO DE VERIFY =================
class VerifyView(View):
    def __init__(self, buyer: discord.User, product: str, seller: discord.Member):
        super().__init__(timeout=None)
        self.buyer = buyer
        self.product = product
        self.seller = seller

    @discord.ui.button(label="Verificar Pagamento", style=discord.ButtonStyle.blurple)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_role(interaction.user, ALLOWED_ROLES):
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

        guild = interaction.guild
        price, stock_channel_name = PRODUCTS[self.product]
        stock_channel = discord.utils.get(guild.text_channels, name=stock_channel_name)
        msgs = [m async for m in stock_channel.history(limit=10)]
        if not msgs:
            return await interaction.response.send_message("❌ Sem stock.", ephemeral=True)

        msg = msgs[0]
        lines = msg.content.splitlines()
        upador_raw = lines[0].strip()
        upador = normalize(upador_raw)
        usuario = lines[2].split(":",1)[1].strip()
        senha = lines[3].split(":",1)[1].strip()

        # Distribui lucros
        upador_gain = price * 0.8
        seller_gain = price * 0.2

        daily_earnings[upador] = daily_earnings.get(upador,0) + upador_gain
        total_earnings[upador] = total_earnings.get(upador,0) + upador_gain

        seller_name = normalize(self.seller.name)
        daily_earnings[seller_name] = daily_earnings.get(seller_name,0) + seller_gain
        total_earnings[seller_name] = total_earnings.get(seller_name,0) + seller_gain

        global store_total
        store_total += price

        await msg.delete()

        # Mensagem para o vendedor
        await interaction.response.send_message(
            f"✅ Pix caiu boa compra.\n\n"
            f"📦 Sua conta está saindo para a entrega.\n"
            f"⏳ Prazo de até 2 dias.\n\n"
            f"🚨 Caso sua conta possua verificação de 2 etapas, informe um Staff, Entregador ou Farmer.",
            ephemeral=True
        )

        # Envia a conta pro cliente
        await self.buyer.send(f"📦 Sua conta:\nUsuário: `{usuario}`\nSenha: `{senha}`")

# ================= /VENDA =================
@bot.tree.command(name="venda", description="Ver seus ganhos")
async def venda(interaction: discord.Interaction):
    user_name = normalize(interaction.user.name)
    if not has_role(interaction.user, ALLOWED_ROLES):
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    diaria = daily_earnings.get(user_name,0)
    total = total_earnings.get(user_name,0)

    text = f"📊 **Relatório — {user_name}**\n\n"
    text += f"💰 Diária: R$ {diaria:.2f}\n"
    text += f"💵 Total: R$ {total:.2f}\n"

    await interaction.response.send_message(text, ephemeral=True)

# ================= /RELATORIO =================
@bot.tree.command(name="relatorio", description="Relatório da loja")
async def relatorio(interaction: discord.Interaction):
    if not has_role(interaction.user, ALLOWED_ROLES):
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    text = f"📊 **Relatório da Loja — {STORE}**\n\n"
    text += f"💵 Total acumulado do mês: R$ {store_total:.2f}\n"
    await interaction.response.send_message(text, ephemeral=True)

# ================= RESET DIÁRIO E MENSAL =================
@tasks.loop(minutes=1)
async def daily_report():
    global daily_reset, monthly_reset, store_total
    now = datetime.utcnow()
    if now >= daily_reset:
        for k in daily_earnings:
            daily_earnings[k] = 0
        daily_reset += timedelta(days=1)

    if now >= monthly_reset:
        for k in total_earnings:
            total_earnings[k] = 0
        store_total = 0
        monthly_reset += timedelta(days=32)

bot.run(TOKEN)
