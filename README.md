Welcome to MapRoulette, the powerful & popular bug fixing tool (or is it a game?) for OpenStreetMap.

This README deals with development related topics only. If you are interested in contributing to OpenStreetMap by fixing some bugs through MapRoulette, just head over to [the MapRoulette web site](http://maproulette.org) and get started - it should be pretty self explanatory.

That said, read on if you want to contribute to MapRoulette development and are ready to deploy your local instance.

## Dependencies

First we need to set up system level dependencies. This is different for Linux and OSX.

### Linux

On a fresh Ubuntu 12.04 LTS (also successfully tested on 13.04):

    sudo apt-get install software-properties-common python-software-properties postgresql-server-dev-9.1 python-dev git virtualenvwrapper

Also make sure you have Postgis 2.0+. Ubuntu does not offer Postgis 2.0+ yet as part of their packages, see [here](http://trac.osgeo.org/postgis/wiki/UsersWikiInstall) for guidance.

### OSX

[See installation with Homebrew](https://gist.github.com/mvexel/5526126)

Note that on Mac OSX you may need to add a symlink to the `coffee` executable:
	
	ln -s ~/node_modules/coffee-script/bin/coffee /usr/local/bin/
	
### Setting up the database

Next we need to make sure we have our MapRoulette database instance set up. MapRoulette uses PostgreSQL through the  [http://www.sqlalchemy.org](SQLAlchemy) ORM and the [https://geoalchemy-2.readthedocs.org/en/latest/](GeoAlchemy2) spatial ORM. Unfortunately, GeoAlchemy2 only supports PostgreSQL / PostGIS, so we need to rely on that. 

As the `postgres` user:

    createuser -s -P osm

Enter the password `osm` twice.

    createdb -O osm maproulette

Then as you:

    psql -h localhost -U osm -d maproulette -c 'CREATE EXTENSION postgis'

### Setting up your environment

If you have not used `virtualenvwrapper` before, you should spawn a new shell at this point for the `virtualenvwrapper` scripts to be sourced.

Set up the virtual environment and activate it:

    mkvirtualenv maproulette

### Setting up MapRoulette itself

Clone the repo:

    git clone https://github.com/osmlab/maproulette.git

Install the python requirements:

    cd maproulette/
    pip install -r requirements.txt

Ensure that maproulette will be accessible to python:

    add2virtualenv .

Generate a Flask application secret:

    python bin/make_secret.py
    
Create a configuration file. Start by copying the example and modify as needed:

    cp maproulette/maproulette.cfg.example maproulette/maproulette.cfg

Generate the database tables:

    python manage.py create_db
    
If you're developing, you may want to load a test challenge with 1000 sample tasks:

    bin/load_fixtures.py

And run the server:

    python manage.py runserver

At this point you should see:

* Running on http://0.0.0.0:3000/
* Restarting with reloader

And you should have a MapRoulette instance at [http://localhost:3000/](http://localhost:3000/)

## Frameworks used

MapRoulette relies heavily on the lightweight Flask web application framework, and some of its extensions, notably Flask-OAuth, Flask-RESTful and Flask-Script. We do not use the Flask-SQLAlchemy bindings but rather work directly with the SQLAlchemy (and GeoAlchemy2) ORM frameworks.

## See also

### API documentation

There is also [API documentation](https://github.com/osmlab/maproulette/wiki/API-Documentation).

### MapRoulette on Amazon EC2

Note that there is also an Amazon EC2 AMI that has all the requirements for MapRoulette already installed and configured. To use, just fire up an instance of `ami-8985f0e0` and 

    cd maproulette
    git pull
    workon maproulette
    python manage.py runserver
