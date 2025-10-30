import os
from litemapy import Schematic
from collections import Counter
import numpy as np


def parse_litematic(file_path):
    try:
        # 加载litematic文件
        import time
        schematic = Schematic.load(file_path)

        # 提取区域信息（使用numpy优化方法）
        regions_info = {}
        for region_name, region in schematic.regions.items():
            # 使用numpy直接统计调色板索引，避免遍历所有坐标
            blocks_array = region._Region__blocks
            palette_list = region._Region__palette

            # 使用numpy统计每个调色板索引的出现次数
            unique_indices, counts = np.unique(blocks_array, return_counts=True)

            # 将调色板索引映射回方块ID并统计
            block_counts = Counter()
            for idx, count in zip(unique_indices, counts):
                block_state = palette_list[idx]
                block_id = block_state.id
                if block_id != "minecraft:air":  # 忽略空气方块
                    block_counts[block_id] += int(count)

            # 存储区域信息，只保留most_common_blocks
            regions_info[region_name] = {
                "most_common_blocks": dict(block_counts.most_common())
            }

        # 组合所有信息
        result = {
            "regions": regions_info
        }

        return result

    except Exception as e:
        return {"error": f"解析文件时出错: {str(e)}"}