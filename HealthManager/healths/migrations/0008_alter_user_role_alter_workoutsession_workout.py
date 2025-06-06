# Generated by Django 5.1.7 on 2025-06-05 03:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('healths', '0007_remove_workout_duration_remove_workoutplan_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('user', 'Người dùng'), ('expert', 'Chuyên gia'), ('Admin', 'admin')], default='user', max_length=20),
        ),
        migrations.AlterField(
            model_name='workoutsession',
            name='workout',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='healths.workout'),
        ),
    ]
