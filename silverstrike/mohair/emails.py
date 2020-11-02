import logging, os, mailbox, schedule, sys, pytz
import time as time
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from silverstrike import models
from silverstrike.mohair import parser
from silverstrike.mohair import utils
# from silverstrike.mohair.utils import remove_unused_accounts
from silverstrike.mohair.utils import match_transaction_recurrence

logger = logging.getLogger(__name__)

def queue():
	while True:
		try:
			logger.info("Creating Queue")
			schedule.every(2).minutes.do(check_new)
			# schedule.every(1).hour.do(remove_unused_accounts)
			logger.info("Starting Schedule")
			schedule.run_all()
			while True:
				schedule.run_pending()
				time.sleep(1)
		except Exception as e:
			logger.error("Error Queue - %s" % e)
			pass
		
def process_email(message, account):
	if account.bank == 'VENMO':
		(account_name, opposing_account, amount, title, notes, date, transaction_type) = parser.venmo_email(message, account.name)
	elif account.bank == 'CHASE':
		(account_name, opposing_account, amount, title, notes, date, transaction_type) = parser.chase_email(message, account.name)
	elif account.bank == 'ALLY':
		(account_name, opposing_account, amount, title, notes, date, transaction_type) = parser.ally_email(message, account.name)
	elif account.bank == 'AMAZON':
                (account_name, opposing_account, amount, title, notes, date, transaction_type) = parser.amazon_email(message, account.name)
	else:
		logger.info("doing nothing")
		return 0

	if not date:
		try:
			date = datetime.strptime(message['Date'], '%a, %d %b %Y %H:%M:%S %z').astimezone(pytz.timezone("US/Eastern")).strftime('%Y%m%d')
		except:
			date = datetime.now(pytz.timezone("US/Eastern")).strftime('%Y%m%d')
					
	amount = str(amount).replace('$','').replace(',','')
	
	logger.info("Email found from %s" % (message['from']))
	try:
		split = utils.create_transaction(date, title, amount, account_name, opposing_account, None, notes, transaction_type)
		match_transaction_recurrence(split)
		data = utils.create_attachment_transaction(split)
		utils.sendMessage('', data)
		models.Email.objects.create(message_id=message['Message-ID'], subject=message['Subject'], email=message['from'].split("<")[1].split(">")[0], account_id=account.id, transaction_id=split.transaction.id)
	except Exception as e:
		logger.error('Error Adding Transaction - %s' % e)
		logger.error('Error on line {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))
	return 1
	
def check_new():
	logger.info("Checking for Emails")
	mbox_file = settings.CONFIG_FOLDER + "/download.mbox"
	os.system("fetchmail -s -f " + settings.CONFIG_FOLDER + "/download.fetchmailrc")
	
	y = 0
	try:
		mbox = mailbox.mbox(mbox_file)
		for message in mbox:
			logger.info("Checking Email from %s" % message['from'])
			try:
				if models.Email.objects.get(message_id=message['Message-ID']):
					logger.info("Email ID: %s, has Already been Processed. Skipping" % (message['Message-ID']))
			except ObjectDoesNotExist:
				try:
					try:
						email = message['from'].split("<")[1].split(">")[0]
					except:
						email = message['from']
						
					account = models.Account.objects.get(email_address=email)
					try:
						y+=process_email(message, account)
					except Exception as e:
						logger.error("Error Adding Message - %s" % e)
						logger.error('Error on line {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))
				except ObjectDoesNotExist:
					logger.info("Unknown Email")
		
		if not mbox:
			logger.info("No Emails Found.")
		else:
			logger.info("%s Emails Found, %s Emails Processed" % (len(mbox), y))
			os.remove(mbox_file)
		
	except Exception as e:
		logger.error("Error Checking for Emails - %s" % e)