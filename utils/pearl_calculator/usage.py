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


def load_config(config_path: str) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


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
    settings = config['CannonSettings'][0]

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


def main():
    print("=== PearlCalculator 核心API示例 (Python) ===")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.example.json')

    if not os.path.exists(config_path):
        print(f"错误：在 {config_path} 找不到配置文件")
        return

    config = load_config(config_path)
    cannon, max_tnt = create_cannon_from_config(config)

    print("1. 配置已加载")
    print(f"   配置路径: {config_path}")
    print(f"   珍珠位置: ({cannon.pearl.position.x:.4f}, {cannon.pearl.position.y:.4f}, {cannon.pearl.position.z:.4f})")
    print(f"   珍珠运动:   ({cannon.pearl.motion.x:.4f}, {cannon.pearl.motion.y:.4f}, {cannon.pearl.motion.z:.4f})")
    print(f"   最大TNT/边:   {max_tnt}")
    print(f"   红色复制器:      {cannon.default_red_duper.value if cannon.default_red_duper else '无'}")
    print(f"   蓝色复制器:     {cannon.default_blue_duper.value if cannon.default_blue_duper else '无'}")
    print()

    print("2. 反向计算（目标求解）")

    destination = Space3D(10000, 0.0, 40000)
    print(f"   目标: ({destination.x:.2f}, {destination.y:.2f}, {destination.z:.2f})")

    start_time = time.perf_counter()

    results = calculate_tnt_amount(
        cannon,
        destination,
        max_tnt,
        None,
        MAX_SIMULATION_TICKS,
        SEARCH_TOLERANCE_BLOCKS,
        PearlVersion.Post1212
    )

    elapsed = time.perf_counter() - start_time
    print(f"   耗时: {elapsed * 1000:.2f} ms")

    if not results:
        print("   结果: 未找到解决方案。")
        return

    print(f"   找到的解决方案数: {len(results)}")
    print()

    best = results[0]
    print("   最佳解决方案（TNTResult）:")
    print(f"     红色TNT:       {best.red} TNT")
    print(f"     蓝色TNT:      {best.blue} TNT")
    print(f"     垂直TNT:  {best.vertical} TNT")
    print(f"     刻度:      {best.tick}")
    print(f"     距离:  {best.distance:.4f} 方块")
    print(f"     方向: {best.direction.name}")
    print()

    print("3. 前向计算（轨迹模拟）")

    sim_ticks = best.tick + 5

    start_time = time.perf_counter()

    trace = calculate_pearl_trace(
        cannon,
        best.red,
        best.blue,
        best.vertical,
        best.direction,
        sim_ticks,
        [],
        PearlVersion.Post1212
    )

    elapsed = time.perf_counter() - start_time
    print(f"   耗时: {elapsed * 1000:.2f} ms")
    print(f"   模拟刻度: {sim_ticks}")
    print()

    if trace is None:
        print("   结果: 模拟失败")
        return

    print("   计算结果:")
    print(f"     轨迹点数: {best.tick}")
    print(
        f"     着陆位置:  ({trace.pearl_trace[best.tick].x:.4f}, {trace.pearl_trace[best.tick].y:.4f}, {trace.pearl_trace[best.tick].z:.4f})")
    print()

    print("   珍珠轨迹（pearl_trace）:")
    print("   刻度        X            Y            Z")
    print("   " + "-" * 48)

    for tick in range(len(trace.pearl_trace)):
        pos = trace.pearl_trace[tick]
        print(f"   {tick:>4}  {pos.x:>12.4f}  {pos.y:>10.4f}  {pos.z:>12.4f}")

    print()

    if best.tick < len(trace.pearl_trace):
        pos = trace.pearl_trace[best.tick]
        dx = pos.x - destination.x
        dz = pos.z - destination.z
        dist_2d = (dx * dx + dz * dz) ** 0.5
        print(f"   第 {best.tick} 刻度的验证:")
        print(f"     位置: ({pos.x:.4f}, {pos.y:.4f}, {pos.z:.4f})")
        print(f"     到目标的2D距离: {dist_2d:.4f} 方块")

    print("\n=---= 示例完成 =---=")


if __name__ == "__main__":
    main()