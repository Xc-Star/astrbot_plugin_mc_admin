from .item_mapping import ItemMapping
from .parse_litematic import parse_litematic
import os


class FileParser:
    def __init__(self):
        # 正确设置映射文件路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)  # 回到插件根目录
        mapping_file_path = os.path.join(parent_dir, 'data', 'item_mapping.json')
        self.item_mapping = ItemMapping(mapping_file_path)

    def get_gb_total(self,name,total) -> tuple:
        # 获取堆叠数量
        if name.endswith("潜影盒") or name.endswith("旗帜") or name.endswith("盔甲架") or name.endswith("告示牌"):
            stackable = 16
        elif name.endswith("潜影盒") or (name.endswith("桶")  and len(name)>=2)or name.endswith("床"):
            stackable = 1
        else:
            stackable = 64
        # 返回组数
        group_total = round(total/stackable,2)
        box_total = round(total/stackable/27,2)
        return group_total,box_total

    def parse(self, file_path: str, task_id: int) -> dict:
        # 材料列表为txt文本的情况
        if file_path.endswith(".txt"):
            # interval（分割符）, head（从头部多少行开始读取）, tail（读区到尾部第多少行）, name_index（名称的索引）, d（是否去除引号）
            interval, head, tail, name_index, d= "|", 5, -4, 1, 0
        # 材料列表为csv的情况
        elif file_path.endswith(".csv"):
            interval, head, tail, name_index, d = ",", 2, -1, 0,  1
        elif file_path.endswith(".litematic"):
            # 解析litematic源文件
            try:
                parse_result = parse_litematic(file_path)
                # 合并多区域的材料
                merged_blocks = self.merged_regions(parse_result)

                result = []
                number = 1
                for block_id in merged_blocks:
                    result.append((self.item_mapping.get_item_name(block_id), block_id, merged_blocks[block_id], '', 0, number, task_id))
                    number += 1

                return {"code": 200, "msg": result}
            except Exception as e:
                return {"code": 500, "msg": f"解析投影源文件报错喵~: {str(e)}"}
        else:
            return {"code":500,"msg":"解析不了喵~"}
        # 处理txt和csv
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                # 读取文件的所有内容
                data_str = file.read()
                # 将文件夹内容以换行符切割为列表
                lines = data_str.split('\n')
                if len(lines) < head - (tail + 1):
                    return {"code":500, "msg":"解析不了喵~"}
                result = []
                for line in lines[head:tail]:
                    parts = line.split(interval)
                    if d:
                        # 如果去除引号为1取字符串的第二个字符到倒数第二个
                        name = parts[name_index].strip()[1:-1]
                    else:
                        name = parts[name_index].strip()
                    total = int(parts[name_index+1].strip())
                    commit_count = 0
                    number = len(result) + 1
                    # 创建元组
                    result.append((name, self.item_mapping.get_item_id(name), total, '', commit_count, number, task_id))
                return {"code":200,"msg":result}
            except Exception as e:
                return {"code":500,"msg":"解析不了喵~"}

    def merged_regions(self, parse_result):
        # 合并所有区域的同种材料
        merged_blocks = {}
        if "regions" in parse_result:
            for region_name, region_data in parse_result["regions"].items():
                if "most_common_blocks" in region_data:
                    for block_id, count in region_data["most_common_blocks"].items():
                        # 累加相同block_id的数量
                        merged_blocks[block_id] = merged_blocks.get(block_id, 0) + count
        return merged_blocks
