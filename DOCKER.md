Docker execution instructions
=============================

These are initial instructions; so far only tested on macOS (M1)

Build Docker image
==================
Checkout Ponymail Foal from Git:

```
$ get clone https://github.com/apache/incubator-ponymail-foal.git ponymail-foal
$ cd ponymail-foal
```

start Docker (e.g. open ~/Applications/Docker.app)
Build the image:

```$ docker compose build pmfoal```

Resolve any issues (e.g. ensure Docker has access to the required directories), and rebuild

Start ElasticSearch and the main server
=======================================

Open a new terminal session

```
$ cd ponymail-foal
$ docker compose up
```

To stop the server, either use ^C, or issue the following in another terminal session:

```$ docker stop pmfoal-pmfoal-1```

Setup the ElasticSearch database
================================

This only needs to be done once.
[The container must already be running.]

Open a new terminal session, start a shell in the container:
```
$ docker exec -it pmfoal-pmfoal-1 bash
# cd tools
# python3 setup.py --devel
```

Or you can do it all in one command:

```$ docker exec -it pmfoal-pmfoal-1 bash -c 'cd tools; python3 setup.py --devel'```

Or you can set up the database from the host.
The container must already be running, and the Python packages (as per tools/requirements.txt)
must have been installed.

```
$ cd ponymail-foal; cd tools
$ python3 setup.py --devel
```

You can then use archiver.py or import-mbox.py to populate the database.

Start the Ponymail api server
=============================

Open a new terminal session, start a shell in the container:

```
$ docker exec -it pmfoal-pmfoal-1 bash
# cd server
# python3 main.py --testendpoints
```

Or you can combine them:

```$ docker exec -it pmfoal-pmfoal-1 bash -c 'cd server; python3 main.py --testendpoints'```

Connect to the server
=====================

Browse to http://localhost:1080/
