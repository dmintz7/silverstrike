import time, logging, sys
from slackclient import SlackClient
from datetime import datetime
from django.conf import settings

from slack.utils import sendMessage

logger = logging.getLogger('root')

def start_bot():
	try:
		logger.info("Creating Slack Bot")
		while True:
			try:
				Bot()
				time.sleep(1)
			except Exception as e:
				logger.error("ERROR Slack Bot: %s" % e)
				logger.error('Error on line {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))
	except Exception as e:
		logger.error("Error Slack Queue - %s" % e)
		logger.error('Error on line {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))

class Bot(object):
	def __init__(self):
		self.slack_client = SlackClient(settings.SLACK_TOKEN)
		self.bot_name = settings.SLACK_RECIPIENT_ID
		self.bot_id = self.get_bot_id()
		if self.bot_id is None: exit("Error, could not find " + self.bot_name)
		self.event = Event(self)
		self.listen()
	
	def get_bot_id(self):
		api_call = self.slack_client.api_call("users.list")
		if api_call.get('ok'):
			users = api_call.get('members')
			for user in users:
				if 'name' in user and user.get('name') == self.bot_name:
					return "<@" + user.get('id') + ">"
			
			return None
			
	def listen(self):
		if self.slack_client.rtm_connect(with_team_state=False):
			logger.info("Successfully connected, listening for commands")
			while True:
				self.event.wait_for_event()
				time.sleep(1)
		else:
			exit("Error, Connection Failed")

class Command(object):
	def __init__(self):
		self.message = None
		self.date_sent = None
		self.commands = { 
			"manual": self.manual,
			"help" : self.help
		}

	def handle_command(self, user, text, date_sent):
		response = ""
		try:
			self.date_sent = date_sent
			logger.info(date_sent)
			command = text.lower()
			if command in self.commands:
				response = self.commands[command]()
				logger.info(response)
			else:
				response = "Sorry I don't understand the command: " + text + ". " + self.help()
		except Exception as e:
			logger.info("Error Handling Command - %s" % e)
			response = ""
			
		return response
		
	def manual(self):
		data=[
		{
		'title': "Silverstrike Transaction",
		'text': "Choose a Transaction Type",
		'color': '#348CB7',
		'thumb_url':'',
		'callback_id': 'manual',
		'actions': [{
			'name':'silverstrike_manual',
			'text':'Transaction Type',
			'type':'select',
			'options':[{"text":"Withdrawal", "value":"Withdrawal"}, {"text":"Deposit", "value":"Deposit"}, {"text":"Transfer", "value":"Transfer"}]
			}]
		}]
		return data

	def help(self):	
		response = "Currently I support the following commands:\r\n"
		
		for command in self.commands:
			response += command + "\r\n"
			
		return response

class Event:
	def __init__(self, bot):
		self.bot = bot
		self.command = Command()
		self.event = ""

	def wait_for_event(self):
		events = self.bot.slack_client.rtm_read()
		if events and len(events) > 0:
			for event in events:
				try:
					self.parse_event(event)
				except:
					pass

	def parse_event(self, event):
		if event and 'text' in event:
			try:
				user = event['user']
			except:
				user = event['username']
			try:
				text = event['text'].split(self.bot.bot_id)[1].strip()
			except:
				text = event['text']
			self.event = event
			self.handle_event(user, text)

	def handle_event(self, user, command):
		if command and self.event['channel']:
			try:
				date_sent_format = datetime.fromtimestamp(float(self.event['event_ts']))
				logger.info("Received command: " + command + " in channel: " + self.event['channel'] + " from user: " + user + " at " + date_sent_format.strftime("%Y-%m-%d %I:%M:%S %p"))
				response = self.command.handle_command(user, command, date_sent_format)
				if response != "":
					sendMessage("", response)
			except:
				logger.error("Error Slack Handling Event")
				pass