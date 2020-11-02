from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc
from datetime import datetime

from silverstrike.mohair.emails import queue
from silverstrike.mohair.utils import remove_unused_accounts
from silverstrike.mohair.slack_bot import start_bot

scheduler = BackgroundScheduler()
scheduler.configure(timezone=utc)

scheduler.add_job(queue, 'interval', minutes=2, next_run_time=datetime.now())
scheduler.add_job(remove_unused_accounts, 'interval', hours=1, next_run_time=datetime.now())
scheduler.add_job(start_bot)
scheduler.start()
