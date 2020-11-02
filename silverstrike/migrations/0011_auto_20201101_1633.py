# Generated by Django 2.2.4 on 2020-11-01 21:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silverstrike', '0010_auto_20201101_1630'),
    ]

    operations = [
        migrations.AddField(
            model_name='split',
            name='buffet',
            field=models.IntegerField(blank=True, choices=[(1, 'Need'), (2, 'Want'), (3, 'Income'), (4, 'Ignore')], null=True),
        ),
        migrations.AddField(
            model_name='split',
            name='slack_ts',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=20, null=True),
        ),
    ]
