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
GRAPH_DIR = Path("traffic_final_graphs_v5")
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

from project_base import *

setup_paths()
set_korean_font()

data = run_base_pipeline()

common_hour = data["common_hour"]
station_latest = data["station_latest"]
hour_model = data["hour_model"]

station_latest["gu"] = (
    station_latest["spot_location"]
        .str.extract(r"([가-힣]+구)")
)

common_hour = common_hour.merge(
    station_latest[
        ["spot_num","gu"]
    ],
    on="spot_num",
    how="left"
)
future_df = pd.concat(
    [
        make_month_quarter_input(year, station_latest)
        for year in range(2026,2031)
    ],
    ignore_index=True
)
future_df["predict"] = predict_regression(
    hour_model,
    future_df
)
future_df = future_df.merge(
    station_latest[
        [
            "spot_num",
            "gu"
        ]
    ],
    on="spot_num",
    how="left"
)
gu_prediction = (
    future_df
        .groupby(
            [
                "year",
                "gu",
                "io_name"
            ],
            as_index=False
        )["predict"]
        .mean()
)

future_df = pd.concat(
    [
        make_month_quarter_input(year, station_latest)
        for year in range(2026, 2031)
    ],
    ignore_index=True
)

future_df["predict"] = predict_regression(
    hour_model,
    future_df
)

station_latest["gu"] = (
    station_latest["spot_location"]
    .str.extract(r"([가-힣]+구)")
)

future_df = future_df.merge(
    station_latest[["spot_num", "gu"]],
    on="spot_num",
    how="left"
)

# 서울이 아닌 지역 제거
exclude_gu = [
    "소사구",
    "수정구",
    "덕양구"
]

future_df = future_df[
    ~future_df["gu"].isin(exclude_gu)
]

gu_prediction = (
    future_df
    .groupby(
        ["year", "gu", "io_name"],
        as_index=False
    )["predict"]
    .mean()
)
# ============================================================
# Graph 1 데이터 준비 (2026~2030 평균)
# ============================================================

graph1_df = (
    gu_prediction[
        gu_prediction["year"].between(2026, 2030)
    ]
    .groupby(
        ["gu", "io_name"],
        as_index=False
    )["predict"]
    .mean()
)

graph1_pivot = (
    graph1_df
    .pivot(
        index="gu",
        columns="io_name",
        values="predict"
    )
    .fillna(0)
)

graph1_pivot["합계"] = (
    graph1_pivot["유입"] +
    graph1_pivot["유출"]
)

graph1_pivot = (
    graph1_pivot
    .sort_values(
        "합계",
        ascending=False
    )
)

graph1_pivot = graph1_pivot.drop(columns="합계")

# ============================================================
# Graph 1
# 2030년 서울시 구별 유입·유출 평균 교통량
# ============================================================

plt.figure(figsize=(16,8))

x = np.arange(len(graph1_pivot))

width = 0.38

plt.bar(
    x - width/2,
    graph1_pivot["유입"],
    width,
    label="유입"
)

plt.bar(
    x + width/2,
    graph1_pivot["유출"],
    width,
    label="유출"
)

plt.xticks(
    x,
    graph1_pivot.index,
    rotation=45
)

plt.title(
   "2026~2030년 서울시 구별 유입·유출 평균 교통량 예측"
)

plt.xlabel("서울시 자치구")

plt.ylabel("평균 교통량")

plt.legend()

save_and_show("graph_01_gu_io_compare.png")

# ============================================================
# Graph 2-1
# 2030년 유입 교통량 TOP5
# ============================================================

graph2_in = (
    graph1_df[
        graph1_df["io_name"] == "유입"
    ]
    .sort_values(
        "predict",
        ascending=False
    )
    .head(5)
)
plt.figure(figsize=(10, 5))

plt.barh(
    graph2_in["gu"],
    graph2_in["predict"]
)

plt.title("2026~2030년 서울시 유입 교통량 TOP5 (예측)")
plt.xlabel("평균 교통량")
plt.ylabel("서울시 자치구")

save_and_show("graph_02_inflow_top5.png")

# ============================================================
# Graph 2
# 2030년 유입/유출 교통량 TOP5 비교 (예측)
# 같은 자치구 = 같은 색 적용
# ============================================================


