from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.shortcuts import *
from django.forms.util import ValidationError, ErrorList

import random, logging, urllib
from urlparse import urljoin
from base64 import urlsafe_b64encode

from google.appengine.api import mail, urlfetch, users
from google.appengine.api.urlfetch import DownloadError 

from core.models import emailHooks, emailPostRequest, GoogleProfile
from forms import AddHookForm

#
#  VIEW LOGIC
#-----------------------------------------------------------------------------------
def home(request):

    return render_to_response('home.html')


#-----------------------------------------------------------------------------------
def faq(request):
    
    try:
        return render_to_response('faq.html', {'email': request.user.email})
    except:
        return render_to_response('faq.html')


#-----------------------------------------------------------------------------------
def log_user_out(request):

    logout(request)
    return HttpResponseRedirect(users.create_logout_url(reverse('core.views.home')))
    

#-----------------------------------------------------------------------------------
def googlelogin(request):

    google_user = users.get_current_user()
    
    if google_user:
        user = authenticate(request=request, google_user=google_user)
        login(request, user)
    else:
        return HttpResponseRedirect(users.create_login_url(reverse('core.views.googlelogin')))
    return redirect('core.views.viewWebhooks')


#-----------------------------------------------------------------------------------
@login_required
def viewWebhooks(request):
    user_id = request.user.google_user_id               
    hooks = emailHooks.objects.filter(google_user_id=user_id)
    if len(hooks)<3:
        canAddMore = True
    else:
        canAddMore = False
    
    return render_to_response('viewHooks.html', {'hooks': hooks,
                                                 'canAddMore': canAddMore,
                                                 'security_key': request.user.security_key,
                                                 'email': request.user.email,
                                                 'nickname': request.user.nickname})

    
#-----------------------------------------------------------------------------------
@login_required
def details(request):
    user_id = request.user.google_user_id
    
    recipient = request.GET.get('recipient')
    script_url = request.GET.get('script_url')
    if recipient is None or script_url is None:
        return redirect('core.views.viewWebhooks')

    else:             
        try:
            details = emailPostRequest.objects.filter(google_user_id=user_id,
                                             recipient=request.GET['recipient'],
                                             script_url=request.GET['script_url']).order_by('-created')[:20]
            if len(details) == 0:
                check = emailHooks.objects.filter(google_user_id=user_id,
                                                  recipient=request.GET['recipient'],
                                                  script_url=request.GET['script_url'])
                if len(check) == 0:
                    return redirect('core.views.viewWebhooks')

            return render_to_response('details.html', {'details': details,
                                                       'empty_details': False,
                                                       'recipient': recipient,
                                                       'script_url': script_url,
                                                       'email': request.user.email})
            
        except emailPostRequest.DoesNotExist:
            return redirect('core.views.viewWebhooks')
    

#-----------------------------------------------------------------------------------
@login_required
def add(request):

    #check again that they dont have more than 3
    user_id = request.user.google_user_id
    hooks = emailHooks.objects.filter(google_user_id=user_id)
    if len(hooks)>=3:
        return redirect('core.views.viewWebhooks')

    #if clear, then show form and process
    form = AddHookForm()
    if request.method == 'POST':
        form = AddHookForm(request.POST)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            script_url = form.cleaned_data['script_url']

            #check to make sure no one else has that hook
            if len(emailHooks.objects.filter(recipient=recipient)) >= 1:
                form._errors['recipient'] = ErrorList(['This recipient is already taken :('])            
                return render_to_response('add.html', {'form': form,
                                                       'email': request.user.email})
            
            #if everything checks out, parse out domain root of the script location
            #and get a rnd str for next step
            #is this really important, maybe not
            hostname = getHostname(script_url)
            word = uri_b64encode(hostname)         
            
            return render_to_response('checkOwnership.html', {'recipient': recipient,
                                                              'script_url': script_url,
                                                              'rndstring': word,
                                                              'domain_root': hostname,
													          'email': request.user.email})

        else:
            #else check this also to get it all in one pass
            if len(emailHooks.objects.filter(recipient=request.POST['recipient'])) >= 1:
                form._errors['recipient'] = ErrorList(['This recipient is already taken :('])            
                return render_to_response('add.html', {'form': form,
                                                       'email': request.user.email})
                
    return render_to_response('add.html', {'form': form,
                                           'email': request.user.email})


