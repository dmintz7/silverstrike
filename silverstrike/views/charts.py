from datetime import date

from dateutil.relativedelta import relativedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic

from silverstrike.lib import last_day_of_month
from silverstrike.models import Split

class ChartView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'silverstrike/charts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu'] = 'charts'
        context['today'] = date.today()
        context['minus_3_months'] = date.today() - relativedelta(months=3)
        context['minus_6_months'] = date.today() - relativedelta(months=6)
        context['minus_12_months'] = date.today() - relativedelta(years=1)
        context['minus_24_months'] = date.today() - relativedelta(years=2)
        context['minus_36_months'] = date.today() - relativedelta(years=3)
        context['minus_48_months'] = date.today() - relativedelta(years=4)
        context['minus_60_months'] = date.today() - relativedelta(years=5)
        
        context['max'] = Split.objects.order_by('date').first().date

        context['first_day_of_month'] = date.today().replace(day=1)
        context['last_day_of_month'] = last_day_of_month(date.today())
        return context
