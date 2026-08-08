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
GRAPH_DIR = Path("traffic_final_graphs_seoyoung_v5_only")
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


# ============================================================
# 시각화 보정
# - 교통량 값의 차이가 작아 막대/선이 일자로 보이는 그래프는 y축 또는 x축을 확대한다.
# - 축 범위만 조정하고 별도 문구는 표시하지 않는다.
# ============================================================

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


def apply_zoom_y(ax, values, lower_margin=0.35, upper_margin=0.65, note=None):
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


def apply_zoom_x(ax, values, lower_margin=0.35, upper_margin=0.90, note=None):
    arr = _numeric_values(values)
    if len(arr) == 0:
        return
    vmin = float(arr.min())
    vmax = float(arr.max())
    spread = vmax - vmin
    if spread <= 0:
        spread = max(abs(vmax) * 0.03, 1.0)
    x_min = vmin - spread * lower_margin
    x_max = vmax + spread * upper_margin
    if vmin >= 0:
        x_min = max(0, x_min)
    if x_max <= x_min:
        x_max = x_min + spread
    ax.set_xlim(x_min, x_max)
    _format_number_axis(ax, "x")


def add_vertical_labels(ax, bars, values, fmt="{:,.0f}", fontsize=9):
    y_min, y_max = ax.get_ylim()
    offset = (y_max - y_min) * 0.025
    for bar, value in zip(bars, values):
        value = float(value)
        va = "bottom" if value >= 0 else "top"
        y = value + offset if value >= 0 else value - offset
        ax.text(bar.get_x() + bar.get_width() / 2, y, fmt.format(value), ha="center", va=va, fontsize=fontsize)


def add_horizontal_labels(ax, bars, values, fmt="{:,.0f}", fontsize=9):
    x_min, x_max = ax.get_xlim()
    offset = (x_max - x_min) * 0.02
    for bar, value in zip(bars, values):
        value = float(value)
        ax.text(value + offset, bar.get_y() + bar.get_height() / 2, fmt.format(value), va="center", fontsize=fontsize)

# ============================================================
# 서영: 날짜별 교통량 TOP5 / LOW5 예측
# 최종 출력 그래프: 5개
# 1) 월별 평균 교통량 비교: 2020~2025 평균 vs 2026~2030 예상 평균
# 2) 요일별 평균 교통량 비교: 2020~2025 평균 vs 2026~2030 예상 평균
# 3) 2026~2030 연도별 TOP5 날짜
# 4) 2026~2030 연도별 LOW5 날짜
# 5) 2026~2030 TOP5 평균 / LOW5 평균 비교
# ============================================================

import project_base as pb

START_YEAR = 2026
END_YEAR = 2030
TOP_N = 5
REPRESENT_YEAR = 2030
WEEKDAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"]
WEEKDAY_ORDER_MAP = {name: i for i, name in enumerate(WEEKDAY_ORDER)}


def add_diff_columns(df, value_col, overall_avg, prefix):
    result = df.copy()
    result[f"{prefix}_diff"] = result[value_col] - overall_avg
    result[f"{prefix}_diff_pct"] = np.where(overall_avg == 0, 0, result[f"{prefix}_diff"] / overall_avg * 100)
    return result


def build_past_pattern(common_weekday):
    past = common_weekday.copy()
    past["vol_daily_avg"] = pd.to_numeric(past["vol_daily_avg"], errors="coerce")
    past = past.dropna(subset=["vol_daily_avg"])
    overall_avg = float(past["vol_daily_avg"].mean())
    month_avg = past.groupby("month", as_index=False).agg(month_past_avg=("vol_daily_avg", "mean")).sort_values("month")
    month_avg = add_diff_columns(month_avg, "month_past_avg", overall_avg, "month")
    weekday_avg = past.groupby(["weekday_code", "weekday_name"], as_index=False).agg(weekday_past_avg=("vol_daily_avg", "mean"))
    weekday_avg["weekday_order"] = weekday_avg["weekday_code"].map(WEEKDAY_ORDER_MAP)
    weekday_avg = weekday_avg.sort_values("weekday_order")
    weekday_avg = add_diff_columns(weekday_avg, "weekday_past_avg", overall_avg, "weekday")
    pattern_avg = past.groupby(["month", "weekday_code", "weekday_name"], as_index=False).agg(pattern_past_avg=("vol_daily_avg", "mean"))
    pattern_avg["weekday_order"] = pattern_avg["weekday_code"].map(WEEKDAY_ORDER_MAP)
    pattern_avg = pattern_avg.sort_values(["month", "weekday_order"])
    pattern_avg = add_diff_columns(pattern_avg, "pattern_past_avg", overall_avg, "pattern")
    high_pattern = pattern_avg.sort_values("pattern_past_avg", ascending=False).head(10).copy()
    low_pattern = pattern_avg.sort_values("pattern_past_avg", ascending=True).head(10).copy()
    return overall_avg, month_avg, weekday_avg, pattern_avg, high_pattern, low_pattern


