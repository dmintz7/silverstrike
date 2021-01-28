import logging, re, emoji
from html2text import html2text
from datetime import datetime

from silverstrike import models

logger = logging.getLogger(__name__)

def chase_email(message, account_name):
	subject = message['Subject']
	body = html2text(getBody(message))
	
	possible_subjects = ['Your Single Transaction Alert from Chase', 'Your Gas Station Charge Alert from Chase']

	if subject in possible_subjects:
		if subject == possible_subjects[0]:
			start = body.find('Alert settings.') + 16
			end = body.find('Do not reply', start) - 1
			description = body[start:end].replace('\n',' ').strip()

			start = description.find(' at ') + 4
			end = description.find(' has ', start)
			opposing_account = description[start:end].title()

			start = description.find('($USD) ') + 7
			end = description.find(' at ', start)
			amount = description[start:end]
		elif subject == possible_subjects[1]:
			start = body.find('charge.') + 7
			end = body.find('Do not reply', start) - 1
			description = body[start:end].replace('\n',' ').strip().replace('This ', 'A gas station ')

			start = description.find(' at ') + 4
			end = description.find(' on ', start)
			opposing_account = description[start:end].title()
			
			amount = '.01'
			
		try:
			start = description.find(' authorized on ') + 15
			end = description.find(' at ', start)
			date = datetime.strptime(description[start:end], "%b %d, %Y").strftime("%Y%m%d")
		except:
			logger.info("Date Error. Using Today's Date")
			date = datetime.today()
	else:
		logger.info("Doing Nothing")
		
	return (account_name, opposing_account, amount, description[:64], description, date, "Withdrawal")

def venmo_email(message, account_name):
	body = str(message)

	action = venmo_comments(body, '<!-- action -->', 'span')
	actor = venmo_comments(body, '<!-- actor name -->', 'a')
	description = venmo_comments(body, '<!-- note -->', 'p')
	recipient = venmo_comments(body, '<!-- recipient name -->', 'a').replace("=20\n                    ","")
	amount = venmo_comments(body, '<!-- amount -->', 'span')
	date = venmo_comments(body, '<!-- date, audience, and amount -->', 'span')
	
	if action in ['paid','charged']:
		date = datetime.strptime(date[:12], "%b %d, %Y").strftime("%Y%m%d")
		description = emoji.demojize(description).replace('![','').replace(']','')
		amount = amount[amount.find('$')+1:]

		if actor == "You":
			opposing_account = recipient
			if action == 'charged':
				transaction_type = "Deposit"
			elif action == 'paid':
				transaction_type = "Withdrawal"
		elif recipient == "You":
			opposing_account = actor
			if action == 'charged':
				transaction_type = "Withdrawal"
			elif action == 'paid':
				transaction_type = "Deposit"

	re_pattern = re.compile(u'[^\u0000-\uD7FF\uE000-\uFFFF]', re.UNICODE)
	description = re_pattern.sub(u'\uFFFD', description)

	return (account_name, opposing_account, amount, description[:64], description, date, transaction_type)

def ally_email(message, account_name):
	subject = message['Subject']
	body = getBody(message)
	body = html2text(body)

	opposing_account = models.Account.objects.get_or_create(account_type=models.Account.AccountType.SYSTEM, defaults={'name': 'System Account'})[0]

	if 'deposit' in subject.lower(): transaction_type = "Deposit"
	if 'debit' in subject.lower(): transaction_type = "Withdrawal"
	
	start = body.find('$') 
	end = body.find('\n', start)
	end2 = body.find(' ', start)
	if end2<end: end = end2
	amount = body[start:end]

	start = end+1
	end = body.find('.', start)+1
	description = body[start:end].replace('\n',' ').replace('This amount', amount)
	
	return (account_name, opposing_account, amount, description[:64], description, None, transaction_type)

def amazon_email(message, account_name):
	subject = message['Subject'][:64]
	body = getBody(message)
	body = html2text(body)
	opposing_account = "Amazon"

	start = body.find('Hello')
	end = body.find('_______________________________________________________________________________________', start)
	notes = body[start:end].strip()

	if 'refund' in subject.lower():
		transaction_type = "Deposit"

		start = notes.replace('\n', ' ').lower().find('refund total') + 14
		end = notes.find('\n', start)
		end2 = notes.find(' ', start)
		if end2<end: end = end2
		if end == -1: end = len(notes)
		amount = notes[start:end].replace('*', '').replace('$','')
	else:
		transaction_type = "Withdrawal"

		start = notes.replace('\n', ' ').lower().find('view or manage your orders in your orders orders in your orders:')+ 45
		start = notes.replace('\n', ' ').lower().find('order ', start) + 6
		flag = notes[start:start+1]
		
		if flag == "#":
			order_count = 1
		else:
			start = notes.replace('\n', ' ').lower().find('of ', start) + 3
			end = notes.find(' ', start)
			try:
				order_count = int(notes[start:end])
			except:
				order_count = 1
		
		amount = 0
		start = 0
		for x in range(order_count):
			if order_count > 1:
				start = notes.replace('\n', ' ').lower().find('order %s of %s' % (x+1, order_count))
				end = notes.replace('\n', ' ').lower().find('order %s of %s' % (x+2, order_count), start)
				temp_notes = notes[start:end]
			else:
				temp_notes = notes
			if start != -1: end = len(notes)
			for order_type in ['order total','gift card']:
				new_amount = 0
				start = temp_notes.replace('\n', ' ').lower().find(order_type) + len(order_type) + 2
				end = temp_notes.find('====', start)
				end2 = temp_notes.find(' ', start)
				if end2 < end: end = end2
				
				if start != -1 and end != -1:
					try:
						new_amount = float(temp_notes[start:end].replace('*', '').replace('$','').replace('-',''))
					except:
						new_amount = 0
					amount = amount + new_amount
			start = end

	return (account_name, opposing_account, amount, subject, notes, None, transaction_type)

def venmo_comments(body, note, search):
	start = body.find(note) + len(note) + 2
	start = body.find('<%s' % search, start) + len(search) + 1
	start = body.find('>', start) + 1
	end = body.find('</%s>' % search, start)
	body = body[start:end].strip()

	if '<' in body:
		body = html2text(body)
		regex = re.compile(".*?\((.*?)\)")
		result = re.findall(regex, body)
		body = body.replace("(%s)" % result[0], '').replace('\n','')

	return body

def getcharsets(msg):
	charsets = set({})
	for c in msg.get_charsets():
		if c is not None:
			charsets.update([c])
	return charsets

def getBody(msg):
	while msg.is_multipart():
		msg=msg.get_payload()[0]
	t=msg.get_payload(decode=True)
	for charset in getcharsets(msg):
		t=t.decode(charset)
	return t
