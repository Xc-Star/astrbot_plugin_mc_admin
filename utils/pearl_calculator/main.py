#!/usr/bin/env python3
"""
PearlCalculatorCore API Usage Example (Python)

This example demonstrates:
1. Loading configuration from JSON file
2. Inverse Calculation: Find TNT amounts to reach a destination
3. Forward Calculation: Simulate pearl trajectory with given TNT

Run with: python examples/usage.py
"""

import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pearl_calculator_core import (
    Space3D, Direction, PearlVersion, Cannon, Pearl, CannonMode, LayoutDirection,
    calculate_tnt_amount, calculate_pearl_trace
)

MAX_SIMULATION_TICKS = 10000
SEARCH_TOLERANCE_BLOCKS = 50.0
MAX_TICK_LIMIT = 100  # Maximum tick limit for finding solutions


def load_config(config_str: str) -> dict:
    if config_str == '' or config_str is None:
        return {"data": None, "msg": "还没有珍珠炮的配置喵～"}
    try:
        pearl_config = json.loads(config_str)
        return {"data": pearl_config, "msg": "success"}
    except json.decoder.JSONDecodeError:
        return {"data": None, "msg": "珍珠炮配置格式错误喵～"}


def parse_space3d(data: dict) -> Space3D:
    return Space3D(
        data.get('X', data.get('x', 0.0)),
        data.get('Y', data.get('y', 0.0)),
        data.get('Z', data.get('z', 0.0))
    )


def parse_layout_direction(s: str) -> LayoutDirection:
    mapping = {
        "NorthWest": LayoutDirection.NorthWest,
        "NorthEast": LayoutDirection.NorthEast,
        "SouthWest": LayoutDirection.SouthWest,
        "SouthEast": LayoutDirection.SouthEast,
    }
    return mapping.get(s, LayoutDirection.NorthWest)


def create_cannon_from_config(config: dict) -> tuple:
    settings = config

    pearl_data = settings['Pearl']
    pearl = Pearl(
        position=parse_space3d(pearl_data['Position']),
        motion=parse_space3d(pearl_data['Motion']),
        offset=Space3D(settings['Offset']['X'], 0.0, settings['Offset']['Z'])
    )

    default_red_duper = parse_layout_direction(settings.get('DefaultRedDirection', 'NorthWest'))
    default_blue_duper = parse_layout_direction(settings.get('DefaultBlueDirection', 'SouthEast'))

    cannon = Cannon(
        pearl=pearl,
        north_west_tnt=parse_space3d(settings['NorthWestTNT']),
        north_east_tnt=parse_space3d(settings['NorthEastTNT']),
        south_west_tnt=parse_space3d(settings['SouthWestTNT']),
        south_east_tnt=parse_space3d(settings['SouthEastTNT']),
        default_red_duper=default_red_duper,
        default_blue_duper=default_blue_duper,
    )

    max_tnt = settings.get('MaxTNT', 1000)

    return cannon, max_tnt

def get_pearl_version(config_version: str):
    if config_version == "Legacy":
        return PearlVersion.Legacy
    elif config_version == "1205":
        return PearlVersion.Post1205
    elif config_version == "1212":
        return PearlVersion.Post1212
    return "UNKNOWN"


def process_bit_config(bit_config: str) -> list[int]:
    # 处理空值情况
    if not bit_config or bit_config.strip() == "":
        return []
    try:
        items = []
        for item in bit_config.split(","):
            items.append(int(item.strip()))
        return items

    except:
        return []

def process_direction_bit(direction_bit: str):
    """
    处理东西南北字典
    """
    direction_dict = {}
    direction_list = direction_bit.split(",")
    if len(direction_list) != 4:
        return direction_dict
    direction_dict["East"] = direction_list[0]
    direction_dict["North"] = direction_list[1]
    direction_dict["West"] = direction_list[2]
    direction_dict["South"] = direction_list[3]
    return direction_dict


