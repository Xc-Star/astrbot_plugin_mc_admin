from mcrcon import MCRcon


class Rcon:
    def __init__(self, host="127.0.0.1", password="password", port=25575, timeout=10):
        self.host = host
        self.port = port
        self.password = password
        self.rcon = MCRcon(self.host, self.password, self.port, timeout=timeout)
        self.rcon.connect()

    def send_command(self, command):
        res = self.rcon.command(command)
        self.close()
        return res

    def close(self):
        self.rcon.disconnect()
