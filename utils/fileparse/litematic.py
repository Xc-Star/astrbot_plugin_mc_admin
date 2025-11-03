import os
from collections import Counter
import numpy as np
from numba import jit
import nbtlib


@jit(nopython=True)
def parse_block_indices(block_states, total_blocks, bits_per_block):
    """使用 numba JIT 加速的位解析（正确处理跨long边界）"""
    block_indices = np.zeros(total_blocks, dtype=np.int32)
    mask = (1 << bits_per_block) - 1

    current_long_idx = 0
    current_bit_offset = 0

    for i in range(total_blocks):
        if current_long_idx >= len(block_states):
            break

        bits_in_current_long = 64 - current_bit_offset

        if bits_in_current_long >= bits_per_block:
            block_indices[i] = (block_states[current_long_idx] >> current_bit_offset) & mask
            current_bit_offset += bits_per_block
        else:
            if current_long_idx + 1 >= len(block_states):
                break  # 防止越界

            low_mask = (1 << bits_in_current_long) - 1
            low_bits = (block_states[current_long_idx] >> current_bit_offset) & low_mask

            high_bits_needed = bits_per_block - bits_in_current_long
            high_mask = (1 << high_bits_needed) - 1
            high_bits = block_states[current_long_idx + 1] & high_mask

            block_indices[i] = low_bits | (high_bits << bits_in_current_long)

            current_long_idx += 1
            current_bit_offset = high_bits_needed

        if current_bit_offset >= 64:
            current_long_idx += 1
            current_bit_offset -= 64

    return block_indices


def parse_litematic(file_path):
    """解析 litematic 文件"""
    if not os.path.exists(file_path):
        return {"error": f"文件不存在: {file_path}"}

    try:
        nbt_file = nbtlib.load(file_path)

        regions_info = {}
        regions = nbt_file.get('Regions', {})

        for region_name, region_data in regions.items():
            palette = region_data.get('BlockStatePalette', [])
            block_states_raw = region_data.get('BlockStates', [])

            size = region_data.get('Size', {})
            width = abs(int(size.get('x', 0)))
            height = abs(int(size.get('y', 0)))
            length = abs(int(size.get('z', 0)))

            bits_per_block = max(2, (len(palette) - 1).bit_length())

            block_states = np.array([int(x) for x in block_states_raw], dtype=np.int64)
            block_states = block_states.view(np.uint64)

            total_blocks = width * height * length
            block_indices = parse_block_indices(block_states, total_blocks, bits_per_block)

            unique_indices, counts = np.unique(block_indices, return_counts=True)

            block_counts = Counter()
            for idx, count in zip(unique_indices, counts):
                idx_int = int(idx)
                if idx_int < len(palette):
                    block_name = str(palette[idx_int].get('Name', 'unknown'))
                    if block_name != "minecraft:air":
                        block_counts[block_name] += int(count)

            regions_info[region_name] = {
                "most_common_blocks": dict(block_counts.most_common())
            }

        return {"regions": regions_info}

    except Exception as e:
        return {"error": f"解析失败: {str(e)}"}