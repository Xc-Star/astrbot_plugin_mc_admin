# 解析材料列表文件（支持txt和csv）
import os


class FileParser:
    def __init__(self, filepath):
        self.filepath = filepath

    def get_gb_total(self,name,total) -> tuple:
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

    def parse(self) -> dict:
        # 材料列表为txt文本的情况
        if self.filepath.endswith(".txt"):
            # interval（分割符）, head（从头部多少行开始读取）, tail（读区到尾部第多少行）, name_index（名称的索引）, d（是否去除引号）
            interval, head, tail, name_index, d= "|", 5, -4, 1, 0
        # 材料列表为csv的情况
        elif self.filepath.endswith(".csv"):
            interval, head, tail, name_index, d = ",", 2, -1, 0,  1
        else:
            return {"code":500,"msg":"不支持的文件类型"}
        # 读取材料列表文件进行处理
        with open(self.filepath, "r", encoding="utf-8") as file:
            try:
                # 读取文件的所有内容
                data_str = file.read()
                # 将文件夹内容以换行符切割为列表
                lines = data_str.split('\n')
                if len(lines) < head - (tail + 1):
                    return {"code":500, "msg":"内容不符合要求，请检查后上传"}
                result = []
                id = 1
                for line in lines[head:tail]:
                    item_info = {}
                    parts = line.split(interval)
                    if d:
                        # 如果去除引号为1取字符串的第二个字符到倒数第二个
                        name = parts[name_index].strip()[1:-1]
                    else:
                        name = parts[name_index].strip()
                    # 获取材料所需的组数和盒数
                    gb_total = self.get_gb_total(name,int(parts[name_index+1].strip()))
                    item_info["id"] = id
                    item_info['name'] = name
                    item_info['total'] = int(parts[name_index+1].strip())
                    item_info['GroupTotal'] = gb_total[0]
                    item_info['BoxTotal'] = gb_total[1]
                    item_info['PersonInCharge'] = "-"
                    item_info['progress'] = 0
                    item_info['location'] = "-"
                    result.append(item_info)
                    id += 1
                return {"code":200,"msg":result}
            except Exception as e:
                print(e)
                return {"code":500,"msg":"文件解析失败"}

if __name__ == "__main__":
    filepath = "../data/ReadMe.txt"
    f = FileParser(filepath).parse()
    print(f)