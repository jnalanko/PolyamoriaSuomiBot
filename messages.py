import logging

# Returns a tuple (message_id, context_id), where context_id can be -1
def parse_message_reference(message_reference):
    message_str = ""
    context_str = None

    # parse ID from URI or use it directly if not an URI
    slash_index = message_reference.rfind('/')
    if slash_index >= 0:
        message_str = message_reference[slash_index+1:]
        context_str = message_reference[:slash_index]
        slash_index_r2 = context_str.rfind('/')
        context_str = message_reference[slash_index_r2+1:slash_index]
    else:
        message_str = message_reference

    message_id = -1
    context_id = -1

    # parse IDs into an integers and handle error if thrown
    try:
        message_id = int(message_str)
        if context_str != None:
            context_id = int(context_str)
    except ValueError:
        pass

    return (message_id, context_id)

# Can fetch a message from anywhere, or within context if reference is merely a Message ID
# returns a tuple (message, error_message) where latter is not None if message is None
async def fetch_message_by_reference(self, ctx, message_reference):
    ids = parse_message_reference(message_reference)

    message_id = ids[0]
    if message_id == -1:
        return (None, "Virheellinen viittaus kopioitavaan viestiin '{}'.".format(message_reference))

    context_id = ids[1]
    if context_id == -1:
        return await fetch_message_by_id(ctx, message_id)

    new_context = self.api.get_guild(self.guild_id).get_channel_or_thread(context_id)
    if new_context == None:
        return (None, "Virheellinen viittaus kanavaan tai ketjuun '{}'->'{}'".format(message_reference, context_id))

    return await fetch_message_by_id(new_context, message_id)

# Can fetch a message by ID, but only within limited context (like the channel where command was given)
# returns a tuple (message, error_message) where latter is not None if message is None
async def fetch_message_by_id(ctx, message_id):
    try:
        message = await ctx.fetch_message(message_id)
    except Exception as e:
        return (None, "Viestin {} hakeminen epäonnistui, virhe: '{}'".format(message_id, str(e)))

    return (message, None)