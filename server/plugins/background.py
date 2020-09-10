import asyncio
import datetime
import re
import sys
import time

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_scan
from elasticsearch_dsl import Search

import plugins.configuration
import plugins.server
import plugins.database

PYPONY_RE_PREFIX = re.compile(r"^([a-zA-Z]+:\s*)+")


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
    client = AsyncElasticsearch(
        [
            {
                "host": database.hostname,
                "port": database.port,
                "url_prefix": database.url_prefix,
                "use_ssl": database.secure,
            },
        ]
    )

    # Fetch aggregations of all public emails
    s = Search(using=client, index=database.db_prefix + "-mbox").query(
        "match", private=False
    )
    s.aggs.bucket("per_list", "terms", field="list_raw")


    res = await client.search(
        index=database.db_prefix + "-mbox", body=s.to_dict(), size=0
    )

    for ml in res["aggregations"]["per_list"]["buckets"]:
        list_name = ml["key"].strip("<>").replace(".", "@", 1)
        lists[list_name] = {
            "count": ml["doc_count"],
            "private": False,
        }

    # Ditto, for private emails
    s = Search(using=client, index=database.db_prefix + "-mbox").query(
        "match", private=True
    )
    s.aggs.bucket("per_list", "terms", field="list_raw")

    res = await client.search(
        index=database.db_prefix + "-mbox", body=s.to_dict(), size=0
    )

    for ml in res["aggregations"]["per_list"]["buckets"]:
        list_name = ml["key"].strip("<>").replace(".", "@", 1)
        lists[list_name] = {
            "count": ml["doc_count"],
            "private": True,
        }
    await client.close()

    return lists


async def get_public_activity(database: plugins.configuration.DBConfig) -> dict:
    """

    :param database: a PyPony database configuration
    :return: A dictionary with activity stats
    """
    client = AsyncElasticsearch(
        [
            {
                "host": database.hostname,
                "port": database.port,
                "url_prefix": database.url_prefix,
                "use_ssl": database.secure,
            },
        ]
    )

    # Fetch aggregations of all public emails
    s = (
        Search(using=client, index=database.db_prefix + "-mbox")
        .query("match", private=False)
        .filter("range", date={"lt": "now+1d", "gt": "now-14d"})
    )

    s.aggs.bucket("number_of_lists", "cardinality", field="list_raw")
    s.aggs.bucket("number_of_senders", "cardinality", field="from_raw")
    s.aggs.bucket(
        "daily_emails", "date_histogram", field="date", calendar_interval="1d"
    )

    res = await client.search(
        index=database.db_prefix + "-mbox", body=s.to_dict(), size=0
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
        Search(using=client, index=database.db_prefix + "-mbox")
        .query("match", private=False)
        .filter("range", date={"lt": "now+1d", "gt": "now-14d"})
    )
    async for doc in async_scan(
        index=database.db_prefix + "-mbox",
        client=client,
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

    await client.close()

    activity = {
        "hits": no_emails,
        "no_threads": thread_count,
        "no_active_lists": no_lists,
        "participants": no_senders,
        "activity": daily_emails,
    }

    return activity


async def run_tasks(server: plugins.server.BaseServer):
    """
        Runs long-lived background data gathering tasks such as gathering statistics about email activity and the list
        of archived mailing lists, for populating the pony mail main index.

        Generally runs every 2½ minutes, or whatever is set in tasks/refresh_rate in ponymail.yaml
    """
    while True:
        async with ProgTimer("Gathering list of archived mailing lists"):
            try:
                server.data.lists = await get_lists(server.config.database)
            except plugins.database.DBError:
                print("Could not fetch lists - database down or not connected?!")
        async with ProgTimer("Gathering bi-weekly activity stats"):
            try:
                server.data.activity = await get_public_activity(server.config.database)
            except plugins.database.DBError:
                print("Could not fetch activity data - database down or not connected?!")
        await asyncio.sleep(server.config.tasks.refresh_rate)
