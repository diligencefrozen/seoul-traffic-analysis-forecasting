# 서울시 교통량 분석 및 예측  
# Seoul Traffic Analysis and Forecasting

> **5명이 함께 진행한 데이터 분석 프로젝트입니다.**  
> 2020~2025년 서울시 교통량을 살펴보고, 그 흐름을 바탕으로 2026~2030년 교통량을 추정했습니다.  
> 이 저장소에서는 팀 전체 작업과 함께 **제가 맡은 ‘특정 날짜의 시간대별 혼잡도 분석’**을 자세히 보여 줍니다.

---

## 한국어

### 1. 한눈에 보기

서울시 교통량은 날짜, 요일, 시간대, 지역에 따라 크게 달라집니다.  
이 프로젝트에서는 과거 교통량 자료를 정리한 뒤, **언제 어디가 붐비는지 살펴보고 앞으로의 교통량도 추정**했습니다.

주요 목표는 다음과 같습니다.

- 시간대와 요일에 따라 교통량이 어떻게 달라지는지 살펴보기
- 2020~2025년 자료를 바탕으로 2026~2030년 교통량 추정하기
- 분기, 날짜, 지역별 유입·유출 교통량 비교하기
- 분석 결과를 그래프와 표로 보여 주어 쉽게 이해할 수 있게 만들기

### 2. 제가 맡은 일

저는 **특정 날짜의 시간대별 예상 혼잡도 분석**을 맡았습니다.

대표 사례로 어린이날(5월 5일)을 골랐습니다. 날짜가 매년 같기 때문에 여러 해의 변화를 비교하기 쉽고, 같은 분석 방법을 다른 공휴일이나 원하는 날짜에도 적용할 수 있기 때문입니다.

제가 구현한 내용은 다음과 같습니다.

- 원하는 날짜와 시간의 예상 교통량 계산
- 지점과 진행 방향별로 과거 교통량과 비교해 혼잡 정도 계산
- 어린이날 오후 6시 기준 예상 혼잡 지점 상위 5곳 찾기
- 해마다 가장 붐빌 것으로 보이는 시간대 찾기
- 2030년 5월의 요일·시간대별 혼잡 흐름을 한눈에 볼 수 있는 그림 만들기
- 2026~2030년의 혼잡 수준이 어떻게 달라지는지 비교하기

### 3. 혼잡도는 어떻게 계산했나요?

이 프로젝트에서 말하는 **혼잡도 100%는 도로의 최대 수용량을 뜻하지 않습니다.**

각 지점과 진행 방향에서 **2025년 교통량 중 상위 10%가 시작되는 값**을 100% 기준으로 잡았습니다.

예를 들면 다음과 같습니다.

- **100%보다 높음**: 2025년에 교통량이 많았던 때보다 더 붐빌 것으로 예상
- **100%보다 낮음**: 그 기준보다 덜 붐빌 것으로 예상

즉, 이 값은 도로의 절대적인 한계를 뜻하는 수치가 아니라 **과거와 비교하기 위한 기준**입니다.

### 4. 주요 결과

#### 어린이날 오후 6시 예상 혼잡 지점 상위 5곳

![어린이날 오후 6시 예상 혼잡 지점 상위 5곳](assets/01_childrens_day_top5.png)

오목교 구간은 여러 해에 걸쳐 혼잡도가 높은 지점으로 반복해서 나타났습니다.  
분석 결과 가운데 가장 높은 값은 **2028년 152.9%**였습니다.

#### 해마다 가장 붐비는 시간대

![해마다 가장 붐비는 시간대](assets/02_peak_hour_change.png)

2026~2028년에는 **오전 8시**가 가장 붐빌 것으로 나타났고,  
2029년부터는 가장 붐비는 시간이 **오후 시간대**로 옮겨가는 흐름이 보였습니다.

#### 2030년 5월 요일·시간대별 예상 혼잡도

![2030년 5월 요일·시간대별 예상 혼잡도](assets/03_weekday_hour_heatmap.png)

