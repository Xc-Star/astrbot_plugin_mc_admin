class LocResult:
    def __init__(self):
        self.msg_type = -1
        self.data = ''

    def msg_result(self, data: str):
        self.msg_type = 0
        self.data = data

    def image_result(self, data: str):
        self.msg_type = 1
        self.data = data
