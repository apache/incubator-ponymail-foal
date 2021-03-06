#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_scan
from elasticsearch import helpers
if not __package__:
    from plugins import generators
else:
    from .plugins import generators
import time
import base64
import hashlib

# Increment this number whenever breaking changes happen in the migration workflow:
MIGRATION_MAGIC_NUMBER = "1"


async def bulk_push(json, es):
    """Pushes a bunch of objects to ES in a bulk operation"""
    js_arr = []
    for entry in json:
        bulk_op = {
            "_op_type": "index",
            "_index": entry['index'],
            "_id": entry['id'],
            "_source": entry['body'],
        }
        js_arr.append(
            bulk_op
        )
    await helpers.async_bulk(es, js_arr)


async def main():
    print("Welcome to the Apache Pony Mail -> Foal migrator.")
    print("This will copy your old database, adjust the structure, and insert the emails into your new foal database.")
    print("------------------------------------")
    old_es_url = input("Enter the full URL (including http/https) of your old ES server: ") or "http://localhost:9200/"
    new_es_url = input("Enter the full URL (including http/https) of your NEW ES server: ") or "http://localhost:9200/"
    if old_es_url == new_es_url:
        print("Old and new DB should not be the same, assuming error in input and exiting!")
        return
    old_es = AsyncElasticsearch([old_es_url])
    new_es = AsyncElasticsearch([new_es_url])

    old_dbname = input("What is the database name for the old Pony Mail emails? [ponymail]: ") or "ponymail"
    new_dbprefix = input("What is the database prefix for the new Pony Mail emails? [ponymail]: ") or "ponymail"

    do_dkim = True
    dkim_txt = input("Do you wish to perform DKIM re-indexing of all emails? This will still preserve old permalinks "
                     "(y/n) [y]: ") or "y"
    if dkim_txt.lower() == 'n':
        do_dkim = False

    # Define index names for new ES
    dbname_mbox = new_dbprefix + "-mbox"
    dbname_source = new_dbprefix + "-source"
    dbname_attachment = new_dbprefix + "-attachment"

    # Let's get started..!
    start_time = time.time()
    now = start_time
    processed = 0
    count = await old_es.count(index=old_dbname, doc_type="mbox")
    no_emails = count['count']

    print("------------------------------------")
    print("Starting migration of %u emails, this may take quite a while..." % no_emails)

    bulk_array = []

    async for doc in async_scan(
            client=old_es,
            query={"query": {"match_all": {}}},
            doc_type="mbox",
            index=old_dbname,
    ):
        list_id = doc['_source']['list_raw'].strip("<>")
        try:
            source = await old_es.get(index=old_dbname, doc_type="mbox_source", id=doc['_id'])
        # If we hit a 404 on a source, we have to fake an empty document, as we don't know the source.
        except:
            print("Source for %s was not found, faking it..." % doc['_id'])
            source = {
                '_source': {
                    'source': ""
                }
            }
        source_text: str = source['_source']['source']
        if ':' not in source_text:  # Base64
            source_text = base64.b64decode(source_text)
        else:  # bytify
            source_text = source_text.encode('utf-8', 'ignore')
        if do_dkim:
            dkim_id = generators.dkimid(None, None, list_id, None, source_text)
            old_id = doc['_id']
            doc['_source']['mid'] = dkim_id
            doc['_source']['permalinks'] = [
                dkim_id,
                old_id
            ]
        else:
            doc['_source']['permalinks'] = [
                doc['_id']
            ]

        source['_source']['permalinks'] = doc['_source']['permalinks']
        doc['_source']['dbid'] = hashlib.sha3_256(source_text).hexdigest()

        # Append migration details to notes field in doc
        notes = doc['_source'].get('_notes', [])
        # We want a list, not a single string
        if isinstance(notes, str):
            notes = list(notes)
        notes.append("MIGRATE: Document migrated from Pony Mail to Pony Mail Foal at %u, "
                     "using foal migrator v/%s" % (now, MIGRATION_MAGIC_NUMBER))
        # If we re-indexed the document, make a note of that as well.
        if do_dkim:
            notes.append("REINDEX: Document re-indexed with DKIM_ID at %u, "
                         "from %s to %s" % (now, dkim_id, old_id))
        doc['_source']['_notes'] = notes

        # Copy to new DB
        bulk_array.append({
            'index': dbname_mbox,
            'id': doc['_id'],
            'body': doc['_source']
        })
        bulk_array.append({
            'index': dbname_source,
            'id': doc['_source']['dbid'],
            'body': source['_source']
        })

        if len(bulk_array) > 100:
            await bulk_push(bulk_array, new_es)
            bulk_array[:] = []

        processed += 1
        if processed % 500 == 0:
            now = time.time()
            time_spent = now - start_time
            docs_per_second = processed / time_spent
            time_left = (no_emails - processed) / docs_per_second

            # stringify time left
            time_left_str = "%u seconds" % time_left
            if time_left > 60:
                time_left_str = "%u minute(s), %u second(s)" % (int(time_left / 60), time_left % 60)
            if time_left > 3600:
                time_left_str = "%u hour(s), %u minute(s), %u second(s)" % (
                int(time_left / 3600), int(time_left % 3600 / 60), time_left % 60)

            print("Processed %u emails, %u remain. ETA: %s (at %u emails per second)" %
                  (processed, (no_emails - processed), time_left_str, docs_per_second)
                  )

    # There may be some docs left over to push
    if bulk_array:
        await bulk_push(bulk_array, new_es)

    start_time = time.time()
    processed = 0
    count = await old_es.count(index=old_dbname, doc_type="attachment")
    no_att = count['count']
    print("Transferring %u attachments..." % no_att)
    async for doc in async_scan(
            client=old_es,
            query={"query": {"match_all": {}}},
            doc_type="attachment",
            index=old_dbname,
    ):
        # Copy to new DB
        await new_es.index(index=dbname_attachment, doc_type='_doc', id=doc['_id'], body=doc['_source'])

        processed += 1
        if processed % 500 == 0:
            now = time.time()
            time_spent = now - start_time
            docs_per_second = processed / time_spent
            time_left = (no_att - processed) / docs_per_second

            # stringify time left
            time_left_str = "%u seconds" % time_left
            if time_left > 60:
                time_left_str = "%u minute(s), %u second(s)" % (int(time_left / 60), time_left % 60)
            if time_left > 3600:
                time_left_str = "%u hour(s), %u minute(s), %u second(s)" % (
                int(time_left / 3600), int(time_left % 3600 / 60), time_left % 60)

            print("Processed %u emails, %u remain. ETA: %s (at %u attachments per second)" %
                  (processed, (no_att - processed), time_left_str, docs_per_second)
                  )

    await old_es.close()
    await new_es.close()
    print("All done, enjoy!")


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
