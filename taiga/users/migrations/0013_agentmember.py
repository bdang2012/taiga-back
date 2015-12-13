# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_auto_20151202_2224'),
    ]

    operations = [
        migrations.CreateModel(
            name='AgentMember',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('agentid', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='user_agent')),
                ('memberid', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='user_member')),
            ],
            options={
                'verbose_name': 'agentmember',
                'verbose_name_plural': 'agentmembers',
            },
            bases=(models.Model,),
        ),
    ]
