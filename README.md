# poe-bot-server-wsgi
This project aims to create a full-featured Poe server bot using a WSGI Python web application (purely synchronous implementation).

This bot is available on Poe by the name of "Server-Bot-WSGI" (by @robhewitt).

To set up your own server bot (or "bot server" as they are called in Poe's API documentation) you will need two things:

1. A means of hosting a Python web application (e.g., shared hosting account with cPanel)
2. An account on Poe that allows you to create server bots (poe.com/create_bot).

Part 1 - Setting up a Python web application:
   - Log into cPanel and navigate to "Setup Python App"
   - Click "Create Application"
   - Select the latest version of Python
   - Enter "poe-bot-server" in "Application root" field
   - Enter "poe-bot-server" in "Application URL" field
   - Leave the "Application startup file" and "Application Entry point" fields BLANK
   - Click "Create" button
   - Enter `https://yourdomain.com/poe-bot-server/` into your browser address bar to see if the default web app setup is running okay
   - Navigate to "File Manager" in cPanel
   - Open the "/poe-bot-server" folder
   - Replace the files you see there with the project files of this repo
   - Go back the "Setup Python App" page and bring up the details of your newly created web app (you may need to click the "edit" button)
   - Near the top of the page you will see "To enter to virtual environment, run the command:" - copy that command to the clipboard
   - SSH into your shared hosting account (by using PuTTY for example)
   - Paste that command into the terminal
   - Enter the command `pip install -r requirements.txt` to install the packages needed for the project
   - Stop and restart your Python web app to refresh it
   - Enter `https://yourdomain.com/poe-bot-server/` into your browser address bar to see if the updated web app is running okay
   - Note: You will need to edit the `.env` file but you need to do Step #2 (below) first


Part 2 - Creating a server bot on Poe:
- Log in to your Poe account
- Click the "Create bot" button or navigate to `poe.com/create_bot`
- Select "Server bot"
- Enter a unique name for your bot
- Enter `https://yourdomain.com/poe-bot-server/` in the "Server URL" field
- Copy the access key to your clipboard
- Now that you have the server bot name and access key you will need to edit the `.env` file of your web app
- Click on the bot access button to test accessibility. If there's a problem then try restarting your web app
- Click the "Save" button
- Start a chat with the new server bot you created
