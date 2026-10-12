"""Combine the two experiment photos and graph on one portrait A4 PDF page."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image


BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "电光效应实验图片-A4竖版.pdf"
URL = "https://github.com/Sherlock-ccf/HNU-physical-experiment"
PHOTO_1 = BASE / "1.jpg"
PHOTO_2 = BASE / "2.jpg"
PLOT = BASE / "电压-输出功率曲线.png"
FONT = Path("C:/Windows/Fonts/simhei.ttf")


def image_panel(fig, path: Path, box: tuple[float, float, float, float]):
    ax = fig.add_axes(box)
    with Image.open(path) as source:
        ax.imshow(source.convert("RGB"))
    ax.set_axis_off()
    return ax


def main() -> None:
    for path in (PHOTO_1, PHOTO_2, PLOT, FONT):
        if not path.is_file():
            raise FileNotFoundError(path)

    font_manager.fontManager.addfont(str(FONT))
    font_name = font_manager.FontProperties(fname=str(FONT)).get_name()
    plt.rcParams["font.family"] = font_name
    plt.rcParams["pdf.fonttype"] = 42

    # A4 portrait, exactly 210 × 297 mm.
    fig = plt.figure(figsize=(210 / 25.4, 297 / 25.4), facecolor="white")
    fig.text(0.06, 0.963, "实验数据、报告已开源",
             ha="left", va="top", fontsize=15, color="#1f2933")
    link = fig.text(0.06, 0.931, URL, ha="left", va="top",
                    fontsize=9.3, color="#1f5a9b", family="DejaVu Sans")
    link.set_url(URL)
    fig.add_artist(plt.Line2D([0.06, 0.94], [0.905, 0.905],
                              transform=fig.transFigure,
                              color="#c8cfd6", linewidth=0.7))

    fig.text(0.06, 0.852, "实验照片 1", ha="left", fontsize=10,
             color="#56616e")
    fig.text(0.52, 0.852, "实验照片 2", ha="left", fontsize=10,
             color="#56616e")
    image_panel(fig, PHOTO_1, (0.06, 0.615, 0.42, 0.222))
    image_panel(fig, PHOTO_2, (0.52, 0.615, 0.42, 0.222))

    fig.text(0.06, 0.566, "电压与输出光功率的三角函数拟合",
             ha="left", fontsize=10, color="#56616e")
    image_panel(fig, PLOT, (0.06, 0.185, 0.88, 0.361))

    fig.savefig(OUTPUT, format="pdf", dpi=200,
                facecolor="white", bbox_inches=None, pad_inches=0)
    plt.close(fig)
    print(f"已生成：{OUTPUT.name}")


if __name__ == "__main__":
    main()
