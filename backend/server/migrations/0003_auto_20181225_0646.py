# Generated by Django 2.1.4 on 2018-12-25 06:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0002_auto_20181101_0315'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mlmodel',
            name='name',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='teammatch',
            name='score',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
