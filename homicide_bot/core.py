from datetime import datetime

import holidays
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil.easter import easter
from loguru import logger

from . import DATA_DIR

NOW = datetime.now()
CURRENT_WEEKDAY = NOW.weekday()
CURRENT_YEAR = NOW.year


def get_holidays():
    """Get holidays."""

    # PA holidays this year
    x = holidays.US(state="PA", years=CURRENT_YEAR)
    names = [
        "New Year's Day",
        "Martin Luther King Jr. Day",
        "Washington's Birthday",
        "Memorial Day",
        "Juneteenth National Independence Day",
        "Independence Day",
        "Labor Day",
        "Columbus Day",
        "Veterans Day",
        "Thanksgiving",
        "Christmas Day",
    ]
    h = {v: k for k, v in x.items() if v in names}

    # Add easter
    h["Good Friday"] = (easter(CURRENT_YEAR) + pd.DateOffset(days=-2)).date()

    return h


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
    date = pd.to_datetime(date).date()

    # Skip weekend updates
    # Don't run if as of date is Friday or Saturday at midnight
    AS_OF_WEEKDAY = date.weekday()
    if AS_OF_WEEKDAY in [4, 5]:
        return

    # Skip holidays too!
    today_is_holiday = NOW.date() in get_holidays().values()
    if today_is_holiday:
        return

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
    fdate = date.strftime("%A %b. %-d, %Y")
    if latest_historic["date"].date() < date:

        messages = []
        change = YTD - latest_historic["total"]

        # Figure out the previous comparison date
        comparison_date = latest_historic["date"]

        # Only one day has elapsed
        if (comparison_date + pd.DateOffset(days=1)).date() == date:
            comparison_string = f"on {fdate}"
        # More than one day has passed
        else:
            previous_fdate = comparison_date.strftime("%A %b. %-d, %Y")
            comparison_string = f"since {previous_fdate}"

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
        fdate2 = date.strftime("%b. %-d, %Y")
        messages.append(
            f"As of 11:59 PM on {fdate2}, there have been {YTD} homicides in Philadelphia,"
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
