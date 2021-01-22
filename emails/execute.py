from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc
from datetime import datetime

from emails.process import check_new
from emails.utils import remove_unused_accounts

scheduler = BackgroundScheduler()
scheduler.configure(timezone=utc)

scheduler.add_job(check_new, 'interval', minutes=2, next_run_time=datetime.now())
scheduler.add_job(remove_unused_accounts, 'interval', hours=1, next_run_time=datetime.now())
scheduler.start()