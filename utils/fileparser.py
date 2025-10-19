# 解析材料列表文件（支持txt和csv）
class FileParser:
    def __init__(self, filepath):
        self.filepath = filepath

    def get_gb_total(self,name,total):
        # 获取堆叠数量
        if name.endswith("潜影盒") or name.endswith("旗帜") or name.endswith("盔甲架") or name.endswith("告示牌"):
            Stackable = 16
        elif name.endswith("潜影盒") or (name.endswith("桶")  and len(name)>=2)or name.endswith("床"):
            Stackable = 1
        else:
            Stackable = 64
        # 返回组数
        group_total = round(total/Stackable,2)
        box_total = round(total/Stackable/27,2)
        return group_total,box_total

    def parse(self):
        # 材料列表为txt文本的情况
        if self.filepath.endswith(".txt"):
            interval, head, tail, name_index, total_index, d= "|", 5, -4, 1, 2, 0
        # 材料列表为csv的情况
        elif self.filepath.endswith(".csv"):
            interval, head, tail, name_index, total_index, d = ",", 2, -1, 0, 1, 1
        else:
            return {"code":500,"msg":"不支持的后缀"}
        # 读取材料列表文件进行处理
        with open(self.filepath, "r", encoding="utf-8") as file:
            data_str = file.read()
            lines = data_str.split('\n')
            result = []
            for line in lines[head:tail]:

                item_info = {}
                parts = line.split(interval)
                if d == 1:
                    name = parts[name_index].strip()[1:-1]
                else:
                    name = parts[name_index].strip()
                gb_total = self.get_gb_total(parts[name_index].strip(),int(parts[total_index].strip()))
                item_info['name'] = name
                item_info['total'] = int(parts[total_index].strip())
                item_info['GroupTotal'] = gb_total[0]
                item_info['BoxTotal'] = gb_total[1]
                item_info['PersonInCharge'] = ""
                item_info['progress'] = "否"
                item_info['location'] = ""
                result.append(item_info)
            return {"code":200,"msg":result}