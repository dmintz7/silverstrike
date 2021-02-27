from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc
from slack.bot import start_bot
from django.conf import settings

scheduler = BackgroundScheduler()
scheduler.configure(timezone=settings.TIME_ZONE)

scheduler.add_job(start_bot)
scheduler.start()
