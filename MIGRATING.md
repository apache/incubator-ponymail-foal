# Migrating from an old Pony Mail database to Foal

To migrate your database, you will need the following:

- Access to the original ES 2.x/5.x database
- Access to the new ES 7.x/8.x database
- Foal fully installed with a new database set up on the ES 7.x+ instance.

Once you have all this at the ready, run the migrator script:
~~~shell script
cd server/
pipenv run python3 migrate.py
~~~
You will need to enter the URL of the old server as well as the new server, 
and the name of the old database and the prefix of the new indices.

You will also need to acknowledge the DKIm re-indexing, or deny it and 
continue with the old document IDs. Re-indexing is recommended if you wish 
to use shorter permalinks, and is fully backwards-compatible with your 
previous permalinks.

Migrating may take quite a while. Assume 250 documents can be migrated per second.
