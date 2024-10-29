"""
Cog for granting and removing the wine carrier role

"""

# libraries
import asyncio

# discord.py
import discord
from discord.app_commands import Group, describe, Choice
from discord.ext import commands, tasks
from discord import app_commands, NotFound

# local constants
from ptn.boozebot.constants import bot, server_admin_role_id, server_sommelier_role_id, \
    server_connoisseur_role_id, server_wine_carrier_role_id, server_mod_role_id, \
    get_primary_booze_discussions_channel, get_wine_carrier_channel, get_steve_says_channel, \
    WELCOME_MESSAGE_FILE_PATH

# local modules
from ptn.boozebot.modules.ErrorHandler import on_app_command_error, GenericError, CustomError, on_generic_error
from ptn.boozebot.modules.helpers import bot_exit, check_roles, check_command_channel

"""
Make Wine Carrier app commands - cannot be placed in the Cog

Uses bot.tree instead of app_commands

Make Wine Carrier
"""

@bot.tree.context_menu(name='Make Wine Carrier')
@check_roles([server_admin_role_id(), server_mod_role_id(), server_sommelier_role_id(), server_connoisseur_role_id()])
@check_command_channel(get_primary_booze_discussions_channel())
async def make_contextuser_wine_carrier(interaction:  discord.Interaction, user: discord.User):
    await make_user_wine_carrier(interaction, user)

"""
MAKE WINE CARRIER COMMANDS

/make_wine_carrier - conn/somm/mod/admin
/remove_wine_carrier - somm/mod/admin
"""

# lock for wine carrier toggle
wine_carrier_toggle_lock = asyncio.Lock()

# initialise the Cog and attach our global error handler
class MakeWineCarrier(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # custom global error handler
    # attaching the handler when the cog is loaded
    # and storing the old handler
    def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = on_app_command_error

    # detaching the handler when the cog is unloaded
    def cog_unload(self):
        tree = self.bot.tree
        tree.on_error = self._old_tree_error
    
        
    @app_commands.command(name="make_wine_carrier", description="Give user the Wine Carrier role. Admin/Sommelier/Connoisseur role required.")
    @describe(user="An @ mention of the Discord user to receive the role.")
    @check_roles([server_admin_role_id(), server_mod_role_id(), server_sommelier_role_id(), server_connoisseur_role_id()])
    async def make_wine_carrier(self, interaction: discord.Interaction, user: discord.Member):
        print(f"make_wine_carrier called by {interaction.user.name} in {interaction.channel.name} for {user} to set the Wine Carrier role")
        
        await make_user_wine_carrier(interaction, user)
    
        
    @app_commands.command(name="remove_wine_carrier", description="Removes the Wine Carrier role from a user. Admin/Sommelier/Connoisseur role required.")
    @describe(user="An @ mention of the Discord user to receive the role.")
    @check_roles([server_admin_role_id(), server_mod_role_id(), server_sommelier_role_id()])
    @check_command_channel(get_steve_says_channel())
    async def remove_wine_carrier(self, interaction: discord.Interaction, user: discord.Member):
        print(f"make_wine_carrier called by {interaction.user.name} in {interaction.channel.name} for {user} to remove the Wine Carrier role")

        await wine_carrier_toggle_lock.acquire()

        # set the target role
        wc_role = discord.utils.get(interaction.guild.roles, id=server_wine_carrier_role_id())
        print(f"Wine Carrier role name is {wc_role.name}")


        if wc_role in user.roles:
            # remove role
            print(f"{user} is a {wc_role.name}, removing the role.")
            try:
                await user.remove_roles(wc_role)
                response = f"{user.display_name} no longer has the {wc_role.name} role."
                wine_carrier_toggle_lock.release()
                return await interaction.response.send_message(content=response)
            except Exception as e:
                print(e)
                await interaction.response.send_message(f"Failed removing role {wc_role.name} from {user}: {e}", ephemeral=True)
                wine_carrier_toggle_lock.release()
                return
        else:
            print("User is not a wine carrier, doing nothing.")
            wine_carrier_toggle_lock.release()
            return await interaction.response.send_message(f"User is not a {wc_role.name}", ephemeral=True)

# function shared by make_wine_carrier and make_contextuser_wine_carrier
async def make_user_wine_carrier(interaction, user):

    await wine_carrier_toggle_lock.acquire()
    channel = bot.get_channel(get_steve_says_channel())
    # set the target role
    wc_role = discord.utils.get(interaction.guild.roles, id=server_wine_carrier_role_id())
    print(f"Wine Carrier role name is {wc_role.name}")

    if wc_role in user.roles:
        print(f"{user} is already a {wc_role.name}, doing nothing.")
        wine_carrier_toggle_lock.release()
        return await interaction.response.send_message(f"User is already a {wc_role.name}", ephemeral=True)
    else:
        # toggle on
        print(f"{user} is not a {wc_role.name}, adding the role.")
        try:
            await user.add_roles(wc_role)
            print(f"Added Wine Carrier role to {user}")
            response = f"{user.display_name} now has the {wc_role.name} role."

            # Open the file in read mode.
            with open(WELCOME_MESSAGE_FILE_PATH, "r") as file:
                wine_welcome_message = file.read() # read contents to variable
            
            wine_channel = bot.get_channel(get_wine_carrier_channel())
            embed = discord.Embed(description=wine_welcome_message)
            embed.set_thumbnail(url="https://cdn.discordapp.com/role-icons/839149899596955708/2d8298304adbadac79679171ab7f0ae6.webp?quality=lossless")
            await wine_channel.send(f"<@{user.id}>", embed=embed)

            wine_carrier_toggle_lock.release()
                
            await channel.send(content=response)
            return await interaction.response.send_message(content=response, ephemeral=True)
        except Exception as e:
            print(e)
            await interaction.response.send_message(f"Failed adding role {wc_role.name} to {user}: {e}", ephemeral=True)
            wine_carrier_toggle_lock.release()
            return