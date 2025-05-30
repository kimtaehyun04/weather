import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv
import os
import pydeck as pdk

# --- API 키 로드 ---
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_today_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric&lang=kr"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    today = datetime.now().date()
    hourly_data = []

    for entry in data["list"]:
        dt = datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
        if dt.date() == today:
            temp = entry["main"]["temp"]
            weather = entry["weather"][0]["description"]
            time = dt.strftime("%H:%M")
            hourly_data.append({
                "시간": time,
                "기온(°C)": temp,
                "날씨": weather
            })

    return pd.DataFrame(hourly_data)

def get_5_day_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric&lang=kr"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    daily_data = {}

    for entry in data["list"]:
        dt_txt = entry["dt_txt"]
        date_str = dt_txt.split(" ")[0]
        temp = entry["main"]["temp"]
        weather_desc = entry["weather"][0]["description"]

        if date_str not in daily_data:
            daily_data[date_str] = {"temps": [], "weather": []}

        daily_data[date_str]["temps"].append(temp)
        daily_data[date_str]["weather"].append(weather_desc)

    result = []
    for date, info in daily_data.items():
        avg_temp = round(sum(info["temps"]) / len(info["temps"]), 1)
        common_weather = Counter(info["weather"]).most_common(1)[0][0]
        result.append({
            "날짜": date,
            "평균기온(°C)": avg_temp,
            "대표날씨": common_weather
        })

    return pd.DataFrame(result)

def get_city_coord(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    lat = data["coord"]["lat"]
    lon = data["coord"]["lon"]
    return lat, lon

st.set_page_config(layout="wide")
st.title("🌤️ 날씨 정보 (OpenWeatherMap)")

# --- 세션 상태 초기화 ---
if "prev_city" not in st.session_state:
    st.session_state["prev_city"] = ""
if "map_zoom" not in st.session_state:
    st.session_state["map_zoom"] = 5.5

col_map, col_main = st.columns([1.2, 2])

with col_main:
    st.subheader("도시별 날씨 조회")
    city = st.text_input("도시 이름을 입력하세요 (예: Seoul, Busan, Jeju)")

    # city가 변경됐을 때 zoom 초기화
    if city != "" and city != st.session_state["prev_city"]:
        st.session_state["map_zoom"] = 5.5
        st.session_state["prev_city"] = city

    if city:
        tab1, tab2 = st.tabs(["📅 오늘 시간별 날씨", "📆 5일간 일별 요약"])

        with tab1:
            st.subheader("📅 오늘 시간별 날씨")
            df_today = get_today_weather(city)
            if df_today is not None and not df_today.empty:
                st.dataframe(df_today)
                if any("비" in w or "소나기" in w for w in df_today["날씨"]):
                    st.info("☔ 우산을 들고 가는 것을 추천합니다!")
                else:
                    st.info("☀ 오늘은 우산이 필요 없을 것 같아요.")
            else:
                st.warning("오늘의 시간별 날씨 데이터를 가져올 수 없습니다.")

        with tab2:
            st.subheader("📆 5일간 일별 요약")
            df_week = get_5_day_weather(city)
            if df_week is not None and not df_week.empty:
                st.dataframe(df_week)
            else:
                st.warning("5일간 일별 날씨 데이터를 가져올 수 없습니다.")
    else:
        st.info("왼쪽 지도에서 위치를 참고해 도시 이름을 입력하세요.")

with col_map:
    st.subheader("🗺️ 지도")

    if city:
        coord = get_city_coord(city)
        if coord:
            lat, lon = coord
        else:
            lat, lon = 36.5, 127.8
    else:
        lat, lon = 36.5, 127.8

    zoom = st.session_state["map_zoom"]

    view_state = pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=zoom,
        pitch=0
    )

    df_marker = pd.DataFrame({
        "위도": [lat],
        "경도": [lon]
    })

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_marker,
        get_position='[경도, 위도]',
        get_fill_color='[0, 128, 255, 160]',
        get_radius=10000
    )

    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=[layer]
    ))