# -------------------------------
# 2030년 유입 TOP5
# -------------------------------
graph2_in = (
    graph1_df[
        graph1_df["io_name"] == "유입"
    ]
    .sort_values(
        "predict",
        ascending=False
    )
    .head(5)
)


# -------------------------------
# 2030년 유출 TOP5
# -------------------------------
graph2_out = (
    graph1_df[
        graph1_df["io_name"] == "유출"
    ]
    .sort_values(
        "predict",
        ascending=False
    )
    .head(5)
)


# ============================================================
# 자치구별 색상 지정
# ============================================================

# 유입 + 유출 TOP5에 등장하는 구 추출
all_gu = list(
    dict.fromkeys(
        list(graph2_in["gu"]) +
        list(graph2_out["gu"])
    )
)


# 최대 6개 색상 지정
colors = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b"
]


# 자치구별 색상 매핑
color_map = {
    gu: colors[i % len(colors)]
    for i, gu in enumerate(all_gu)
}


# ============================================================
# 그래프 출력
# ============================================================

fig, axes = plt.subplots(
    2, 1,
    figsize=(10, 10)
)


# -------------------------------
# 유입 TOP5
# -------------------------------
axes[0].barh(
    graph2_in["gu"],
    graph2_in["predict"],
    color=[
        color_map[gu]
        for gu in graph2_in["gu"]
    ]
)

axes[0].set_title(
    "2026~2030년 서울시 유입 교통량 TOP5 (예측)"
)

axes[0].set_xlabel("평균 교통량")
axes[0].set_ylabel("서울시 자치구")

axes[0].invert_yaxis()



# -------------------------------
# 유출 TOP5
# -------------------------------
axes[1].barh(
    graph2_out["gu"],
    graph2_out["predict"],
    color=[
        color_map[gu]
        for gu in graph2_out["gu"]
    ]
)

axes[1].set_title(
    "2026~2030년 서울시 유출 교통량 TOP5 (예측)"
)

axes[1].set_xlabel("평균 교통량")
axes[1].set_ylabel("서울시 자치구")

axes[1].invert_yaxis()


plt.tight_layout()


save_and_show(
    "graph_02_inflow_outflow_top5_color.png"
)

# ============================================================
# Graph 2-2
# 2030년 유출 교통량 TOP5
# ============================================================

graph2_out = (
    graph1_df[
        graph1_df["io_name"] == "유출"
    ]
    .sort_values(
        "predict",
        ascending=False
    )
    .head(5)
)
plt.figure(figsize=(10, 5))

plt.barh(
    graph2_out["gu"],
    graph2_out["predict"]
)

plt.title("2030년 서울시 유출 교통량 TOP5 (예측)")
plt.xlabel("평균 교통량")
plt.ylabel("서울시 자치구")

save_and_show("graph_03_outflow_top5.png")

print(common_hour.columns.tolist())

print(station_latest.columns.tolist())

# ============================================================
# Graph 4
# 2020~2030 유입 교통량 TOP5 변화 추이 (실측 + 예측)
# ============================================================

# -------------------------------
# 실제 데이터 (2020~2025)
# -------------------------------
history_gu = (
    common_hour[
        common_hour["io_name"] == "유입"
    ]
    .groupby(
        ["year", "gu"],
        as_index=False
    )["vol_hour_avg"]
    .mean()
    .rename(columns={
        "vol_hour_avg": "traffic"
    })
)


# -------------------------------
# 예측 데이터 (2026~2030)
# -------------------------------
future_gu = (
    gu_prediction[
        gu_prediction["io_name"] == "유입"
    ][["year", "gu", "predict"]]
    .rename(columns={"predict": "traffic"})
)

# -------------------------------
# 데이터 합치기
# -------------------------------
graph4_df = pd.concat(
    [history_gu, future_gu],
    ignore_index=True
)

# -------------------------------
# 2030년 기준 TOP5 자치구 선정
# -------------------------------
top5_gu = (
    future_gu[
        future_gu["year"].between(2026, 2030)
    ]
    .groupby(
        "gu",
        as_index=False
    )["traffic"]
    .mean()
    .sort_values(
        "traffic",
        ascending=False
    )
    .head(5)["gu"]
    .tolist()
)

graph4_df = graph4_df[
    graph4_df["gu"].isin(top5_gu)
]

# ============================================================
# 그래프 출력
# ============================================================

plt.figure(figsize=(13, 7))

