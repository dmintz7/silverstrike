import logging, os, mailbox, sys, pytz
from datetime import datetime
from django.conf import settings


from django.core.exceptions import ObjectDoesNotExist

from silverstrike import models
from emails import parser
from slack import utils
from emails.utils import match_transaction_recurrence

logger = logging.getLogger(__name__)

def process_email(message, account):
	if account.bank:
		logger.info("Email found from %s" % (message['from']))
		(opposing_account, amount, title, notes, date, transaction_type) = eval('parser.' + account.bank.lower() + '_email')(message)
		if not date:
			try:
				date = datetime.strptime(message['Date'], '%a, %d %b %Y %H:%M:%S %z').astimezone(pytz.timezone(settings.TIME_ZONE)).strftime('%Y%m%d')
			except:
				date = datetime.now(pytz.timezone(settings.TIME_ZONE)).strftime('%Y%m%d')
		amount = str(amount).replace('$','').replace(',','')
		
		try:
			split = utils.create_transaction(date, title[:64], amount, account.name, opposing_account, None, notes, transaction_type)
			match_transaction_recurrence(split)
			data = utils.create_attachment_transaction(split)
			utils.sendMessage('', data)
			models.Email.objects.create(message_id=message['Message-ID'], subject=message['Subject'], email=message['from'].split("<")[1].split(">")[0], account_id=account.id, transaction_id=split.transaction.id)
		except Exception as e:
			logger.error('Error Adding Transaction - %s' % e)
			logger.error('Error on line {} {} {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))
		return 1
		
	else:
		logger.info("doing nothing")
		return 0
	
def check_new():
	logger.info("Checking for Emails")
	mbox_file = "/app/emails/download.mbox"
	os.system("fetchmail -s -f /app/download.fetchmailrc")
	
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
						logger.error('Error on line {} {} {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))
				except ObjectDoesNotExist:
					logger.info("Unknown Email")
		
		if not mbox:
			logger.info("No Emails Found.")
		else:
			logger.info("%s Emails Found, %s Emails Processed" % (len(mbox), y))
			os.remove(mbox_file)
		
	except Exception as e:
		logger.error("Error Checking for Emails - %s" % e)
		logger.error('Error on line {} {} {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))