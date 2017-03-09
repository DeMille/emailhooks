from django.conf.urls import url, include

from . import views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^faq/$', views.faq, name='faq'),

    url(r'^login/$', views.login, name='login'),
    url(r'^logout/$', views.logout, name='logout'),

    url(r'^hooks/$', views.hook_list, name='hook_list'),
    url(r'^hooks/add/$', views.hook_add, name='hook_add'),
    url(r'^hooks/delete/$', views.hook_delete, name='hook_delete'),

    url(r'^hooks/edit/(?P<recipient>[-\w]+)/$',
        views.hook_edit, name='hook_edit'),

    url(r'^hooks/logs/(?P<recipient>[-\w]+)/$',
        views.hook_logs, name='hook_logs'),

    url(r'^_ah/mail/', views.email_handler),
]
