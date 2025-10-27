class FileParser:
    def __init__(self):
        pass

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
            # TODO: 解析litematic源文件
            pass
        else:
            return {"code":500,"msg":"解析不了喵~"}
        # 读取材料列表文件进行处理
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
                    # 创建元组  TODO: name_id
                    result.append((name, '', total, '', commit_count, number, task_id))
                return {"code":200,"msg":result}
            except Exception as e:
                print(e)
                return {"code":500,"msg":"解析不了喵~"}
