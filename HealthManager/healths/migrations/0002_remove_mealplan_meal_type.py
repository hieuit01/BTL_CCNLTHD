# Generated by Django 5.1.7 on 2025-05-03 09:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('healths', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='mealplan',
            name='meal_type',
        ),
    ]
