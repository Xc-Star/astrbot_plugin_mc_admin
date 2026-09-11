class Loc:
    def __init__(
        self,
        name="",
        dimension=-1,
        location=None,
        overworld=None,
        nether=None,
        end=None,
    ):
        """
        初始化Loc类
        """
        self.name = name
        self.overworld = overworld
        self.nether = nether
        self.end = end

        if dimension == 0:
            self.overworld = location
        elif dimension == 1:
            self.nether = location
        elif dimension == 2:
            self.end = location

    def set_location(self, dimension=-1, location=None):
        if dimension == 0:
            self.overworld = location
        elif dimension == 1:
            self.nether = location
        elif dimension == 2:
            self.end = location

    def get_info_str(self) -> str:
        result_parts = [f"位置: {self.name}"]
        if self.overworld:
            result_parts.append(f"主世界: {self.overworld}")
        if self.nether:
            result_parts.append(f"地狱: {self.nether}")
        if self.end:
            result_parts.append(f"末地: {self.end}")
        return "\n".join(result_parts)

    def __str__(self):
        """返回位置信息的字符串表示"""
        return f"Loc(name='{self.name}', overworld={self.overworld}, nether={self.nether}, end={self.end})"

    def __repr__(self):
        """返回位置信息的正式字符串表示"""
        return self.__str__()
