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
                return f'位置 {loc.name} 已存在'
        
        # 格式化坐标为字符串
        overworld_str = None
        nether_str = None
        end_str = None
        
        if loc.overworld:
            overworld_str = f"{loc.overworld[0]} {loc.overworld[1]} {loc.overworld[2]}"
        if loc.nether:
            nether_str = f"{loc.nether[0]} {loc.nether[1]} {loc.nether[2]}"
        if loc.end:
            end_str = f"{loc.end[0]} {loc.end[1]} {loc.end[2]}"
        
        loc_list.append({
            'name': loc.name,
            'overworld': overworld_str,
            'nether': nether_str,
            'end': end_str
        })
        config_utils.set_loc_list(loc_list)
        return f'已将 {loc.name} 添加到列表'

    def remove_loc(self, name: str) -> str:
        config_utils = ConfigUtils()
        loc_list = config_utils.get_loc_list()
        for i, loc in enumerate(loc_list):
            if loc['name'] == name:
                loc_list.pop(i)
                config_utils.set_loc_list(loc_list)
                return f'已将 {name} 从列表移除'
        return f'未找到{name}'
    
    def get_loc_by_name(self, name: str) -> Loc:
        config_utils = ConfigUtils()
        loc_list = config_utils.get_loc_list()
        for loc in loc_list:
            if loc['name'] == name:
                return Loc(loc['name'], loc['overworld'], loc['nether'], loc['end'])
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
        for i, existing_loc in enumerate(loc_list):
            if existing_loc['name'] == loc.name:
                # 格式化坐标为字符串
                overworld_str = None
                nether_str = None
                end_str = None
                
                if loc.overworld:
                    overworld_str = f"{loc.overworld[0]} {loc.overworld[1]} {loc.overworld[2]}"
                if loc.nether:
                    nether_str = f"{loc.nether[0]} {loc.nether[1]} {loc.nether[2]}"
                if loc.end:
                    end_str = f"{loc.end[0]} {loc.end[1]} {loc.end[2]}"
                
                loc_list[i] = {
                    'name': loc.name,
                    'overworld': overworld_str,
                    'nether': nether_str,
                    'end': end_str
                }
                config_utils.set_loc_list(loc_list)
                return f'已将 {loc.name} 更新'
        return f'未找到 {loc.name}'
