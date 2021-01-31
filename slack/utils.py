import json, logging, sys
from datetime import datetime
from slackclient import SlackClient

from silverstrike import models
from django.conf import settings

from emails.utils import match_transaction_recurrence
from emails.utils import check_altname


logger = logging.getLogger(__name__)


def create_attachment_transaction(split):
	if isinstance(split, str): split = models.Split.objects.get(id=split)
	match_transaction_recurrence(split)
	logger.info("Creating Attachment for Split %s transferred from %s to %s on %s" % (split.amount, split.account.name, split.opposing_account.name, split.date))
	actions =  [
		{
		'name':'silverstrike_options',
		'text':'Options',
		'type':'select',
		'options':[{"text":"Primary","value":"silverstrike_primary"}, {"text":"Secondary","value":"silverstrike_secondary"}, {"text":"Refresh","value":"silverstrike_refresh"}, {"text":"Split","value":"silverstrike_split"}]
		}
	]

	data=[
		{
		  'title': split.transaction.notes if split.transaction.title in  split.transaction.notes else split.transaction.title,
		  'text': split.transaction.notes if not split.transaction.title in  split.transaction.notes else "", 
		  'color': '#348CB7',
		  'thumb_url':'',
		  'fields': [{'title':'Date' ,'value': split.date.strftime("%Y-%m-%d"),'short':'True'}, {'title': 'Amount','value': '${:,.2f}'.format(split.amount),'short':'True'}, {'title':'Account' ,'value': split.account.name,'short':'True'}, {'title': 'Opposing Account','value': split.opposing_account.name,'short':'True'}, {'title': 'Transaction Type', 'value': split.transaction.get_transaction_type_str(), 'short':'True'}, {'title': 'Recurrence', 'value': split.transaction.recurrence.title if split.transaction.recurrence else None, 'short':'True'}, {'title':'Category', 'value': split.category.name if split.category else None, 'short':'False'}, {'title':'Buffet', 'value': models.get_buffet_type_str(split.buffet) if split.buffet else None, 'short':'False'}],
		  'callback_id': split.id,
		  'actions': actions
		}]
	return data

def sendMessage(response, attachments=None, update=False, ts=False):
	try:
		logger.debug("Sending Message (%s) and Attachments (%s) to User (%s)" % (response, attachments, settings.SLACK_RECIPIENT_ID))

		sc = SlackClient(settings.SLACK_TOKEN)
		if update:
			result = sc.api_call("chat.update", channel=settings.SLACK_CHANNEL, icon_url=settings.HOST + "/static/silverstrike/img/android-chrome-512x512.png", text=response, as_user=False, ts=ts, attachments=json.dumps(attachments))
		else:
			result = sc.api_call("chat.postMessage", channel=settings.SLACK_CHANNEL, icon_url=settings.HOST + "/static/silverstrike/img/android-chrome-512x512.png", text=response, as_user=False, attachments=json.dumps(attachments))
			
		if str(result['ok']) == 'True':
			return "success"
		else:
			logger.error("Failed Sending Message - %s" % result)
			return "fail"
	except Exception as e:
		logger.error("Error Sending Message - Exception: %s" % (e))
		return "error"
		
def create_transaction(date, title, amount, account, opposing_account, category, notes, transaction_type, transaction=None):
		account = models.Account.objects.get(name=account, account_type=models.Account.AccountType.PERSONAL)
		amount = float(amount)
		date = datetime.strptime(date, '%Y%m%d')

		if isinstance(opposing_account, str): opposing_account = check_altname(opposing_account)
		if transaction_type == 'Transfer':
			transaction_type = 'Transfer'
			t_type = models.Transaction.TRANSFER
			if isinstance(opposing_account, str): opposing_account = models.Account.objects.get(name=opposing_account, account_type=models.Account.AccountType.PERSONAL)[0]
		else:
			if isinstance(opposing_account, str): opposing_account = models.Account.objects.get_or_create(name=opposing_account, account_type=models.Account.AccountType.FOREIGN)[0]
			if transaction_type == 'Withdrawal':
				t_type = models.Transaction.WITHDRAW
			elif transaction_type == 'Deposit':
				t_type = models.Transaction.DEPOSIT

		if category:
			category = models.Category.objects.get_or_create(name=category)[0].id
		else:
			category = None

		try:
			if not transaction: transaction = models.Transaction.objects.create(title=title, date=date, transaction_type=t_type, notes=notes, dst_id = opposing_account.id, src_id=account.id, amount=amount)
			main_split = models.Split.objects.create(account_id=account.id, title=title, date=date, opposing_account_id=opposing_account.id, amount=amount, transaction_id=transaction.id, category_id=category)
			models.Split.objects.create(account_id=opposing_account.id, title=title, date=date, opposing_account_id=account.id, amount=-amount, transaction_id=transaction.id, category_id=category)
		except Exception as e:
			logger.error("Error Creating Transaction - %s" % e)
			logger.error('Error on line {}{} {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))
	
		return main_split

def manual_entry(account_type):
	date = datetime.now().strftime("%Y%m%d")
	title = "Manual Entry at %s" % datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
	amount = .01
	account = models.Account.objects.get(name="Wallet", account_type=models.Account.AccountType.PERSONAL)
	opposing_account = models.Account.objects.get_or_create(account_type=models.Account.AccountType.SYSTEM, defaults={'name': 'System Account'})[0]

	split = create_transaction(date, title, amount, account, opposing_account, None, "", account_type)
	data = create_attachment_transaction(split)
	return data