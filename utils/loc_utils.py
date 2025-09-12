from .config_utils import ConfigUtils
from .pojo.loc import Loc

class LocUtils:
    def __init__(self):
        pass

    def add_loc(self, loc: Loc) -> str:
        config_utils = ConfigUtils()
        loc_list = config_utils.get_loc_list()
        loc_list.append(loc.__dict__)
        config_utils.set_loc_list(loc_list)
        return f'已将${loc.name}添加到列表'

    def remove_loc(self, name: str) -> str:
        config_utils = ConfigUtils()
        loc_list = config_utils.get_loc_list()
        for loc in loc_list:
            if loc['name'] == name:
                loc_list.remove(loc)
                config_utils.set_loc_list(loc_list)
                return f'已将{name}从列表移除'
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
        # TODO: 列表loc
        for loc in loc_list:
            print(loc['name'])

    def set_loc(self, loc: Loc) -> str:
        config_utils = ConfigUtils()
        loc_list = config_utils.get_loc_list()
        for loc in loc_list:
            if loc['name'] == loc.name:
                loc['overworld'] = loc.overworld
                loc['nether'] = loc.nether
                loc['end'] = loc.end
                config_utils.set_loc_list(loc_list)
                return f'已将{loc.name}更新'
        return f'未找到{loc.name}'