def calculate_bit_encoding(value: int, bit_counts: list[int]) -> str:
    if not bit_counts:
        return ""

    # 记录原始索引
    indexed_bits = [(bit, idx) for idx, bit in enumerate(bit_counts)]
    # 按值从大到小排序
    sorted_bits = sorted(indexed_bits, key=lambda x: x[0], reverse=True)

    remaining = value
    selected = [False] * len(bit_counts)

    for bit_value, original_idx in sorted_bits:
        if remaining >= bit_value:
            selected[original_idx] = True
            remaining -= bit_value

    if remaining > 0:
        print(f"Warning: 无法完全表示 {value}，剩余 {remaining}")

    return ''.join(['1' if selected[i] else '0' for i in range(len(bit_counts))])

class PearlCalculatorUtils:
    def __init__(self, config: dict):
        self.config = config.get('pearl_config')
        self.pearl_version = get_pearl_version(config.get('pearl_version'))
        self.red_bit_count = process_bit_config(config.get('red_bit_count'))
        self.blue_bit_count = process_bit_config(config.get('blue_bit_count'))
        self.direction_dict = process_direction_bit(config.get('direction_bit'))
        self.real_red_color = config.get('real_red_color')
        self.real_blue_color = config.get('real_red_color')

    async def pearl_calculator(self, target_x: int, target_z: int) -> dict:
        """

        """
        # 校验珍珠版本
        if self.pearl_version == "UNKNOWN":
            return {"data": None, "msg": "游戏版本识别失败喵～"}
        # 加载配置文件
        pearl_config = load_config(self.config)
        if pearl_config["msg"] != "success":
            return {"data": None, "msg": pearl_config["msg"]}
        pearl_config = pearl_config["data"]
        cannon, max_tnt = create_cannon_from_config(pearl_config)

        # 计算TNT当量
        destination = Space3D(target_x, 0.0, target_z)
        results = calculate_tnt_amount(cannon, destination, max_tnt, None, MAX_SIMULATION_TICKS, SEARCH_TOLERANCE_BLOCKS, self.pearl_version,)
        if not results:
            return {"data": None, "msg": "算不出来喵呜˃̣̣̥᷄⌓˂̣̣̥᷅"}

        # 拼装基础响应数据
        best = results[0]
        result = dict()
        result["redTNT"] = best.red
        result["blueTNT"] = best.blue
        result["direction"] = best.direction.name
        # 如果配置了阵列数量则加上bit编码结果
        if len(self.red_bit_count) != 0 and len(self.blue_bit_count) != 0 and len(self.red_bit_count) == len(self.blue_bit_count):
            result["redTNTBit"] = calculate_bit_encoding(best.red, self.red_bit_count)
            result["blueTNTBit"] = calculate_bit_encoding(best.blue, self.blue_bit_count)
        # 如果配置了方向编码则加上方向bit编码结果
        if self.direction_dict.get(best.direction.name):
            result["direction_bit"] = self.direction_dict[best.direction.name]
        if self.real_red_color and self.real_red_color != "":
            result["real_red_color"] = self.real_red_color
        if self.real_blue_color and self.real_blue_color != "":
            result["real_blue_color"] = self.real_blue_color

        # 模拟珍珠轨迹
        sim_ticks = best.tick + 1
        trace = calculate_pearl_trace(cannon, best.red, best.blue, best.vertical, best.direction, sim_ticks, [], self.pearl_version,)
        if trace is None:
            return {"data": None, "msg": "珍珠轨迹模拟失败喵呜˃̣̣̥᷄⌓˂̣̣̥᷅"}

        # 选择的计算结果
        result["calculatedTick"] = best.tick
        result["calculatedCoordinates"] = f"X:{trace.pearl_trace[best.tick].x:.2f} Y:{trace.pearl_trace[best.tick].y:.2f} Z:{trace.pearl_trace[best.tick].z:.2f}"
        # 路径
        pearl_path = []
        for tick in range(len(trace.pearl_trace)):
            pos = trace.pearl_trace[tick]
            pearl_path.append({"tick": tick, "x": pos.x, "y": pos.y, "z": pos.z})
        result["pearlPath"] = pearl_path

        return {"data": result, "msg": "success"}