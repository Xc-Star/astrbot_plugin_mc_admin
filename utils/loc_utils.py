from .config_utils import ConfigUtils
from .pojo.loc import Loc

class LocUtils:
    def __init__(self):
        pass

    def add_loc(self, loc: Loc) -> str:
        config_utils = ConfigUtils()
        loc_list = config_utils.get_loc_list()
        for existing_loc in loc_list:
            if existing_loc['name'] == loc.name:
                return f'"{loc.name}"已存在'
        
        loc_list.append({
            'name': loc.name,
            'overworld': loc.overworld,
            'nether': loc.nether,
            'end': loc.end
        })
        config_utils.set_loc_list(loc_list)
        return f'已添加"{loc.name}"'

    def remove_loc(self, name: str) -> str:
        config_utils = ConfigUtils()
        loc_list = config_utils.get_loc_list()
        for i, loc in enumerate(loc_list):
            if loc['name'] == name:
                loc_list.pop(i)
                config_utils.set_loc_list(loc_list)
                return f'已将"{name}"移除'
        return f'未找到"{name}"'
    
    def get_loc_by_name(self, name: str) -> Loc | None:
        config_utils = ConfigUtils()
        loc_list = config_utils.get_loc_list()
        for loc in loc_list:
            if loc['name'] == name:
                # 转成Loc对象
                return Loc(name=loc['name'], overworld=loc['overworld'], nether=loc['nether'], end=loc['end'])
        return None

    def list_loc(self):
        config_utils = ConfigUtils()
        loc_list = config_utils.get_loc_list()
        result = "服务器位置列表:\n"
        for loc in loc_list:
            result += f"- {loc['name']}\n"
        return result.strip()

    def set_loc(self, loc: Loc) -> str:
        config_utils = ConfigUtils()
        loc_list = config_utils.get_loc_list()
        
        # 查找同名位置
        for i, existing_loc in enumerate(loc_list):
            if existing_loc['name'] == loc.name:
                # 更新位置信息
                loc_list[i] = {
                    'name': loc.name,
                    'overworld': loc.overworld,
                    'nether': loc.nether,
                    'end': loc.end
                }
                config_utils.set_loc_list(loc_list)
                return f'已更新"{loc.name}"'
        
        # 未找到对应位置
        return f'未找到"{loc.name}"'
        
