from datetime import datetime

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from loguru import logger

from . import DATA_DIR

NOW = datetime.now()
CURRENT_WEEKDAY = NOW.weekday()


def load_historic_data():
    """Load the historic data file."""

    path = DATA_DIR / "homicide_totals_daily.csv"
    return pd.read_csv(path, parse_dates=[0])


def check_for_update(dry_run=False):
    """Check for updates"""

    # Parse the website
    url = "https://www.phillypolice.com/crime-maps-stats/"
    soup = BeautifulSoup(requests.get(url).content, "html.parser")

    # Get the table
    table = soup.select_one("#homicide-stats")
    if table is None:
        raise ValueError("No table found to scrape")

    # Year comparison
    years = [int(td.text) for td in table.find("tr").find_all("th")[1:]]

    # check datetime
    date = table.select("tbody")[0].select_one("td").text.split("\n")[0]
    date = pd.to_datetime(date + " 11:59:00")

    # Skip weekend updates
    # Don't run if as of date is Friday or Saturday at midnight
    AS_OF_WEEKDAY = date.weekday()
    if AS_OF_WEEKDAY in [4, 5]:
        return
    print(AS_OF_WEEKDAY)

    # historic
    historic = load_historic_data()
    latest_historic = historic.iloc[-1]

    # Get homicides
    homicides = [table.select("tbody")[0].select(".homicides-count")[0].text]
    homicides += [td.text for td in table.select("tbody")[0].find_all("td")[2:-1]]
    homicides = list(map(int, homicides))

    if len(homicides) != len(years):
        raise ValueError("Length mismatch between parsed years and homicides")

    # Check if we need to update
    YTD = homicides[0]
    fdate = date.strftime("%b %-d, %Y")
    if latest_historic["date"] < date:

        messages = []
        change = YTD - latest_historic["total"]

        # Figure out the previous comparison date
        if AS_OF_WEEKDAY == 6:
            previous_date = date - pd.DateOffset(days=2)
            previous_fdate = previous_date.strftime("%b %-d, %Y")
            comparison_string = f"since Friday {previous_fdate}"
        else:
            comparison_string = f"on {fdate}"

        # Figure out how to state change in homicides
        if change == 1:
            message = f"There was one new homicide in Philadelphia"
        elif change > 1:
            message = f"There were {change} new homicides in Philadelphia"
        else:
            message = f"There were no new homicides in Philadelphia"

        # Combine and save the message
        message = f"{message} {comparison_string}."
        messages.append(message)

        # Create YTD message
        messages.append(
            f"As of 11:59 PM on {fdate}, there have been {YTD} homicides in Philadelphia,"
        )

        # Check historic max
        last_year_homicides = homicides[1]
        last_year = years[1]

        percent_change = 100 * (YTD / last_year_homicides - 1)
        if percent_change > 0:
            messages[-1] += f" an increase of {percent_change:.0f}% from {last_year}."
        elif percent_change == 0:
            messages[-1] += f" equal to the rate from {last_year}."
        else:
            messages[
                -1
            ] += f" a decrease of {abs(percent_change):.0f}% from {last_year}."

        # Save!
        if not dry_run:
            historic.loc[len(historic)] = [date, YTD]
            historic.to_csv(DATA_DIR / "homicide_totals_daily.csv", index=False)

        return messages