#-----------------------------------------------------------------------------------
@login_required
def check(request):
    form = AddHookForm()
    if request.method == 'POST':
        form = AddHookForm(request.POST)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            script_url = form.cleaned_data['script_url']
            file_to_find = request.POST['rndstring']+'.html'
            domain_root = request.POST['domain_root']
           
            validate = URLValidator(verify_exists=True)
            try:
                validate(domain_root+file_to_find)
                                         
                #if it works, run some final validation and save
                user_id = request.user.google_user_id
                hooks = emailHooks.objects.filter(google_user_id=user_id)
                if len(hooks)>=3:
                    return redirect('core.views.viewWebhooks')
                if len(emailHooks.objects.filter(recipient=recipient)) >= 1 and request.POST['edit'] == False:
                    return redirect('core.views.viewWebhooks')               
                
                #if this is an edit, delete old entry
                if request.POST['edit'] == 'True':
                    old_url = request.POST['old_url']
                    old_recipient = request.POST['old_recipient']
                    
                    try:
                        hook = emailHooks.objects.filter(google_user_id=user_id,
                                                      recipient=old_recipient,
                                                      script_url=old_url)
                        hook.delete()
                    except emailHooks.DoesNotExist:
                        return redirect('core.views.viewWebhooks')
                
                #and save                
                newHook = emailHooks(script_url=script_url,
                                     google_user_id=user_id,
                                     recipient=recipient)
                newHook.save()
                return redirect('core.views.viewWebhooks') 

            except ValidationError:
                ownershipCheckFail = True            
                return render_to_response('checkOwnership.html', {'recipient': recipient,
                                     'script_url': script_url,
                                     'rndstring': request.POST['rndstring'],
                                     'domain_root':domain_root,
                                     'ownershipCheckFail': ownershipCheckFail,
                                     'email': request.user.email})
    
    return redirect('core.views.add')


#-----------------------------------------------------------------------------------
@login_required
def delete(request):

    recipient = request.GET.get('recipient')
    if recipient is None:
        return redirect('core.views.viewWebhooks')
        
    user_id = request.user.google_user_id    
    try:
        hook = emailHooks.objects.filter(google_user_id=user_id,
                                         recipient=request.GET['recipient'])
        hook.delete()
        return redirect('core.views.viewWebhooks') 
    except emailHooks.DoesNotExist:
        return redirect('core.views.viewWebhooks')


#-----------------------------------------------------------------------------------
@login_required
def edit(request):

    if request.method == 'POST':
        form = AddHookForm(request.POST)
        if form.is_valid():
            recipient = form.cleaned_data['recipient']
            script_url = form.cleaned_data['script_url']
            old_recipient = request.POST['old_recipient']
            old_url = request.POST['old_url']

            new_domain = getHostname(script_url)
            old_domain = getHostname(old_url)

            if recipient != old_recipient:
                #check to make sure no one else has that hook
                if len(emailHooks.objects.filter(recipient=recipient)) >= 1:
                    form._errors['recipient'] = ErrorList(['That recipient is already taken :('])            
                    return render_to_response('edit.html', {'form': form,
                                                            'old_recipient': old_recipient,
                                                            'old_url': old_url,
                                                            'email': request.user.email})
            
            if new_domain != old_domain:
                
                #send to check ownership again                
                hostname = getHostname(script_url)
                word = uri_b64encode(hostname)
                return render_to_response('checkOwnership.html', {'recipient': recipient,
                                                         'script_url': script_url,
                                                         'rndstring': word,
                                                         'domain_root': hostname,
                                                         'edit': True,
                                                         'old_recipient': old_recipient,
                                                         'old_url': old_url,
                                                         'email': request.user.email})
            
            #if all is good then delete the old one and save the new
            try:
                user_id = request.user.google_user_id  
                hook = emailHooks.objects.filter(google_user_id=user_id,
                                                 recipient=old_recipient,
                                                 script_url=old_url)
                hook.delete()
            except emailHooks.DoesNotExist:
                return redirect('core.views.viewWebhooks')
                     
            newHook = emailHooks(script_url=script_url,
                                 google_user_id=user_id,
                                 recipient=recipient)
            newHook.save()
            return redirect('core.views.viewWebhooks')

        else:
            return render_to_response('edit.html', {'form': form,
                                  'old_recipient': request.POST['old_recipient'],
                                  'old_url': request.POST['old_url'],
                                  'email': request.user.email})          
    
    try:    
        recipient=request.GET['recipient']        
        try:
            user_id = request.user.google_user_id
            hookInstance = emailHooks.objects.get(google_user_id=user_id,
                                                  recipient=recipient)
            form = AddHookForm({'recipient': hookInstance.recipient,
                                'script_url': hookInstance.script_url})

            return render_to_response('edit.html', {'form': form,
                                            'old_recipient': hookInstance.recipient,
                                            'old_url': hookInstance.script_url,
                                            'email': request.user.email})

        except ObjectDoesNotExist:
            return redirect('core.views.viewWebhooks')
    except:
        return redirect('core.views.viewWebhooks')
  