오전에도 교통량이 많지만, **오후 3시부터 6시 사이**가 더 붐비는 흐름을 보였습니다.  
이 분석에서는 **금요일 오후**가 특히 혼잡한 구간으로 나타났습니다.

#### 2026~2030년 혼잡 수준 비교

![2026~2030년 혼잡 수준 비교](assets/04_congestion_level_distribution.png)

해마다 `원활 / 보통 / 혼잡 / 매우 혼잡`에 해당하는 비율이 어떻게 달라지는지 비교했습니다.

### 5. 팀 전체에서 한 일

| 팀원 | 맡은 분석 |
|---|---|
| 엄선필 | 분기별 평균 교통량 추정 |
| 윤서영 | 날짜별 교통량 상위 5개·하위 5개 추정 |
| 심승보 | 요일별 교통량 추정 |
| **강지성** | **특정 날짜의 시간대별 예상 혼잡도 분석** |
| 백승재 | 지역별 유입·유출 교통량 추정 |

### 6. 데이터는 어떻게 처리했나요?

팀에서 함께 쓰는 `project_base.py`를 먼저 만들고, 모든 분석이 같은 방식으로 데이터를 읽고 정리하도록 했습니다.

```text
2020~2025년 교통량 자료
        ↓
자료 불러오기와 정리
        ↓
교통량과 날짜·시간 정보 합치기
        ↓
시간대·요일별 학습용 자료 만들기
        ↓
과거 흐름을 이용해 2026~2030년 값 추정
        ↓
실제 2025년 자료와 비교해 오차 확인
        ↓
팀원별 주제 분석과 그래프 만들기
```

미래 값을 구할 때는 **연도에 따른 변화 흐름을 바탕으로 값을 추정하는 단순 회귀 방식**을 사용했습니다.  
또한 MAE와 R²를 이용해 실제 값과 추정값의 차이를 확인했습니다.

> **쉽게 말하면:** 과거 몇 년 동안의 변화를 보고 앞으로 값이 어느 방향으로 움직일지 계산한 것입니다.

### 7. 사용한 기술

| 구분 | 사용 도구 |
|---|---|
| 개발 언어 | Python |
| 작업 환경 | Google Colab, Jupyter Notebook |
| 자료 처리 | pandas, NumPy |
| 그래프 | Matplotlib |
| 파일 처리 | pathlib, glob, zipfile, os |
| 오차 확인 | MAE, R² |

### 8. 저장소 구성

```text
.
├── README.md
├── requirements.txt
├── assets/
│   ├── 01_childrens_day_top5.png
│   ├── 02_peak_hour_change.png
│   ├── 03_weekday_hour_heatmap.png
│   └── 04_congestion_level_distribution.png
├── data/
│   └── README.md
└── src/
    ├── project_base.py
    ├── specific_day_congestion.py
    ├── weekday_forecast.py
    ├── quarterly_forecast.py
    ├── district_flow_forecast.py
    └── daily_top_low_forecast.py
```

- `project_base.py`  
  모든 팀원이 함께 쓰는 자료 처리와 예측 기능이 들어 있습니다.

- `specific_day_congestion.py`  
  제가 맡은 **특정 날짜의 시간대별 혼잡도 분석 코드**입니다.

- `assets/`  
  발표와 README에 사용한 주요 결과 그림이 들어 있습니다.

### 9. 실행 방법

원래 코드는 **Google Colab 환경**에서 실행하도록 만들었습니다.

1. `data/README.md`를 보고 필요한 정제 자료를 준비합니다.
2. 자료 파일과 `src/project_base.py`, 실행할 분석 파일을 Colab에 올립니다.
3. 필요한 라이브러리를 설치합니다.

```bash
pip install -r requirements.txt
```

4. 제가 맡은 분석을 실행하려면 다음 파일을 실행합니다.

```bash
python src/specific_day_congestion.py
```

> 현재 일부 코드는 Colab의 `/content` 경로를 기준으로 작성되어 있습니다.  
> 개인 컴퓨터에서 바로 실행하려면 파일 경로를 설정값으로 바꾸는 작업이 필요합니다.

