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

from elasticsearch import AsyncElasticsearch, Elasticsearch, helpers
from elasticsearch.helpers import async_scan

if not __package__:
    from plugins import generators, textlib
else:
    from .plugins import generators, textlib

import argparse
import base64
import email.utils
import hashlib
import multiprocessing
import time
import sys
import archiver

# Increment this number whenever breaking changes happen in the migration workflow:
MIGRATION_MAGIC_NUMBER = "2"


# Max number of parallel conversions to perform before pushing. 75-ish percent of max cores.
cores = multiprocessing.cpu_count()
MAX_PARALLEL_OPS = max(min(int((cores + 1) * 0.75), cores - 1), 1)

class MultiDocProcessor:
    """MultiProcess document processor"""

    def __init__(self, old_es_url: str, new_es_url: str, target: callable, num_processes: int = 8, graceful: bool = False):
        self.processes = []
        self.queues = []
        self.target = target
        self.graceful = graceful
        self.manager = multiprocessing.Manager()
        self.lock = self.manager.Lock()
        self.processed = self.manager.Value("i", 0)
        self.processed_last_count = 0
        self.start_time = time.time()
        self.queue_pointer = 0
        self.num_processes = num_processes
        for _ in range(0, num_processes):
            q = multiprocessing.Queue()
            p = multiprocessing.Process(
                target=self.start,
                args=(
                    q,
                    old_es_url,
                    new_es_url,
                ),
            )
            self.queues.append(q)
            self.processes.append(p)
            p.start()

    def feed(self, *params):
        """Feed arguments to the next available processor"""
        self.queues[self.queue_pointer].put(params)
        self.queue_pointer += 1
        self.queue_pointer %= self.num_processes

    def sighup(self):
        for queue in self.queues:
            queue.put("SIGHUP")

    def stop(self):
        for queue in self.queues:
            queue.put("DONE")
        for proc in self.processes:
            proc.join()

    def status(self, total):
        processed = self.processed.value
        if processed - self.processed_last_count >= 1000:
            self.processed_last_count = processed
            now = time.time()
            time_spent = now - self.start_time
            docs_per_second = (processed / time_spent) or 1
            time_left = (total - processed) / docs_per_second

            # stringify time left
            time_left_str = "%u seconds" % time_left
            if time_left > 60:
                time_left_str = "%u minute(s), %u second(s)" % (int(time_left / 60), time_left % 60)
            if time_left > 3600:
                time_left_str = "%u hour(s), %u minute(s), %u second(s)" % (
                    int(time_left / 3600),
                    int(time_left % 3600 / 60),
                    time_left % 60,
                )

            print(
                "Processed %u documents, %u remain. ETA: %s (at %u documents per second)"
                % (processed, (total - processed), time_left_str, docs_per_second)
            )

    def start(self, queue, old_es_url, new_es_url):
        old_es = Elasticsearch([old_es_url])
        new_es = Elasticsearch([new_es_url])
        bulk_array = []
        while True:
            params = queue.get()
            if params == "SIGHUP":  # Push stragglers
                if bulk_array:
                    bulk_push(bulk_array, new_es, self.graceful)
                    bulk_array[:] = []
            elif params == "DONE":  # Close up shop completely
                if bulk_array:
                    bulk_push(bulk_array, new_es, self.graceful)
                old_es.close()
                new_es.close()
                return
            else:
                as_list = list(params)
                as_list.insert(0, old_es)
                try:
                    ret_val = self.target(*as_list)
                except:
                    if self.graceful:
                        print("Unexpected error:", sys.exc_info()[0])
                    else:
                        print("Unexpected error:", sys.exc_info()[0])
                        raise
                if ret_val:
                    bulk_array.extend(ret_val)
                with self.lock:
                    self.processed.value += 1
                if len(bulk_array) >= 200:
                    bulk_push(bulk_array, new_es, self.graceful)
                    bulk_array[:] = []


