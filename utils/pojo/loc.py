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
            overworld (tuple or str, optional): 主世界坐标，格式为 (x, y, z) 或 "x y z"
            nether (tuple or str, optional): 下界坐标，格式为 (x, y, z) 或 "x y z"
            end (tuple or str, optional): 末地坐标，格式为 (x, y, z) 或 "x y z"
        """
        self.name = name
        
        # 处理坐标参数，如果是字符串则转换为元组
        if isinstance(overworld, str):
            coords = overworld.split()
            if len(coords) == 3:
                self.overworld = (int(coords[0]), int(coords[1]), int(coords[2]))
            else:
                self.overworld = None
        else:
            self.overworld = overworld
            
        if isinstance(nether, str):
            coords = nether.split()
            if len(coords) == 3:
                self.nether = (int(coords[0]), int(coords[1]), int(coords[2]))
            else:
                self.nether = None
        else:
            self.nether = nether
            
        if isinstance(end, str):
            coords = end.split()
            if len(coords) == 3:
                self.end = (int(coords[0]), int(coords[1]), int(coords[2]))
            else:
                self.end = None
        else:
            self.end = end
    
    def __str__(self):
        """返回位置信息的字符串表示"""
        return f"Loc(name='{self.name}', overworld={self.overworld}, nether={self.nether}, end={self.end})"
    
    def __repr__(self):
        """返回位置信息的正式字符串表示"""
        return self.__str__()