for gu in top5_gu:

    temp = (
        graph4_df[
            graph4_df["gu"] == gu
        ]
        .set_index("year")
        .reindex(range(2020, 2031))
    )

    temp["gu"] = gu

    # 없는 연도는 선형 보간
    temp["traffic"] = (
        temp["traffic"]
        .interpolate()
        .bfill()
        .ffill()
    )

    temp = temp.reset_index().rename(columns={"index": "year"})

    plt.plot(
        temp["year"],
        temp["traffic"],
        marker="o",
        linewidth=2,
        label=gu
    )
# 실측/예측 구분선
plt.axvline(
    x=2025.5,
    linestyle="--",
    linewidth=2
)

plt.text(
    2022,
    plt.ylim()[1] * 0.98,
    "실측 데이터",
    fontsize=10
)

plt.text(
    2026,
    plt.ylim()[1] * 0.98,
    "예측 데이터",
    fontsize=10
)

plt.title("2020~2030 유입 교통량 TOP5 자치구 변화 추이")

plt.xlabel("연도")

plt.ylabel("평균 교통량")

plt.xticks(range(2020, 2031))

plt.legend()

plt.grid(alpha=0.3)

save_and_show("graph_04_inflow_trend.png")

# ============================================================
# Graph 5
# 2020~2030 유출 교통량 TOP5 변화 추이 (실측 + 예측)
# ============================================================

# -------------------------------
# 실제 데이터 (2020~2025)
# -------------------------------
history_gu_out = (
    common_hour[
        common_hour["io_name"] == "유출"
    ]
    .groupby(
        ["year", "gu"],
        as_index=False
    )["vol_hour_avg"]
    .mean()
    .rename(columns={
        "vol_hour_avg": "traffic"
    })
)


# -------------------------------
# 예측 데이터 (2026~2030)
# -------------------------------
future_gu_out = (
    gu_prediction[
        gu_prediction["io_name"] == "유출"
    ][["year", "gu", "predict"]]
    .rename(columns={"predict": "traffic"})
)


# -------------------------------
# 데이터 합치기
# -------------------------------
graph5_df = pd.concat(
    [history_gu_out, future_gu_out],
    ignore_index=True
)


# -------------------------------
# 2030년 기준 TOP5 자치구 선정
# -------------------------------
top5_gu_out = (
    future_gu_out[
        future_gu_out["year"].between(2026, 2030)
    ]
    .groupby(
        "gu",
        as_index=False
    )["traffic"]
    .mean()
    .sort_values(
        "traffic",
        ascending=False
    )
    .head(5)["gu"]
    .tolist()
)

graph5_df = graph5_df[
    graph5_df["gu"].isin(top5_gu_out)
]

# ============================================================
# 그래프 출력
# ============================================================

plt.figure(figsize=(13, 7))


for gu in top5_gu_out:

    temp = (
        graph5_df[
            graph5_df["gu"] == gu
        ]
        .set_index("year")
        .reindex(range(2020, 2031))
    )

    temp["gu"] = gu

    # 없는 연도는 선형 보간
    temp["traffic"] = (
        temp["traffic"]
        .interpolate()
        .bfill()
        .ffill()
    )

    temp = temp.reset_index().rename(columns={"index": "year"})

    plt.plot(
        temp["year"],
        temp["traffic"],
        marker="o",
        linewidth=2,
        label=gu
    )

# 실측/예측 구분선
plt.axvline(
    x=2025.5,
    linestyle="--",
    linewidth=2
)


plt.text(
    2022,
    plt.ylim()[1] * 0.98,
    "실측 데이터",
    fontsize=10
)

plt.text(
    2026,
    plt.ylim()[1] * 0.98,
    "예측 데이터",
    fontsize=10
)


plt.title("2020~2030 유출 교통량 TOP5 자치구 변화 추이")

plt.xlabel("연도")

plt.ylabel("평균 교통량")

plt.xticks(range(2020, 2031))

plt.legend()

plt.grid(alpha=0.3)


save_and_show("graph_05_outflow_trend.png")

# ============================================================
# 2020~2025 연도별 유출량 최대 자치구 확인
# ============================================================

outflow_year_gu = (
    common_hour[
        common_hour["io_name"] == "유출"
    ]
    .groupby(
        ["year", "gu"],
        as_index=False
    )["vol_hour_avg"]
    .mean()
    .rename(columns={
        "vol_hour_avg": "traffic"
    })
)


