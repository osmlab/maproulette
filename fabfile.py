from fabric.api import run
from fabric.colors import red
from fabric.contrib.files import exists, cd, upload_template, sed
from fabric.contrib.project import rsync_project
from fabric.operations import sudo

pg_hba_fname = "/etc/postgresql/9.3/main/pg_hba.conf"


def restart_nginx():
    sudo('service nginx restart')


def restart_uwsgi():
    sudo('service uwsgi restart')


def restart_postgres():
    sudo('service postgresql restart')


def update_packages():
    sudo('apt-get -qq update')


def upgrade_packages():
    sudo('apt-get -q dist-upgrade')


def reboot_server():
    sudo('reboot')


def install_packages():
    packages = ["software-properties-common",
                "python-software-properties",
                "python-dev",
                "git",
                "virtualenvwrapper",
                "nginx",
                "uwsgi",
                "uwsgi-plugin-python"]
    sudo('apt-get -q -y --no-upgrade install %s' %
         ' '.join(packages), shell=False)


def create_deploy_directories(instance):
    basedir = "/srv/www/%s" % instance
    sudo("mkdir -p %s" % basedir)
    sudo("mkdir -p %s/virtualenv %s/htdocs %s/log" %
         (basedir, basedir, basedir))
    sudo("chown -R www-data:www-data %s" % basedir)


def create_virtualenv(instance):
    dirname = "/srv/www/%s" % instance
    cmd = "virtualenv %s/virtualenv" % (dirname)
    sudo('su -s /bin/bash -c "%s" www-data' % cmd)


def checkout_repo(instance, branch=None):
    dirname = "/srv/www/%s/htdocs/maproulette" % instance
    if branch:
        cmd = "git clone https://github.com/osmlab/maproulette.git -b %s %s" %\
              (branch, dirname)
    else:
        cmd = "git clone https://github.com/osmlab/maproulette.git %s" %\
            (dirname)
    with cd("/srv/www"):
        sudo('su -s /bin/bash -c "%s" www-data' % cmd)


def install_python_dependencies(instance):
    dirname = "/srv/www/%s" % instance
    cmd = 'source %s/virtualenv/bin/activate && pip\
    install -r %s/htdocs/maproulette/requirements.txt' % (dirname, dirname)
    sudo('su -s /bin/bash -c "%s" www-data' % cmd)


def setup_uwsgi_file(instance):
    sites_available_file = "/etc/uwsgi/apps-available/%s.ini" % instance
    sites_enabled_file = "/etc/uwsgi/apps-enabled/%s.ini" % instance
    upload_template("uwsgi", sites_available_file,
                    use_sudo=True,
                    use_jinja=True,
                    template_dir="fabric_templates",
                    context={"instance": instance})
    sudo("ln -s %s %s" % (sites_available_file, sites_enabled_file))


def setup_nginx_file(instance):
    # remove 'default' from sites-enabled
    if exists('/etc/nginx/sites-enabled/default'):
        sudo('rm /etc/nginx/sites-enabled/default')
    sites_available_file = "/etc/nginx/sites-available/%s" % instance
    sites_enabled_file = "/etc/nginx/sites-enabled/%s" % instance
    upload_template("nginx", sites_available_file,
                    use_jinja=True,
                    use_sudo=True,
                    template_dir="fabric_templates",
                    context={"instance": instance})
    if not exists(sites_enabled_file):
        sudo("ln -s %s %s" % (sites_available_file, sites_enabled_file))


def setup_config_file(instance, setting):
    basedir = "/srv/www/%s" % instance
    target = basedir + "/config.py"
    upload_template("config",
                    target,
                    use_jinja=True,
                    use_sudo=True,
                    template_dir="fabric_templates",
                    context={
                        "instance": instance,
                        "setting": setting,
                        #"consumer_key": '',
                        #"consumer_secret": ''
                    })
    sudo('chown www-data:www-data %s' % target)
    restart_uwsgi()


def rsync(instance, reload_pip=False):
    basedir = "/srv/www/%s" % instance
    target = basedir + '/htdocs/'
    rsync_project(target, delete="yes", exclude=".git")
    if reload_pip:
        install_python_dependencies()


def git_pull(instance):
    cmd = "cd /srv/www/%s/htdocs/maproulette && git pull" % instance
    sudo('su -s /bin/bash -c "%s" www-data' % cmd)


def setup_postgres_permissions():
    if not exists(pg_hba_fname):
        print(red(pg_hba_fname + "is not present on the filesystem"))
        exit()
    sed(pg_hba_fname,
        "local\s+all\s+all\s+peer",
        "local\tall\t\tall\t\t\t\t\ttrust",
        use_sudo="yes")
    restart_postgres()


def install_postgis():
    # from
    # http://trac.osgeo.org/postgis/wiki/UsersWikiPostGIS21UbuntuPGSQL93Apt
    sudo(
        "sh -c 'echo \"deb http://apt.postgresql.org/"
        "pub/repos/apt/ precise-pgdg main\"' >> /etc/apt/sources.list")
    run("wget --quiet -O - http://apt.postgresql.org/pub/"
        "repos/apt/ACCC4CF8.asc | sudo apt-key add -")
    update_packages()
    postgres_packages = ["Postgresql-9.3-postgis",
                         "postgresql-contrib",
                         "postgresql-server-dev-9.3"]
    sudo("sudo apt-get -q install %s" % (' '.join(postgres_packages)))


def create_db_user():
    cmd = 'createuser -s -w osm'
    sudo('su -s /bin/bash -c "%s" postgres' % cmd)


def create_databases():
    cmd = "createdb -O osm maproulette"
    sudo('su -s /bin/bash -c "%s" postgres' % cmd)
    cmd = "createdb -O osm maproulette_test"
    sudo('su -s /bin/bash -c "%s" postgres' % cmd)
    cmd = "createdb -O osm maproulette_dev"
    sudo('su -s /bin/bash -c "%s" postgres' % cmd)
    cmd = "psql -U osm -d maproulette"\
        " -c 'CREATE EXTENSION postgis'"
    sudo('su -s /bin/bash -c "%s" postgres' % cmd)
    cmd = "psql -U osm -d maproulette_test"\
        " -c 'CREATE EXTENSION postgis'"
    sudo('su -s /bin/bash -c "%s" postgres' % cmd)
    cmd = "psql -U osm -d maproulette_dev"\
        " -c 'CREATE EXTENSION postgis'"
    sudo('su -s /bin/bash -c "%s" postgres' % cmd)


def setup_system():
    update_packages()
    upgrade_packages()
    install_packages()
    install_postgis()
    setup_postgres_permissions()
    create_db_user()
    create_databases()


def create_deployment(instance, setting="dev", branch=None):
    create_deploy_directories(instance)
    create_virtualenv(instance)
    checkout_repo(instance, branch)
    install_python_dependencies(instance)
    setup_uwsgi_file(instance)
    setup_nginx_file(instance)
    setup_config_file(instance, setting)
    restart_uwsgi()
    restart_nginx()


def deploy(instance, setting="dev", branch=None):
    setup_system()
    create_deployment(instance, setting, branch)