### 10. 결과를 볼 때 알아둘 점

이 프로젝트는 **학습을 목적으로 만든 교통량 분석·예측 프로젝트**입니다.  
실제 도로 운영에 바로 쓰는 교통 예측 시스템은 아닙니다.

- 2026~2030년 값은 과거 자료의 흐름을 바탕으로 계산한 **추정값**입니다.
- 공사, 정책 변화, 대중교통 변화, 날씨, 대형 행사 같은 미래 변수는 충분히 반영하지 못했습니다.
- 혼잡도 100%는 도로의 최대 수용량이 아니라 **2025년 교통량과 비교하기 위한 기준**입니다.
- 실제 서비스로 발전시키려면 더 다양한 자료와 여러 예측 방법을 함께 비교해야 합니다.

### 11. 다음에 개선하고 싶은 점

- Colab 전용 파일 경로를 없애고 어느 컴퓨터에서도 실행하기 쉽게 만들기
- 자료 처리와 혼잡도 계산 기능에 자동 검사 코드 추가하기
- 예측 결과와 오차를 자동으로 저장하도록 만들기
- 현재 방식과 다른 예측 방법을 함께 비교하기
- 날씨, 행사, 공휴일, 도로 정보 같은 자료 추가하기
- 명령 한 번으로 분석하거나 화면에서 결과를 볼 수 있도록 프로그램 형태로 정리하기

### 12. 데이터 출처

**서울 열린데이터광장 — 서울시 교통량 정보**  
https://data.seoul.go.kr/dataList/OA-15064/L/1/datasetView.do

**프로젝트 기간:** 2026년 7월 1일~7월 22일  
**프로젝트 형태:** 5명 팀 프로젝트 / 데이터 분석 및 예측

---

## English

### 1. Overview

Traffic in Seoul changes widely depending on the date, day of the week, time of day, and location.  
This project uses traffic-volume records from **2020 to 2025** to study those patterns and estimate traffic levels for **2026 to 2030**.

The team focused on four goals:

- Understand how traffic changes by hour and weekday
- Estimate traffic volume for 2026–2030 from historical trends
- Compare traffic by quarter, date, and district inflow/outflow
- Present the results with charts that are easy to read without a data-science background

### 2. My Role

I was responsible for **forecasting congestion for a selected date and time of day**.

I used Children's Day (May 5) as the main example because it falls on the same calendar date every year. That makes year-to-year comparisons easier, while the same workflow can also be used for other holidays or selected dates.

My work included:

- Estimating traffic for a selected date and hour
- Measuring congestion relative to recent traffic at each counting point and direction
- Ranking the five locations expected to be most congested at 6:00 PM on Children's Day
- Finding the predicted peak hour for each year
- Building a weekday-by-hour view of expected congestion in May 2030
- Comparing congestion-level distributions from 2026 through 2030

### 3. How the Congestion Score Works

A congestion score of **100% does not mean the road has reached its physical capacity**.

For each counting point and direction, I used the value where the **top 10% of 2025 traffic observations begin** as the 100% reference point.

That means:

- **Above 100%**: busier than the high-traffic range seen in 2025
- **Below 100%**: less busy than that reference level

The score is therefore a **historical comparison**, not a measure of maximum road capacity.

### 4. Key Results

#### Children's Day at 6:00 PM — Top 5 Expected Congestion Locations

