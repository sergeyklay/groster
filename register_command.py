import os

import requests
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("DISCORD_APP_ID")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

url = f"https://discord.com/api/v10/applications/{APP_ID}/guilds/{GUILD_ID}/commands"
json = {
    "name": "whois",
    "description": "Get information about a player.",
    "options": [
        {
            "name": "player",
            "description": "The player to get information about.",
            "type": 3,
            "required": True,
        }
    ],
    "type": 1,
}

headers = {"Authorization": f"Bot {BOT_TOKEN}"}

try:
    print("Registering /ping command...")
    r = requests.post(url, headers=headers, json=json)
    r.raise_for_status()
    print(f"Command registered successfully (Status: {r.status_code})")
    print(r.json())
except requests.HTTPError as e:
    print("Error registering command:")
    print(e.response.text if e.response else str(e))
