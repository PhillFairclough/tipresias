# Generated by Django 2.1.2 on 2018-11-01 03:15

from django.db import migrations, models
import django.db.models.deletion
import server.models


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mlmodel',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='mlmodel',
            name='filepath',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='mlmodel',
            name='trained_to_match',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='server.Match'),
        ),
        migrations.AlterField(
            model_name='team',
            name='name',
            field=models.CharField(max_length=100, unique=True, validators=[server.models.validate_name]),
        ),
    ]