def predict_one_year(target_year, base_result):
    future_input = pb.make_date_range_weekday_input(f"{target_year}-01-01", f"{target_year}-12-31", base_result["station_latest"])
    future_input["predicted_vol"] = pb.predict_regression(base_result["weekday_model"], future_input)
    daily = future_input.groupby(["ymd", "year", "month", "weekday_code", "weekday_name", "day_type"], as_index=False).agg(
        predicted_total=("predicted_vol", "sum"), predicted_avg=("predicted_vol", "mean")
    ).sort_values("ymd")
    daily = pb.add_congestion_label(daily, "predicted_total", "congestion_level")
    top = daily.sort_values("predicted_total", ascending=False).drop_duplicates(["month", "weekday_code"]).head(TOP_N).copy()
    low = daily.sort_values("predicted_total", ascending=True).drop_duplicates(["month", "weekday_code"]).head(TOP_N).copy()
    top["rank"] = range(1, len(top) + 1)
    low["rank"] = range(1, len(low) + 1)
    top["result_type"] = "TOP"
    low["result_type"] = "LOW"
    for df in [top, low]:
        df["date_label"] = pd.to_datetime(df["ymd"]).dt.strftime("%m.%d") + "\n" + df["weekday_name"]
    return daily, top, low


def predict_range(base_result):
    daily_by_year = {}
    top_parts = []
    low_parts = []
    for year in range(START_YEAR, END_YEAR + 1):
        daily, top, low = predict_one_year(year, base_result)
        daily_by_year[year] = daily
        top_parts.append(top)
        low_parts.append(low)
    return daily_by_year, pd.concat(top_parts, ignore_index=True), pd.concat(low_parts, ignore_index=True)


def plot_month_average(month_avg, overall_avg):
    values = month_avg["month_past_avg"].values
    ax = plt.figure(figsize=(10, 5)).gca()
    bars = ax.bar(month_avg["month"].astype(str), values)
    ax.axhline(overall_avg, linestyle="--", label="전체 평균")
    ax.set_title("2020~2025 과거 월별 평균 교통량")
    ax.set_xlabel("월")
    ax.set_ylabel("평균 일교통량")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    apply_zoom_y(ax, values)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, value, f"{value:,.0f}", ha="center", va="bottom", fontsize=8)
    save_and_show("서영_01_과거_월별_평균.png")


def plot_weekday_average(weekday_avg, overall_avg):
    plot_df = weekday_avg.sort_values("weekday_order")
    values = plot_df["weekday_past_avg"].values
    ax = plt.figure(figsize=(9, 5)).gca()
    bars = ax.bar(plot_df["weekday_name"], values)
    ax.axhline(overall_avg, linestyle="--", label="전체 평균")
    ax.set_title("2020~2025 과거 요일별 평균 교통량")
    ax.set_xlabel("요일")
    ax.set_ylabel("평균 일교통량")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    apply_zoom_y(ax, values)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, value, f"{value:,.0f}", ha="center", va="bottom", fontsize=8)
    save_and_show("서영_02_과거_요일별_평균.png")