def bulk_push(json, es, graceful=False):
    """Pushes a bunch of objects to ES in a bulk operation"""
    js_arr = []
    for entry in json:
        bulk_op = {
            "_op_type": "index",
            "_index": entry["index"],
            "_id": entry["id"],
            "_source": entry["body"],
        }
        js_arr.append(bulk_op)
    try:
        helpers.bulk(es, js_arr)
    except helpers.errors.BulkIndexError as e:
        if graceful:
            print("Bulk index error: %s" % e)
        else:
            raise


def process_document(old_es, doc, old_dbname, dbname_source, dbname_mbox, do_dkim):
    now = time.time()
    list_id = textlib.normalize_lid(doc["_source"]["list_raw"])
    try:
        source = old_es.get(index=old_dbname, doc_type="mbox_source", id=doc["_id"])
        # If we hit a 404 on a source, we have to fake an empty document, as we don't know the source.
    except:
        print("Source for %s was not found, faking it..." % doc["_id"])
        source = {"_source": {"source": ""}}
    source_text: str = source["_source"]["source"]
    if ":" not in source_text:  # Base64
        source_text = base64.b64decode(source_text)
    else:  # bytify
        source_text = source_text.encode("utf-8", "ignore")
    archive_as_id = doc["_id"]
    if do_dkim:
        dkim_id = generators.dkimid(None, None, list_id, None, source_text)
        old_id = doc["_id"]
        archive_as_id = dkim_id
        doc["_source"]["mid"] = dkim_id
        doc["_source"]["permalinks"] = [dkim_id, old_id]
    else:
        doc["_source"]["permalinks"] = [doc["_id"]]

    doc["_source"]["dbid"] = hashlib.sha3_256(source_text).hexdigest()

    # Add in shortened body for search aggs
    # We add +1 to know whether to use ellipsis in reports.
    doc["_source"]["body_short"] = doc["_source"]["body"][:archiver.SHORT_BODY_MAX_LEN+1]

    # Add in gravatar
    header_from = doc["_source"]["from"]
    mailaddr = email.utils.parseaddr(header_from)[1]
    ghash = hashlib.md5(mailaddr.encode("utf-8")).hexdigest()
    doc["_source"]["gravatar"] = ghash

    # Append migration details to notes field in doc
    notes = doc["_source"].get("_notes", [])
    # We want a list, not a single string
    if isinstance(notes, str):
        notes = list(notes)
    notes.append(
        "MIGRATE: Document migrated from Pony Mail to Pony Mail Foal at %u, "
        "using foal migrator v/%s" % (now, MIGRATION_MAGIC_NUMBER)
    )
    # If we re-indexed the document, make a note of that as well.
    if do_dkim:
        notes.append("REINDEX: Document re-indexed with DKIM_ID at %u, " "from %s to %s" % (now, dkim_id, old_id))
    doc["_source"]["_notes"] = notes

    # Copy to new DB
    return (
        {"index": dbname_mbox, "id": archive_as_id, "body": doc["_source"]},
        {"index": dbname_source, "id": doc["_source"]["dbid"], "body": source["_source"]},
    )


def process_attachment(old_es, doc, dbname_attachment):
    return ({"index": dbname_attachment, "id": doc["_id"], "body": doc["_source"]},)


