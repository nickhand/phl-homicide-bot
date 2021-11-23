import os

import click
import tweepy
from dotenv import find_dotenv, load_dotenv
from loguru import logger

from homicide_bot.core import check_for_update


@click.group()
def main():
    """Run the homicide bot analysis."""
    pass


@main.command()
@click.option("--dry-run", is_flag=True, help="Dry run only; do not tweet.")
def update(dry_run=False):
    """Run the daily update."""

    # Load any environment variables
    load_dotenv(find_dotenv())

    # Check
    keys = ["CONSUMER_KEY", "CONSUMER_SECRET", "ACCESS_KEY", "ACCESS_SECRET"]
    params = {}
    for key in keys:
        params[key] = os.environ.get(key)
        if params[key] is None:
            raise ValueError(f"Please define the '{key}' environment variable")

    # Setup the tweepy API
    auth = tweepy.OAuthHandler(params["CONSUMER_KEY"], params["CONSUMER_SECRET"])
    auth.set_access_token(params["ACCESS_KEY"], params["ACCESS_SECRET"])
    api = tweepy.API(auth)

    # Get the messages
    messages = check_for_update(dry_run=dry_run)
    if messages is not None:
        status_id = None
        for tweet in messages:

            logger.info(tweet)
            if not dry_run:
                s = api.update_status(
                    status=tweet,
                    in_reply_to_status_id=status_id,
                    auto_populate_reply_metadata=True,
                )
                status_id = s.id