# 연도별 유출량 최대 자치구 추출
max_outflow_gu = (
    outflow_year_gu
    .sort_values(
        ["year", "traffic"],
        ascending=[True, False]
    )
    .groupby("year")
    .head(1)
    .reset_index(drop=True)
)


max_outflow_gu

# ============================================================
# 2020~2025 연도별 유입량 최대 자치구 확인
# ============================================================

inflow_year_gu = (
    common_hour[
        common_hour["io_name"] == "유입"
    ]
    .groupby(
        ["year", "gu"],
        as_index=False
    )["vol_hour_avg"]
    .mean()
    .rename(columns={
        "vol_hour_avg": "traffic"
    })
)


# 연도별 유입량 최대 자치구 추출
max_inflow_gu = (
    inflow_year_gu
    .sort_values(
        ["year", "traffic"],
        ascending=[True, False]
    )
    .groupby("year")
    .head(1)
    .reset_index(drop=True)
)


max_inflow_gu

gangnam_year = (
    common_hour[
        common_hour["gu"] == "동작구"
    ]
    .groupby(
        ["year", "io_name"],
        as_index=False
    )["vol_hour_avg"]
    .mean()
)

display(gangnam_year)

# ============================================================
# 권역 분류
# ============================================================

region_map = {
    "종로구": "도심권",
    "중구": "도심권",
    "용산구": "도심권",

    "강북구": "동북권",
    "노원구": "동북권",
    "도봉구": "동북권",
    "동대문구": "동북권",
    "성동구": "동북권",
    "성북구": "동북권",
    "중랑구": "동북권",
    "광진구": "동북권",

    "은평구": "서북권",
    "서대문구": "서북권",
    "마포구": "서북권",

    "강서구": "서남권",
    "양천구": "서남권",
    "구로구": "서남권",
    "금천구": "서남권",
    "영등포구": "서남권",
    "동작구": "서남권",
    "관악구": "서남권",

    "강남구": "동남권",
    "서초구": "동남권",
    "송파구": "동남권",
    "강동구": "동남권",
}

graph1_df["권역"] = graph1_df["gu"].map(region_map)
region_df = (
    graph1_df
    .groupby(
        ["권역", "io_name"],
        as_index=False
    )["predict"]
    .mean()
)
region_pivot = (
    region_df
    .pivot(
        index="권역",
        columns="io_name",
        values="predict"
    )
    .fillna(0)
)
region_order = [
    "서북권",
    "서남권",
    "도심권",
    "동북권",
    "동남권"
]

region_pivot = region_pivot.reindex(region_order)
plt.figure(figsize=(10,6))

x = np.arange(len(region_pivot))
width = 0.35

plt.xticks(
    x,
    region_pivot.index
)

plt.title(
    "2026~2030년 서울시 권역별 평균 교통량 예측"
)

plt.xlabel("서울시 권역")

plt.ylabel("평균 교통량")

bars_in = plt.bar(
    x - width/2,
    region_pivot["유입"],
    width,
    label="유입"
)

bars_out = plt.bar(
    x + width/2,
    region_pivot["유출"],
    width,
    label="유출"
)

# 막대 위에 값 표시
for bar in bars_in:
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{height:,.0f}",
        ha="center",
        va="bottom",
        fontsize=9
    )

for bar in bars_out:
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{height:,.0f}",
        ha="center",
        va="bottom",
        fontsize=9
    )
    plt.ylim(bottom=1300)

plt.yticks(
    np.arange(
        1300,
        plt.ylim()[1] + 100,
        100
    )
)
plt.legend()

save_and_show("graph_region_io_compare.png")

# 권역별 구 평균
region_detail = (
    graph1_df
    .groupby(
        ["권역", "gu", "io_name"],
        as_index=False
    )["predict"]
    .mean()
)

print("=" * 60)

for region in region_detail["권역"].unique():

    print(f"\n[{region}]")

    temp = (
        region_detail[
            region_detail["권역"] == region
        ]
        .sort_values(
            ["io_name", "gu"]
        )
    )

    print(temp)

    print("\n권역별 요약")

    summary = (
        temp
        .groupby("io_name")["predict"]
        .agg(
            총합="sum",
            평균="mean"
        )
    )

    print(summary.round(2))