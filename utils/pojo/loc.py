class Loc:
    """
    位置信息类，包含四个属性：
    - name: 位置名称
    - overworld: 主世界坐标
    - nether: 下界坐标
    - end: 末地坐标
    """
    
    def __init__(self, name="", overworld=None, nether=None, end=None):
        """
        初始化Loc类
        
        Args:
            name (str): 位置名称
            overworld (tuple, optional): 主世界坐标，格式为 (x, y, z)
            nether (tuple, optional): 下界坐标，格式为 (x, y, z)
            end (tuple, optional): 末地坐标，格式为 (x, y, z)
        """
        self.name = name
        self.overworld = overworld
        self.nether = nether
        self.end = end
    
    def __str__(self):
        """返回位置信息的字符串表示"""
        return f"Loc(name='{self.name}', overworld={self.overworld}, nether={self.nether}, end={self.end})"
    
    def __repr__(self):
        """返回位置信息的正式字符串表示"""
        return self.__str__()
        