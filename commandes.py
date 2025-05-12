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

# --------------------------------------------------------  BASE  --------------------------------------------------------

load_dotenv()
token = os.getenv("DISCORD_TOKEN")


intents = discord.Intents.all()
init(autoreset=True)

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
bot.help_command = None

OWNER_ID = 1265356662907076681
WHITELIST_IDS = [OWNER_ID, 1122259572267155577]  # Ajoute ici les IDs autorisés

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
        json.dump(data, file)

# Dictionnaire des messages supprimés : {channel_id: [{"content": ..., "author": ..., "time": ...}]}
sniped_messages = load_messages()

# -----------------------------------------------------  CONFIG DES LOGS  ------------------------------------------------------

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

# Handler pour la console (coloré)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Niveau de log pour la console
console_formatter = ColorFormatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)

# Handler pour le fichier (sans couleurs)
file_handler = logging.FileHandler("bot_logs.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)  # Modifié pour enregistrer tous les logs à partir de DEBUG
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)

# Configuration du logger global
logging.basicConfig(level=logging.DEBUG, handlers=[console_handler, file_handler])

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
    activity = discord.Game(name="!help")
    await bot.change_presence(activity=activity)

# Exemple d'erreur de commande
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        logging.warning(f"Commande inconnue utilisée par {ctx.author}: {ctx.message.content}")  # Log d'avertissement
        await ctx.send("❌ Commande inconnue.")
    else:
        logging.error(f"Erreur dans la commande de {ctx.author}: {error}")  # Log d'erreur
        await ctx.send(f"Une erreur s'est produite: {error}")
@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.content:
        return

    # Enregistrer le message supprimé avec son timestamp
    channel_id = str(message.channel.id)
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []

    sniped_messages[channel_id].append({
        "content": message.content,
        "author": message.author.name,
        "time": time.time()
    })

    save_messages(sniped_messages)  # Sauvegarder les messages après chaque suppression

# Lorsque le bot reçoit un message
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignore les messages envoyés par le bot lui-même
    await bot.process_commands(message)

# --------------------------------------------------------  COMMANDES  --------------------------------------------------------

#Hello world
@bot.command(name="bonjour_monde", aliases=['hw', 'hello'])
async def hello_world(context):
    logging.info(f"Commande !hello_world exécutée par {context.author}")  # Log de la commande
    await context.send("Hello World!")

# ---------------------------------

#Faire un décompte
@bot.command()
async def decompte(context, delai: int):
    logging.info(f"Commande !decompte exécutée par {context.author}")  # Log de la commande
    await context.send("Départ dans...")
    for i in range(delai, 0, -1):
        await context.send(i)
    await context.send("C'est parti!")

# ---------------------------------

#Répéter un message
@bot.command()
async def repeter(context, *, message):
    logging.info(f"Commande !repeter exécutée par {context.author}")  # Log de la commande
    await context.send(message)

# ---------------------------------

#Redemarrer le bot
@bot.command()
@commands.is_owner()
async def restart(ctx):
    logging.info(f"Le bot est redémarré par {ctx.author}")
    await ctx.send("♻️ Redémarrage du bot...")

    # Nettoyage complet du logging pour éviter les handlers persistants
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        handler.close()

    await bot.close()
    os.execl(sys.executable, sys.executable, *sys.argv)

# ---------------------------------

#Commande de spam
@bot.command()
async def spam(ctx, member: discord.Member, count: int = 5):
    logging.info(f"Commande !spam exécutée par {ctx.author} sur {member} avec {count} messages")
        # Autorisation : owner ou whitelist
    if ctx.author.id not in WHITELIST_IDS:
        await ctx.send("🚫 Tu n'as pas la permission d'utiliser cette commande.")
        return
    
    await ctx.message.delete()  # Supprime le message de commande
    # Ne pas spammer l'owner du bot
    if member.id == OWNER_ID:
        await ctx.send("Tu ne peux pas spammer le boss du bot 😎 !")
        return
    
    if count > 20:
        await ctx.send("Calme-toi 😅 ! Max 20 messages pour éviter les abus.")
        return
    
    try:
        for i in range(count):
            await member.send(f"Hey {member.mention} 👀, c'est le spam n°{i + 1} !")
            await asyncio.sleep(0.25)  # Pause de 0.25 secondes entre chaque DM pour éviter les abus
        await ctx.send(f"Je viens de DM {count} fois {member.name} 😎")
    except discord.Forbidden:
        await ctx.send("Je ne peux pas lui envoyer de DM. Peut-être qu'il les a fermés ?")

