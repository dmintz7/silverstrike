from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.views import generic

from silverstrike.lib import last_day_of_month
from silverstrike.models import Account, Split, get_buffet_type_str

class BuffetByMonth(LoginRequiredMixin, generic.TemplateView):
	template_name = 'silverstrike/buffet_by_month.html'

	def dispatch(self, request, *args, **kwargs):
		if 'month' in kwargs:
			self.month = date(kwargs.pop('year'), kwargs.pop('month'), 1)
		else:
			self.month = date.today().replace(day=1)
		return super(BuffetByMonth, self).dispatch(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['menu'] = 'buffet'
		dstart = self.month
		dend = last_day_of_month(dstart)

		split = Split.objects.personal().past().date_range(dstart, dend).order_by('buffet').values('buffet').annotate(spent=Sum('amount'))
		buffet = []
		spent = 0
		income_total = 0
		if len(split):
			for c in split:
				try:
					buffet.append({'id': c['buffet'] if c['buffet'] is not None else 0, 'name': get_buffet_type_str(c['buffet']), 'total': c['spent'], 'percent': 0,})
					if c['buffet'] == 3: income_total = c['spent']
				except:
					pass

		buffet = sorted(buffet, key=lambda x: x['id'] == 5) 
		saving_total = 0
		for buff in buffet:
			if 1 <= buff['id'] <= 3: saving_total+=buff['total']
			if 1 <= buff['id'] <= 2: buff['total'] = -buff['total']
			if income_total > 0:
				buff['percent'] = buff['total'] / income_total
			else:
				buff['percent'] = 0
				
			if buff['id'] == 0: buff['id'] = 7
			if buff['id'] == 4: buff['id'] = 5

		if income_total > 0:
			saving_percent =  saving_total/income_total
		else:
			saving_percent = 0
		
		try:
			if buffet[0]['id'] == 7: buffet.append(buffet.pop(0))
		except:
			pass
		
		buffet.insert(2, {'id': 6, 'name': 'Savings', 'total': saving_total, 'percent': saving_percent})
		
		context['buffet'] = buffet
		context['month'] = self.month
		context['next_month'] = self.month + relativedelta(months=1)
		context['previous_month'] = self.month - relativedelta(months=1)
		return context

class BuffetDetailView(LoginRequiredMixin, generic.DetailView):
	model = Split
	context_object_name = 'buffet'
	template_name = 'silverstrike/buffet_detail.html'

	def dispatch(self, request, *args, **kwargs):
		if 'month' in kwargs:
			self.current_month = date(kwargs.pop('year'), kwargs.pop('month'), 1)
		else:
			self.current_month = date.today().replace(day=1)
		return super(BuffetDetailView, self).dispatch(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		buffet = int(self.request.path.split('/')[2])
		if buffet == 5: buffet = 4
		if buffet == 7: buffet = None
		context = super(BuffetDetailView, self).get_context_data(**kwargs)
		next_month = self.current_month + relativedelta(months=1)
		two_months_ago = self.current_month - relativedelta(months=2)
		last_month = self.current_month - relativedelta(months=1)
		splits = Split.objects.filter(buffet=buffet,
			account__account_type=Account.AccountType.PERSONAL,
			date__gte=self.current_month, date__lt=next_month)
		last_two_months_splits = Split.objects.filter(buffet=buffet,
			account__account_type=Account.AccountType.PERSONAL,
			date__gte=two_months_ago, date__lt=self.current_month)
		sum_last_month = 0
		sum_two_months_ago = 0
		for s in last_two_months_splits:
			if s.date < last_month:
				sum_two_months_ago += s.amount
			else:
				sum_last_month += s.amount
		context['sum_two_months_ago'] = sum_two_months_ago
		context['sum_last_month'] = sum_last_month
		context['average'] = (sum_last_month + sum_two_months_ago) / 2
		splits = splits.select_related('account', 'opposing_account')
		spent_this_month = 0
		account_spending = defaultdict(int)
		destination_spending = defaultdict(int)
		category_spending = defaultdict(int)
		for s in splits:
			spent_this_month += s.amount
			account_spending[s.account] += s.amount
			destination_spending[s.opposing_account] += s.amount
			category_spending[s.category] += -s.amount

		context['sum_this_month'] = spent_this_month
		context['splits'] = splits
		for account in account_spending.keys():
			account_spending[account] = abs(account_spending[account])

		for account in destination_spending.keys():
			destination_spending[account] = abs(destination_spending[account])
		context['account_spending'] = dict(account_spending)
		context['destination_spending'] = dict(destination_spending)
		context['category_spending'] = dict(category_spending)

		context['current_month'] = self.current_month
		context['previous_month'] = last_month
		context['next_month'] = self.current_month + relativedelta(months=1)
		context['month_before'] = two_months_ago
	  
		context['buffet_name'] = get_buffet_type_str(buffet)
		return context
