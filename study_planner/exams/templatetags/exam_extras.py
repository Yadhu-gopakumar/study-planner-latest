from django import template

register = template.Library()

@register.filter
def split_options(value, key):
    return value.split(key) if value else []