import streamlit as st
import pandas as pd
import requests
import re
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# GitHub에서 최신 population.py 코드 가져오기
GITHUB_RAW_URL = "https://raw.githubusercontent.com/chg0630/DDC_Project/main/population.py"

@st.cache_data
def fetch_github_end_date(current_quarter):
    response = requests.get(GITHUB_RAW_URL)
    if response.status_code == 200:
        match = re.search(r'end_date\s*=\s*["'](\d+)["']', response.text)  # ✅ 수정된 정규표현식
        if match:
            return match.group(1)
    return None

# 현재 연도와 분기 계산
today = datetime.date.today()
current_year = today.year
current_quarter = (today.month - 1) // 3 + 1  # 1~12월 → 1~4분기 변환

# GitHub에서 최신 end_date 가져오기
new_end_date = fetch_github_end_date(f"{current_year}-Q{current_quarter}")

# 분기가 바뀌면 자동 업데이트
if new_end_date and ("end_date" not in st.session_state or st.session_state["end_date"] != new_end_date):
    st.session_state["end_date"] = new_end_date
    st.cache_data.clear()
    st.rerun()

# 최종 end_date 값
end_date = st.session_state["end_date"]

# GitHub 저장소에 업로드된 폰트 파일 경로 설정
font_path = os.path.join(os.path.dirname(__file__), 'NanumGothic.ttf')
fontprop = fm.FontProperties(fname=font_path, size=10)

@st.cache_data
def fetch_population_data(end_date):
    regions = ["41250", "41630", "41650", "41800", "41820", "41150", "41280", "41310", "41360", "41480"]
    start_date = '200801'
    monthly_list = pd.date_range(start="2008-01", end=end_date, freq='M').strftime('%Y%m').tolist()
    filtered_monthly_list = [month for month in monthly_list if month.endswith('01') and (int(month[:4]) - 2008) % 5 == 0]

    all_data = []

    for region in regions:
        for month in filtered_monthly_list:
            month1 = str(int(month) + 411)
            url_page = (f"https://kosis.kr/openapi/Param/statisticsParameterData.do?"
                        f"method=getList&apiKey=ODZlMTM0NGEyYWFlNmRmNzhmMmJhZDRkN2I2OWRmOGE=&"
                        f"itmId=T2+T3+T4+&objL1={region}+&objL2=ALL&objL3=&format=json&"
                        f"jsonVD=Y&prdSe=M&startPrdDe={month}&endPrdDe={month1}&orgId=101&tblId=DT_1B04006")

            response = requests.get(url_page)
            json_data = response.json()

            if 'err' not in json_data:
                data = pd.DataFrame({
                    '연도': [datetime.strptime(f"{x['PRD_DE']}01", '%Y%m%d').strftime('%Y%m') for x in json_data],
                    '시군구': [x['C1_NM'] for x in json_data],
                    '연령별': [x['C2_NM'] for x in json_data],
                    '성별': [x['ITM_NM'] for x in json_data],
                    '인구수': [float(x['DT']) for x in json_data]
                })
                all_data.append(data)

    df_final = pd.concat(all_data, ignore_index=True)
    return df_final

df_final = fetch_population_data()
df_filtered = df_final[df_final['연령별'] != '계']

def group_age(row):
    if row == '100세 이상':
        return '75-99'
    else:
        age = int(row.replace('세', ''))
        if age < 15:
            return '00-14'
        elif 15 <= age <= 24:
            return '15-24'
        elif 25 <= age <= 34:
            return '25-34'
        elif 35 <= age <= 44:
            return '35-44'
        elif 45 <= age <= 54:
            return '45-54'
        elif 55 <= age <= 64:
            return '55-64'
        elif 65 <= age <= 74:
            return '65-74'
        else:
            return '75-99'

df_filtered['연령그룹'] = df_filtered['연령별'].apply(group_age)

st.title("지역별 인구수 시각화")
st.write("KOSIS 데이터를 활용하여 특정 지역의 인구 변화를 시각화합니다.")

regions = df_filtered['시군구'].unique()
selected_region = st.selectbox("시각화할 지역을 선택하세요:", regions)

# # 앱 실행시 자동 캐시 제거 후 재시작
# if "cache_cleared" not in st.session_state:
#     st.cache_data.clear()
#     st.session_state["cache_cleared"] = True

# # 버튼 클릭시 캐시 제거 후 재시작
# if st.button("🔄 캐시 초기화 및 새로고침(관리자용)"):
#     st.cache_data.clear()
#     st.rerun()

fig1, ax1 = plt.subplots(figsize=(10, 6))

df_region = df_filtered[df_filtered['시군구'] == selected_region]
df_grouped = df_region.groupby(['연도', '연령그룹'])['인구수'].sum().reset_index()

age_groups = df_grouped['연령그룹'].unique()
line_styles = ['-', '--', '-.', ':']
for j, age_group in enumerate(age_groups):
    age_group_data = df_grouped[df_grouped['연령그룹'] == age_group]
    line_style = line_styles[j % len(line_styles)]
    ax1.plot(age_group_data['연도'], age_group_data['인구수'], label=age_group, linestyle=line_style, linewidth=2 + (j % 3))

ax1.set_title(f'{selected_region} - 연령 그룹별 인구 변화', fontproperties=fontprop, fontsize=16)
ax1.set_xlabel('YearMonth', fontproperties=fontprop, fontsize=12)
ax1.set_ylabel('Population', fontproperties=fontprop, fontsize=12)
ax1.legend(loc='upper left', bbox_to_anchor=(1, 1))

unique_years = df_grouped['연도'].unique()
tick_positions = list(unique_years[::36])
if tick_positions[-1] != unique_years[-1]:
    tick_positions.append(unique_years[-1])
ax1.set_xticks(tick_positions)
ax1.set_xticklabels(tick_positions, rotation=0, fontproperties=fontprop)

st.pyplot(fig1)

# 두 번째 그래프: 전체 인구 변화 (월별 전체 합계)
fig2, ax2 = plt.subplots(figsize=(10, 6))

# 연도별 인구수 합계 계산
df_total_population = df_region.groupby('연도')['인구수'].sum().reset_index()

# 전체 인구 변화를 선 그래프로 표시
ax2.plot(df_total_population['연도'], df_total_population['인구수'], marker='o', linestyle='-', markersize=3, linewidth=1.5)
ax2.set_title(f"{selected_region}의 인구 변화", fontproperties=fontprop, fontsize=16)
ax2.set_xlabel('YearMonth', fontproperties=fontprop, fontsize=12)
ax2.set_ylabel('Population', fontproperties=fontprop, fontsize=12)

# X축 레이블 간격 설정 (3년 간격 + 데이터의 마지막 날짜 추가)
unique_years = df_total_population['연도'].unique()
tick_positions = list(unique_years[::36])
if tick_positions[-1] != unique_years[-1]:
    tick_positions.append(unique_years[-1])
ax2.set_xticks(tick_positions)
ax2.set_xticklabels(tick_positions, rotation=0, fontsize=8, fontproperties=fontprop)

# Streamlit을 통한 두 번째 그래프 출력
st.pyplot(fig2)
