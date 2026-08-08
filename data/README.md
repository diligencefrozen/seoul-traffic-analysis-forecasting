# Data

The source dataset is Seoul traffic-volume open data from the Seoul Open Data Plaza.

This repository does not include the cleaned traffic dataset used by the team.
To reproduce the analysis in the original Google Colab workflow, prepare a ZIP file containing:

- `seoul_traffic_2020_2025_point_month_weekday_all.csv`
- `seoul_traffic_2020_2025_point_month_hour_all.csv`
- `seoul_traffic_2020_2025_station_master_all.csv`

The original `project_base.py` searches for a ZIP whose filename contains:

`2020~2025 서울특별시 교통량 정제 데이터`

Data source used by the project:
https://data.seoul.go.kr/dataList/OA-15064/L/1/datasetView.do
