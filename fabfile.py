from fabric.api import run
from fabric.colors import red
from fabric.contrib.files import exists, cd, upload_template, sed, append, contains
from fabric.contrib.project import rsync_project
from fabric.operations import sudo, local

pg_hba_fname = "/etc/postgresql/9.3/main/pg_hba.conf"


def service(service, command):
    sudo('service %s %s' % (service, command))


def update_packages():
    sudo('apt-get -qq update')


def upgrade_packages():
    sudo('apt-get -q dist-upgrade')


def reboot_server():
    sudo('reboot')


def _is_ubuntu_1404():
    result = run('uname -a | grep -q Ubuntu', quiet=True).succeeded and\
        run('lsb_release -r | grep -q 14.04', quiet=True).succeeded
    if result:
        print "This is Ubuntu 14.04."
    return result


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


def install_nodejs():
    sudo('sudo add-apt-repository -y ppa:chris-lea/node.js')
    update_packages()
    sudo('apt-get -q install nodejs')


def install_react_tools():
    sudo('npm install -g react-tools')


def install_bower():
    sudo('npm install -g bower')


def create_deploy_directories(instance):
    basedir = "/srv/www/%s" % instance
    sudo("mkdir -p %s" % basedir)
    sudo("mkdir -p %s/virtualenv %s/htdocs %s/log %s/cron" %
         (basedir, basedir, basedir, basedir))
    sudo("chown -R www-data:www-data %s" % basedir)


def create_virtualenv(instance):
    dirname = "/srv/www/%s" % instance
    sudo("virtualenv %s/virtualenv" % (dirname), user="www-data")


def checkout_repo(instance, branch=None):
    dirname = "/srv/www/%s/htdocs/maproulette" % instance
    if branch:
        cmd = "git clone https://github.com/osmlab/maproulette.git -b %s %s" %\
              (branch, dirname)
    else:
        cmd = "git clone https://github.com/osmlab/maproulette.git %s" %\
            (dirname)
    with cd("/srv/www"):
        sudo(cmd, user="www-data")


def git_fetch_all(instance):
    with cd("/srv/www/%s/htdocs/maproulette" % instance):
        sudo('git fetch --all', user="www-data")


def git_change_branch(instance, branch):
    with cd("/srv/www/%s/htdocs/maproulette" % instance):
        sudo('git checkout %s' % branch, user="www-data")


def flask_manage(instance, command):
    dirname = "/srv/www/%s" % instance
    cmd = "export MAPROULETTE_SETTINGS=%s/config.py &&\
    source %s/virtualenv/bin/activate && python\
    manage.py %s" % (dirname, dirname, command)
    with cd("%s/htdocs/maproulette" % dirname):
        sudo(cmd, user="www-data")


def setup_cron(instance):
    dirname = "/srv/www/%s" % instance
    upload_template("cron", "%s/cron/scrub_stale_tasks.sh" % dirname,
                    use_sudo=True,
                    use_jinja=True,
                    template_dir="fabric_templates",
                    context={"instance": instance})
    sudo('chown www-data:www-data %s/cron/scrub_stale_tasks.sh' % dirname)
    sudo('chmod 0755 %s/cron/scrub_stale_tasks.sh' % dirname, user='www-data')
    if exists('/var/spool/cron/crontabs/www-data'):
        # if an existing crontab file exists, start with that
        sudo('crontab -l >/tmp/crondump', user='www-data')
    if not contains('/tmp/crondump', 'scrub_stale_tasks.sh'):
        # check if the job is already in the file
        sudo('echo "15 * * * * %s/cron/scrub_stale_tasks.sh >>'
             ' %s/log/scrub_stale_tasks.log" >> /tmp/crondump' %
             (dirname, dirname), user='www-data')
        sudo('crontab /tmp/crondump', user='www-data')


def install_python_dependencies(instance, upgrade=False):
    dirname = "/srv/www/%s" % instance
    cmd = 'source {basepath}/virtualenv/bin/activate && pip\
    install {upgrade}-r {basepath}/htdocs/maproulette/requirements.txt'.format(
        basepath=dirname,
        upgrade='--upgrade' if upgrade else '')
    sudo(cmd, user="www-data")


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
    sudo('rm -f /etc/nginx/sites-enabled/default')
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
    service('uwsgi', 'restart')


