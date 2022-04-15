# Generated by Django 3.2.12 on 2022-04-15 14:19

from django.db import migrations, models
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('myinfo', '0003_alter_information_updated_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkShifts',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_path', models.FileField(upload_to='uploads/')),
                ('created_at', models.DateTimeField()),
            ],
            options={
                'verbose_name_plural': 'シフト',
            },
        ),
        migrations.AlterField(
            model_name='information',
            name='body',
            field=tinymce.models.HTMLField(blank=True, null=True),
        ),
    ]