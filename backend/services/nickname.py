import random

ADJECTIVES = [
    "夜半", "雷霆", "风暴", "沉睡", "悠扬", "轰鸣",
    "温柔", "狂暴", "银河", "深海", "山谷", "云端",
    "午夜", "闪电", "摇滚", "蒸汽", "极光", "宇宙",
]

NOUNS = [
    "鼓手", "之息", "号角", "雷鸣", "微风", "发动机",
    "低音炮", "协奏曲", "交响乐", "独奏者", "节拍器",
    "拖拉机", "轰炸机", "小夜曲", "贝斯手", "电钻",
]


def generate_nickname() -> str:
    return random.choice(ADJECTIVES) + random.choice(NOUNS)
