# -*- coding: utf-8 -*-
import os
import glob
import sys
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

try:
    from IPython.display import display
except Exception:
    display = print

SAVE_FIGURES = True
GRAPH_DIR = Path("sunphil_final_3graphs_v2")
GRAPH_DPI = 150


def _is_colab():
    try:
        import google.colab  # noqa: F401
        return True
    except Exception:
        return False


def maybe_upload_required_files():
    if not _is_colab():
        return
    search_dirs = [Path("/content"), Path.cwd()]
    has_zip = any(glob.glob(str(d / "*2020~2025 서울특별시 교통량 정제 데이터*.zip")) for d in search_dirs)
    has_base = any((d / "project_base.py").exists() for d in search_dirs)
    if not (has_zip and has_base):
        from google.colab import files
        print("필수 파일을 업로드하세요.")
        print(" - 2020~2025 서울특별시 교통량 정제 데이터.zip")
        print(" - project_base.py")
        files.upload()


def setup_paths():
    maybe_upload_required_files()
    for p in ["/content", os.getcwd()]:
        if p not in sys.path:
            sys.path.append(p)
    if Path("/content").exists():
        return "/content"
    return os.getcwd()


def set_korean_font():
    candidates = [
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    font_path = next((p for p in candidates if os.path.exists(p)), None)
    if font_path is None and _is_colab():
        subprocess.run(["apt-get", "-qq", "update"], check=False)
        subprocess.run(["apt-get", "-qq", "install", "-y", "fonts-nanum"], check=False)
        font_path = next((p for p in candidates if os.path.exists(p)), None)
    if font_path:
        fm.fontManager.addfont(font_path)
        font_name = fm.FontProperties(fname=font_path).get_name()
        plt.rc("font", family=font_name)
    else:
        plt.rc("font", family="DejaVu Sans")
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 120


def save_and_show(filename):
    plt.tight_layout()
    if SAVE_FIGURES:
        GRAPH_DIR.mkdir(parents=True, exist_ok=True)
        out_path = GRAPH_DIR / filename
        plt.savefig(out_path, dpi=GRAPH_DPI, bbox_inches="tight")
        print(f"그래프 저장: {out_path}")
    plt.show()
    plt.close()


def load_base_result():
    search_dir = setup_paths()
    set_korean_font()
    import project_base
    return project_base.run_base_pipeline(search_dir=search_dir)


def display_table(title, df):
    print(f"\n[{title}]")
    display(df)


def _numeric_values(values):
    arr = pd.Series(np.ravel(values)).dropna().astype(float)
    arr = arr[np.isfinite(arr)]
    return arr


def _format_number_axis(ax, axis="y"):
    try:
        from matplotlib.ticker import FuncFormatter
        formatter = FuncFormatter(lambda x, pos: f"{x:,.0f}")
        if axis == "y":
            ax.yaxis.set_major_formatter(formatter)
        else:
            ax.xaxis.set_major_formatter(formatter)
    except Exception:
        pass


def apply_zoom_y(ax, values, lower_margin=0.35, upper_margin=0.65):
    arr = _numeric_values(values)
    if len(arr) == 0:
        return
    vmin = float(arr.min())
    vmax = float(arr.max())
    spread = vmax - vmin
    if spread <= 0:
        spread = max(abs(vmax) * 0.03, 1.0)
    y_min = vmin - spread * lower_margin
    y_max = vmax + spread * upper_margin
    if vmin >= 0:
        y_min = max(0, y_min)
    if y_max <= y_min:
        y_max = y_min + spread
    ax.set_ylim(y_min, y_max)
    _format_number_axis(ax, "y")


from project_base import train_regression_model, predict_regression

START_YEAR = 2026
END_YEAR = 2030
QUARTER_ORDER = ["1분기", "2분기", "3분기", "4분기"]
QUARTER_COLOR_MAP = {
    "1분기": "#1f77b4",
    "2분기": "#ff7f0e",
    "3분기": "#2ca02c",
    "4분기": "#d62728",
}


def make_quarter_train_data(common_hour):
    return (
        common_hour.groupby(["year", "quarter", "spot_num", "road_type", "io_type", "io_name"], as_index=False, observed=True)["vol_hour_avg"]
        .mean()
        .rename(columns={"vol_hour_avg": "quarter_avg_vol"})
    )


def make_quarter_input(target_year, station_latest):
    spots = station_latest[["spot_num", "road_type"]].drop_duplicates().copy()
    rows = []
    for _, spot in spots.iterrows():
        for quarter in range(1, 5):
            for io_type, io_name in [(1, "유입"), (2, "유출")]:
                rows.append({
                    "year": target_year,
                    "quarter": quarter,
                    "spot_num": spot["spot_num"],
                    "road_type": spot["road_type"],
                    "io_type": io_type,
                    "io_name": io_name,
                })
    return pd.DataFrame(rows)


def predict_quarter_average(target_year, station_latest, quarter_model):
    future = make_quarter_input(target_year, station_latest)
    future["pred_quarter_avg_vol"] = predict_regression(quarter_model, future)
    result = future.groupby("quarter", as_index=False)["pred_quarter_avg_vol"].mean()
    result["year"] = target_year
    result["quarter_name"] = result["quarter"].astype(str) + "분기"
    result["pred_quarter_avg_vol"] = result["pred_quarter_avg_vol"].round(2)
    return result[["year", "quarter", "quarter_name", "pred_quarter_avg_vol"]]


def build_quarter_result(base_result):
    quarter_train = make_quarter_train_data(base_result["common_hour"])
    quarter_model = train_regression_model(
        quarter_train,
        "quarter_avg_vol",
        ["quarter", "spot_num", "road_type", "io_type"],
        valid_year=2025,
    )
    parts = [predict_quarter_average(year, base_result["station_latest"], quarter_model) for year in range(START_YEAR, END_YEAR + 1)]
    return pd.concat(parts, ignore_index=True)


def make_pivot(all_result):
    return all_result.pivot(index="year", columns="quarter_name", values="pred_quarter_avg_vol").reindex(columns=QUARTER_ORDER)


def plot_quarter_grouped_bar(all_result):
    pivot = make_pivot(all_result)
    ax = pivot.plot(kind="bar", figsize=(11, 6), width=0.78, color=[QUARTER_COLOR_MAP[q] for q in pivot.columns])
    ax.set_title("2026~2030년 분기별 평균 교통량 예측")
    ax.set_xlabel("연도")
    ax.set_ylabel("예상 평균 교통량")
    ax.tick_params(axis="x", rotation=0)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(title="분기")
    apply_zoom_y(ax, pivot.values)
    for container in ax.containers:
        ax.bar_label(container, fmt="%.0f", padding=2, fontsize=8)
    save_and_show("선필_01_분기별_평균_교통량_예측.png")


def plot_quarter_heatmap(all_result):
    pivot = make_pivot(all_result)
    data = pivot.values.astype(float)
    plt.figure(figsize=(8.8, 5.2))
    im = plt.imshow(data, aspect="auto")
    plt.colorbar(im, label="예상 평균 교통량")
    plt.xticks(np.arange(len(pivot.columns)), pivot.columns)
    plt.yticks(np.arange(len(pivot.index)), pivot.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            plt.text(j, i, f"{data[i, j]:,.0f}", ha="center", va="center", fontsize=9)
    plt.title("2026~2030 연도×분기 평균 교통량 히트맵")
    plt.xlabel("분기")
    plt.ylabel("연도")
    save_and_show("선필_02_연도_분기_히트맵.png")


def plot_quarter_grouped_by_quarter(all_result):
    pivot = make_pivot(all_result)
    years = list(pivot.index)
    n_years = len(years)
    group_gap = 1.3
    bar_width = 0.72

    fig, ax = plt.subplots(figsize=(14, 6.8))

    xtick_positions = []
    xtick_labels = []
    group_centers = []

    all_values = []
    for q_idx, quarter_name in enumerate(QUARTER_ORDER):
        color = QUARTER_COLOR_MAP[quarter_name]
        values = pivot[quarter_name].values
        all_values.extend(values.tolist())

        base = q_idx * (n_years + group_gap)
        positions = base + np.arange(n_years)
        bars = ax.bar(positions, values, width=bar_width, color=color, alpha=0.88)
        ax.plot(positions, values, marker="o", linewidth=2.2, color=color)

        for x, y in zip(positions, values):
            ax.text(x, y, f"{y:,.0f}", ha="center", va="bottom", fontsize=8)

        xtick_positions.extend(positions)
        xtick_labels.extend([f"{year}년" for year in years])
        group_centers.append(positions.mean())

        if q_idx < len(QUARTER_ORDER) - 1:
            sep_x = base + n_years - 0.5 + group_gap / 2
            ax.axvline(sep_x, color="lightgray", linewidth=1, linestyle="--", alpha=0.8)

    ax.set_title("2026~2030년 분기별 예상 평균 교통량 비교", fontsize=14, fontweight="bold")
    ax.set_xlabel("연도")
    ax.set_ylabel("예상 평균 교통량")
    ax.set_xticks(xtick_positions)
    ax.set_xticklabels(xtick_labels, rotation=0)
    ax.grid(axis="y", alpha=0.3)
    apply_zoom_y(ax, all_values)

    y_min, y_max = ax.get_ylim()
    quarter_label_y = y_min - (y_max - y_min) * 0.12
    for center, quarter_name in zip(group_centers, QUARTER_ORDER):
        ax.text(center, quarter_label_y, quarter_name, ha="center", va="top", fontsize=11, fontweight="bold", color=QUARTER_COLOR_MAP[quarter_name], clip_on=False)

    from matplotlib.patches import Patch
    legend_handles = [Patch(facecolor=QUARTER_COLOR_MAP[q], label=q) for q in QUARTER_ORDER]
    ax.legend(handles=legend_handles, title="분기", loc="upper left")

    plt.subplots_adjust(bottom=0.2)
    save_and_show("선필_03_분기기준_연도비교_통합.png")


def main():
    base_result = load_base_result()
    all_result = build_quarter_result(base_result)
    summary = make_pivot(all_result).reset_index().round(2)
    display_table("2026~2030 분기별 평균 교통량 예측표", summary)
    plot_quarter_grouped_bar(all_result)
    plot_quarter_heatmap(all_result)
    plot_quarter_grouped_by_quarter(all_result)


if __name__ == "__main__":
    main()