![Top 5 expected congestion locations on Children's Day](assets/01_childrens_day_top5.png)

The Omokgyo section appeared repeatedly among the most congested locations.  
The highest value in this analysis was **152.9% in 2028**.

#### Predicted Peak Hour by Year

![Predicted peak congestion hour by year](assets/02_peak_hour_change.png)

The peak was predicted at **8:00 AM from 2026 to 2028**.  
From 2029 onward, the peak shifted into the **afternoon**.

#### Weekday × Hour Pattern for May 2030

![Weekday and hour congestion pattern for May 2030](assets/03_weekday_hour_heatmap.png)

Morning traffic remained high, but the stronger pattern appeared between **3:00 PM and 6:00 PM**.  
**Friday afternoon** stood out as the busiest period in this view.

#### Congestion-Level Mix, 2026–2030

![Congestion level distribution from 2026 to 2030](assets/04_congestion_level_distribution.png)

This chart compares how the share of `Free / Normal / Congested / Very Congested` conditions changes from year to year.

### 5. Team Responsibilities

| Member | Responsibility |
|---|---|
| Sunpil Eom | Quarterly average traffic forecast |
| Seoyoung Yoon | Daily Top 5 / Low 5 traffic forecast |
| Seungbo Sim | Weekday traffic forecast |
| **Jisung Kang** | **Selected-date congestion forecast by time of day** |
| Seungjae Baek | District inflow/outflow traffic forecast |

### 6. Data and Forecasting Workflow

The team built a shared `project_base.py` module so every analysis used the same data-loading and preprocessing steps.

```text
2020–2025 traffic data
        ↓
Load and clean the data
        ↓
Combine traffic records with date and time information
        ↓
Build hourly and weekday analysis tables
        ↓
Estimate 2026–2030 values from historical trends
        ↓
Check error against 2025 observations
        ↓
Run each team member's analysis and create charts
```

The forecast uses a **simple regression model based on year-over-year trends**.  
MAE and R² were used to check how closely the estimates matched observed values.

In plain terms, the model looks at how traffic changed over the previous years and extends that direction into the future.

### 7. Tech Stack

| Area | Tools |
|---|---|
| Language | Python |
| Environment | Google Colab, Jupyter Notebook |
| Data processing | pandas, NumPy |
| Visualization | Matplotlib |
| File handling | pathlib, glob, zipfile, os |
| Evaluation | MAE, R² |

### 8. Repository Structure

```text
.
├── README.md
├── requirements.txt
├── assets/
│   ├── 01_childrens_day_top5.png
│   ├── 02_peak_hour_change.png
│   ├── 03_weekday_hour_heatmap.png
│   └── 04_congestion_level_distribution.png
├── data/
│   └── README.md
└── src/
    ├── project_base.py
    ├── specific_day_congestion.py
    ├── weekday_forecast.py
    ├── quarterly_forecast.py
    ├── district_flow_forecast.py
    └── daily_top_low_forecast.py
```

- `project_base.py` contains the shared preprocessing and forecasting logic.
- `specific_day_congestion.py` contains my selected-date congestion analysis.
- `assets/` contains the main charts used in this README.

### 9. How to Run

The original project was built for **Google Colab**.

1. Prepare the cleaned dataset described in `data/README.md`.
2. Upload the dataset, `src/project_base.py`, and the analysis script to Colab.
3. Install the required packages.

```bash
pip install -r requirements.txt
```

4. To run my part of the project:

```bash
python src/specific_day_congestion.py
```

> Some scripts still assume Colab's `/content` directory.  
> Running them locally requires replacing those fixed paths with configurable ones.

### 10. Limitations

This is an **educational traffic-analysis and forecasting project**, not a production traffic system.

- The 2026–2030 values are estimates based on historical patterns.
- The model does not fully account for future construction, policy changes, public transit changes, weather, or major events.
- The 100% congestion score is a historical reference point, not road capacity.
- A production system would need more data, stronger validation, and comparisons across several forecasting methods.

### 11. What I Would Improve Next

- Replace Colab-specific paths with configurable paths
- Add automated tests for preprocessing and congestion scoring
- Save model metrics and forecast outputs automatically
- Compare the current model with additional forecasting methods
- Add weather, holiday, event, and road-network data
- Package the workflow as a command-line tool or lightweight dashboard

### 12. Data Source

**Seoul Open Data Plaza — Seoul Traffic Volume Information**  
https://data.seoul.go.kr/dataList/OA-15064/L/1/datasetView.do

**Project period:** July 1–22, 2026  
**Project type:** 5-person team project / data analysis and forecasting
