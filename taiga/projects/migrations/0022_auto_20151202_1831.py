# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0021_auto_20150504_1524'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='is_kanban_activated',
            field=models.BooleanField(default=True, verbose_name='active kanban panel'),
            preserve_default=True,
        ),
    ]
