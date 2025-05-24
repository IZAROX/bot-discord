import os
from dotenv import load_dotenv
import sys
import colorama
from colorama import Fore, Style, init
import discord
from discord.ext import commands
from keep_alive import keep_alive
import asyncio
import time
from datetime import datetime, timedelta
import json
import logging
import requests
from requests import post
from config import BOT_VERSION

# --------------------------------------------------------  BASE  --------------------------------------------------------

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
solar = os.getenv("SOLARWINDS_TOKEN")

intents = discord.Intents.all()
init(autoreset=True)

# Ensemble temporaire pour stocker les IDs des messages supprimés par le bot
bot_deleted_messages = set()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
bot.help_command = None

OWNER_ID = 1265356662907076681
WHITELIST_IDS = [OWNER_ID, 1122259572267155577]  # Ajoute ici les IDs autorisés

async def delete_command_message(msg):
    bot_deleted_messages.add(msg.id)
    await msg.delete()

# -----------------------------------------------------  CONFIG DU SNIPE  ------------------------------------------------------

# Nom du fichier JSON pour stocker les messages supprimés
FILE_PATH = 'sniped_messages.json'

# Fonction pour charger les données depuis le fichier JSON
def load_messages():
    if os.path.exists(FILE_PATH):
        try:
            with open(FILE_PATH, 'r') as file:
                return json.load(file)
        except json.JSONDecodeError:
            print("Le fichier JSON est corrompu. Création d'un nouveau fichier.")
            return {}
    return {}

# Fonction pour sauvegarder les messages dans le fichier JSON
def save_messages(data):
    with open(FILE_PATH, 'w') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

# Dictionnaire des messages supprimés : {channel_id: [{"content": ..., "author": ..., "time": ...}]}
sniped_messages = load_messages()

# -----------------------------------------------------  CONFIG DES LOGS  ------------------------------------------------------

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        message = super().format(record)
        return f"{color}{message}{Style.RESET_ALL}"

