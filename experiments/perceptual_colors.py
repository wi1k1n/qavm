import math
import random
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QApplication, QGridLayout, QLabel, QMainWindow, QWidget


COLOR_COUNT = 50


def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    if c <= 0.0031308:
        c = 12.92 * c
    else:
        c = 1.055 * (c ** (1.0 / 2.4)) - 0.055
    return round(max(0.0, min(1.0, c)) * 255)


def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def rgb_to_oklab(rgb):
    r, g, b = [srgb_to_linear(c) for c in rgb]

    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l_, m_, s_ = math.cbrt(l), math.cbrt(m), math.cbrt(s)

    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklch_to_rgb(lightness, chroma, hue_degrees):
    hue = math.radians(hue_degrees)
    a = chroma * math.cos(hue)
    b = chroma * math.sin(hue)

    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b

    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3

    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    if not all(0.0 <= channel <= 1.0 for channel in (r, g, b)):
        return None

    return linear_to_srgb(r), linear_to_srgb(g), linear_to_srgb(b)


def oklab_distance(c1, c2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def generate_candidate_colors():
    candidates = []

    lightness_values = [0.66, 0.72, 0.78, 0.84]
    chroma_values = [0.10, 0.13, 0.16]

    for lightness in lightness_values:
        for chroma in chroma_values:
            for hue in range(0, 360, 4):
                rgb = oklch_to_rgb(lightness, chroma, hue)
                if rgb is not None:
                    candidates.append(rgb)

    return candidates


def generate_distinguishable_colors(count):
    candidates = generate_candidate_colors()
    if count <= 0:
        return []

    colors = [random.choice(candidates)]
    candidate_oklab = {rgb: rgb_to_oklab(rgb) for rgb in candidates}

    while len(colors) < count:
        chosen_oklab = [candidate_oklab[rgb] for rgb in colors]

        best_rgb = max(
            candidates,
            key=lambda rgb: min(
                oklab_distance(candidate_oklab[rgb], existing)
                for existing in chosen_oklab
            ),
        )

        colors.append(best_rgb)
        candidates.remove(best_rgb)

    return colors


def readable_text_color(rgb):
    color = QColor(*rgb)
    luminance = (
        0.2126 * srgb_to_linear(color.red())
        + 0.7152 * srgb_to_linear(color.green())
        + 0.0722 * srgb_to_linear(color.blue())
    )
    return "#111111" if luminance > 0.55 else "#FFFFFF"


class BubbleLabel(QLabel):
    def __init__(self, index, rgb):
        super().__init__(f"{index}\n{rgb_to_hex(rgb)}")
        text_color = readable_text_color(rgb)
        bg_color = rgb_to_hex(rgb)

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(112, 112)
        self.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 56px;
                border: 2px solid rgba(0, 0, 0, 45);
            }}
            """
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{COLOR_COUNT} distinguishable bubble colors")

        root = QWidget()
        layout = QGridLayout(root)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        colors = generate_distinguishable_colors(COLOR_COUNT)
        columns = math.ceil(math.sqrt(COLOR_COUNT))

        for i, rgb in enumerate(colors, start=1):
            row = (i - 1) // columns
            column = (i - 1) % columns
            layout.addWidget(BubbleLabel(i, rgb), row, column)

        self.setCentralWidget(root)
        self.resize(760, 650)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()