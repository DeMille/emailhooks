from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('',
    (r'^$', 'core.views.home'),
    (r'^login/$', 'core.views.googlelogin'),
    (r'^logout/$', 'core.views.log_user_out'),
    (r'^myRecipients/$', 'core.views.viewWebhooks'),
    (r'^add/$', 'core.views.add'),
    (r'^check/$', 'core.views.check'),
    (r'^delete/$', 'core.views.delete'),
    (r'^edit/$', 'core.views.edit'),
    (r'^details/$', 'core.views.details'),
    (r'^faq/$', 'core.views.faq'),
    (r'^_ah/mail/(?P<catchall>[-\w]+)@emailization.appspotmail.com', 'core.views.email_handler'),
)