class SolarWindsHandler(logging.Handler):
    def __init__(self, token):
        super().__init__()
        self.token = token
        self.url = "https://logs.collector.eu-01.cloud.solarwinds.com/v1/logs"

    def emit(self, record):
        log_entry = self.format(record)

        # Contenu réduit
        payload = {
            "logs": [
                {
                    "message": log_entry
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {solar}",
            "Content-Type": "application/json"
        }


        try:
            response = requests.post(self.url, headers=headers, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), timeout=5)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[SolarWinds] Échec d'envoi du log : {e}")

# Configuration du logger global
logger = logging.getLogger("discord_bot")
logger.setLevel(logging.DEBUG)

# Supprimer les handlers existants si redémarrage
logger.handlers.clear()

# Console (colorée)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(ColorFormatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

# Fichier log
file_handler = logging.FileHandler("bot_logs.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

# SolarWinds
solarwinds_handler = SolarWindsHandler(os.getenv("SOLARWINDS_TOKEN"))
solarwinds_handler.setLevel(logging.INFO)
solarwinds_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(solarwinds_handler)

# -----------------------------------------------------  NETTOYAGE LOGS  -----------------------------------------------------

# Fonction pour nettoyer les logs
def nettoyer_logs():
    # Chemin vers le fichier des logs
    log_file_path = "bot_logs.log"

    # Vérifie si le fichier existe
    if not os.path.exists(log_file_path):
        return  # Si le fichier n'existe pas, on arrête ici

    # Temps actuel
    current_time = time.time()

    # Calculer le seuil (une semaine en secondes)
    seuil_temps = current_time - 7 * 24 * 60 * 60  # 7 jours

    # Lire le fichier de log
    with open(log_file_path, "r", encoding="utf-8") as log_file:
        lines = log_file.readlines()

    # Filtrer les lignes dont la date est plus ancienne que le seuil
    filtered_lines = []
    for line in lines:
        # Extraire la date de chaque ligne du log (au format YYYY-MM-DD HH:MM:SS,fff)
        date_str = line.split(" - ")[0]  # Supposer que la date est avant " - "
        try:
            log_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S,%f")
        except ValueError:
            continue  # Ignore les lignes avec un format de date invalide

        # Comparer la date avec le seuil
        if log_date.timestamp() >= seuil_temps:
            filtered_lines.append(line)

    # Réécrire le fichier de log avec les lignes filtrées
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        log_file.writelines(filtered_lines)

# Appeler cette fonction périodiquement (par exemple, une fois par jour)
nettoyer_logs()

# --------------------------------------------------------  EVENT  --------------------------------------------------------

@bot.event
async def on_ready():
    print(f"{Fore.GREEN}(ID: {Fore.YELLOW}{bot.user.name}{Fore.GREEN}) est connecté !")
    #Activité du bot
    activity = discord.Game(name=f"!help | V{BOT_VERSION}")
    await bot.change_presence(activity=activity)

# Exemple d'erreur de commande
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        logger.warning(f"Commande inconnue utilisée par {ctx.author}: {ctx.message.content}")  # Log d'avertissement
        await ctx.send("❌ Commande inconnue.")
    else:
        logger.error(f"Erreur dans la commande de {ctx.author}: {error}")  # Log d'erreur
        await ctx.send(f"Une erreur s'est produite: {error}")

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.content:
        return

    if message.id in bot_deleted_messages:
        bot_deleted_messages.discard(message.id)
        return

    guild_id = str(message.guild.id)
    channel_id = str(message.channel.id)

    if guild_id not in sniped_messages:
        sniped_messages[guild_id] = {}

    if channel_id not in sniped_messages[guild_id]:
        sniped_messages[guild_id][channel_id] = []

    sniped_messages[guild_id][channel_id].insert(0, {
        "content": message.content,
        "author": str(message.author),
        "time": time.time()
    })

    # Ne garde que les 10 derniers
    sniped_messages[guild_id][channel_id] = sniped_messages[guild_id][channel_id][:10]

    save_messages(sniped_messages)
    logger.info(f"Message supprimé dans {message.channel.name} par {message.author}: {message.content}")



# Lorsque le bot reçoit un message
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignore les messages envoyés par le bot lui-même
    await bot.process_commands(message)
    
@bot.event
async def on_guild_join(guild):
    logger.info(f"Rejoint un nouveau serveur : {guild.name} ({guild.id})")

@bot.event
async def on_guild_remove(guild):
    logger.info(f"Retiré du serveur : {guild.name} ({guild.id})")

# --------------------------------------------------------  COMMANDES  --------------------------------------------------------

#Hello world
@bot.command(name="bonjour_monde", aliases=['hw', 'hello'])
async def hello_world(context):
    logger.info(f"Commande !hello_world exécutée par {context.author}")  # Log de la commande
    await context.send("Hello World!")

# ---------------------------------

#Faire un décompte secondes par secondes
@bot.command()
async def decompte(context, delai: int):
    await delete_command_message(context.message)
    if delai < 1:
        await context.send("Le délai doit être supérieur à 0.")
        return
    logger.info(f"Commande !decompte exécutée par {context.author}")  # Log de la commande
    await context.send("Départ dans...")
    for i in range(delai, 0, -1):
        await context.send(i)
        await asyncio.sleep(1)  # Pause de 1 seconde entre chaque message
    await context.send("GO! 🚀")

# ---------------------------------

#Répéter un message
@bot.command()
async def repeter(context, *, message):
    await delete_command_message(context.message)
  # Supprime le message de commande
    logger.info(f"Commande !repeter exécutée par {context.author}")  # Log de la commande
    await context.send(message)

# ---------------------------------

#Redemarrer le bot
@bot.command()
@commands.is_owner()
async def restart(ctx):
    logger.info(f"Le bot est redémarré par {ctx.author}")
    await ctx.send("♻️ Redémarrage du bot...")
    await asyncio.sleep(1)  # Pause de 2 secondes avant le redémarrage

    # Nettoyage complet du logging pour éviter les handlers persistants
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        handler.close()

    await bot.close()
    os.execl(sys.executable, sys.executable, *sys.argv)

# ---------------------------------

#Commande de spam avec le message au choix
@bot.command()
async def spam(ctx, member: discord.Member, count: int = 5, *, message: str = None):
    logger.info(f"Commande !spam exécutée par {ctx.author} sur {member} avec {count} messages")
    
    # Autorisation : owner ou whitelist
    if ctx.author.id not in WHITELIST_IDS:
        await ctx.send("🚫 Tu n'as pas la permission d'utiliser cette commande.")
        return

    await delete_command_message(ctx.message)  # Supprime le message de commande

    if member.id == OWNER_ID:
        await ctx.send("Tu ne peux pas spammer le boss du bot 😎 !")
        return

    if count > 20:
        await ctx.send("Calme-toi 😅 ! Max 20 messages pour éviter les abus.")
        return

    if not message:
        message = f"Hey {member.mention} 👀, c'est le spam n°{{}} !"

    try:
        for i in range(count):
            # Si message contient {} (comme une template), on remplit le numéro
            try:
                final_msg = message.format(i + 1)
            except IndexError:
                final_msg = message
            else:
                final_msg = message
            await member.send(final_msg)
            await asyncio.sleep(0.25)  # Petite pause
        await ctx.send(f"Je viens de DM {count} fois {member.name} 😎")
    except discord.Forbidden:
        await ctx.send("Je ne peux pas lui envoyer de DM. Peut-être qu'il les a fermés ?")

# ---------------------------------

#Commande pour le ping
@bot.command()
async def ping(ctx):
    logger.info(f"Commande !ping exécutée par {ctx.author}")  # Log de la commande
    await ctx.send(f"🏓 Pong! Latence: {round(bot.latency * 1000)}ms")

# ---------------------------------

#Commande help avec embed
@bot.command()
async def help(ctx):
    logger.info(f"Commande !help exécutée par {ctx.author}")  # Log de la commande
    embed = discord.Embed(title="Aide", description="Voici la liste des commandes disponibles:", color=discord.Color.from_rgb(0, 204, 204))
    embed.add_field(name="!hw", value="Affiche 'Hello World!'", inline=False)
    embed.add_field(name="!decompte <delai>", value="Fait un décompte de <delai> secondes.", inline=False)
    embed.add_field(name="!repeter <message>", value="Répète le message donné.", inline=False)
    embed.add_field(name="!ping", value="Vérifie la latence du bot.", inline=False)
    embed.add_field(name="!help", value="Affiche cette aide.", inline=False)
    embed.add_field(name="!snipe", value="Affiche le dernier message supprimé.", inline=False)
    embed.add_field(name="!clear <nombre>", value="Supprime <nombre> de messages.", inline=False)
    embed.add_field(name="!kick <membre> [raison]", value="Expulse un membre avec une raison.", inline=False)
    embed.add_field(name="!ban <membre> [raison]", value="Bannit un membre avec une raison.", inline=False)
    embed.add_field(name="!info", value="Affiche les informations sur le bot.", inline=False)
    embed.add_field(name="!version", value="Affiche la version du bot.", inline=False)
    embed.add_field(name="!ahelp", value="les commandes admin", inline=False)
    embed.set_footer(text=f"Bot développé par IZAROX | V{BOT_VERSION}")
    embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)
    await ctx.send(embed=embed)

# ---------------------------------

@bot.command()
async def ahelp(ctx):
    logger.info(f"Commande !ahelp exécutée par {ctx.author}")
    if ctx.author.id not in WHITELIST_IDS:
        await ctx.send("🚫 Tu n'as pas la permission d'utiliser cette commande.")
        return
    await delete_command_message(ctx.message)  # Supprime le message de commande
    embed = discord.Embed(title="Aide Admin", description="Voici la liste des commandes administratives disponibles:", color=discord.Color.brand_red())
    embed.add_field(name="!spam <membre> <nombre> [message]", value="Envoie un message à un membre plusieurs fois.", inline=False)
    embed.add_field(name="D'autres commandes sont a venir.", value="Si vous avez des suggestions venz DM izar0x", inline=False)
    embed.set_footer(text=f"Bot développé par IZAROX | V{BOT_VERSION}")
    embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)
    await ctx.send(embed=embed)

