import os
from dotenv import load_dotenv
import sys
import colorama
from colorama import Fore, Style, init
import discord
from discord.ext import commands
from keep_alive import keep_alive

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents); help_command=(None)


@bot.event
async def on_ready():
    print(f"{Fore.GREEN}(ID: {Fore.YELLOW}{bot.user.name}{Fore.GREEN}) est connecté !")

#Hello world
@bot.command(name="bonjour_monde", aliases=['hw', 'hello'])
async def hello_world(context):
    await context.send("Hello World!")

#Faire un décompte
@bot.command()
async def decompte(context, delai: int):
    await context.send("Départ dans...")
    for i in range(delai, 0, -1):
        await context.send(i)
    await context.send("C'est parti!")

#Répéter un message
@bot.command()
async def repeter(context, *, message):
    await context.send(message)

#Redemarrer le bot
@bot.command()
@commands.is_owner()
async def restart(ctx):
    await ctx.send("♻️ Redémarrage du bot...")
    await bot.close()
    os.execl(sys.executable, sys.executable, *sys.argv)

#Commande pour le ping
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latence: {round(bot.latency * 1000)}ms")

#Commande inconnue
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Commande inconnue.")

#Commande help avec embed
@bot.command()
async def liste(ctx):
    embed = discord.Embed(title="Aide", description="Voici la liste des commandes disponibles:", color=discord.Color.blue())
    embed.add_field(name="!bonjour_monde", value="Affiche 'Hello World!'", inline=False)
    embed.add_field(name="!decompte <delai>", value="Fait un décompte de <delai> secondes.", inline=False)
    embed.add_field(name="!repeter <message>", value="Répète le message donné.", inline=False)
    embed.add_field(name="!ping", value="Vérifie la latence du bot.", inline=False)
    embed.add_field(name="!help", value="Affiche cette aide.", inline=False)
    embed.add_field(name="!snipe", value="Affiche le dernier message supprimé.", inline=False)
    embed.add_field(name="!clear <nombre>", value="Supprime <nombre> de messages.", inline=False)
    await ctx.send(embed=embed)

#Commande pour arreter le bot
@bot.command()
@commands.is_owner()
async def stop(ctx):
    await ctx.send("💤 Arrêt du bot...")
    await bot.close()

#commande clear
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ {len(deleted) - 1} messages supprimés.", delete_after=5)

#Commande pour afficher le dernier message supprimé et par qui sous forme d'embed

snipe_message_content = {}
snipe_message_author = {}

@bot.event
async def on_message_delete(message):
    snipe_message_content[message.channel.id] = message.content
    snipe_message_author[message.channel.id] = message.author.name

@bot.command()
@commands.has_permissions(manage_messages=True)
async def snipe(ctx):
    channel_id = ctx.channel.id
    if channel_id in snipe_message_content:
        content = snipe_message_content[channel_id]
        author = snipe_message_author[channel_id]
        embed = discord.Embed(
            title="❌ __**Dernier message supprimé:**__",
            description=content,
            color=discord.Color.red()
        )
        embed.add_field(name="**Auteur**:", value=author, inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Aucun message supprimé trouvé.")

#Commande pour kick un membre avec une raison
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    if reason is None:
        reason = "Aucune raison fournie."
    kick_embed = discord.Embed(
        title="🔨 **Kick**",
        description=f"{member.name} a été kické.",
        feilds=[
            discord.EmbedField(name="**Raison:**", value=reason, inline=False),
            ],
        color=discord.Color.red() 
    )

#Commande pour ban un membre avec une raison
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    if reason is None:
        reason = "Aucune raison fournie."
    ban_embed = discord.Embed(
        title="🔨 **Ban**",
        description=f"{member.name} a été banni.",
        fields=[
            discord.EmbedField(name="**Raison:**", value=reason, inline=False),
            ],
        color=discord.Color.red() 
    )
    await ctx.send(embed=ban_embed)

keep_alive()
bot.run(token)
