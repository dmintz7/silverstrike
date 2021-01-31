import logging, json, urllib.parse, sys
from html2text import html2text

from rest_framework.decorators import action
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from slack.utils import manual_entry
from slack.utils import sendMessage
from slack.utils import create_attachment_transaction
from slack.utils import create_transaction
from emails.utils import add_altname

from django.conf import settings
from silverstrike import models

from slackclient import SlackClient
from multiprocessing import Process

logger = logging.getLogger('root')

@action(detail=True, methods=['GET','POST'])
@csrf_exempt
def slack_post(request):
	logger.info("Received Slack Request - %s" % request.method)
	try:
		if request.method == 'POST':
			json_text = json.loads(urllib.parse.unquote_plus(request.body.decode('utf-8'))[8:])
			p1 = Process(target=process_slack, args=[json_text])
			p1.start()
		return HttpResponse(status=200)
	except Exception as ex:
		logger.info(ex)

def process_slack(json_text):
	data = None
	message_type = json_text['type']

	if message_type == 'message' or message_type == 'interactive_message':
		original_message = json_text['original_message']
		ts = original_message['ts']
		actions = json_text['actions'][0]
		name = actions['name']
		callback_id = original_message['attachments'][0]['callback_id']

		logger.info("Slack Bot Name: %s, Callback ID: %s, Timestamp: %s" % (name, callback_id, ts))

		if name in 'silverstrike_refresh':
			data = create_attachment_transaction(callback_id)
		elif name in 'silverstrike_primary':
			silverstrike_primary(json_text)
			data = create_attachment_transaction(callback_id)
		elif name in 'silverstrike_secondary':
			silverstrike_secondary(json_text)
			data = create_attachment_transaction(callback_id)
		elif name in 'silverstrike_split':
			silverstrike_split(json_text)
		elif name in 'silverstrike_manual':
			data = manual_entry(json_text['actions'][0]['selected_options'][0]['value'])
		elif name in 'silverstrike_options':
			value = json_text['actions'][0]['selected_options'][0]['value']
			if value in 'silverstrike_refresh':
				data = create_attachment_transaction(callback_id)
			elif value in 'silverstrike_primary':
				silverstrike_primary(json_text)
				data = create_attachment_transaction(callback_id)
			elif value in 'silverstrike_secondary':
				silverstrike_secondary(json_text)
				data = create_attachment_transaction(callback_id)
			elif value in 'silverstrike_split':
				silverstrike_split(json_text)

		if callback_id != 'manual': models.Split.objects.update_or_create(id=callback_id, defaults={'slack_ts':ts})

		if not data: data = original_message['attachments']
		sendMessage("", data, True, ts)
		logger.info("Message Update Sent")
	elif message_type == 'dialog_submission':
		submissions = json_text['submission']
		command  = json_text['callback_id'].split(';')[0]
		callback_id = json_text['callback_id'].split(';')[1]
		logger.info("Dialog Submission Received: Command: %s, Callback ID: %s" % (command, callback_id))
		
		split = models.Split.objects.get(id=callback_id)
		opposing_split = models.Split.objects.filter(account=split.opposing_account, opposing_account=split.account, amount=-split.amount, transaction=split.transaction.id)[0]
		transaction = models.Transaction.objects.get(id=split.transaction.id)
		ts = split.slack_ts

		if command == "silverstrike-primary":
			logger.info('Modifying Splits %s & %s' % (split.id, opposing_split.id))

			opposing_account = split.opposing_account
			amount = split.amount
			category = split.category
			buffet = split.buffet

			if submissions['opposing_account_select'] or submissions['opposing_account_manual']:
				if transaction.is_transfer:
					opposing_account_name = submissions['opposing_account_select'] if submissions['opposing_account_select'] else submissions['opposing_account_manual']
					opposing_account = models.Account.objects.get_or_create(name=opposing_account_name, account_type=models.Account.AccountType.PERSONAL)[0]
				else:
					opposing_account_name = submissions['opposing_account_select'] if submissions['opposing_account_select'] else submissions['opposing_account_manual']
					opposing_account = models.Account.objects.get_or_create(name=opposing_account_name, account_type=models.Account.AccountType.FOREIGN)[0]
					add_altname(split.opposing_account.name, opposing_account)
			if submissions['amount']:
				if submissions['amount'][:1] == '$':
					amount = float(submissions['amount'][1:].replace(',',''))
				else:
					amount = float(submissions['amount'].replace(',',''))
			if submissions['category']:
				category = models.Category.objects.get(name=submissions['category'])
			if submissions['buffet']:
				buffet = submissions['buffet']
			models.Split.objects.update_or_create(id=callback_id, defaults={'amount': amount, 'opposing_account': opposing_account, 'category': category, 'buffet' : buffet})
			models.Split.objects.update_or_create(id=opposing_split.id, defaults={'amount': -amount, 'account': opposing_account, 'category': category, 'buffet' : buffet})
		elif command == "silverstrike_secondary":
			logger.info('Modifying Splits %s & %s' % (split.id, opposing_split.id))
			
			account = split.account
			date = transaction.date
			title = transaction.title
			notes = transaction.notes
			tran_type = transaction.transaction_type
			recurrence = transaction.recurrence

			if submissions['account']:
				account = submissions['account']
				account = models.Account.objects.get(name=account)
			if submissions['tran_type']:
				tran_type = submissions['tran_type']
			if submissions['title']:
				title = submissions['title'][0:64]
			if submissions['notes']:
				notes = submissions['notes']
			if submissions['recurrence']:
				recurrence = submissions['recurrence']
				recurrence = models.RecurringTransaction.objects.get(title=recurrence)

			try:
				if not transaction.is_split:
					models.Transaction.objects.update_or_create(id=split.transaction.id, defaults={'title':title, 'transaction_type':tran_type, 'notes':notes, 'recurrence':recurrence})
				else:
					models.Transaction.objects.update_or_create(id=split.transaction.id, defaults={'transaction_type':tran_type, 'notes':notes, 'recurrence':recurrence})

				models.Split.objects.update_or_create(id=callback_id, defaults={'account': account, 'title': title})
				models.Split.objects.update_or_create(id=opposing_split.id, defaults={'opposing_account': account, 'title': title})
			except Exception as e:
				logger.error("Error Updating Transaction/Split - %s" % e)
				logger.error('Error on line {} {} {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))

		elif command == "silverstrike_split":
			result = submissions['split_result']
			splits = result.split('\n')

			split= models.Split.objects.get(id=callback_id)

			account = split.account
			title = split.title
			date = split.date.strftime("%Y%m%d")
			opposing_account = split.opposing_account
			amount = split.amount
			category = split.category
			transaction_type = split.transaction.transaction_type
		
			for index, x in enumerate(splits[1:]):
				if amount > 0:
					amount = abs(float(x))
				else:
					amount = -abs(float(x))

				split_loop = create_transaction(date, title, amount, account, opposing_account, category, split.transaction.notes, transaction_type, split.transaction)

				data_loop = create_attachment_transaction(split_loop)
				sendMessage('', data_loop)
			
			if amount > 0:
				amount = abs(float(splits[0]))
			else:
				amount = -abs(float(splits[0]))

			models.Split.objects.update_or_create(id=callback_id, defaults={'amount': amount})
			models.Split.objects.update_or_create(id=opposing_split.id, defaults={'amount': -amount})

		data = create_attachment_transaction(callback_id)
		sendMessage("", data, True, ts)
		logger.info("Message Update Sent")

def silverstrike_primary(json_text):	
	logger.info("Processing Silverstrike Primary Request")
	sc = SlackClient(settings.SLACK_TOKEN)
	original_message = json_text['original_message']
	callback_id = html2text(original_message['attachments'][0]['callback_id']).strip()
	
	split= models.Split.objects.get(id=callback_id)

	opposing_accounts = []
	for x in models.Account.objects.raw("SELECT silverstrike_account.* FROM silverstrike_account LEFT JOIN silverstrike_split ON (silverstrike_split.account_id = silverstrike_account.id) GROUP BY silverstrike_account.id, silverstrike_account.name, silverstrike_account.account_type ORDER BY COUNT(*) ASC"):
		if x.account_type == models.Account.AccountType.PERSONAL and split.transaction.is_transfer:
			opposing_accounts.insert(0, {"label":x.name, "value": x.name})
		elif x.account_type  == models.Account.AccountType.FOREIGN and not split.transaction.is_transfer:
			opposing_accounts.insert(0, {"label":x.name, "value": x.name})

	try:
		opposing_accounts.remove({"label":split.opposing_account.name, "value": split.opposing_account.name})
	except:
		pass

	opposing_accounts = opposing_accounts[:99]
	opposing_accounts = sorted(opposing_accounts, key=lambda x: x['label'],  reverse=False)
	opposing_accounts.insert(0, {"label":split.opposing_account.name, "value": split.opposing_account.name})

	categories = [{"label":'None', "value": 'None'}]
	for name in reversed(models.Category.objects.all().values_list('name')):
		categories.insert(0, {"label":name, "value": name})

	buffet = []
	for value, name in models.BUFFET_TYPES:
		if int(value) != 0: buffet.insert(0, {"label":name, "value": value})

	open_dialog = sc.api_call(
		"dialog.open",
		trigger_id=json_text['trigger_id'],
		dialog={
			"title": "Transaction %s" % split.transaction.id,
			"submit_label": "Submit",
			"callback_id": "silverstrike-primary;%s" % (callback_id),
			"elements": [
					{
						"label": "Opposing Account",
						"type": "select",
						"name": "opposing_account_select",
						"value": "",
						"options": opposing_accounts,
						"optional": "true"
					},
					{
						"label": "Opposing Account",
						"name": "opposing_account_manual",
						"type": "text",
						"value": "",
						"optional": "true"
					},
					{
						"label": "Transaction Amount",
						"type": "text",
						"subtype": "number",
						"name": "amount",
						"value": "",
						"optional": "true"
					},
					{
						"label": "Category",
						"type": "select",
						"name": "category",
						"value":  '',
						"options": categories,
						"optional": "true"
					},
					{
						"label": "Buffet",
						"type": "select",
						"name": "buffet",
						"value":  "",
						"options": buffet,
						"optional": "true"
					}
		]})

	if open_dialog['ok']:
		logger.info("Dialog Successfully Openned")
	else:
		logger.error("Dialog Failed to Open - %s" % open_dialog)

def silverstrike_secondary(json_text):
	logger.info("Processing Silverstrike Secondary Request")
	sc = SlackClient(settings.SLACK_TOKEN)
	original_message = json_text['original_message']
	callback_id = html2text(original_message['attachments'][0]['callback_id']).strip()

	split= models.Split.objects.get(id=callback_id)
	
	accounts = []
	for name, t in models.Account.objects.all().values_list('name', 'account_type'):
		if t == models.Account.AccountType.PERSONAL:
			accounts.insert(0, {"label":name, "value": name})

	try:
		accounts.remove({"label":split.account.name, "value": split.account.name})
	except:
		pass

	accounts = accounts[:98]
	accounts = sorted(accounts, key=lambda x: x['label'],  reverse=False)
	accounts.insert(0, {"label":split.account.name, "value": split.account.name})

	recurrence = []
	for title in models.RecurringTransaction.objects.all().values_list('title'):
		recurrence.insert(0, {"label":title, "value": title})
	recurrence = sorted(recurrence, key=lambda x: x['label'],  reverse=False)

	elements =      [
				{
					"label": "Transaction Title",
					"type": "text",
					"name": "title",
					"value": "",
					"optional": "true",
					"max_length": 64
				},
	
				{
					"label": "Transaction Notes",
					"type": "textarea",
					"name": "notes",
					"value": "",
					"optional": "true"
				},
				{
					"label": "Account",
					"type": "select",
					"name": "account",
					"value": "",
					"optional": "true",
					"options": accounts
				},
				{
					"label": "Transaction Type",
					"type": "select",
					"name": "tran_type",
					"value": "",
					"optional": "true",
					"options": [{"label":"Deposit", "value": "1"},{"label":"Withdraw", "value": "2"},{"label":"Transfer", "value": "3"}]
				}
			]
			
	if recurrence:
		elements.append({
					"label": "Recurrences",
					"type": "select",
					"name": "recurrence",
					"value": "",
					"optional": "true",
					"options": recurrence
				})
			
	open_dialog = sc.api_call(
		"dialog.open",
		trigger_id=json_text['trigger_id'],
		dialog={
			"title": "Transaction %s" % callback_id,
			"submit_label": "Submit",
			"callback_id": "silverstrike_secondary;%s" % (callback_id),
			"elements": elements
		}
	)

	if open_dialog['ok']:
		logger.info("Dialog Successfully Openned")
	else:
		logger.error("Dialog Failed to Open - %s" % open_dialog)

def silverstrike_split(json_text):
	logger.info("Processing Silverstrike Split Request")
	sc = SlackClient(settings.SLACK_TOKEN)
	original_message = json_text['original_message']
	callback_id = html2text(original_message['attachments'][0]['callback_id']).strip()

	open_dialog = sc.api_call(
		"dialog.open",
		trigger_id=json_text['trigger_id'],
		dialog={
			"title": "Split Transaction",
			"submit_label": "Submit",
			"callback_id": "silverstrike_split;%s" % (callback_id),
			"elements": [
					{
						"name": "split_result",
						"label": "Split for Transaction",
						"type": "textarea",
						"hint": "Enter New Amount on Each Line"
					}
				]
		}
	)

	if open_dialog['ok']:
		logger.info("Dialog Successfully Openned")
	else:
		logger.error("Dialog Failed to Open - %s" % open_dialog)
