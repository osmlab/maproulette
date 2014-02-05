This document describes production documentation tips.

Overview
=========

MapRoulette has been deployed successfully using uWSGI behind an nginx
web server.

Directory Layout
=================

The production environment we've used stores the base directory for
the web server as `/srv/www`, with the base directory for the
deployment as the fully qualified domain of the server, such as
`maproulette.org`, meaning that the base directory would be
`/srv/www/maproulette.org`.

Inside this directory, we will place the virtual environment used by
maproulette, in a directory called `virtualenv`. We will not create
this directory manually- as it needs to be created by the `virtualenv`
command.


The program itself will live in the standard `htdocs` directory in a
directory called `maproulette` (`htdocs/maproulette`).

We will also create a log directory.

In the end, you will end up with an directory structure like:

    /srv/www/maproulette.org/htdocs
    /srv/www/maproulette.org/logs
    /srv/www/maproulette.org/virtualenv

All of these should be owned by the web server user. On Debian/Ubuntu,
this is `www-data`, so we will use that as the identifier of the web
user for the remainder of this guide. Feel free to change it as you
see fit on your own installation.

Getting from Git
=================

As the `www-data` user, run:

    git https://github.com/osmlab/maproulette.git \
        /srv/www/maproulette.org/htdocs/maproulette

Virtualenv
==========

We will use `virtualenv` to contain the directory. We should do this
as the final user, which we will assume to be `www-data` in this
guide.

As `www-data` run:

    virtualenv /srv/www/maproulette.org/virtualenv

You will need to be using the environment set up by that virtualenv,
so now run

    source /srv/www/maproulette.org/virtualenv/bin/activate

And finally, install the requirements for the project

     pip -i /srv/www/maproulette.org/htdocs/maproulette/requirements.txt

   
UWSGI
======

We will use UWSGI as the application container. To install it, run:

    apt-get install uwsgi uwsgi-plugin-python

And then create a file `/etc/uwsgi/apps-available/maproulette.org`
which contains the following:

    [uwsgi]
    vhost = true
    socket = /tmp/maproulette.org.sock
    venv =   /srv/www/maproulette.org/virtualenv
    chdir =  /srv/www/maproulette.org/htdocs/maproulette
    module = maproulette
    callable = app

Then, create a symlink from `/etc/uwsgi/apps-enabled/maproulette.org`
to `/etc/uwsgi/apps-available/maproulette.org` with the command:

   ln -s /etc/uwsgi/apps-available/maproulette.org \
      /etc/uwsgi/apps-available/maproulette.org

Nginx
=====

We will use the Nginx web server to run our application. To install
it, just run:

    apt-get install nginx

And then create a file in `/etc/nginx/sites-available/maproulette.org`
containing:

    server {
        listen 80;
        server_tokens off;
        server_name maproulette.org;

         location / {
             include uwsgi_params;
             uwsgi_pass unix:/tmp/maproulette.org.sock;
          }

         ## Only requests to our Host are allowed
         if ($host !~ ^(www.maproulette.org|maproulette.org)$ ) {
            return 444;
         }
    }


Which gets symlined to `/etc/nginx/sites-enabled/maproulette.org`

Finally
========

service uwsgi restart
service nginx restart

And the service should be up and running

