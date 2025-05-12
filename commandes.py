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
import json

# --------------------------------------------------------  BASE  --------------------------------------------------------

load_dotenv()
token = os.getenv("DISCORD_TOKEN")


intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
bot.help_command = None

OWNER_ID = 1265356662907076681
WHITELIST_IDS = [OWNER_ID, 1122259572267155577]  # Ajoute ici les IDs autorisés

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

# --------------------------------------------------------  EVENT  --------------------------------------------------------

@bot.event
async def on_ready():
    print(f"{Fore.GREEN}(ID: {Fore.YELLOW}{bot.user.name}{Fore.GREEN}) est connecté !")
    #Activité du bot
    activity = discord.Game(name="!help")
    await bot.change_presence(activity=activity)

#Commande inconnue
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Commande inconnue.")

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


# --------------------------------------------------------  COMMANDES  --------------------------------------------------------

#Hello world
@bot.command(name="bonjour_monde", aliases=['hw', 'hello'])
async def hello_world(context):
    await context.send("Hello World!")

# ---------------------------------

#Faire un décompte
@bot.command()
async def decompte(context, delai: int):
    await context.send("Départ dans...")
    for i in range(delai, 0, -1):
        await context.send(i)
    await context.send("C'est parti!")

# ---------------------------------

#Répéter un message
@bot.command()
async def repeter(context, *, message):
    await context.send(message)

# ---------------------------------

#Redemarrer le bot
@bot.command()
@commands.is_owner()
async def restart(ctx):
    await ctx.send("♻️ Redémarrage du bot...")
    await bot.close()
    os.execl(sys.executable, sys.executable, *sys.argv)

# ---------------------------------

@bot.command()
async def spam(ctx, member: discord.Member, count: int = 5):
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
    await ctx.send("💤 Arrêt du bot...")
    await bot.close()

# ---------------------------------

#commande clear
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ {len(deleted) - 1} messages supprimés.", delete_after=5)

# ---------------------------------

@bot.command()
@commands.has_permissions(manage_messages=True)
async def snipe(ctx):
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
