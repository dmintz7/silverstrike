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
        possible_id = [1,2,3,4,5, 6]
        buffet = []
        spent = 0
        income_total = 0
        if len(split):
            for index in range(1,6):
                try:
                    c = split[index-1]
                    id = c['buffet']
                    spent = c['spent']
                    possible_id.remove(id)
 
                    buffet.append({
                       'id': id,
                        'name': get_buffet_type_str(id),
                        'total': spent,
                        'percent': 0,
                    })
    
                    if id == 3: income_total = spent
                except:
                    pass

        for x in possible_id:
            buffet.insert(x-1, {
                       'id': x,
                        'name': get_buffet_type_str(x),
                        'total': spent,
                        'percent': 0,
                    })

        buffet = sorted(buffet, key=lambda x: x['id'] == 5) 
        saving_total = 0
        for buff in buffet:
            if 1 <= buff['id'] <= 3:
                saving_total+=buff['total']
            buff['total'] = abs(buff['total'])
            if income_total > 0:
                buff['percent'] = buff['total'] / income_total
            else:
                buff['percent'] = 0

        if income_total > 0:
            saving_percent =  saving_total/income_total
        else:
            saving_percent = 0
   
        if abs(saving_total) > 0:
            buffet.insert(2, {
                        'id': 6,
                        'name': 'Savings',
                        'total': saving_total,
                        'percent': saving_percent
                     })

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
        context = super(BuffetDetailView, self).get_context_data(**kwargs)
        next_month = self.current_month + relativedelta(months=1)
        two_months_ago = self.current_month - relativedelta(months=2)
        last_month = self.current_month - relativedelta(months=1)
        splits = Split.objects.filter(buffet=buffet,
            account__account_type=Account.PERSONAL,
            date__gte=self.current_month, date__lt=next_month)
        last_two_months_splits = Split.objects.filter(buffet=buffet,
            account__account_type=Account.PERSONAL,
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
            category_spending[s.category] += s.amount

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
      
        context['buffet_name'] = get_buffet_type_str(int(buffet))
        return context