def plot_pattern_bar(pattern_df, title, filename, ascending=False):
    plot_df = pattern_df.copy()
    plot_df["label"] = plot_df["month"].astype(str) + "월 " + plot_df["weekday_name"]
    plot_df = plot_df.sort_values("pattern_past_avg", ascending=ascending)
    ax = plt.figure(figsize=(11, 5)).gca()
    bars = ax.bar(plot_df["label"], plot_df["pattern_past_avg"])
    ax.set_title(title)
    ax.set_xlabel("월×요일")
    ax.set_ylabel("평균 일교통량")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)
    apply_zoom_y(ax, plot_df["pattern_past_avg"])
    for bar, value in zip(bars, plot_df["pattern_past_avg"]):
        ax.text(bar.get_x() + bar.get_width()/2, value, f"{value:,.0f}", ha="center", va="bottom", fontsize=8)
    save_and_show(filename)


def plot_represent_year_top_low(all_top, all_low):
    top = all_top[all_top["year"] == REPRESENT_YEAR].sort_values("predicted_total", ascending=True)
    low = all_low[all_low["year"] == REPRESENT_YEAR].sort_values("predicted_total", ascending=False)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    axes[0].barh(top["date_label"], top["predicted_total"])
    axes[0].set_title(f"{REPRESENT_YEAR}년 교통량 많은 날 TOP{TOP_N}")
    axes[0].set_xlabel("예상 전체 교통량")
    axes[0].grid(axis="x", alpha=0.3)
    apply_zoom_x(axes[0], top["predicted_total"])
    for y, value in enumerate(top["predicted_total"]):
        axes[0].text(value + (axes[0].get_xlim()[1] - axes[0].get_xlim()[0]) * 0.02, y, f"{value:,.0f}", va="center", fontsize=9)
    axes[1].barh(low["date_label"], low["predicted_total"])
    axes[1].set_title(f"{REPRESENT_YEAR}년 교통량 적은 날 LOW{TOP_N}")
    axes[1].set_xlabel("예상 전체 교통량")
    axes[1].grid(axis="x", alpha=0.3)
    apply_zoom_x(axes[1], low["predicted_total"])
    for y, value in enumerate(low["predicted_total"]):
        axes[1].text(value + (axes[1].get_xlim()[1] - axes[1].get_xlim()[0]) * 0.02, y, f"{value:,.0f}", va="center", fontsize=9)
    fig.suptitle("날짜별 예상 교통량 TOP5 / LOW5")
    save_and_show("서영_05_날짜별_TOP5_LOW5.png")


def plot_top_low_summary(all_top, all_low):
    top_summary = all_top.groupby("year", as_index=False)["predicted_total"].mean().rename(columns={"predicted_total": "top5_avg"})
    low_summary = all_low.groupby("year", as_index=False)["predicted_total"].mean().rename(columns={"predicted_total": "low5_avg"})
    summary = top_summary.merge(low_summary, on="year")
    ax = plt.figure(figsize=(10, 5)).gca()
    ax.plot(summary["year"], summary["top5_avg"], marker="o", linewidth=2, label="TOP5 평균")
    ax.plot(summary["year"], summary["low5_avg"], marker="o", linewidth=2, label="LOW5 평균")
    ax.set_title("2026~2030 TOP5 평균 / LOW5 평균 교통량")
    ax.set_xlabel("연도")
    ax.set_ylabel("예상 전체 교통량")
    ax.set_xticks(summary["year"])
    ax.grid(True, linestyle="--", alpha=0.4)
    apply_zoom_y(ax, summary[["top5_avg", "low5_avg"]].values)
    ax.legend()
    for _, row in summary.iterrows():
        ax.text(row["year"], row["top5_avg"], f"{row['top5_avg']:,.0f}", ha="center", va="bottom", fontsize=9)
        ax.text(row["year"], row["low5_avg"], f"{row['low5_avg']:,.0f}", ha="center", va="top", fontsize=9)
    save_and_show("서영_06_TOP5_LOW5_평균_추이.png")



