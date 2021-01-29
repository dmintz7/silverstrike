import json, sys, logging
from datetime import datetime
from slackclient import SlackClient

from django.core.exceptions import ObjectDoesNotExist

from silverstrike import models
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)


def add_altname(name, account):
	try:
		account_current = models.Account.objects.filter(name=name)
		if len(list(account_current)) > 0:
			num_trans = len(list(models.Split.objects.filter(account=account_current[0])))
		else:
			num_trans = 0

		if name != account.name and num_trans == 1:
			models.Account_Altname.objects.create(name=name, account_id=account.id)
	except:
		pass

def check_altname(opposing_account):
	try:
		opposing_account = models.Account_Altname.objects.get(name=opposing_account).account
	except ObjectDoesNotExist:
		try:
			opposing_account = models.Account.objects.get(name=opposing_account)
		except ObjectDoesNotExist:
			pass
	return opposing_account
	
def remove_unused_accounts():
	try:
		connection.cursor().execute("DELETE IGNORE FROM silverstrike_account where id not IN (select opposing_account_id as id from silverstrike_split union select account_id from silverstrike_split) and account_type = '2'")
	except:
		logger.error("Error Removing Unused Accounts")
		pass
		

def match_transaction_recurrence(split):
	if split.transaction.transaction_type == models.Transaction.DEPOSIT:
		account = split.opposing_account
		opposing_account = split.account
	else:
		account = split.account
		opposing_account = split.opposing_account

	try:
		recurrence = models.RecurringTransaction.objects.get(transaction_type=split.transaction.transaction_type, src=account, dst=opposing_account)
		if abs(split.date-recurrence.date).days < 3:
			split.transaction.recurrence = recurrence
			recurrence.update_date(save=True)
			split.transaction.save()
	except:
		pass
