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
`/srv/www/maproulette`.

Inside this directory, we will place the virtual environment used by
maproulette, in a directory called `venv`.

The app itself will live in the `app` directory in a
directory called `maproulette` (`app/maproulette`).

We will also directories for log files and the uwsgi socket.

In the end, you will end up with an directory structure like:

    /srv/www/maproulette/app
    /srv/www/maproulette/log
    /srv/www/maproulette/venv
    /srv/www/maproulette/uwsgi

All of these should be owned by the web server user. On Debian/Ubuntu,
this is `www-data`, so we will use that as the identifier of the web
user for the remainder of this guide. Feel free to change it as you
see fit on your own installation.

Getting from Git
=================

As the `www-data` user, run:

    git clone https://github.com/osmlab/maproulette.git \
        /srv/www/maproulette/app/maproulette

Virtualenv
==========

We will use `venv` to contain the directory. We should do this
as the final user, which we will assume to be `www-data` in this
guide.

As `www-data` run:

    virtualenv /srv/www/maproulette/venv

You will need to be using the environment set up by that virtualenv,
so now run

    source /srv/www/maproulette/venv/bin/activate

And finally, install the requirements for the project

     pip install -r /srv/www/maproulette/app/maproulette/requirements.txt


UWSGI
======

We will use Uwsgi as the application container. To install it, run:

    apt-get install uwsgi uwsgi-plugin-python

And then create a file `/etc/uwsgi/apps-available/maproulette.ini`
which contains the following:

    [uwsgi]
    plugin = python
    vhost = true
    socket = /srv/www/maproulette/uwsgi/socket
    venv = /srv/www/maproulette/virtualenv
    chdir = /srv/www/maproulette/app/maproulette
    module = maproulette:app

Then, create a symlink from `/etc/uwsgi/apps-enabled/maproulette.ini`
to `/etc/uwsgi/apps-available/maproulette.org` with the command:

    ln -s /etc/uwsgi/apps-available/maproulette.ini \
      /etc/uwsgi/apps-available/maproulette.ini

Nginx
=====

We will use the Nginx web server to serve up our application. To install
it, just run:

    apt-get install nginx

And then create a file in `/etc/nginx/sites-available/maproulette`
containing:

    server {
        listen 80;
        server_tokens off;
        server_name maproulette.org;

         location / {
             include uwsgi_params;
             uwsgi_pass unix:/srv/www/maproulette/uwsgi/socket;
          }

    }


Create a symlink to the enabled sites directory:
    ln -s /etc/nginx/sites-available/maproulette\
    /etc/nginx/sites-enabled/

Finally
========

Restart the services

    service uwsgi restart
    service nginx restart

And the service should be up and running!