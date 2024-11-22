# poe-bot-server-wsgi

This project aims to build a fully functional server bot for the [Poe platform](https://poe.com/) using a WSGI Python web application. The bot is implemented in a purely synchronous manner, making it easy to set up on shared hosting environments (such as those with cPanel).

A functioning instance of this bot is available on Poe as [Server-Bot-WSGI](https://poe.com/Server-Bot-WSGI) (by @robhewitt).

The ultimate goal of this project is to allow the bot to forward user messages to other bots on Poe and relay their responses back to the user. Currently, the bot echoes user messages in uppercase but will be extended with more functionality as the expected JSON payloads for bot-to-bot communication become clearer.

## Features

- **Synchronous (no async)**: The bot is implemented using synchronous Python, making it compatible with standard WSGI-based web hosting environments.
- **Flask-based**: Built using the Flask microframework to handle HTTP requests and responses.
- **Logging**: Logs requests and responses for easier debugging and monitoring.
- **Echo Bot**: Responds to user input by echoing it back in uppercase (for now).

## Setup Instructions

### Part 1: Setting up a Python Web Application

To host this project, you'll need a Python web application setup, which is often available on shared hosting platforms like cPanel.

1. Log into your hosting provider's control panel (e.g., cPanel) and navigate to "Setup Python App".
2. Click "Create Application".
3. Select the latest version of Python (3.x).
4. Set the **Application root** to `poe-bot-server`.
5. Set the **Application URL** to `poe-bot-server`.
6. Leave the **Application startup file** and **Application Entry point** fields blank for now.
7. Click "Create" to initialize the app.
8. Open your browser and visit `https://yourdomain.com/poe-bot-server/` to confirm that the default web app setup is running.
9. Use the File Manager in cPanel to navigate to the `/poe-bot-server` directory.
10. Replace the existing files in this directory with the project files from this repository.
11. Return to "Setup Python App" and click "Edit" to view your app's details.
12. Copy the command provided to enter the virtual environment and run it via SSH (e.g., using PuTTY).
13. Within the SSH session, run `pip install -r requirements.txt` to install the necessary dependencies.
14. Restart your Python web app to apply the changes.
15. Revisit `https://yourdomain.com/poe-bot-server/` to check if the updated app is running.
16. **Note**: Before your bot can function, you'll need to configure the `.env` file. This requires completing Part 2.

### Part 2: Creating a Server Bot on Poe

To link your web app to Poe, you need to create a server bot profile.

1. Log into your Poe account.
2. Click "Create bot" or navigate to [poe.com/create_bot](https://poe.com/create_bot).
3. Select "Server bot".
4. Choose a unique name for your bot.
5. Enter your server's URL (e.g., `https://yourdomain.com/poe-bot-server/`) under **Server URL**.
6. Copy the access key provided by Poe.
7. Update the `.env` file in your web app directory with the bot name and access key.
8. Click "Check reachability" to test the connection between Poe and your web app. If there are issues, try restarting the app.
9. Once the connection is successful, click "Create bot".
10. Start a chat with your new server bot on Poe to see it in action!

## Contributing

Are you familiar with the Poe platform's API or have insight into the JSON payloads used for bot-to-bot communication? Contributions are welcome!

This project is in active development and one key challenge is understanding the specifics of how bots on Poe interact with each other. If you have information or code related to this, particularly regarding the format of JSON payloads for requests and responses, your help would be greatly appreciated!

Here's how you can contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/new-feature`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/new-feature`).
5. Open a pull request.

Please feel free to open issues or reach out if you have any questions or ideas!

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
