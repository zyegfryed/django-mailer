from datetime import datetime, timedelta
from types import StringTypes

from django.contrib.auth.decorators import permission_required
from django.db.models import Count, Max, Min
from django.shortcuts import render_to_response
from django.template import RequestContext

from mailer.models import Message, MessageLog

default_cutoff = timedelta(days=7)

# check one of the permissions dealing with the mailer app
@permission_required("mailer.add_message")
def report(request, cutoff=default_cutoff):
    priorities = dict(Message._meta.get_field("priority").flatchoices)
    pending_messages = list(Message.objects.values("priority").annotate(
            count=Count("priority")).order_by("priority"))
    pending_total = 0
    for item in pending_messages:
        item["name"] = priorities.get(item["priority"])
        pending_total += item["count"]

    pending_dates = Message.objects.aggregate(
            earliest=Min("when_added"), latest=Max("when_added"))

    current_time = datetime.now()
    cutoff_date = current_time - cutoff
    # These queries are atrocious without indexes...
    log_qs = MessageLog.objects.filter(
            when_attempted__gte=cutoff_date).defer("message_data")
    log_stats = log_qs.aggregate(total=Count("id"), latest=Max("when_added"))
    log_success_stats = log_qs.filter(result="1").aggregate(
            total=Count("id"), latest=Max("when_added"))

    dates = log_qs.filter(result="1").values_list("when_added", "when_attempted")
    date_diffs = []
    for date in dates:
        date_diffs.append(date[1] - date[0])
    # this makes the min/max/mean/median code a lot easier
    if len(date_diffs) == 0:
        date_diffs.append(timedelta(seconds=0))
    date_diffs.sort()
    if len(date_diffs) > 1:
        total_delay = sum(date_diffs, timedelta(seconds=0))
        delay_mean = total_delay / (len(date_diffs) - 1)
    else:
        delay_mean = timedelta(seconds=0)

    class DelayLookup(object):
        def __getitem__(self, val):
            if isinstance(val, StringTypes):
                val = val.replace("_", ".")
            rank = float(val) / 100 * len(date_diffs) + 0.5
            return date_diffs[int(rank)]

    delay_pctiles = DelayLookup()

    grouped_errors = log_qs.exclude(result="1").values(
            "result", "log_message").annotate(
            count=Count("id")).order_by("-count")[:20]
    most_recent_errors = MessageLog.objects.exclude(
            result="1").defer("message_data").order_by("-id")[:10]

    context = {
        "pending_messages": pending_messages,
        "pending_total": pending_total,
        "pending_earliest": pending_dates["earliest"],
        "pending_latest": pending_dates["latest"],

        "log_total": log_stats["total"],
        "log_success": log_success_stats["total"],
        "log_latest": log_stats["latest"],
        "log_success_latest": log_success_stats["latest"],

        "delay_min": date_diffs[0],
        "delay_max": date_diffs[-1],
        "delay_mean": delay_mean,
        "delay_pctiles": delay_pctiles,

        "grouped_errors": grouped_errors,
        "most_recent_errors": most_recent_errors,

        "cutoff": cutoff,
        "cutoff_date": cutoff_date,
        "current_time": current_time,
    }
    return render_to_response("mailer/report.html",
            RequestContext(request, context))

