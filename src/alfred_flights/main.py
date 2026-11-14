from pathlib import Path

from alfred_flights.api import create_app


app = create_app(Path(__file__).parents[2] / "data" / "accounts.sqlite3")
