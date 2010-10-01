from django.contrib import admin

from mailer.models import Message, DontSendEntry, MessageLog


class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "to_addresses", "subject", "when_added", "priority"]
    list_filter = ["priority", "when_added"]
    date_hierarchy = "when_added"


class DontSendEntryAdmin(admin.ModelAdmin):
    list_display = ["to_address", "when_added"]
    search_fields = ["to_address"]


class MessageLogAdmin(admin.ModelAdmin):
    list_display = ["id", "to_addresses", "subject", "when_added", "when_attempted", "priority", "result"]
    list_filter = ["result", "priority", "when_added", "when_attempted"]
    date_hierarchy = "when_attempted"


admin.site.register(Message, MessageAdmin)
admin.site.register(DontSendEntry, DontSendEntryAdmin)
admin.site.register(MessageLog, MessageLogAdmin)
