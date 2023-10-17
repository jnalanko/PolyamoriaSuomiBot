async def send_dm(api, to_user_id, message):
    to_user = await api.fetch_user(to_user_id)
    dm_channel = await api.create_dm(to_user)
    await dm_channel.send(message)