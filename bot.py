import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
from datetime import datetime, timedelta
import os

# ================= CONFIGURAÇÕES =================
TOKEN = os.environ.get("TOKEN")  # Coloque seu token no environment variable
STORE = "World Blox"
ALLOWED_ROLES = ["Staff", "Mod", "Entregador", "Farmer", "Influencer"]

WORKERS = {
    "n4ndin": "Nandin", "nandin": "Nandin",
    "lucas": "Lucas", "ℒ𝓊𝒸𝒶𝓈 ℒ𝓊𝒾𝓏".lower(): "Lucas",
    "scther541": "Dionata", "dionata": "Dionata",
    "mklon15": "Mikhayas", "mikhayas": "Mikhayas",
    "__xblaster": "Kaio", "kaio": "Kaio",
    "ramixz": "Ramilson", "ramilson": "Ramilson",
    "eduardo": "Eduardo", "edu": "Eduardo"
}

PIX_KEY = "world.blox018@gmail.com"

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

daily_earnings = {}
total_earnings = {}
weekly_earnings = {}

daily_reset = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
monthly_reset = datetime.utcnow().replace(day=28, hour=0, minute=0, second=0, microsecond=0)
if monthly_reset < datetime.utcnow():
    monthly_reset += timedelta(days=30)

def normalize(name: str) -> str:
    return WORKERS.get(name.lower(), name)

def has_allowed_role(member: discord.Member) -> bool:
    return any(r.name in ALLOWED_ROLES for r in member.roles)

# ================= EVENTOS =================
@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.playing, name=f"Vendendo contas | {STORE}")
    )
    await bot.tree.sync()
    daily_reset_task.start()
    monthly_reset_task.start()
    print(f"{bot.user} online!")

# ================= COMANDO /vendas =================
@bot.tree.command(name="vendas", description="Ver seus ganhos diários, totais e média semanal")
async def vendas(interaction: discord.Interaction):
    if not has_allowed_role(interaction.user):
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    user_name = normalize(interaction.user.name)
    diaria = daily_earnings.get(user_name, 0.0)
    total = total_earnings.get(user_name, 0.0)
    weekly = weekly_earnings.get(user_name, 0.0)
    media_semanal = weekly / 7  # média diária da semana

    text = f"""📊 **Seus ganhos — {STORE}**

👤 Nome: {user_name}
🗓 Diária: R$ {diaria:.2f}
💰 Total: R$ {total:.2f}
📈 Média semanal: R$ {media_semanal:.2f}

👀 Mande o nome da conta desejada que então lhe enviaremos.
"""
    await interaction.user.send(text)
    await interaction.response.send_message("✅ Informações enviadas no privado!", ephemeral=True)

# ================= INTERAÇÃO PARA COMPRAR =================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not has_allowed_role(message.author):
        return

    account_requested = message.content.lower()
    matched = None
    for product in PRODUCTS.keys():
        if account_requested in product.lower():
            matched = product
            break

    if not matched:
        return await message.channel.send("❌ Conta não encontrada, tente ser mais próximo do nome.")

    # Mensagens simulando verificação de stock
    await message.channel.send("📦 Verificando conta em Stock\n⏰ Aguarde um momento...")
    await message.channel.send("✅ Conta disponível será enviada pós o pagamento.\n💸 Chave Pix: " + PIX_KEY)

    # Botão de verificação no canal
    guild = message.guild
    verify_ch = discord.utils.get(guild.text_channels, name=VERIFY_CHANNEL)
    if verify_ch:
        view = VerifyView(buyer=message.author, product=matched)
        await verify_ch.send(f"🔔 {message.author.mention} solicitou {matched}. Clique para confirmar pagamento:", view=view)

# ================= BOTÃO DE VERIFICAÇÃO =================
class VerifyView(View):
    def __init__(self, buyer: discord.User, product: str):
        super().__init__(timeout=None)
        self.buyer = buyer
        self.product = product

    @discord.ui.button(label="Confirmar Pagamento", style=discord.ButtonStyle.green)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_allowed_role(interaction.user):
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

        guild = interaction.guild
        price, stock_channel_name = PRODUCTS[self.product]
        stock_channel = discord.utils.get(guild.text_channels, name=stock_channel_name)
        msgs = [m async for m in stock_channel.history(limit=10)]
        if not msgs:
            return await interaction.response.send_message("🚫 Sem stock.", ephemeral=True)

        # Pega primeira mensagem (conta)
        msg = msgs[0]
        lines = msg.content.splitlines()
        upador_raw = lines[0].strip()
        upador = normalize(upador_raw)
        usuario = lines[2].split(":",1)[1].strip()
        senha = lines[3].split(":",1)[1].strip()

        # Atualiza ganhos
        if interaction.user.name.lower() == upador.lower():
            ganho_upador = price
            ganho_vendedor = 0
        else:
            ganho_upador = price * 0.8
            ganho_vendedor = price * 0.2

        daily_earnings[upador] = daily_earnings.get(upador,0)+ganho_upador
        total_earnings[upador] = total_earnings.get(upador,0)+ganho_upador
        weekly_earnings[upador] = weekly_earnings.get(upador,0)+ganho_upador

        daily_earnings[interaction.user.name] = daily_earnings.get(interaction.user.name,0)+ganho_vendedor
        total_earnings[interaction.user.name] = total_earnings.get(interaction.user.name,0)+ganho_vendedor
        weekly_earnings[interaction.user.name] = weekly_earnings.get(interaction.user.name,0)+ganho_vendedor

        # Deleta a conta do stock
        await msg.delete()

        # DM final para o comprador
        dm_msg = f"""✅ Pix caiu boa compra.

**📦 Sua conta está saindo para a entrega.**
⏳ Prazo de até 2 Dias.

🚨 Caso a conta possua verificação de 2 etapas, informe um Staff, Entregador ou Farmer.

Usuário: `{usuario}`
Senha: `{senha}`

(Contas)
🚨 Botão de compra se expira 🚨
"""
        await self.buyer.send(dm_msg)

        # Confirmação no canal
        await interaction.response.send_message(f"✅ Conta entregue com sucesso!", ephemeral=True)

# ================= RESET DIÁRIO =================
@tasks.loop(minutes=1)
async def daily_reset_task():
    global daily_reset
    now = datetime.utcnow()
    if now >= daily_reset:
        for k in daily_earnings:
            daily_earnings[k] = 0
        daily_reset += timedelta(days=1)

# ================= RESET MENSAL =================
@tasks.loop(minutes=60)
async def monthly_reset_task():
    global monthly_reset
    now = datetime.utcnow()
    if now >= monthly_reset:
        for k in total_earnings:
            total_earnings[k] = 0
            weekly_earnings[k] = 0
        monthly_reset += timedelta(days=30)

bot.run(TOKEN)
