# 标准普通颜色 (已补充)
MESSAGE_COLOR_BLACK = 30    # 黑色
MESSAGE_COLOR_RED = 31      # 红色
MESSAGE_COLOR_GREEN = 32    # 绿色
MESSAGE_COLOR_YELLOW = 33   # 黄色
MESSAGE_COLOR_BLUE = 34     # 蓝色
MESSAGE_COLOR_PURPLE = 35   # 紫色
MESSAGE_COLOR_CYAN = 36     # 青色（青绿色）
MESSAGE_COLOR_WHITE = 37    # 白色

# 高亮颜色 (90-97)
MESSAGE_COLOR_BRIGHT_BLACK = 90    # 亮黑色（灰色）
MESSAGE_COLOR_BRIGHT_RED = 91      # 亮红色
MESSAGE_COLOR_BRIGHT_GREEN = 92    # 亮绿色
MESSAGE_COLOR_BRIGHT_YELLOW = 93   # 亮黄色
MESSAGE_COLOR_BRIGHT_BLUE = 94     # 亮蓝色
MESSAGE_COLOR_BRIGHT_PURPLE = 95   # 亮紫色
MESSAGE_COLOR_BRIGHT_CYAN = 96     # 亮青色
MESSAGE_COLOR_BRIGHT_WHITE = 97    # 亮白色

# 256 色常用扩展 (38;5;XX)（以下是常见色）
MESSAGE_COLOR_ORANGE = 202          # 橙色
MESSAGE_COLOR_PINK = 200            # 粉色
MESSAGE_COLOR_LIGHT_GREEN = 120     # 浅绿色
MESSAGE_COLOR_LIGHT_BLUE = 81       # 浅蓝色
MESSAGE_COLOR_LIGHT_PURPLE = 183    # 浅紫色
MESSAGE_COLOR_TURQUOISE = 45        # 青绿色
MESSAGE_COLOR_GOLD = 214            # 金色
MESSAGE_COLOR_GRAY = 244            # 灰色
MESSAGE_COLOR_LIGHT_GRAY = 250      # 浅灰色
MESSAGE_COLOR_DARK_RED = 52         # 深红色
MESSAGE_COLOR_DARK_GREEN = 22       # 深绿色
MESSAGE_COLOR_DARK_BLUE = 18        # 深蓝色

ANSI_COLOR_MAP = {
    30: "black",               # 标准普通颜色
    31: "red",
    32: "green",
    33: "yellow",
    34: "blue",
    35: "purple",
    36: "cyan",
    37: "white",
    90: "bright_black",        # 高亮颜色
    91: "bright_red",
    92: "bright_green",
    93: "bright_yellow",
    94: "bright_blue",
    95: "bright_purple",
    96: "bright_cyan",
    97: "bright_white",
    202: "orange",             # 256 色常用扩展
    200: "pink",
    120: "light_green",
    81: "light_blue",
    183: "light_purple",
    45: "turquoise",
    214: "gold",
    244: "gray",
    250: "light_gray",
    52: "dark_red",
    22: "dark_green",
    18: "dark_blue",
}