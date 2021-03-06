# Generated by Django 2.2 on 2021-10-30 08:25

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleCategory',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, max_length=100)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'verbose_name': '文章类别管理',
                'verbose_name_plural': '文章类别管理',
                'db_table': 'tb_category',
            },
        ),
    ]
