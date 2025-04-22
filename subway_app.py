import streamlit as st
import pandas as pd
import requests
from google.transit import gtfs_realtime_pb2
import zipfile
import io

# Config
GTFS_STATIC_URL = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"
GTFS_RT_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace"

st.set_page_config(page_title="NYC Subway Realtime", layout="wide")
st.title("🚇 NYC Subway Realtime Map")

# Auto-refresh every 15 seconds
st.experimental_rerun(interval=15_000)  # 15 seconds

@st.cache_data(ttl=3600)
def load_stops():
    response = requests.get(GTFS_STATIC_URL)
    z = zipfile.ZipFile(io.BytesIO(response.content))
    stops = pd.read_csv(z.open("stops.txt"))
    return stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]]

stops_df = load_stops()
stops_df = stops_df[stops_df["stop_id"].str.endswith("N")]  # Just northbound for demo

# Station selector
station = st.selectbox("Choose a station:", sorted(stops_df["stop_name"].unique()))
selected = stops_df[stops_df["stop_name"] == station].iloc[0]
st.map(pd.DataFrame([{
    "lat": selected["stop_lat"],
    "lon": selected["stop_lon"]
}]))

# Realtime feed
@st.cache_data(ttl=15)
def get_arrivals(stop_id):
    feed = gtfs_realtime_pb2.FeedMessage()
    r = requests.get(GTFS_RT_URL)
    feed.ParseFromString(r.content)

    times = []
    for entity in feed.entity:
        if entity.HasField("trip_update"):
            for stu in entity.trip_update.stop_time_update:
                if stu.stop_id == stop_id and stu.HasField("arrival"):
                    ts = pd.to_datetime(stu.arrival.time, unit="s")
                    times.append(ts.strftime("%H:%M:%S"))
    return sorted(times)

st.subheader(f"Next arrivals at {station}:")
arrivals = get_arrivals(selected["stop_id"])
if arrivals:
    for time in arrivals[:5]:
        st.write(f"🕒 {time}")
else:
    st.write("No upcoming arrivals.")
