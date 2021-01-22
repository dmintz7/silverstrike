from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc
from datetime import datetime

from slack.bot import start_bot

scheduler = BackgroundScheduler()
scheduler.configure(timezone=utc)

scheduler.add_job(start_bot)
scheduler.start()
