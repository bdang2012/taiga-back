# Copyright (C) 2014 Andrey Antukh <niwi@niwi.be>
# Copyright (C) 2014 Jesús Espino <jespinog@gmail.com>
# Copyright (C) 2014 David Barragán <bameda@dbarragan.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext as _

from taiga.projects.history import services as history_services
from taiga.projects.models import Project
from taiga.users.models import User
from taiga.projects.history.choices import HistoryType
from taiga.timeline.service import (push_to_timeline,
                                    build_user_namespace,
                                    build_project_namespace,
                                    extract_user_info)

# TODO: Add events to followers timeline when followers are implemented.
# TODO: Add events to project watchers timeline when project watchers are implemented.


def _push_to_timeline(*args, **kwargs):
    if settings.CELERY_ENABLED:
        push_to_timeline.delay(*args, **kwargs)
    else:
        push_to_timeline(*args, **kwargs)


def _push_to_timelines(project, user, obj, event_type, created_datetime, extra_data={}):
    if project is not None:
        # Actions related with a project

        ## Project timeline
        _push_to_timeline(project, obj, event_type, created_datetime,
            namespace=build_project_namespace(project),
            extra_data=extra_data)

        ## User profile timelines
        ## - Me
        related_people = User.objects.filter(id=user.id)

        ## - Owner
        if hasattr(obj, "owner_id") and obj.owner_id:
            related_people |= User.objects.filter(id=obj.owner_id)

        ## - Assigned to
        if hasattr(obj, "assigned_to_id") and obj.assigned_to_id:
            related_people |= User.objects.filter(id=obj.assigned_to_id)

        ## - Watchers
        watchers = getattr(obj, "watchers", None)
        if watchers:
            related_people |= obj.watchers.all()

        ## - Exclude inactive and system users and remove duplicate
        related_people = related_people.exclude(is_active=False)
        related_people = related_people.exclude(is_system=True)
        related_people = related_people.distinct()

        _push_to_timeline(related_people, obj, event_type, created_datetime,
            namespace=build_user_namespace(user),
            extra_data=extra_data)
    else:
        # Actions not related with a project
        ## - Me
        _push_to_timeline(user, obj, event_type, created_datetime,
            namespace=build_user_namespace(user),
            extra_data=extra_data)


def _clean_description_fields(values_diff):
    # Description_diff and description_html if included can be huge, we are
    # removing the html one and clearing the diff
    values_diff.pop("description_html", None)
    if "description_diff" in values_diff:
        values_diff["description_diff"] = _("Check the history API for the exact diff")


def on_new_history_entry(sender, instance, created, **kwargs):

    if instance._importing:
        return

    if instance.is_hidden:
        return None

    model = history_services.get_model_from_key(instance.key)
    pk = history_services.get_pk_from_key(instance.key)
    obj = model.objects.get(pk=pk)
    project = obj.project

    if instance.type == HistoryType.create:
        event_type = "create"
    elif instance.type == HistoryType.change:
        event_type = "change"
    elif instance.type == HistoryType.delete:
        event_type = "delete"

    user = User.objects.get(id=instance.user["pk"])
    values_diff = instance.values_diff
    _clean_description_fields(values_diff)

    extra_data = {
        "values_diff": values_diff,
        "user": extract_user_info(user),
        "comment": instance.comment,
        "comment_html": instance.comment_html,
    }

    # Detect deleted comment
    if instance.delete_comment_date:
        extra_data["comment_deleted"] = True

    created_datetime = instance.created_at
    _push_to_timelines(project, user, obj, event_type, created_datetime, extra_data=extra_data)


def create_membership_push_to_timeline(sender, instance, **kwargs):
    """
    Creating new membership with associated user. If the user is the project owner we don't
    do anything because that info will be shown in created project timeline entry

    @param sender: Membership model
    @param instance: Membership object
    """

    # We shown in created project timeline entry
    if not instance.pk and instance.user and instance.user != instance.project.owner:
        created_datetime = instance.created_at
        _push_to_timelines(instance.project, instance.user, instance, "create", created_datetime)

    # Updating existing membership
    elif instance.pk:
        try:
            prev_instance = sender.objects.get(pk=instance.pk)
            if instance.user != prev_instance.user:
                created_datetime = timezone.now()
                # The new member
                _push_to_timelines(instance.project, instance.user, instance, "create", created_datetime)
                # If we are updating the old user is removed from project
                if prev_instance.user:
                    _push_to_timelines(instance.project,
                                       prev_instance.user,
                                       prev_instance,
                                       "delete",
                                       created_datetime)
        except sender.DoesNotExist:
            # This happens with some tests, when a membership is created with a concrete id
            pass


def delete_membership_push_to_timeline(sender, instance, **kwargs):
    if instance.user:
        created_datetime = timezone.now()
        _push_to_timelines(instance.project, instance.user, instance, "delete", created_datetime)


def create_user_push_to_timeline(sender, instance, created, **kwargs):
    if created:
        project = None
        user = instance
        _push_to_timelines(project, user, user, "create", created_datetime=user.date_joined)
