from django import template


register = template.Library()


@register.filter
def negate(value):
    return -value


@register.filter
def intvalue(value):
    return int(value)

@register.filter(name='add_float')
def add_float(value, arg):
    return value + arg

@register.filter
def percentage(value):
    return format(value, ".4%")

@register.filter
def currency(dollars):
    dollars = round(float(dollars), 2)
    return '${:,.2f}'.format(dollars)
