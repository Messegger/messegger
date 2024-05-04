CREATE TABLE IF NOT EXISTS messages (
    message_id BIGINT,
    channel_id BIGINT,
    author_id BIGINT,
    content TEXT,
    embeds JSONB[],
    attachments VARCHAR(255)[],
    action VARCHAR(10),
    timestamp TIMESTAMPTZ,
    is_webhook BOOLEAN
);
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT,
    log_channel_id BIGINT,
    persistent_messages BOOLEAN,
    premium_level SMALLINT,
    locale VARCHAR(10),
    PRIMARY KEY (guild_id)
);

CREATE INDEX IF NOT EXISTS message_channels_index ON messages USING hash (channel_id);
CREATE INDEX IF NOT EXISTS guild_ids_index ON guilds USING btree (guild_id);

CREATE OR REPLACE FUNCTION delete_related_messages()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM messages WHERE message_id = OLD.message_id AND channel_id = OLD.channel_id;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER delete_related_messages_trigger
BEFORE DELETE ON messages
FOR EACH ROW
WHEN (OLD.action = 'create')
EXECUTE FUNCTION delete_related_messages();