def build_future_summary(daily_by_year):
    all_daily = pd.concat(daily_by_year.values(), ignore_index=True).copy()
    month_summary = (
        all_daily.groupby(["year", "month"], as_index=False)["predicted_total"]
        .mean().rename(columns={"predicted_total": "month_pred_avg"})
    )
    weekday_summary = (
        all_daily.groupby(["year", "weekday_code", "weekday_name"], as_index=False)["predicted_total"]
        .mean().rename(columns={"predicted_total": "weekday_pred_avg"})
    )
    weekday_summary["weekday_order"] = weekday_summary["weekday_code"].map(WEEKDAY_ORDER_MAP)
    return all_daily, month_summary, weekday_summary


def build_compare_tables(month_avg, weekday_avg, all_daily):
    """과거 평균과 미래 예상 평균을 같은 기준으로 비교할 표를 만든다.
    과거는 common_weekday의 vol_daily_avg 평균이고,
    미래는 날짜별 예측을 만들 때 사용한 predicted_avg 평균을 사용한다.
    """
    future_month = (
        all_daily.groupby("month", as_index=False)["predicted_avg"]
        .mean().rename(columns={"predicted_avg": "month_future_avg"})
        .sort_values("month")
    )
    future_weekday = (
        all_daily.groupby(["weekday_code", "weekday_name"], as_index=False)["predicted_avg"]
        .mean().rename(columns={"predicted_avg": "weekday_future_avg"})
    )
    future_weekday["weekday_order"] = future_weekday["weekday_code"].map(WEEKDAY_ORDER_MAP)
    future_weekday = future_weekday.sort_values("weekday_order")

    month_compare = (
        month_avg[["month", "month_past_avg"]]
        .merge(future_month, on="month", how="left")
        .sort_values("month")
    )
    weekday_compare = (
        weekday_avg[["weekday_code", "weekday_name", "weekday_order", "weekday_past_avg"]]
        .merge(future_weekday[["weekday_code", "weekday_future_avg"]], on="weekday_code", how="left")
        .sort_values("weekday_order")
    )
    return month_compare, weekday_compare


def plot_month_average_compare(month_compare):
    x = np.arange(len(month_compare))
    width = 0.38
    fig, ax = plt.subplots(figsize=(12, 5.8))
    bars1 = ax.bar(x - width / 2, month_compare["month_past_avg"], width=width, label="2020~2025 평균")
    bars2 = ax.bar(x + width / 2, month_compare["month_future_avg"], width=width, label="2026~2030 예상 평균")
    ax.set_title("월별 평균 교통량 비교: 과거 평균 vs 미래 예상")
    ax.set_xlabel("월")
    ax.set_ylabel("평균 일교통량")
    ax.set_xticks(x)
    ax.set_xticklabels(month_compare["month"].astype(str) + "월")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    apply_zoom_y(ax, month_compare[["month_past_avg", "month_future_avg"]].values)
    add_vertical_labels(ax, bars1, month_compare["month_past_avg"], fontsize=7)
    add_vertical_labels(ax, bars2, month_compare["month_future_avg"], fontsize=7)
    save_and_show("서영_01_월별_과거미래_평균비교.png")


def plot_weekday_average_compare(weekday_compare):
    x = np.arange(len(weekday_compare))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    bars1 = ax.bar(x - width / 2, weekday_compare["weekday_past_avg"], width=width, label="2020~2025 평균")
    bars2 = ax.bar(x + width / 2, weekday_compare["weekday_future_avg"], width=width, label="2026~2030 예상 평균")
    ax.set_title("요일별 평균 교통량 비교: 과거 평균 vs 미래 예상")
    ax.set_xlabel("요일")
    ax.set_ylabel("평균 일교통량")
    ax.set_xticks(x)
    ax.set_xticklabels(weekday_compare["weekday_name"])
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    apply_zoom_y(ax, weekday_compare[["weekday_past_avg", "weekday_future_avg"]].values)
    add_vertical_labels(ax, bars1, weekday_compare["weekday_past_avg"], fontsize=8)
    add_vertical_labels(ax, bars2, weekday_compare["weekday_future_avg"], fontsize=8)
    save_and_show("서영_02_요일별_과거미래_평균비교.png")


