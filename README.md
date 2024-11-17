# poe-bot-server-wsgi
This project aims to create a full-featured Poe server bot using a WSGI Python web application (purely synchronous implementation).

This bot is available on Poe as [Server-Bot-WSGI](https://poe.com/Server-Bot-WSGI) (by @robhewitt).

To set up your own server bot (or "bot server" as they're called in Poe's API documentation) you will need two things:

1. A means of creating a Python web application (e.g., shared hosting account with cPanel)
2. An account on Poe that allows you to create server bots (`poe.com/create_bot`)

### Part 1 - Setting up a Python web application:
1. Log into cPanel and navigate to "Setup Python App"
1. Click "Create Application"
1. Select the latest version of Python
1. Enter "poe-bot-server" in "Application root" field
1. Enter "poe-bot-server" in "Application URL" field
1. Leave the "Application startup file" and "Application Entry point" fields BLANK
1. Click "Create" button
1. Enter `https://yourdomain.com/poe-bot-server/` into your browser address bar to see if the default web app setup is running okay
1. Navigate to "File Manager" in cPanel
1. Open the `/poe-bot-server` folder
1. Replace the files you see there with the project files of this repo
1. Go back the "Setup Python App" page and bring up the details of your newly created web app (you may need to click the "Edit" button)
1. Near the top of the page you will see "To enter to virtual environment, run the command: {command}" - copy that command to the clipboard
1. SSH into your shared hosting account (by using PuTTY for example)
1. Paste that command into the terminal
1. Enter the command `pip install -r requirements.txt` to install the packages needed for the project
1. Stop and restart your Python web app to refresh it
1. Enter `https://yourdomain.com/poe-bot-server/` into your browser address bar to see if the updated web app is running okay
1. Note: You will need to edit the `.env` file but you need to complete Part #2 (below) first

### Part 2 - Creating a server bot (profile) on Poe:
1. Log in to your Poe account
1. Click the "Create bot" button or navigate to [poe.com/create_bot](https://poe.com/create_bot)
1. Select "Server bot"
1. Enter a unique name for your bot
1. Enter `https://yourdomain.com/poe-bot-server/` in the "Server URL" field
1. Copy the access key to your clipboard
1. Now that you have the server bot name and access key you will need to edit the `.env` file of your web app
1. Click on the "Check reachability" button to test basic connectivity with your web app. If there's a problem then try restarting your web app
1. Click the "Create bot" button near bottom of page
1. Start a chat with the new server bot you created
