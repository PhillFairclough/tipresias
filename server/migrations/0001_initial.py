# Generated by Django 2.1.2 on 2018-10-30 00:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date_time', models.DateTimeField()),
                ('round_number', models.PositiveSmallIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='MLModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('filepath', models.CharField(max_length=500)),
                ('trained_to_match', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='server.Match')),
            ],
        ),
        migrations.CreateModel(
            name='Prediction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('predicted_margin', models.SmallIntegerField()),
                ('match', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='server.Match')),
                ('ml_model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='server.MLModel')),
            ],
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='TeamMatch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('at_home', models.BooleanField()),
                ('score', models.PositiveSmallIntegerField()),
                ('match', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='server.Match')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='server.Team')),
            ],
        ),
        migrations.AddField(
            model_name='prediction',
            name='predicted_winner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='server.Team'),
        ),
    ]