def plot_all_year_top_dates(all_top):
    fig, axes = plt.subplots(5, 1, figsize=(12.5, 14.5))
    for ax, year in zip(axes, range(START_YEAR, END_YEAR + 1)):
        df = all_top[all_top["year"] == year].sort_values("predicted_total", ascending=True)
        values = df["predicted_total"].values
        bars = ax.barh(df["date_label"], values)
        ax.set_title(f"{year}년 교통량 많은 날 TOP{TOP_N}")
        ax.grid(axis="x", alpha=0.25)
        apply_zoom_x(ax, values)
        add_horizontal_labels(ax, bars, values, fontsize=8)
    axes[-1].set_xlabel("예상 전체 교통량")
    fig.suptitle("2026~2030 연도별 TOP5 교통량 날짜", fontsize=16, y=1.005)
    save_and_show("서영_03_2026_2030_TOP5_날짜.png")


def plot_all_year_low_dates(all_low):
    fig, axes = plt.subplots(5, 1, figsize=(12.5, 14.5))
    for ax, year in zip(axes, range(START_YEAR, END_YEAR + 1)):
        df = all_low[all_low["year"] == year].sort_values("predicted_total", ascending=False)
        values = df["predicted_total"].values
        bars = ax.barh(df["date_label"], values)
        ax.set_title(f"{year}년 교통량 적은 날 LOW{TOP_N}")
        ax.grid(axis="x", alpha=0.25)
        apply_zoom_x(ax, values)
        add_horizontal_labels(ax, bars, values, fontsize=8)
    axes[-1].set_xlabel("예상 전체 교통량")
    fig.suptitle("2026~2030 연도별 LOW5 교통량 날짜", fontsize=16, y=1.005)
    save_and_show("서영_04_2026_2030_LOW5_날짜.png")


def build_top_low_summary(all_top, all_low):
    top_summary = (
        all_top.groupby("year", as_index=False)["predicted_avg"]
        .mean().rename(columns={"predicted_avg": "top5_avg"})
    )
    low_summary = (
        all_low.groupby("year", as_index=False)["predicted_avg"]
        .mean().rename(columns={"predicted_avg": "low5_avg"})
    )
    summary = top_summary.merge(low_summary, on="year")
    summary["gap"] = summary["top5_avg"] - summary["low5_avg"]
    return summary


def plot_top_low_average_compare(summary):
    x = np.arange(len(summary))
    width = 0.36
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    bars1 = ax.bar(x - width / 2, summary["top5_avg"], width=width, label="TOP5 평균")
    bars2 = ax.bar(x + width / 2, summary["low5_avg"], width=width, label="LOW5 평균")
    ax.set_title("2026~2030 TOP5 vs LOW5 연평균 비교")
    ax.set_xlabel("연도")
    ax.set_ylabel("예상 일평균 교통량")
    ax.set_xticks(x)
    ax.set_xticklabels(summary["year"].astype(str) + "년")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    apply_zoom_y(ax, summary[["top5_avg", "low5_avg"]].values)
    add_vertical_labels(ax, bars1, summary["top5_avg"], fontsize=8)
    add_vertical_labels(ax, bars2, summary["low5_avg"], fontsize=8)
    save_and_show("서영_05_TOP5_LOW5_연평균_비교.png")


def plot_top_low_gap(summary):
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    bars = ax.bar(summary["year"].astype(str) + "년", summary["gap"])
    ax.set_title("2026~2030 TOP5-LOW5 연평균 격차")
    ax.set_xlabel("연도")
    ax.set_ylabel("격차")
    ax.grid(axis="y", alpha=0.3)
    apply_zoom_y(ax, summary["gap"].values)
    add_vertical_labels(ax, bars, summary["gap"], fontsize=9)
    save_and_show("서영_06_TOP5_LOW5_연평균_격차.png")


