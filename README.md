# Messegger

A Discord bot dedicated to providing the best message moderation and logging experience. Add the bot to your server [here](https://discord.com/oauth2/authorize?client_id=1226243129733156906&permissions=0&scope=bot).

The public bot's operation and its uptime, while it's still being added to its first servers, is not guaranteed. Join the [Messegger Discord server](https://discord.gg/rWVHU3qjvK) for any updates about the project.

## Features

Currently supported:
- **Message Logging** - log edited and deleted messages in a dedicated channel.
- **Persistent Messages** - store new, edited, and deleted messages in its own database for an improved logging effectiveness.
- **Sniping** - snipe the latest deleted message from a channel.

Planned features:
- **Persistent Attachments** - store a copy of message attachments as to not rely on Discord's auto-expiring CDN.
- **Translator** - translate messages to any supported languages.
- **Web Access** - the Messegger project has a registered domain name `messegger.xyz`, which will be used to have more control over providing a much richer view of message logs. And a dashboard, but that's probably for a v2.
- And much more...

Planned improvements:
- Learn more about the complex system of interaction commands to properly organize commands and improve their convenient use.
- And much more...

## Self-hosting

As of this point, there is no official support or guidance for hosting your own instance of the bot. The project is open-source, however, so if you have the technical knowledge, an experienced Python developer or have experience hosting other Discord bots, you may be able to figure stuff out on your own, and I'm happy for you.

### Prerequisites

- **PostgreSQL 16** - Messegger's primary database storage.
- **S3 Server** - Object storage for storing message attachments.

The easiest way to host the entire project locally on the same device is with Docker. This also ensures proper support and compatibility of the project, since Messegger is being developed only around a pre-defined environment which you can find in Dockerfile, which is what the public bot runs on. The Docker alternatives to the above prerequisites are [postgres](https://hub.docker.com/_/postgres) and [minio](https://hub.docker.com/r/minio/minio), for example.

### Why not Docker Compose?

I tried writing a compose file, but seems like I don't have enough experience with it to properly implement it for this project. For example, because PostgreSQL needs time to start up before a client can connect to it, Messegger trying to do so immediately fails to start up, because it requires an active PostgreSQL connection to operate.

If you know how to write a proper compose file, you're welcome to open a Pull Request with the `compose.yml` file.

## License

The project is released under the GNU AGPLv3 license.

Some key points about the license:
- Any changes made to the source code must be disclosed with the same license as the original project.
- Users interacting with the software over the network (e.g. interacting with a bot on Discord) have the right to receive a copy of the source code.