# ---------------------------------

#Commande pour le ping
@bot.command()
async def ping(ctx):
    logging.info(f"Commande !ping exécutée par {ctx.author}")  # Log de la commande
    await ctx.send(f"🏓 Pong! Latence: {round(bot.latency * 1000)}ms")

# ---------------------------------

#Commande help avec embed
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Aide", description="Voici la liste des commandes disponibles:", color=discord.Color.blue())
    embed.add_field(name="!bonjour_monde", value="Affiche 'Hello World!'", inline=False)
    embed.add_field(name="!decompte <delai>", value="Fait un décompte de <delai> secondes.", inline=False)
    embed.add_field(name="!repeter <message>", value="Répète le message donné.", inline=False)
    embed.add_field(name="!ping", value="Vérifie la latence du bot.", inline=False)
    embed.add_field(name="!help", value="Affiche cette aide.", inline=False)
    embed.add_field(name="!snipe", value="Affiche le dernier message supprimé.", inline=False)
    embed.add_field(name="!clear <nombre>", value="Supprime <nombre> de messages.", inline=False)
    await ctx.send(embed=embed)

# ---------------------------------

#Commande pour arreter le bot
@bot.command()
@commands.is_owner()
async def stop(ctx):
    logging.info(f"Le bot est arrêté par {ctx.author}")  # Log de l'arrêt
    await ctx.send("💤 Arrêt du bot...")
    await bot.close()

# ---------------------------------

#commande clear
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    logging.info(f"Commande !clear exécutée par {ctx.author} pour supprimer {amount} messages")  # Log de la commande
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ {len(deleted) - 1} messages supprimés.", delete_after=5)

# ---------------------------------

# Commande de snipe
@bot.command()
@commands.has_permissions(manage_messages=True)
async def snipe(ctx):
    logging.info(f"Commande !snipe exécutée par {ctx.author}")
    channel_id = str(ctx.channel.id)
    data = sniped_messages.get(channel_id)

    if not data:
        await ctx.send("Aucun message supprimé trouvé.")
        return

    # Nettoyage des messages expirés (plus de 5 jours)
    current_time = time.time()
    sniped_messages[channel_id] = [
        msg for msg in data if current_time - msg["time"] <= 432000  # 5 jours en secondes
    ]

    # Sauvegarder les messages après nettoyage
    save_messages(sniped_messages)

    if not sniped_messages[channel_id]:
        await ctx.send("Tous les messages supprimés ont expiré.")
        return

    # Affichage du dernier message supprimé
    last_message = sniped_messages[channel_id][-1]
    embed = discord.Embed(
        title="❌ __**Dernier message supprimé:**__",
        description=last_message["content"],
        color=discord.Color.red()
    )
    embed.add_field(name="**Auteur**:", value=last_message["author"], inline=False)
    await ctx.send(embed=embed)

# ---------------------------------

#Commande pour kick un membre avec une raison
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Aucune raison fournie."):
    logging.info(f"Commande !kick exécutée par {ctx.author} sur {member} avec raison: {reason}")
    try:
        await member.kick(reason=reason)
        print("Membre expulsé avec succès.")
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
    logging.info(f"Commande !ban exécutée par {ctx.author} sur {member} avec raison: {reason}")
    try:
        await member.ban(reason=reason)
        print("Membre expulsé avec succès.")
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

# --------------------------------------------------------  FIN  --------------------------------------------------------

keep_alive()
bot.run(token)
