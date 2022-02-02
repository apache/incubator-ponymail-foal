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
import datetime
import re
import sys
import time

from elasticsearch_dsl import Search
from elasticsearch import VERSION as ES_VERSION

import plugins.configuration
import plugins.server
import plugins.database

PYPONY_RE_PREFIX = re.compile(r"^([a-zA-Z]+:\s*)+")
ACTIVITY_TIMESPAN = "now-90d"  # How far back to look for "current" activity in lists


class ProgTimer:
    start: float
    title: str

    def __init__(self, title):
        self.title = title

    async def __aenter__(self):
        sys.stdout.write(
            "[%s] %s..." % (datetime.datetime.now().strftime("%H:%M:%S"), self.title)
        )
        self.start = time.time()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("Done in %.2f seconds" % (time.time() - self.start))


async def get_lists(database: plugins.configuration.DBConfig) -> dict:
    """

    :param database: a Pony Mail database configuration
    :return: A dictionary of all mailing lists found, and whether they are considered
             public or private
    """
    lists = {}
    db = plugins.database.Database(database)
    limit = database.max_lists

    # Fetch aggregations of all private emails
    # Do this first, so mixed lists are not marked private
    s = Search(using=db.client, index=db.dbs.db_mbox).filter(
        "term", private=True
    )
    s.aggs.bucket("per_list", "terms", field="list_raw", size=limit)

    res = await db.search(
        index=db.dbs.db_mbox, body=s.to_dict(), size=0
    )

    for ml in res["aggregations"]["per_list"]["buckets"]:
        list_name = ml["key"].strip("<>").replace(".", "@", 1)
        lists[list_name] = {
            "count": 0,  # Sorting later
            "private": True,
        }

    # Fetch aggregations of all public emails
    s = Search(using=db.client, index=db.dbs.db_mbox).filter(
        "term", private=False
    )
    s.aggs.bucket("per_list", "terms", field="list_raw", size=limit)

    res = await db.search(
        index=db.dbs.db_mbox, body=s.to_dict(), size=0
    )

    for ml in res["aggregations"]["per_list"]["buckets"]:
        list_name = ml["key"].strip("<>").replace(".", "@", 1)
        lists[list_name] = {
            "count": 0,   # We'll sort this later
            "private": False,
        }

    # Get 90 day activity, if any
    s = Search(using=db.client, index=db.dbs.db_mbox)
    s = s.filter('range', date = {'gte': ACTIVITY_TIMESPAN})
    s.aggs.bucket("per_list", "terms", field="list_raw", size=limit)

    res = await db.search(
        index=db.dbs.db_mbox, body=s.to_dict(), size=0
    )

    for ml in res["aggregations"]["per_list"]["buckets"]:
        list_name = ml["key"].strip("<>").replace(".", "@", 1)
        if list_name in lists:
            lists[list_name]["count"] = ml["doc_count"]

    await db.client.close()

    return lists


async def get_public_activity(database: plugins.configuration.DBConfig) -> dict:
    """

    :param database: a PyPony database configuration
    :return: A dictionary with activity stats
    """
    db = plugins.database.Database(database)

    # Fetch aggregations of all public emails
    s = (
        Search(using=db, index=db.dbs.db_mbox)
        .query("match", private=False)
        .filter("range", date={"lt": "now+1d", "gt": "now-14d"})
    )

    s.aggs.bucket("number_of_lists", "cardinality", field="list_raw")
    s.aggs.bucket("number_of_senders", "cardinality", field="from_raw")
    s.aggs.bucket(
        "daily_emails", "date_histogram", field="date", calendar_interval="1d"
    )

    res = await db.search(
        index=db.dbs.db_mbox, body=s.to_dict(), size=0
    )

    no_emails = res["hits"]["total"]["value"]
    no_lists = res["aggregations"]["number_of_lists"]["value"]
    no_senders = res["aggregations"]["number_of_senders"]["value"]
    daily_emails = []
    for entry in res["aggregations"]["daily_emails"]["buckets"]:
        daily_emails.append((entry["key"], entry["doc_count"]))

    # Now the nitty gritty thread count
    seen_emails = {}
    seen_topics = []
    thread_count = 0

    s = (
        Search(using=db.client, index=db.dbs.db_mbox)
        .query("match", private=False)
        .filter("range", date={"lt": "now+1d", "gt": "now-14d"})
    )
    async for docs in db.scan(
        index=db.dbs.db_mbox,
        query=s.to_dict(),
        _source_includes=[
            "message-id",
            "in-reply-to",
            "subject",
            "references",
            "epoch",
            "list_raw",
        ],
    ):

        for doc in docs:
            found = False
            
            message_id = doc["_source"].get("message-id")
            irt = doc["_source"].get("in-reply-to")
            references = doc["_source"].get("references")
            list_raw = doc["_source"].get("list_raw", "_")
            subject = doc["_source"].get("subject", "_")
            if irt and irt in seen_emails:
                seen_emails[message_id] = irt
                found = True
            elif references:
                for refid in re.split(r"\s+", references):
                    if refid in seen_emails:
                        seen_emails[message_id] = refid
                        found = True
            if not found:
                subject = PYPONY_RE_PREFIX.sub("", subject)
                subject += list_raw
                if subject in seen_topics:
                    seen_emails[message_id] = subject
                else:
                    seen_topics.append(subject)
                    thread_count += 1

    await db.client.close()

    activity = {
        "hits": no_emails,
        "no_threads": thread_count,
        "no_active_lists": no_lists,
        "participants": no_senders,
        "activity": daily_emails,
    }

    return activity

async def get_data(server: plugins.server.BaseServer):
    """
    Fetches the data once.
    This is a separate function so it can be invoked on demand.
    """
    async with ProgTimer("Gathering list of archived mailing lists"):
        try:
            server.data.lists = await get_lists(server.config.database)
            print(f"Found {len(server.data.lists)} lists")
        except plugins.database.DBError as e:
            print("Could not fetch lists - database down or not connected: %s" % e)
    async with ProgTimer("Gathering bi-weekly activity stats"):
        try:
            server.data.activity = await get_public_activity(server.config.database)
        except plugins.database.DBError as e:
            print(
                "Could not fetch activity data - database down or not connected: %s"
                % e
            )

async def run_tasks(server: plugins.server.BaseServer) -> None:
    """
        Runs long-lived background data gathering tasks such as gathering statistics about email activity and the list
        of archived mailing lists, for populating the pony mail main index.

        Generally runs every 2½ minutes, or whatever is set in tasks/refresh_rate in ponymail.yaml
    """

    # Initial setup
    server.library_version = ".".join([str(v) for v in ES_VERSION])
    db = plugins.database.Database(server.config.database)
    server.engine_version = (await db.info())['version']['number']
    await db.client.close()

    while True:
        await get_data(server)
        try:
            await asyncio.wait_for(server.background_event.wait(), timeout=server.config.tasks.refresh_rate)
            break # if the event is set, then we have been asked to stop
        except asyncio.TimeoutError:
            pass # This is normal
