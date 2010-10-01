from django.conf.urls.defaults import patterns

urlpatterns = patterns('mailer.views',
    (r'^report/$', 'report'),
)
