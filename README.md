<img src="https://emailhooks.xyz/static/img/name.svg" width="250px;" alt="Emailhooks.xyz">
<br/>
Source for https://emailhooks.xyz


### What is it?
Emailhooks is a service that receives email for you and sends it to your endpoint as a json post request.

It is a python project that runs on google app engine. App engine is **required** for this project because it uses platform specific stuff to receive the incoming mail. It was made with a django variant called [django-nonrel](https://github.com/django-nonrel/djangoappengine) that was modified to run on non-relational databases like app engine's nosql cloud datastore.

More info about emailhooks on the [faq](https://emailhooks.xyz/faq).

If you just want to handle incoming email and don't need a web app interface to add/remove/change recipients, consider running a stand alone receiver with [this project](https://github.com/DeMille/bare-bone-receiver). It's the same basic logic but a single python file.


### How to deploy
- Create a new app engine project ([getting started page](https://cloud.google.com/appengine/docs/standard/python/quickstart))
- Download the google cloud sdk (if you don't have it)
- Clone repo
- Add a django `SECRET_KEY` to `settings.example.py` and rename the file `settings.py`

Deploy with:
```sh
$ gcloud app deploy app.yaml
```

Then you need to deploy the datastore indexes (only the first time or if they have changed since your last deploy):
```sh
$ gcloud app deploy index.yaml
```

Indexes might take some time to process after you deploy them. You can check on their progress from the datastore admin page.


### Development
Run the development server with:
```sh
$ manage.py runserver
```

This runs the app on localhost:8080 and the gcloud dev console on localhost:8000, which lets you look at the datastore, send test email, etc. The `.gaedata` folder that gets created by this is just the development datastore.

Also note that django-nonrel has to be vendored to work on app engine (that's why it's in the repo).


### License

The MIT License (MIT)

Copyright (c) 2014 Sterling DeMille

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.