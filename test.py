interval, head, tail, name_index, d= "|", 5, -4, 1, 0
with open("./data/ReadMe.txt", "r", encoding="utf-8") as file:
    # 读取文件的所有内容
    data_str = file.read()
    # 将文件夹内容以换行符切割为列表
    lines = data_str.split('\n')
    print(len(lines) < head - (tail + 1))