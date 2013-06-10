This is MapRoulette. 

### [API documentation](https://github.com/mvexel/maproulette/wiki/API-Documentation)

## Installation

Note that there is also an Amazon EC2 AMI that has all the requirements for MapRoulette already installed and configured. To use, just fire up an instance of `ami-8985f0e0` and 

    cd maproulette
    git pull
    workon maproulette
    python manage.py runserver

### Dependencies: Linux

On a fresh Ubuntu 12.04 LTS (also successfully tested on 13.04):

    sudo apt-get install python-software-properties
    sudo apt-add-repository -y ppa:ubuntugis/ppa
    sudo apt-get -qq update && sudo apt-get -qq upgrade
    sudo apt-get install postgresql-9.1-postgis postgresql-server-dev-9.1 python-dev git virtualenvwrapper
    sudo su postgres

### Dependencies: OSX

[See installation with Homebrew](https://gist.github.com/mvexel/5526126)

### Setting up the DB

Then as the `postgres` user:

    createuser -s -P osm

Enter the password `osm` twice.

    createdb -O osm maproulette
    exit

Then as you:

    psql -h localhost -U osm -d maproulette -f /usr/share/postgresql/9.1/contrib/postgis-2.0/postgis.sql
    psql -h localhost -U osm -d maproulette -f /usr/share/postgresql/9.1/contrib/postgis-2.0/spatial_ref_sys.sql


Or with PostGIS 2.0

    psql -U osm maproulette

    > CREATE EXTENSION POSTGIS

At this point you should spawn a new shell for the `virtualenvwrapper` scripts to be sourced.

Set up the virtual environment and activate it:

    mkvirtualenv maproulette
    workon maproulette

Clone the repo:

    git clone git://github.com/osmlab/maproulette.git

Install the python requirements:

    cd maproulette/
    pip install -r requirements.txt

Generate a Flask application secret:

    python bin/make_secret.py

Generate the database tables:

    python maproulette/models.py

And run the server:

    python manage.py runserver

At this point you should see:

* Running on http://0.0.0.0:3000/
* Restarting with reloader

And you should have a MapRoulette instance at [http://localhost:3000/](http://localhost:3000/)