#
# FCTs USED REPEATEDLY
#-----------------------------------------------------------------------------------
def getHostname(script_url):
    hostname = urljoin(script_url,' ').rstrip()
    return hostname

def uri_b64encode(s):
    return urlsafe_b64encode(s).strip('=')[:10]
        
		
		
#
# EMAIL PROCESSING
#-----------------------------------------------------------------------------------
 
def email_handler(request, catchall):
    if request.POST:
        message = mail.InboundEmailMessage(request.raw_post_data)        
        
        # pull out the emailization recipient from the
		# Delivered-To: _____ @emailization.com part of the original
		# This works because its being redirected from the catchall
		# otherwise it would fail
        original = str(message.original)
        start = original.index('Delivered-To: ') + len('Delivered-To: ')
        end = original.index('@emailization.com', start)
        recipient = original[start:end]
        		
        hook = emailHooks.objects.get(recipient=recipient)
        user = GoogleProfile.objects.get(google_user_id=hook.google_user_id)        

        url = hook.script_url
        logging.info('Received message for user: ' + user.email)
        
        security_key = user.security_key

        plaintext_body = list(message.bodies(content_type='text/plain'))[0]
        plaintext_body = plaintext_body[1].decode()
        		
        html_bodies = message.bodies('text/html')
        decoded_html = ''

        for content_type, body in html_bodies:
            decoded_html += body.decode()

        try:
            cc = message.cc
        except:
            cc = ''

        try:
            subject = message.subject
        except:
            subject = ''
              
        form_fields = {
            'sender': message.sender,
            'to': message.to,
            'cc': cc,
            'date': message.date,
            'subject': subject,
            'plaintext_body': plaintext_body,
            'html_body': decoded_html,
            'security_key': security_key
        }	

        form_data = urllib.urlencode(form_fields)
		    
        try:        
            logging.info('saving...')
            result = urlfetch.fetch(url=url,
                            payload=form_data,
                            method=urlfetch.POST,
                            headers={'Content-Type': 'application/x-www-form-urlencoded'})

            status_code = result.status_code
            logging.info(status_code)

            response = result.content

            if response == '':
                response = 'N/A'
            else:            
                response = (response[:50] + '..') if len(response) > 75 else response
            
            newRequestResponse = emailPostRequest(status_code = status_code,
                                                  returned_response = response,
                                                  sender = message.sender,
                                                  subject = subject,
                                                  google_date = message.date,
                                                  script_url = url,
                                                  google_user_id = hook.google_user_id,
                                                  recipient = recipient)

            newRequestResponse.save()          

        except DownloadError:
            logging.info('timeout!')

            newRequestResponse = emailPostRequest(status_code = '408',
                                                  returned_response = 'Request Timeout',
                                                  sender = message.sender,
                                                  subject = subject,
                                                  google_date = message.date,
                                                  script_url = url,
                                                  google_user_id = hook.google_user_id,
                                                  recipient = recipient)

            newRequestResponse.save() 
            
    return HttpResponse('done!')