def plot_future_month_heatmap(month_summary):
    pivot = month_summary.pivot(index="year", columns="month", values="month_pred_avg").sort_index()
    data = pivot.values.astype(float)
    plt.figure(figsize=(11.5, 5.2))
    im = plt.imshow(data, aspect="auto")
    plt.colorbar(im, label="예상 일평균 교통량")
    plt.xticks(np.arange(len(pivot.columns)), [f"{m}월" for m in pivot.columns])
    plt.yticks(np.arange(len(pivot.index)), pivot.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            plt.text(j, i, f"{data[i, j]/1000:.0f}k", ha="center", va="center", fontsize=8)
    plt.title("2026~2030 월별 예상 교통량 히트맵")
    plt.xlabel("월")
    plt.ylabel("연도")
    save_and_show("서영_03_미래_월별_히트맵.png")


def plot_future_weekday_heatmap(weekday_summary):
    pivot = weekday_summary.pivot(index="year", columns="weekday_code", values="weekday_pred_avg").reindex(columns=WEEKDAY_ORDER).sort_index()
    data = pivot.values.astype(float)
    plt.figure(figsize=(9.5, 5.2))
    im = plt.imshow(data, aspect="auto")
    plt.colorbar(im, label="예상 일평균 교통량")
    plt.xticks(np.arange(len(pivot.columns)), pivot.columns)
    plt.yticks(np.arange(len(pivot.index)), pivot.index)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            plt.text(j, i, f"{data[i, j]/1000:.0f}k", ha="center", va="center", fontsize=8)
    plt.title("2026~2030 요일별 예상 교통량 히트맵")
    plt.xlabel("요일")
    plt.ylabel("연도")
    save_and_show("서영_04_미래_요일별_히트맵.png")


def plot_future_month_line(month_summary):
    ax = plt.figure(figsize=(11, 5.5)).gca()
    for year, group in month_summary.groupby("year"):
        group = group.sort_values("month")
        ax.plot(group["month"], group["month_pred_avg"], marker="o", linewidth=2, label=str(year))
    ax.set_title("2026~2030 월별 예상 교통량 추이")
    ax.set_xlabel("월")
    ax.set_ylabel("예상 일평균 교통량")
    ax.set_xticks(range(1, 13))
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend(title="연도", ncol=3)
    apply_zoom_y(ax, month_summary["month_pred_avg"].values)
    save_and_show("서영_05_미래_월별_추이.png")


def plot_future_month_bar_by_year(month_summary, year, seq):
    """한 연도 안의 1~12월 예상 교통량을 별도 큰 그래프로 본다.
    2026~2030을 한 선그래프에 겹쳐 그렸을 때 뭉쳐 보이는 문제를 피한다.
    """
    df = month_summary[month_summary["year"] == year].sort_values("month")
    values = df["month_pred_avg"].values
    ax = plt.figure(figsize=(10.5, 5.2)).gca()
    bars = ax.bar(df["month"].astype(str) + "월", values)
    ax.set_title(f"{year}년 월별 예상 교통량")
    ax.set_xlabel("월")
    ax.set_ylabel("예상 일평균 교통량")
    ax.grid(axis="y", alpha=0.3)
    apply_zoom_y(ax, values)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, value, f"{value/1000:,.0f}k", ha="center", va="bottom", fontsize=8)
    save_and_show(f"서영_{seq:02d}_{year}년_월별_예상교통량.png")


def plot_future_weekday_bar_by_year(weekday_summary, year, seq):
    """한 연도 안의 요일별 예상 교통량을 별도 큰 그래프로 본다."""
    df = weekday_summary[weekday_summary["year"] == year].sort_values("weekday_order")
    values = df["weekday_pred_avg"].values
    ax = plt.figure(figsize=(9.2, 5.2)).gca()
    bars = ax.bar(df["weekday_code"], values)
    ax.set_title(f"{year}년 요일별 예상 교통량")
    ax.set_xlabel("요일")
    ax.set_ylabel("예상 일평균 교통량")
    ax.grid(axis="y", alpha=0.3)
    apply_zoom_y(ax, values)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, value, f"{value/1000:,.0f}k", ha="center", va="bottom", fontsize=8)
    save_and_show(f"서영_{seq:02d}_{year}년_요일별_예상교통량.png")


