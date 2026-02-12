from rcon.source import rcon

async def rcon_send(host, port, passwd, command, timeout=3):
    return await rcon(
        command,
        host=host, port=port, passwd=passwd, timeout=timeout
    )