import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# GitHub 저장소에 업로드된 폰트 파일 경로 설정
font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"  # Colab 및 리눅스 환경 대응
fontprop = fm.FontProperties(fname=font_path, size=10)

@st.cache_data
def fetch_population_data():
    regions = ["41250", "41630", "41650", "41800", "41820", "41150", "41280", "41310", "41360", "41480"]
    start_date = '200801'
    end_date = '202501'
    monthly_list = pd.date_range(start="2008-01", end="2025-01", freq='M').strftime('%Y%m').tolist()
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

if "cache_cleared" not in st.session_state:
    st.cache_data.clear()
    st.session_state["cache_cleared"] = True

st.title("지역별 인구수 시각화")
st.write("KOSIS 데이터를 활용하여 특정 지역의 인구 변화를 시각화합니다.")

regions = df_filtered['시군구'].unique()
selected_region = st.selectbox("시각화할 지역을 선택하세요:", regions)

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
