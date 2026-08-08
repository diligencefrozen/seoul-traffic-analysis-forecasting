import os
import glob
import zipfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


def find_zip(keyword, search_dir="/content"):
    candidates = glob.glob(os.path.join(search_dir, "*.zip"))
    candidates += glob.glob(os.path.join(os.getcwd(), "*.zip"))
    candidates = sorted(set(candidates))

    for path in candidates:
        if keyword in os.path.basename(path):
            return path

    raise FileNotFoundError(f"'{keyword}'가 들어간 ZIP 파일을 찾지 못했습니다. 현재 폴더에 업로드했는지 확인하세요.")


def unzip_if_needed(zip_path, extract_dir, expected_files=None):
    extract_dir = Path(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    if expected_files:
        exists_all = True
        for filename in expected_files:
            if len(list(extract_dir.rglob(filename))) == 0:
                exists_all = False
                break
        if exists_all:
            print(f"이미 압축 해제된 파일을 사용합니다: {extract_dir}")
            return str(extract_dir)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    print(f"압축 해제 완료: {zip_path} -> {extract_dir}")
    return str(extract_dir)


def find_file(root_dir, filename):
    matches = list(Path(root_dir).rglob(filename))
    if len(matches) == 0:
        raise FileNotFoundError(f"{root_dir} 안에서 {filename} 파일을 찾지 못했습니다.")
    return str(matches[0])


def load_pdf_clean_data(clean_root):
    monthly_weekday = pd.read_csv(find_file(clean_root, "seoul_traffic_2020_2025_point_month_weekday_all.csv"))
    monthly_hour = pd.read_csv(find_file(clean_root, "seoul_traffic_2020_2025_point_month_hour_all.csv"))
    stations = pd.read_csv(find_file(clean_root, "seoul_traffic_2020_2025_station_master_all.csv"))

    print("2020~2025 월/요일 데이터:", monthly_weekday.shape)
    print("2020~2025 월/시간 데이터:", monthly_hour.shape)
    print("2020~2025 지점 데이터:", stations.shape)

    return monthly_weekday, monthly_hour, stations


def build_common_tables(monthly_weekday_pdf, monthly_hour_pdf, stations):
    hour_pdf = monthly_hour_pdf.copy()
    weekday_pdf = monthly_weekday_pdf.copy()

    hour_pdf["is_total_row"] = hour_pdf["is_total_row"].astype(str).str.lower().isin(["true", "1"])
    hour_pdf = hour_pdf[(hour_pdf["month"] != 0) & (hour_pdf["is_total_row"] == False)].copy()
    weekday_pdf = weekday_pdf[
        (weekday_pdf["month"] != 0) &
        (weekday_pdf["weekday_code"].isin(["월", "화", "수", "목", "금", "토", "일"]))
    ].copy()

    station_latest = (
        stations.sort_values("year")
        .drop_duplicates("spot_num", keep="last")
        [["spot_num", "spot_name", "road_type", "spot_location", "lon", "lat", "in_lanes", "out_lanes", "in_direction", "out_direction"]]
    )

    common_hour = hour_pdf.merge(station_latest, on="spot_num", how="left")
    common_weekday = weekday_pdf.merge(station_latest, on="spot_num", how="left")

    common_hour["quarter"] = ((common_hour["month"] - 1) // 3 + 1).astype("int8")
    common_weekday["quarter"] = ((common_weekday["month"] - 1) // 3 + 1).astype("int8")

    print("공통 시간대 학습 테이블:", common_hour.shape)
    print("공통 요일 학습 테이블:", common_weekday.shape)

    return common_hour, common_weekday, station_latest


def mean_absolute_error_simple(y_true, y_pred):
    return float(np.mean(np.abs(np.array(y_true) - np.array(y_pred))))


def r2_score_simple(y_true, y_pred):
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 0.0
    return float(1 - ss_res / ss_tot)


def _fit_trend_table(df, target_col, group_cols):
    data = df.dropna(subset=[target_col]).copy()
    data[target_col] = pd.to_numeric(data[target_col], errors="coerce")
    data = data.dropna(subset=[target_col])

    for col in group_cols:
        data[col] = data[col].astype("string").fillna("미상")

    data["_x"] = data["year"].astype(float)
    data["_y"] = data[target_col].astype(float)
    data["_xx"] = data["_x"] * data["_x"]
    data["_xy"] = data["_x"] * data["_y"]

    trend = (
        data.groupby(group_cols, as_index=False, observed=True)
        .agg(
            n=("_y", "count"),
            sx=("_x", "sum"),
            sy=("_y", "sum"),
            sxx=("_xx", "sum"),
            sxy=("_xy", "sum"),
            mean_value=("_y", "mean"),
        )
    )

    denom = trend["n"] * trend["sxx"] - trend["sx"] * trend["sx"]
    slope = (trend["n"] * trend["sxy"] - trend["sx"] * trend["sy"]) / denom.replace(0, np.nan)
    trend["slope"] = slope.fillna(0)
    trend["intercept"] = (trend["sy"] - trend["slope"] * trend["sx"]) / trend["n"]

    return trend[group_cols + ["n", "mean_value", "slope", "intercept"]]


def train_trend_model(df, target_col, group_cols, valid_year=None):
    data = df.dropna(subset=[target_col]).copy()
    data[target_col] = pd.to_numeric(data[target_col], errors="coerce")
    data = data.dropna(subset=[target_col])

    if valid_year is None:
        valid_year = int(data["year"].max())

    train_df = data[data["year"] < valid_year].copy()
    valid_df = data[data["year"] == valid_year].copy()

    if len(train_df) > 0 and len(valid_df) > 0:
        temp_model = {
            "trend": _fit_trend_table(train_df, target_col, group_cols),
            "target_col": target_col,
            "group_cols": group_cols,
            "fallback_value": float(train_df[target_col].mean()),
        }
        pred = predict_trend_model(temp_model, valid_df)
        mae = mean_absolute_error_simple(valid_df[target_col], pred)
        r2 = r2_score_simple(valid_df[target_col], pred)
        print("검증 연도:", valid_year)
        print("MAE:", round(mae, 2))
        print("R2:", round(r2, 4))
    else:
        mae = np.nan
        r2 = np.nan
        print("검증 데이터가 부족해서 검증 점수는 계산하지 않았습니다.")

    final_model = {
        "trend": _fit_trend_table(data, target_col, group_cols),
        "target_col": target_col,
        "group_cols": group_cols,
        "fallback_value": float(data[target_col].mean()),
        "valid_mae": mae,
        "valid_r2": r2,
    }
    return final_model


def predict_trend_model(model_info, input_df):
    group_cols = model_info["group_cols"]
    data = input_df.copy()

    for col in group_cols:
        data[col] = data[col].astype("string").fillna("미상")

    merged = data.merge(model_info["trend"], on=group_cols, how="left")
    pred = merged["intercept"] + merged["slope"] * merged["year"].astype(float)
    pred = pred.fillna(model_info["fallback_value"])
    pred = np.where(pred < 0, 0, pred)
    return pred


train_regression_model = train_trend_model
predict_regression = predict_trend_model


def add_congestion_label(df, value_col, label_col="congestion_level"):
    q50 = df[value_col].quantile(0.50)
    q75 = df[value_col].quantile(0.75)
    q90 = df[value_col].quantile(0.90)

    df[label_col] = np.select(
        [df[value_col] >= q90, df[value_col] >= q75, df[value_col] >= q50],
        ["매우 높음", "높음", "보통"],
        default="낮음"
    )
    return df


def get_day_type(date_value):
    dt = pd.to_datetime(date_value)
    if dt.weekday() <= 4:
        return "평일"
    if dt.weekday() == 5:
        return "토요일"
    return "일요일"


def get_weekday_code_name(date_value):
    dt = pd.to_datetime(date_value)
    code_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    name_map = {0: "월요일", 1: "화요일", 2: "수요일", 3: "목요일", 4: "금요일", 5: "토요일", 6: "일요일"}
    return code_map[dt.weekday()], name_map[dt.weekday()]


def make_specific_day_hour_input(target_date, station_latest, hour_start=None, spot_num=None):
    dt = pd.to_datetime(target_date)
    spots = station_latest[["spot_num", "road_type"]].drop_duplicates().copy()

    if spot_num is not None:
        spots = spots[spots["spot_num"] == spot_num]

    hours = list(range(24)) if hour_start is None else [int(hour_start)]
    rows = []

    for _, spot in spots.iterrows():
        for io_type, io_name in [(1, "유입"), (2, "유출")]:
            for hh in hours:
                rows.append({
                    "year": dt.year,
                    "month": dt.month,
                    "quarter": (dt.month - 1) // 3 + 1,
                    "spot_num": spot["spot_num"],
                    "road_type": spot["road_type"],
                    "io_type": io_type,
                    "io_name": io_name,
                    "day_type": get_day_type(dt),
                    "hour_start": hh,
                })

    return pd.DataFrame(rows)


def make_month_quarter_input(target_year, station_latest):
    spots = station_latest[["spot_num", "road_type"]].drop_duplicates().copy()
    rows = []

    for _, spot in spots.iterrows():
        for month in range(1, 13):
            for io_type, io_name in [(1, "유입"), (2, "유출")]:
                for day_type in ["평일", "토요일", "일요일"]:
                    for hh in range(24):
                        rows.append({
                            "year": target_year,
                            "month": month,
                            "quarter": (month - 1) // 3 + 1,
                            "spot_num": spot["spot_num"],
                            "road_type": spot["road_type"],
                            "io_type": io_type,
                            "io_name": io_name,
                            "day_type": day_type,
                            "hour_start": hh,
                        })

    return pd.DataFrame(rows)


def make_weekday_input(target_year, target_month, station_latest):
    spots = station_latest[["spot_num", "road_type"]].drop_duplicates().copy()
    code_name = [("월", "월요일"), ("화", "화요일"), ("수", "수요일"), ("목", "목요일"), ("금", "금요일"), ("토", "토요일"), ("일", "일요일")]
    rows = []

    for _, spot in spots.iterrows():
        for code, name in code_name:
            for io_type, io_name in [(1, "유입"), (2, "유출")]:
                rows.append({
                    "year": target_year,
                    "month": target_month,
                    "quarter": (target_month - 1) // 3 + 1,
                    "spot_num": spot["spot_num"],
                    "road_type": spot["road_type"],
                    "weekday_code": code,
                    "weekday_name": name,
                    "io_type": io_type,
                    "io_name": io_name,
                })

    return pd.DataFrame(rows)


def make_date_range_weekday_input(start_date, end_date, station_latest):
    dates = pd.date_range(start_date, end_date, freq="D")
    spots = station_latest[["spot_num", "road_type"]].drop_duplicates().copy()
    rows = []

    for dt in dates:
        weekday_code, weekday_name = get_weekday_code_name(dt)
        for _, spot in spots.iterrows():
            for io_type, io_name in [(1, "유입"), (2, "유출")]:
                rows.append({
                    "ymd": dt,
                    "year": dt.year,
                    "month": dt.month,
                    "quarter": (dt.month - 1) // 3 + 1,
                    "spot_num": spot["spot_num"],
                    "road_type": spot["road_type"],
                    "weekday_code": weekday_code,
                    "weekday_name": weekday_name,
                    "io_type": io_type,
                    "io_name": io_name,
                    "day_type": get_day_type(dt),
                })

    return pd.DataFrame(rows)


def add_holiday_flag(df, holiday_dates):
    result = df.copy()
    holidays = set(pd.to_datetime(holiday_dates).date)
    result["is_holiday"] = pd.to_datetime(result["ymd"]).dt.date.isin(holidays)
    result["holiday_type"] = np.where(result["is_holiday"], "공휴일", "평일/주말")
    return result


def run_base_pipeline(search_dir="/content"):
    expected_files = [
        "seoul_traffic_2020_2025_point_month_weekday_all.csv",
        "seoul_traffic_2020_2025_point_month_hour_all.csv",
        "seoul_traffic_2020_2025_station_master_all.csv",
    ]

    clean_zip = find_zip("2020~2025 서울특별시 교통량 정제 데이터", search_dir=search_dir)
    clean_root = unzip_if_needed(clean_zip, "/content/traffic_clean_2020_2025", expected_files)

    monthly_weekday_pdf, monthly_hour_pdf, stations = load_pdf_clean_data(clean_root)
    common_hour, common_weekday, station_latest = build_common_tables(monthly_weekday_pdf, monthly_hour_pdf, stations)

    hour_features = ["month", "quarter", "spot_num", "road_type", "io_type", "day_type", "hour_start"]
    weekday_features = ["month", "quarter", "spot_num", "road_type", "io_type", "weekday_code"]

    print("\n[시간대 모델 학습]")
    hour_model = train_regression_model(common_hour, "vol_hour_avg", hour_features, valid_year=2025)

    print("\n[요일 모델 학습]")
    weekday_model = train_regression_model(common_weekday, "vol_daily_avg", weekday_features, valid_year=2025)

    return {
        "monthly_weekday_pdf": monthly_weekday_pdf,
        "monthly_hour_pdf": monthly_hour_pdf,
        "stations": stations,
        "daily_2025": None,
        "daily_hour_2025": None,
        "common_hour": common_hour,
        "common_weekday": common_weekday,
        "station_latest": station_latest,
        "hour_model": hour_model,
        "weekday_model": weekday_model,
    }
