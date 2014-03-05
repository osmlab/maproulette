Welcome to MapRoulette, the powerful & popular bug fixing tool (or is it a game?) for OpenStreetMap.

This README deals with development related topics only. If you are interested in contributing to OpenStreetMap by fixing some bugs through MapRoulette, just head over to [the MapRoulette web site](http://maproulette.org) and get started - it should be pretty self explanatory.

That said, read on if you want to contribute to MapRoulette development and are ready to deploy your local instance.

## Contributing

Please fork the project and submit pull requests on the `develop` branch.

See the code style conventions at https://github.com/osmlab/maproulette/wiki/Code-style-conventions

## Dependencies

First we need to set up system level dependencies. This is different for Linux and OSX.

### Linux

On a fresh Ubuntu 12.04 LTS (also successfully tested on 13.04 and 13.10):

    sudo apt-get install software-properties-common python-software-properties postgresql-server-dev-all python-dev git virtualenvwrapper postgresql-client

Also make sure you have Postgis 2.0+. Ubuntu does not offer Postgis 2.0+ yet as part of their packages, see [here](http://trac.osgeo.org/postgis/wiki/UsersWikiInstall) for guidance. In short:

    sudo apt-get install autoconf libtool libxml2-dev libgeos-dev libproj-dev libgdal-dev
    wget http://download.osgeo.org/postgis/source/postgis-2.x.x.tar.gz
    tar zxvf postgis-2.x.x.tar.gz
    cd postgis-2.x.x
    ./autogen.sh
    ./configure
    make && make install

The above tested on Ubuntu 13.10 only. 

If you want to install the latest PostgreSQL and PostGIS from packages for a non-LTS version of Ubuntu, [this](http://askubuntu.com/a/289388/23679) may help.

### OSX

[See installation with Homebrew](https://gist.github.com/mvexel/5526126)

Note that on Mac OSX you may need to add a symlink to the `coffee` executable:

	ln -s ~/node_modules/coffee-script/bin/coffee /usr/local/bin/

### Setting up the database

Next we need to make sure we have our MapRoulette database instance set up. MapRoulette uses PostgreSQL through the  [http://www.sqlalchemy.org](SQLAlchemy) ORM and the [https://geoalchemy-2.readthedocs.org/en/latest/](GeoAlchemy2) spatial ORM. Unfortunately, GeoAlchemy2 only supports PostgreSQL / PostGIS, so we need to rely on that.

As the `postgres` user:

    createuser -s -P osm

Enter the password `osm` twice.

Now create the three databases for the production, test and dev environments:

    createdb -O osm maproulette
    createdb -O osm maproulette_test
    createdb -O osm maproulette_dev

Now you can switch back to a non-postgres user.

Add PostGIS extensions to the databases:

    psql -h localhost -U osm -d maproulette -c 'CREATE EXTENSION postgis'
    psql -h localhost -U osm -d maproulette_test -c 'CREATE EXTENSION postgis'
    psql -h localhost -U osm -d maproulette_dev -c 'CREATE EXTENSION postgis'

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

Wait for things to be downloaded, compiled and moved into place. There will be warnings, but the process should end with a confirmation that a bunch of python modules were installed.

Ensure that maproulette will be accessible to python:

    add2virtualenv .

Generate a Flask application secret:

    python bin/make_secret.py

Have a look at the configuration defaults at `maproulette/config/__init__.py` and adapt as needed. In particular:

* Set an application secret unique to your instance
* Ensure that the DEFAULT_CHALLENGE exists.

Generate the database tables:

    python manage.py create_db

If you're developing, you may want to load some test challenges and tasks:

    bin/load_fixtures.py

Finally, run the server:

    python manage.py runserver

At this point you should see:

* Running on http://0.0.0.0:5000/
* Restarting with reloader

And you should have a MapRoulette instance at [http://localhost:5000/](http://localhost:5000/)

## Production deployment

We have a guide for production deployment on a Debian flavored linux machine using nginx and uwsgi. See the `docs` folder.

## Migrations

We use [alembic](http://alembic.readthedocs.org/en/latest/) and [Flask-migrate](http://flask-migrate.readthedocs.org/en/latest/) for database migrations. When you first install, `python manage.py db init` will initialize the migration directory and configuration files to sensible defaults - but do check `migrations/alembic.ini`.

Now when you pull a new version of MapRoulette that includes changes to the model, perform a `python manage.db db migrate` and edit the generated migration file in `migrations/versions` removing all references to the `spatial_ref_sys` table. (This is a PostGIS generated table that needs to be excluded from db migrations.) Then perform `python manage.py db upgrade` to migrate the database and bring it back in sync with the model.

## Frameworks used

MapRoulette relies heavily on the lightweight Flask web application framework, and some of its extensions, notably Flask-OAuth, Flask-RESTful, Flask-Script, Flask-Runner and Flask-SQLAlchemy. For working with geospatial data, MapRoulette relies on GeoAlchemy2 and Shapely.

## See also

### API documentation

There is also [API documentation](https://github.com/osmlab/maproulette/wiki/API-Documentation).

### MapRoulette on Amazon EC2

Note that there is also an Amazon EC2 AMI that has all the requirements for MapRoulette already installed and configured. To use, just fire up an instance of `ami-8985f0e0` and

    cd maproulette
    git pull
    workon maproulette
    python manage.py runserver
