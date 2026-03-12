from langchain.tools import tool
import requests
import os
from dotenv import load_dotenv
from utils.logger import get_logger

_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")

WEATHERSTACK_ACCESS_KEY = os.getenv("WEATHERSTACK_ACCESS_KEY", "")

if not WEATHERSTACK_ACCESS_KEY:
    raise RuntimeError("Please set WEATHERSTACK_ACCESS_KEY")

# ---------------------------------------------------------
# SERVICE — PUBLIC API (Current Weather API)
# ---------------------------------------------------------

@tool
def get_current_weather(location="Toronto") -> str:
    '''
    Fetches current weather information for a city.
    '''
    try:
        url = f"https://api.weatherstack.com/current?access_key={WEATHERSTACK_ACCESS_KEY}&query={location}"
        _logs.debug(f'url : {url}')
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        temp = data["current"]["temperature"]
        desc = data["current"]["weather_descriptions"]
        _logs.debug(f"The current temperature in {location.title()} is {temp}°C, {desc}.")
        return f"The current temperature in {location.title()} is {temp}°C, {desc}."
    except Exception as e:
        return f"Error fetching weather: {e}"
    