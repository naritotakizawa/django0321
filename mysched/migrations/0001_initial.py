# Generated by Django 3.0.4 on 2022-03-21 12:19

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MoneyTrans',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transfer', models.DateField(verbose_name='送金日')),
                ('deadline', models.DateField(verbose_name='到着締切')),
                ('entry', models.DateField(verbose_name='登録日')),
                ('fix', models.DateField(verbose_name='承認日')),
                ('setoff', models.DateField(verbose_name='相殺締切')),
            ],
            options={
                'verbose_name_plural': '送金スケジュール',
            },
        ),
    ]