# ---------------------------------

#Commande pour arreter le bot
@bot.command()
@commands.is_owner()
async def stop(ctx):
    await delete_command_message(ctx.message)  # Supprime le message de commande
    logger.info(f"Le bot est arrêté par {ctx.author}")  # Log de l'arrêt
    await ctx.send("💤 Arrêt du bot...")
    await bot.close()

# ---------------------------------

#commande clear
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    logger.info(f"Commande !clear exécutée par {ctx.author} pour supprimer {amount} messages")
    # Supprimer les messages, y compris la commande elle-même
    deleted = await ctx.channel.purge(limit=amount + 1)

    # Ajouter les IDs des messages supprimés à la liste temporaire
    for msg in deleted:
        bot_deleted_messages.add(msg.id)

    await ctx.send(f"🗑️ {len(deleted) - 1} messages supprimés.", delete_after=5)


# ---------------------------------

# Commande de snipe
@bot.command()
@commands.has_permissions(manage_messages=True)
async def snipe(ctx):
    await delete_command_message(ctx.message)
    logger.info(f"Commande !snipe exécutée par {ctx.author}")

    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)

    data = sniped_messages.get(guild_id, {}).get(channel_id)

    if not data:
        await ctx.send("Aucun message supprimé trouvé.")
        return

    # Nettoyage des messages expirés
    current_time = time.time()
    sniped_messages[guild_id][channel_id] = [
        msg for msg in data if current_time - msg["time"] <= 432000
    ]

    save_messages(sniped_messages)

    if not sniped_messages[guild_id][channel_id]:
        await ctx.send("Tous les messages supprimés ont expiré.")
        return

    last_message = sniped_messages[guild_id][channel_id][0]
    embed = discord.Embed(
        title="❌ __**Dernier message supprimé:**__",
        description=last_message["content"],
        color=discord.Color.orange()
    )
    embed.add_field(name="**Auteur**:", value=last_message["author"], inline=False)
    await ctx.send(embed=embed)