async def main(args):
    no_jobs = args.jobs
    graceful = args.graceful
    print("Welcome to the Apache Pony Mail -> Foal migrator.")
    print("This will copy your old database, adjust the structure, and insert the emails into your new foal database.")
    print("We will be utilizing %u cores for this operation." % no_jobs)
    print("------------------------------------")
    old_es_url = args.old_url or input("Enter the full URL (including http/https) of your old ES server: ") or "http://localhost:9200/"
    new_es_url = args.new_url or input("Enter the full URL (including http/https) of your NEW ES server: ") or "http://localhost:9200/"
    if old_es_url == new_es_url:
        print("Old and new DB should not be the same, assuming error in input and exiting!")
        return
    ols_es_async = AsyncElasticsearch([old_es_url])

    old_dbname = args.old_name or input("What is the database name for the old Pony Mail emails? [ponymail]: ") or "ponymail"
    new_dbprefix = args.new_prefix or input("What is the database prefix for the new Pony Mail emails? [ponymail]: ") or "ponymail"

    do_dkim = True
    dkim_txt = (
        input(
            "Do you wish to perform DKIM re-indexing of all emails? This will NOT preserve all old permalinks currently "
            "(y/n) [y]: "
        )
        or "y"
    )
    if dkim_txt.lower() == "n":
        do_dkim = False

    # Define index names for new ES
    dbname_mbox = new_dbprefix + "-mbox"
    dbname_source = new_dbprefix + "-source"
    dbname_attachment = new_dbprefix + "-attachment"

    # Let's get started..!
    # start_time = time.time()
    count = await ols_es_async.count(index=old_dbname, doc_type="mbox")
    no_emails = count["count"]

    print("------------------------------------")
    print("Starting migration of %u emails, this may take quite a while..." % no_emails)

    processes = MultiDocProcessor(old_es_url, new_es_url, process_document, no_jobs)

    docs_read = 0
    async for doc in async_scan(
        client=ols_es_async,
        query={"query": {"match_all": {}}},
        doc_type="mbox",
        index=old_dbname,
    ):
        docs_read += 1
        processes.feed(doc, old_dbname, dbname_source, dbname_mbox, do_dkim)
        # Don't speed too far ahead of processing...
        processed = processes.processed.value
        while docs_read - processed > 100 * no_jobs:
            await asyncio.sleep(0.01)
            processed = processes.processed.value + 0

        processes.status(no_emails)

    # There may be some docs left over to push
    processes.sighup()
    while processed < no_emails:  # Wait for all documents to have been processed.
        await asyncio.sleep(1)
        print(f"Waiting for bulk push to complete ({processed} out of {no_emails} done...)")
        processed = processes.processed.value

    processes.stop()

    # Process attachments
    # start_time = time.time()
    processes = MultiDocProcessor(old_es_url, new_es_url, process_attachment, no_jobs, graceful)
    docs_read = 0
    count = await ols_es_async.count(index=old_dbname, doc_type="attachment")
    no_att = count["count"]
    print("Transferring %u attachments..." % no_att)
    async for doc in async_scan(
        client=ols_es_async,
        query={"query": {"match_all": {}}},
        doc_type="attachment",
        index=old_dbname,
    ):
        processes.feed(doc, dbname_attachment)
        docs_read += 1

        # Don't speed ahead
        processed = processes.processed.value + 0
        while docs_read - processed > 10 * no_jobs:
            await asyncio.sleep(0.01)
            processed = processes.processed.value + 0

        processes.status(no_att)

    # There may be some docs left over to push
    processes.sighup()
    while processed < no_att:  # Wait for all attachments to have been processed.
        await asyncio.sleep(1)
        print(f"Waiting for bulk push to complete ({processed} out of {no_att} done...)")
        processed = processes.processed.value

    processes.stop()
    await ols_es_async.close()
    print("All done, enjoy!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--jobs",
        "-j",
        help="Number of concurrent processing jobs to run. Default is %u." % MAX_PARALLEL_OPS,
        type=int,
        default=MAX_PARALLEL_OPS,
    )
    parser.add_argument(
        "--graceful",
        "-g",
        help="Fail gracefully and continue if a processing error occurs",
        action='store_true'
    )
    # the default on macOS is spawn, but this fails with:
    #  ForkingPickler(file, protocol).dump(obj)
    # TypeError: cannot pickle 'weakref' object
    # Work-round: allow override of start method
    parser.add_argument(
        "--start_method",
        help="Override start method (e.g. fork on macos)",
        type=str
    )
    parser.add_argument(
        "--old_url",
        help="Provide input database URL",
        type=str
    )
    parser.add_argument(
        "--old_name",
        help="Provide input database name",
        type=str
    )
    parser.add_argument(
        "--new_url",
        help="Provide output database URL",
        type=str
    )
    parser.add_argument(
        "--new_prefix",
        help="Provide output database prefix",
        type=str
    )
    args = parser.parse_args()
    if args.start_method:
        multiprocessing.set_start_method(args.start_method)
    asyncio.run(main(args))
