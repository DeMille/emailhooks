import logging
import hmac
import hashlib

from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.core import paginator
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import Truncator
from django.template.defaultfilters import filesizeformat

from google.appengine.api import urlfetch, users

from .models import EmailHook, Email, LogEntry, GoogleUser
from forms import EmailHookForm


def home(request):
    return render(request, 'home.html')


def faq(request):
    return render(request, 'faq.html')


def logout(request):
    auth.logout(request)
    return redirect(users.create_logout_url(reverse('home')))


def login(request):
    user = auth.authenticate(google_user=users.get_current_user())

    if not user:
        return redirect(users.create_login_url(reverse('login')))

    auth.login(request, user)
    return redirect('hook_list')


@login_required
def hook_list(request):
    hooks = EmailHook.objects.filter(user_id=request.user.user_id)
    return render(request, 'hook_list.html', {'hooks': hooks})


@login_required
def hook_add(request):
    # check that they dont have more than the max per user (10)
    if len(EmailHook.objects.filter(user_id=request.user.user_id)) >= 10:
        return redirect('hook_list')

    form = EmailHookForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        hook = EmailHook(
            user_id=request.user.user_id,
            recipient=form.cleaned_data['recipient'],
            destination=form.cleaned_data['destination'])

        hook.save()
        return redirect('hook_list')

    return render(request, 'hook_add.html', {'form': form})


@login_required
def hook_delete(request):
    if request.method == 'POST':
        hook = get_object_or_404(
            EmailHook,
            user_id=request.user.user_id,
            recipient=request.POST.get('recipient'))

        hook.delete()

    return redirect('hook_list')


@login_required
def hook_edit(request, recipient):
    hook = get_object_or_404(
        EmailHook,
        recipient=recipient,
        user_id=request.user.user_id)

    form = EmailHookForm(request.POST or None, instance=hook)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('hook_list')

    return render(request, 'hook_edit.html', {'form': form})


@login_required
def hook_logs(request, recipient):
    # make sure user owns requested recipient first
    hook = get_object_or_404(
        EmailHook,
        recipient=recipient,
        user_id=request.user.user_id)

    all_logs = LogEntry.objects.filter(
        recipient=recipient,
        destination=hook.destination,
        user_id=request.user.user_id)

    pager = paginator.Paginator(all_logs, 25)

    try:
        logs = pager.page(request.GET.get('page'))
    except paginator.PageNotAnInteger:
        logs = pager.page(1)
    except paginator.EmptyPage:
        logs = pager.page(pager.num_pages)

    return render(request, 'hook_logs.html', {
        'logs': logs,
        'recipient': recipient,
        'destination': hook.destination
    })


@csrf_exempt
def email_handler(request):
    if (len(request.body) > 500 * 1000):
        logging.error('Email too big (%s), ignoring', len(request.body))
        return

    # parse email from request body
    email = Email(request.body)

    logging.info('Incoming message for recipient: %s', email.recipient)

    # get associated hook, if it exists, and its user
    hook = get_object_or_404(EmailHook, recipient=email.recipient)
    user = get_object_or_404(GoogleUser, user_id=hook.user_id)

    payload = email.payload()
    size = len(payload)

    # hmac needs bytes (str() == bytes() in python 2.7)
    signature = hmac.new(
        bytes(user.key),
        bytes(payload),
        hashlib.sha1).hexdigest()

    logging.info('Message matched to user: %s', user.email)
    logging.info(
        '%s attachments, request is about ~%s',
        len(email.attachments),
        filesizeformat(size))

    # keep log of the outgoing request
    entry = LogEntry(
        user_id=user.user_id,
        recipient=email.recipient,
        destination=hook.destination,
        num_attachments=len(email.attachments),
        size=size)

    # try to post to destination
    try:
        url = hook.destination
        headers = {
            'Content-Type': 'application/json',
            'X-Hook-Signature': signature,
        }

        result = urlfetch.fetch(
            url=url,
            headers=headers,
            payload=payload,
            method=urlfetch.POST)

        entry.status_code = result.status_code
        entry.response = Truncator(result.content).chars(100)

        if (result.content == ''):
            entry.response = 'N/A'

        logging.info('Returned %s : %s', entry.status_code, entry.response)
    except urlfetch.Error as err:
        logging.exception('urlfetch error: %s', err)

    entry.save()
    return HttpResponse()
