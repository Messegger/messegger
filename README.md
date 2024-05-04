# Messegger v0.2

A very work-in-progress/early release of the Discord bot dedicated to providing the best message moderation and logging experience. Add the bot to your server [here](https://discord.com/oauth2/authorize?client_id=1226243129733156906&permissions=0&scope=bot).

The public bot's operation and its uptime, while it's still being added to its first servers, is not guaranteed. Join the [Messegger Discord server](https://discord.gg/rWVHU3qjvK) for any updates about the project.

## Features

Currently supported:
- **Message logging** - log edited and deleted messages in a dedicated channel.
- **Persistent messages** - store new, edited, and deleted messages in its own database for an improved logging effectiveness.

Planned features:
- **Attachment logging** - download and store message attachments as to not rely on Discord's auto-expiring CDN.
- **Web access** - the Messegger project has a registered domain name `messegger.xyz`, which will be used to have more control over providing a much richer view of message logs. And a dashboard, but that's probably for a v2.
- And much more...

Planned improvements:
- Learn more about the complex system of interaction commands to properly organize commands and improve their convenient use.
- And much more...

## Self-hosting

As of this point, there is no official support or guidance for hosting your own instance of the bot. The project is open-source, however, so if you have the technical knowledge, an experienced Python developer or have experience hosting other Discord bots, you may be able to figure stuff out on your own, and I'm happy for you.

Until the full v1 release, with whatever free time I have working on this, I will only be focusing on features and their specific implementations that make it convenient for me to run the public bot. This also includes Linux-exclusive hosting.

Apologies to any self-hosting nerds.

## License

The project is released under the GNU AGPLv3 license.

Some key points:
- Any changes made to the source code must be disclosed with the same (or any GPL compatible) license as the original project.
- Users using the software over the network (e.g. interacting with the bot on Discord) have the right to receive a copy of the source code.
