import os
import json
from litemapy import Schematic
import numpy as np
from collections import Counter

def parse_litematic(file_path):
    """解析litematic文件并返回其内容的结构化数据"""
    if not os.path.exists(file_path):
        return {"error": f"文件不存在: {file_path}"}
    
    try:
        # 加载litematic文件
        import time
        start_time = time.time()
        schematic = Schematic.load(file_path)
        end_time = time.time()
        print(f"加载文件耗时: {end_time - start_time:.4f}秒")
        
        # 提取基本信息
        import time
        start_time = time.time()
        basic_info = {
            "name": schematic.name,
            "author": schematic.author,
            "description": schematic.description,
            "regions_count": len(schematic.regions)
        }
        end_time = time.time()
        print(f"提取基本信息耗时: {end_time - start_time:.4f}秒")
        
        # 计算总方块数和总体积
        import time
        start_time = time.time()
        total_blocks = 0
        total_volume = 0
        for region_name, region in schematic.regions.items():
            total_volume += region.volume()  # volume是方法，需要调用
            # 计算非空气方块
            for x, y, z in region.block_positions():
                block = region[x, y, z]
                if block.id != "minecraft:air":
                    total_blocks += 1
        
        basic_info["total_blocks"] = total_blocks
        basic_info["total_volume"] = total_volume
        end_time = time.time()
        print(f"计算总方块数和总体积耗时: {end_time - start_time:.4f}秒")
        
        # 提取区域信息
        import time
        start_time = time.time()
        regions_info = {}
        for region_name, region in schematic.regions.items():
            # 计算区域中不同方块的数量
            block_counts = Counter()
            for x, y, z in region.block_positions():
                block = region[x, y, z]
                if block.id != "minecraft:air":  # 忽略空气方块
                    block_counts[block.id] += 1
            
            # 获取区域的尺寸
            width = region.width
            height = region.height
            length = region.length
            
            # 存储区域信息
            regions_info[region_name] = {
                "position": (region.x, region.y, region.z),
                "size": (width, height, length),
                "volume": region.volume(),  # volume是方法，需要调用
                "non_air_blocks": sum(block_counts.values()),
                "block_types": len(block_counts),
                "most_common_blocks": dict(block_counts.most_common())
            }
        end_time = time.time()
        print(f"提取区域信息耗时: {end_time - start_time:.4f}秒")
        
        # 组合所有信息
        import time
        start_time = time.time()
        result = {
            "file_name": os.path.basename(file_path),
            "file_size_bytes": os.path.getsize(file_path),
            "basic_info": basic_info,
            "regions": regions_info
        }
        end_time = time.time()
        print(f"组合所有信息耗时: {end_time - start_time:.4f}秒")
        
        return result
    
    except Exception as e:
        return {"error": f"解析文件时出错: {str(e)}"}

def main():
    """主函数"""
    litematic_file = "CZDBT末地大厅.litematic"
    
    print(f"正在解析 {litematic_file}...")
    result = parse_litematic(litematic_file)
    
    # 保存为JSON
    with open("litematic_analysis.json", 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()