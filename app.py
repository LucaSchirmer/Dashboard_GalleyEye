"""FSAIR Streamlit entrypoint."""

from pathlib import Path

import streamlit as st

from galleyeye.data import DataValidationError, load_data


ROOT = Path(__file__).resolve().parent
st.set_page_config(
    page_title="FSAIR · Airline Catering Intelligence", page_icon="✈️", layout="wide"
)

# Import after page configuration so the dashboard's original blue sidebar
# styling is registered before data loading and rendering.
from galleyeye.dashboard import render_dashboard


@st.cache_data(show_spinner=False)
def get_data():
    return load_data(ROOT / "data")


try:
    data = get_data()
except DataValidationError as exc:
    st.error(f"Dashboard blocked by invalid data: {exc}", icon="🚫")
    st.info("Correct the named repository CSV and restart the application.")
    st.stop()

render_dashboard(data)
