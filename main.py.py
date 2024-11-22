import discord
from discord.ext import commands
import psycopg2
from datetime import datetime
import pytz
import os
import logging
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# Configuração do Flask para manter o bot ativo no Heroku
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot está rodando!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

if not TOKEN or not DATABASE_URL:
    logging.critical("Erro: TOKEN ou DATABASE_URL não configurados. Verifique o arquivo .env.")
    exit()

# Conexão com o banco de dados
try:
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
except Exception as e:
    logging.critical(f"Erro ao conectar ao banco de dados: {e}")
    exit()

# Criar tabela de registros, se não existir
def criar_tabela():
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pontos (
            id SERIAL PRIMARY KEY,
            usuario TEXT,
            user_id BIGINT,
            data DATE,
            hora TIME,
            acao TEXT
        );
    """)
    conn.commit()

criar_tabela()

# Configuração do bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

brt = pytz.timezone('America/Sao_Paulo')

@bot.event
async def on_ready():
    logging.info(f"Bot conectado como {bot.user} e pronto para uso!")

def registrar_ponto(usuario, user_id, data, hora, acao):
    """Registra um ponto no banco de dados."""
    try:
        cur.execute("""
            INSERT INTO pontos (usuario, user_id, data, hora, acao)
            VALUES (%s, %s, %s, %s, %s);
        """, (usuario, user_id, data, hora, acao))
        conn.commit()
        logging.info(f"{acao} registrada para {usuario} às {hora}.")
    except Exception as e:
        logging.error(f"Erro ao registrar ponto: {e}")

@bot.command(name="baterponto")
async def bater_ponto(ctx):
    try:
        usuario = ctx.author.name
        user_id = ctx.author.id
        data_atual = datetime.now(brt).strftime("%Y-%m-%d")
        hora_atual = datetime.now(brt).strftime("%H:%M:%S")

        registrar_ponto(usuario, user_id, data_atual, hora_atual, "Entrada")

        embed = discord.Embed(
            title="📥 Ponto Registrado",
            color=discord.Color.green()
        )
        embed.add_field(name="Usuário", value=f"<@{user_id}>", inline=True)
        embed.add_field(name="Data", value=f"{data_atual}", inline=True)
        embed.add_field(name="Hora de Entrada", value=f"{hora_atual}", inline=True)
        embed.set_footer(text="Entrada registrada com sucesso!", icon_url=bot.user.avatar.url)

        await ctx.send(embed=embed)
        await ctx.message.delete()
    except Exception as e:
        await ctx.send("Ocorreu um erro ao registrar seu ponto. Tente novamente mais tarde.")
        logging.error(f"Erro ao registrar ponto de entrada: {e}")

@bot.command(name="finalizarponto")
async def finalizar_ponto(ctx):
    try:
        usuario = ctx.author.name
        user_id = ctx.author.id
        data_atual = datetime.now(brt).strftime("%Y-%m-%d")
        hora_atual = datetime.now(brt).strftime("%H:%M:%S")

        registrar_ponto(usuario, user_id, data_atual, hora_atual, "Saída")

        embed = discord.Embed(
            title="📤 Ponto Finalizado",
            color=discord.Color.red()
        )
        embed.add_field(name="Usuário", value=f"<@{user_id}>", inline=True)
        embed.add_field(name="Data", value=f"{data_atual}", inline=True)
        embed.add_field(name="Hora de Saída", value=f"{hora_atual}", inline=True)
        embed.set_footer(text="Saída registrada com sucesso!", icon_url=bot.user.avatar.url)

        await ctx.send(embed=embed)
        await ctx.message.delete()
    except Exception as e:
        await ctx.send("Ocorreu um erro ao finalizar seu ponto. Tente novamente mais tarde.")
        logging.error(f"Erro ao registrar ponto de saída: {e}")

@bot.command(name="verpontos")
async def ver_pontos(ctx, usuario: discord.User = None):
    try:
        if usuario is None:
            cur.execute("SELECT * FROM pontos;")
        else:
            cur.execute("SELECT * FROM pontos WHERE user_id = %s;", (usuario.id,))

        registros = cur.fetchall()

        if not registros:
            await ctx.send("Nenhum registro encontrado.")
            return

        embed = discord.Embed(title="📜 Registros de Ponto", color=discord.Color.blurple())
        for registro in registros:
            embed.add_field(
                name=f"{registro[1]} ({registro[2]})",
                value=f"**Data:** {registro[3]}\n**Hora:** {registro[4]}\n**Ação:** {registro[5]}",
                inline=False
            )
        await ctx.send(embed=embed)
        await ctx.message.delete()
    except Exception as e:
        await ctx.send("Erro ao visualizar os pontos.")
        logging.error(f"Erro ao visualizar os pontos: {e}")

if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    bot.run(TOKEN)
