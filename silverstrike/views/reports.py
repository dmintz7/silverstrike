from django.db import models
from django.db.models.functions.datetime import TruncMonth
from django.views import generic

from silverstrike.models import Split


class ReportView(generic.TemplateView):
    template_name = 'silverstrike/reports.html'


class IncomeExpenseReport(generic.TemplateView):
    template_name = 'silverstrike/income_expense_report.html'

    def get_context_data(self, **kwargs):
        context = super(IncomeExpenseReport, self).get_context_data(**kwargs)
        queryset = Split.objects.past().order_by()
        incomes = queryset.income().annotate(m=TruncMonth('date')).values('m').annotate(
            total=models.Sum('amount'))
        expenses = queryset.expense().annotate(m=TruncMonth('date')).values('m').annotate(
            total=models.Sum('amount'))
        incomes = sorted([{'m': x['m'], 'total' : x['total']} for x in incomes], key = lambda i: i['m'])
        expenses = sorted([{'m': x['m'], 'total' : x['total']} for x in expenses], key = lambda i: i['m'])
        result = []
        for i, e in zip(incomes, expenses):
            result.append({
                'month': i['m'],
                'income': i['total'],
                'expense': e['total'],
                'total': i['total'] + e['total']
            })
        context['result'] = result
        return context
