This is MapRoulette. 

### [API documentation](https://github.com/osmlab/maproulette/wiki/API-Documentation)

## Installation

Note that there is also an Amazon EC2 AMI that has all the requirements for MapRoulette already installed and configured. To use, just fire up an instance of `ami-8985f0e0` and 

    cd maproulette
    git pull
    workon maproulette
    python manage.py runserver

### Dependencies: General

MapRoulette requires [CoffeeScript](http://coffeescript.org/), which can easily be installed using `npm`:

    npm install coffee-script -g
    
Note that you may need to run this as root.

### Dependencies: Linux

On a fresh Ubuntu 12.04 LTS (also successfully tested on 13.04):

    sudo apt-get install software-properties-common python-software-properties postgresql-server-dev-9.1 python-dev git virtualenvwrapper

Also make sure you have Postgis 2.0+. Ubuntu does not offer Postgis 2.0+ yet as part of their packages, see [here](http://trac.osgeo.org/postgis/wiki/UsersWikiInstall) for guidance.

### Dependencies: OSX

[See installation with Homebrew](https://gist.github.com/mvexel/5526126)

Note that on Mac OSX you may need to add a symlink to the `coffee` executable:
	
	ln -s ~/node_modules/coffee-script/bin/coffee /usr/local/bin/
	
### Setting up the DB

Then as the `postgres` user:

    createuser -s -P osm

Enter the password `osm` twice.

    createdb -O osm maproulette

Then as you:

    psql -h localhost -U osm -d maproulette -c 'CREATE EXTENSION postgis'

At this point you should spawn a new shell for the `virtualenvwrapper` scripts to be sourced.

Set up the virtual environment and activate it:

    mkvirtualenv maproulette

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

And run the server:

    python manage.py runserver

At this point you should see:

* Running on http://0.0.0.0:3000/
* Restarting with reloader

And you should have a MapRoulette instance at [http://localhost:3000/](http://localhost:3000/)