def plot_year_top_low_detail(all_top, all_low, year, seq):
    top = all_top[all_top["year"] == year].sort_values("predicted_total", ascending=True)
    low = all_low[all_low["year"] == year].sort_values("predicted_total", ascending=False)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.7))
    axes[0].barh(top["date_label"], top["predicted_total"])
    axes[0].set_title(f"{year}년 교통량 많은 날 TOP{TOP_N}")
    axes[0].set_xlabel("예상 전체 교통량")
    axes[0].grid(axis="x", alpha=0.3)
    apply_zoom_x(axes[0], top["predicted_total"])
    for y, value in enumerate(top["predicted_total"]):
        axes[0].text(value + (axes[0].get_xlim()[1] - axes[0].get_xlim()[0]) * 0.02, y, f"{value:,.0f}", va="center", fontsize=9)

    axes[1].barh(low["date_label"], low["predicted_total"])
    axes[1].set_title(f"{year}년 교통량 적은 날 LOW{TOP_N}")
    axes[1].set_xlabel("예상 전체 교통량")
    axes[1].grid(axis="x", alpha=0.3)
    apply_zoom_x(axes[1], low["predicted_total"])
    for y, value in enumerate(low["predicted_total"]):
        axes[1].text(value + (axes[1].get_xlim()[1] - axes[1].get_xlim()[0]) * 0.02, y, f"{value:,.0f}", va="center", fontsize=9)
    fig.suptitle(f"{year}년 날짜별 예상 교통량 TOP5 / LOW5")
    save_and_show(f"서영_{seq:02d}_{year}년_TOP5_LOW5.png")


def plot_future_daily_year_average(daily_by_year):
    rows = []
    for year, daily in daily_by_year.items():
        rows.append({"year": year, "daily_avg": daily["predicted_total"].mean(), "daily_max": daily["predicted_total"].max(), "daily_min": daily["predicted_total"].min()})
    summary = pd.DataFrame(rows)
    ax = plt.figure(figsize=(10, 5.2)).gca()
    ax.plot(summary["year"], summary["daily_avg"], marker="o", linewidth=2, label="연평균")
    ax.plot(summary["year"], summary["daily_max"], marker="o", linewidth=2, label="연중 최대")
    ax.plot(summary["year"], summary["daily_min"], marker="o", linewidth=2, label="연중 최소")
    ax.set_title("2026~2030 날짜별 예측값 요약")
    ax.set_xlabel("연도")
    ax.set_ylabel("예상 전체 교통량")
    ax.set_xticks(summary["year"])
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend()
    apply_zoom_y(ax, summary[["daily_avg", "daily_max", "daily_min"]].values)
    save_and_show("서영_12_미래_날짜별_요약.png")


def main():
    base_result = load_base_result()
    overall_avg, month_avg, weekday_avg, pattern_avg, high_pattern, low_pattern = build_past_pattern(base_result["common_weekday"])
    daily_by_year, all_top, all_low = predict_range(base_result)
    all_daily, month_summary, weekday_summary = build_future_summary(daily_by_year)
    month_compare, weekday_compare = build_compare_tables(month_avg, weekday_avg, all_daily)
    top_low_summary = build_top_low_summary(all_top, all_low)

    display_table("월별 평균 비교: 2020~2025 평균 vs 2026~2030 예상 평균", month_compare.round(2))
    display_table("요일별 평균 비교: 2020~2025 평균 vs 2026~2030 예상 평균", weekday_compare.round(2))
    display_table("2026~2030 연도별 TOP5", all_top[["rank", "ymd", "year", "weekday_name", "predicted_avg", "predicted_total", "congestion_level"]].round(2))
    display_table("2026~2030 연도별 LOW5", all_low[["rank", "ymd", "year", "weekday_name", "predicted_avg", "predicted_total", "congestion_level"]].round(2))
    display_table("2026~2030 TOP5 / LOW5 연평균 요약", top_low_summary.round(2))

    # 01~02: 과거 평균과 미래 예상 평균을 같은 그래프에 병합해서 비교한다.
    plot_month_average_compare(month_compare)
    plot_weekday_average_compare(weekday_compare)

    # 03~04: 2026~2030 각 연도별 TOP5 / LOW5 날짜를 한 이미지씩 요약한다.
    plot_all_year_top_dates(all_top)
    plot_all_year_low_dates(all_low)

    # 05: TOP5 / LOW5 결과 자체를 요약한다.
    plot_top_low_average_compare(top_low_summary)


if __name__ == "__main__":
    main()
