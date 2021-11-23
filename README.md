# homicide-bot

Tweeting information about yesterday's 311 requests in Philadelphia

## Setup

Modify the [philly_311_bot/config.py](philly_311_bot/config.py) file with your [Twitter Developer API tokens](https://www.google.com/search?q=twitter+API+keys&oq=twitter+API+keys&aqs=chrome..69i57j69i64.3196j0j7&sourceid=chrome&ie=UTF-8).

## Running the bot

For daily status updates, run:

```python
python scripts/update.py
```

To reply to mentions, run:

```python
python scripts/reply.py
```