# ---------------------------------

#Commande pour kick un membre avec une raison
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Aucune raison fournie."):
    logger.info(f"Commande !kick exécutée par {ctx.author} sur {member} avec raison: {reason}")
    try:
        await member.kick(reason=reason)
        kick_embed = discord.Embed(
            title="🔨 **Expulsion**",
            description=f"{member.name} a été expulsé.",
            color=discord.Color.red()
        )
        kick_embed.add_field(name="**Raison :**", value=reason, inline=False)
        print("Embed créé avec succès.")
        await ctx.send(embed=kick_embed)
        print("Embed envoyé avec succès.")
    except discord.Forbidden:
        await ctx.send("Je n'ai pas la permission d'expulser ce membre.")
    except discord.HTTPException as e:
        await ctx.send(f"Une erreur est survenue lors de l'envoi de l'embed : {e}")

# ---------------------------------

#Commande pour ban un membre avec une raison
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="Aucune raison fournie."):
    logger.info(f"Commande !ban exécutée par {ctx.author} sur {member} avec raison: {reason}")
    try:
        await member.ban(reason=reason)
        ban_embed = discord.Embed(
            title="🔨 **Bannissement**",
            description=f"{member.name} a été bannit.",
            color=discord.Color.red()
        )
        ban_embed.add_field(name="**Raison :**", value=reason, inline=False)
        print("Embed créé avec succès.")
        await ctx.send(embed=ban_embed)
        print("Embed envoyé avec succès.")
    except discord.Forbidden:
        await ctx.send("Je n'ai pas la permission de bannir ce membre.")
    except discord.HTTPException as e:
        await ctx.send(f"Une erreur est survenue lors de l'envoi de l'embed : {e}")

# ---------------------------------

#Commande pour afficher les infos de l'owner en embed
@bot.command()
async def info(ctx):
    logger.info(f"Commande !info exécutée par {ctx.author}")
    embed = discord.Embed(
        title="👤 **Informations sur le Bot**",
        description="Voici les informations sur le bot.",
        color=discord.Color.pink()
    )
    embed.add_field(name="**Nom :**", value=bot.user.name, inline=False)
    embed.add_field(name="**ID :**", value=bot.user.id, inline=False)
    embed.add_field(name="**Créateur :**", value="<@1265356662907076681>", inline=False)
    embed.add_field(name="**Version :**", value=f"{BOT_VERSION}", inline=False)
    embed.add_field(name="**Serveurs :**", value=len(bot.guilds), inline=False)
    embed.set_thumbnail(url=bot.user.avatar.url)
    embed.set_footer(text="Bot développé par IZAROX")
    await ctx.send(embed=embed)

# ---------------------------------

@bot.command()
async def version(ctx):
    logger.info(f"Commande !version exécutée par {ctx.author}")
    embed = discord.Embed(
        title="🔧 **Version du Bot**",
        description=f"📌 Version actuelle : {BOT_VERSION}",
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot développé par IZAROX")
    await ctx.send(embed=embed)

# --------------------------------------------------------  FIN  --------------------------------------------------------

keep_alive()
bot.run(token)
