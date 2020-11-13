# Generated by Django 2.2.4 on 2020-11-02 15:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silverstrike', '0013_recurringtransaction_buffet'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recurringtransaction',
            name='buffet',
            field=models.IntegerField(blank=True, choices=[(0, '---------'), (1, 'Need'), (2, 'Want'), (3, 'Income'), (4, 'Ignore')], null=True),
        ),
        migrations.AlterField(
            model_name='split',
            name='buffet',
            field=models.IntegerField(blank=True, choices=[(0, '---------'), (1, 'Need'), (2, 'Want'), (3, 'Income'), (4, 'Ignore')], null=True),
        ),
    ]