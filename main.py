#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
字体多重变形工具（链式变换版本）
================================
功能：
    - 读取一个 TTF/OTF 字体
    - 遍历所有字形，按顺序执行多个几何变形
    - 支持模式：缩放+旋转、倾斜、波浪、旋涡、像素化
    - 参数有安全范围限制，避免极端变形导致字形丢失
    - 可灵活定义“变形链”，一次处理多种效果

依赖：
    pip install fonttools

使用示例：
    # 先旋涡（强度 0.003），再波浪（幅度 20，频率 0.05）
    python font_transformer_chain.py
"""

import math
from fontTools.ttLib import TTFont


# ======== 基础几何变形函数 ========

def transform_scale_rotate(coords, sx=1.0, sy=1.0, angle_deg=0, center_x=0, center_y=0):
    """缩放 + 旋转"""
    angle = math.radians(angle_deg)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    new_coords = []
    for x, y in coords:
        # 平移到中心
        x -= center_x
        y -= center_y
        # 缩放
        x *= sx
        y *= sy
        # 旋转
        x_new = x * cos_a - y * sin_a
        y_new = x * sin_a + y * cos_a
        # 平移回去
        x_new += center_x
        y_new += center_y
        new_coords.append((int(x_new), int(y_new)))
    return new_coords


def shear(coords, shx=0.2, shy=0.0):
    """倾斜（斜切变形）"""
    return [(int(x + shx * y), int(y + shy * x)) for x, y in coords]


def wave(coords, amp=30, freq=0.05):
    """波浪形（沿 X 方向正弦变形）"""
    return [(x, int(y + amp * math.sin(x * freq))) for x, y in coords]


def swirl(coords, center_x=0, center_y=0, strength=0.005):
    """旋涡扭曲（距离中心越远，旋转角度越大）"""
    new_coords = []
    for x, y in coords:
        dx = x - center_x
        dy = y - center_y
        r = math.sqrt(dx ** 2 + dy ** 2)
        angle = strength * r  # 半径越大，旋转越多
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        x_new = dx * cos_a - dy * sin_a + center_x
        y_new = dx * sin_a + dy * cos_a + center_y
        new_coords.append((int(x_new), int(y_new)))
    return new_coords


def pixelate(coords, step=10):
    """像素化（将坐标吸附到最近的网格点）"""
    return [(int(round(x / step) * step), int(round(y / step) * step)) for x, y in coords]


# ======== 安全参数检查 ========

def clamp(value, min_val, max_val, name=""):
    """限制参数在安全范围内"""
    if value < min_val:
        print(f"[警告] {name}={value} 太小，已调整为 {min_val}")
        return min_val
    elif value > max_val:
        print(f"[警告] {name}={value} 太大，已调整为 {max_val}")
        return max_val
    return value


def validate_params(params):
    """检查并修正参数范围"""
    limits = {
        "sx": (0.5, 2.0),
        "sy": (0.5, 2.0),
        "angle": (-45, 45),
        "shx": (-1.0, 1.0),
        "shy": (-1.0, 1.0),
        "amp": (5, 200),
        "freq": (0.01, 0.2),
        "strength": (0.0005, 0.02),
        "step": (2, 100)
    }
    safe_params = {}
    for key, val in params.items():
        if key in limits:
            min_val, max_val = limits[key]
            safe_params[key] = clamp(val, min_val, max_val, key)
        else:
            safe_params[key] = val
    return safe_params


# ======== 主处理函数（支持多重变形链） ========

def process_font_chain(input_path, output_path, transform_chain):
    """
    处理字体并应用多重变形链
    transform_chain: 列表，每个元素是 (mode, 参数字典)
                     例如：[("swirl", {...}), ("wave", {...})]
    """
    font = TTFont(input_path)
    glyf = font["glyf"]

    # 获取字体边界中心点（用于旋涡、旋转等）
    head_table = font["head"]
    center_x = (head_table.xMin + head_table.xMax) / 2
    center_y = (head_table.yMin + head_table.yMax) / 2

    for glyph_name in glyf.keys():
        glyph = glyf[glyph_name]
        if glyph.isComposite():
            continue
        if not hasattr(glyph, "coordinates"):
            continue

        coords = glyph.coordinates

        # 按顺序执行变形链
        for mode, raw_params in transform_chain:
            params = validate_params(raw_params)
            if mode == "scale_rotate":
                coords[:] = transform_scale_rotate(coords,
                                                   sx=params.get("sx", 1.0),
                                                   sy=params.get("sy", 1.0),
                                                   angle_deg=params.get("angle", 0),
                                                   center_x=center_x,
                                                   center_y=center_y)
            elif mode == "shear":
                coords[:] = shear(coords,
                                  shx=params.get("shx", 0.2),
                                  shy=params.get("shy", 0.0))
            elif mode == "wave":
                coords[:] = wave(coords,
                                 amp=params.get("amp", 30),
                                 freq=params.get("freq", 0.05))
            elif mode == "swirl":
                coords[:] = swirl(coords,
                                  center_x=center_x,
                                  center_y=center_y,
                                  strength=params.get("strength", 0.005))
            elif mode == "pixelate":
                coords[:] = pixelate(coords,
                                     step=params.get("step", 10))
            else:
                print(f"未知模式: {mode}")

    font.save(output_path)
    print(f"✅ 变形完成，新字体已保存到 {output_path}")


# ======== 配置入口 ========

if __name__ == "__main__":
    # 输入 / 输出字体
    input_font = "Roboto-Regular.ttf"
    output_font = "modified_chain.ttf"

    # 变形链定义（按顺序执行）
    transform_chain = [
        ("swirl", {"strength": 0.003}),           # 先旋涡
        ("wave", {"amp": 25, "freq": 0.04}),      # 再波浪
        ("pixelate", {"step": 12}),               # 最后像素化
    ]

    # transform_chain = [
    #     ("scale_rotate", {"sx": 1.1, "sy": 0.85, "angle": 8}),
    #     ("swirl", {"strength": 0.005}),
    #     ("wave", {"amp": 30, "freq": 0.06}),
    # ]

    # 运行处理
    process_font_chain(input_font, output_font, transform_chain)