Docker execution instructions
=============================

These are initial instructions; so far, they have only been tested on macOS (M1).

Build Docker image
==================
Checkout Ponymail Foal from Git:

```
$ git clone https://github.com/apache/incubator-ponymail-foal.git ponymail-foal
$ cd ponymail-foal
```

Start Docker (e.g., open ~/Applications/Docker.app). Build the image:

```$ docker compose build```

Resolve any issues (e.g., ensure Docker has access to the required directories) and rebuild.

Start ElasticSearch and the main server
=======================================

Open a new terminal session:

```
$ cd ponymail-foal
$ [MAIL_DATA=/path/to/mailboxes] docker compose up
```

To stop the server, either use `^C`, or issue the following in another terminal session:

```$ docker stop pmfoal-pmfoal-1```

Setup the ElasticSearch database
================================

The following step only needs to be done once.
The container must already be running.

Open a new terminal session and start a shell in the container:

```
$ docker exec -it pmfoal-pmfoal-1 bash
# cd tools
# python3 setup.py --devel
```

Or you can do it all in one command:

```$ docker exec -it pmfoal-pmfoal-1 bash -c 'cd tools; python3 setup.py --devel'```

Or you can set up the database from the host.
The container must be running, and the Python packages (as per tools/requirements.txt)
must have been installed.

```
$ cd ponymail-foal; cd tools
$ python3 setup.py --devel
```

You can then use archiver.py or import-mbox.py to populate the database.

Importing mbox files for testing
================================

To test existing mbox files, you can use the import-mbox.py script.
You can download a publicly available file using this link:

```
mkdir mbox-testdata
cd mbox-testdata
wget https://lists.apache.org/api/mbox.lua?list=dev&domain=community.apache.org
cd ..
```

Then import it:

```
$ tools/import-mbox.py --source mbox-testdata/dev_community_apache_org.mbox
```

This will import the mbox file into the database.

Start the Ponymail api server
=============================

Open a new terminal session start a shell in the container:

```
$ docker exec -it pmfoal-pmfoal-1 bash
# cd server
# python3 main.py --testendpoints
```

Or you can combine them:

```$ docker exec -it pmfoal-pmfoal-1 bash -c 'cd server; python3 main.py --testendpoints'```

Update config.js to allow local login
=====================================

If you wish to test functions that require log in, update config.js to enable the two logins.

For testing email and admin functions, you may need to update server/ponymail.yaml

Connect to the server
=====================

Browse to http://localhost:1080/
