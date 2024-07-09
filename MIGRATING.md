<!---
 Licensed to the Apache Software Foundation (ASF) under one or more
 contributor license agreements.  See the NOTICE file distributed with
 this work for additional information regarding copyright ownership.
 The ASF licenses this file to You under the Apache License, Version 2.0
 (the "License"); you may not use this file except in compliance with
 the License.  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
-->

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