def compile_jsx(instance=None):
    if not instance:
        # we are compiling locally
        local("cat ./jsx/maproulette.js | jsx >"
              " ./maproulette/static/js/maproulette.js")
    else:
        basedir = "/srv/www/%s" % instance
        sudo("cat %s/htdocs/maproulette/jsx/maproulette.js "
             "| jsx > %s/htdocs/maproulette/maproulette/static"
             "/js/maproulette.js" % (basedir, basedir))


def update_bower_dependencies(instance):
    with cd("/srv/www/%s/htdocs/maproulette/maproulette/static" % instance):
        run('bower -q install')


def rsync(instance, reload_pip=False):
    compile_jsx()
    basedir = "/srv/www/%s" % instance
    target = basedir + '/htdocs/'
    rsync_project(target, delete="yes", exclude=[".git", "sessiondata"])
    if reload_pip:
        install_python_dependencies()
    service('uwsgi', 'restart')


def reset_sessions(instance):
    '''Removes all sessions stored on disk'''

    target = "/srv/www/%s/htdocs/maproulette/sessiondata" % instance
    sudo("rm -rf %s" % target)
    service('uwsgi', 'restart')


def git_pull(instance):
    '''Pulls latest for current branch from github'''

    sudo("cd /srv/www/%s/htdocs/maproulette && git pull" %
         instance, user="www-data")


def setup_postgres_permissions():
    '''Adds local trust to pg_hba.conf'''

    if not exists(pg_hba_fname):
        print red(pg_hba_fname + "is not present on the filesystem")
        exit()
    sed(pg_hba_fname,
        "host\s*all\s*all\s*127.0.0.1/32\s*md5",
        "host\tall\tall\t127.0.0.1/32\ttrust",
        use_sudo="yes")
    service('postgresql', 'restart')


def install_postgis():
    # from
    # http://trac.osgeo.org/postgis/wiki/UsersWikiPostGIS21UbuntuPGSQL93Apt
    if not _is_ubuntu_1404():
        append("/etc/apt/sources.list", "deb http://apt.postgresql.org/"
               "pub/repos/apt/ precise-pgdg main", use_sudo=True)
        run("wget --quiet -O - http://apt.postgresql.org/pub/"
            "repos/apt/ACCC4CF8.asc | sudo apt-key add -")
        update_packages()
        postgres_packages = ["Postgresql-9.3-postgis",
                             "postgresql-contrib",
                             "postgresql-server-dev-9.3"]
    else:
        postgres_packages = ["postgresql-9.3-postgis-2.1",
                             "postgresql-server-dev-9.3"]
    sudo("sudo apt-get -q install %s" % (' '.join(postgres_packages)))


def create_db_user():
    sudo('createuser -s -w osm', user='postgres')


def create_databases():
    sudo("createdb -O osm maproulette", user='postgres')
    sudo("createdb -O osm maproulette_test", user='postgres')
    sudo("createdb -O osm maproulette_dev", user='postgres')
    sudo("psql -U osm -h localhost -d maproulette -c"
         " 'CREATE EXTENSION postgis'", user='postgres')
    sudo("psql -U osm -h localhost -d maproulette_test -c"
         " 'CREATE EXTENSION postgis'", user='postgres')
    sudo("psql -U osm -h localhost -d maproulette_dev -c"
         " 'CREATE EXTENSION postgis'", user='postgres')


def setup_system():
    update_packages()
    upgrade_packages()
    install_packages()
    install_postgis()
    setup_postgres_permissions()
    create_db_user()
    create_databases()
    install_nodejs()
    install_react_tools()
    install_bower()


def create_deployment(instance, setting="dev", branch=None):
    create_deploy_directories(instance)
    create_virtualenv(instance)
    checkout_repo(instance, branch)
    install_python_dependencies(instance)
    setup_uwsgi_file(instance)
    setup_nginx_file(instance)
    setup_cron(instance)
    setup_config_file(instance, setting)
    flask_manage(instance, command='create_db')
    flask_manage(instance, command='db init')  # initialize alembic
    update_bower_dependencies(instance)
    compile_jsx(instance)
    service('uwsgi', 'restart')
    service('nginx', 'restart')


def update_application(instance):
    service('uwsgi', 'stop')
    service('postgresql', 'stop')
    git_pull(instance)
    install_python_dependencies(instance)
    service('postgresql', 'start')
    flask_manage(instance, command='db upgrade')
    update_bower_dependencies(instance)    
    compile_jsx(instance)
    service('uwsgi', 'start')


def deploy(instance, setting="dev", branch=None):
    setup_system()
    create_deployment(instance, setting, branch)
