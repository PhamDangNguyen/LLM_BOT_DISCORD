# BOT LLM ASR DISCORD
This is a bot set up to calculate food expenses and answer user questions (e.g., “Do you know Vietnam?”, “What is the best food in Hanoi?”, etc.).

## Config BOT for application
**B1**: Create a bot on the Discord Developer Portal

    Visit: https://discord.com/developers/applications

    Click "New Application" and give your bot a name (ex: "Bot").

    In the left-hand menu "Selected App" , select "Bot"

    Under the Bot section:

    Copy the Token (important – it’s required to connect the bot via code).

    Enable MESSAGE CONTENT INTENT (if your bot needs to read message content).

    Enable other intents if needed, such as "Presence Intent" or "Server Members Intent".

**B2**: Grant Permissions and Invite the Bot to Your Server
    Go to OAuth2 > URL Generator.

    Under Scopes, select: "bot"

    (Optionally, also select applications.commands if your bot uses slash commands).

    Under Bot Permissions, choose the appropriate permissions.
    Suggested permissions:

    - Send Messages

    - Read Message History

    - Manage Messages

    - Use Slash Commands

    - Connect

    - Speak

    (and others depending on your bot's functionality)

    Copy the generated URL and open it in your browser to invite the bot to your server.

## Set up evirerment
1. Create Conda environments run ```conda create --name BOT python=3.10``` and activate ```conda activate BOT```
2.  Install dependencies run ```pip install -r requirements.txt```

## Get .env file
You can reach it by visiting [link](https://drive.google.com/drive/u/0/folders/1sRNPoqGzKpnr0LE-KBWFziyHQgW5aM7L)

# Run bot 
Run ```python test_bot.py```