#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
    bulk-edit.py: mbox bulk editor for Apache Pony Mail (Foal)

    Examples:
        - Move all email from <foo.bar.example.org> to <bar.baz.example.org>:
            python3 bulk-edit.py --search 'list_raw:"<foo.bar.example.org>"' --action move --destination "<bar.baz.example.org>"
        - Make all emails from gnome@example.org private:
            python3 bulk-edit.py --search 'from:"<gnome@example.org>"' --action private
        - Delete all emails on foo@bar.example.org with 'gnomes' in the subject:
           python3 bulk-edit.py --search 'list_raw:"<foo.bar.example.org>" AND subject:gnomes' --action delete

    Be sure to always run your query with --test first, to see which documents would be affected!
"""

import elasticsearch.exceptions
import sys
import asyncio
import argparse
import time
import re
import warnings
from elasticsearch.helpers import async_scan


if not __package__:
    from plugins import ponymailconfig
    from plugins.elastic import Elastic
else:
    from .plugins import ponymailconfig
    from .plugins.elastic import Elastic


def gen_args() -> argparse.Namespace:
    """Generate/parse CLI arguments"""
    parser = argparse.ArgumentParser(description="Command line options.")
    parser.add_argument(
        "--search",
        dest="search",
        nargs=1,
        help="""Search parameters (Lucene query string) to narrow down what to edit (for instance: 'list_raw:"<dev.maven.apache.org>"')""",
        default="*",
    ),
    parser.add_argument(
        "--action",
        dest="action",
        type=str,
        choices=["move", "delete", "private", "public", "list"],
        help="The action to perform on each matching document",
        default="list",
    )
    parser.add_argument(
        "--destination",
        dest="destination",
        type=str,
        help="If action is 'move', this sets the destination list-id to move the matching documents to",
        default="",
    ),
    parser.add_argument(
        "--test",
        dest="test",
        action="store_true",
        help="Test mode, only scan database and report, but do not make any changes to it.",
    )
    parser.add_argument(
        "--warn",
        dest="warn",
        action="store_true",
        help="Enable ElasticSearch Warnings (defaults to disabled to suppress xpack nonsense)",
        default=False,
    )
    args = parser.parse_args()
    return args


async def main():
    start_time = time.time()
    args = gen_args()
    config = ponymailconfig.PonymailConfig()
    es = Elastic(is_async=True)
    if not args.warn:
        warnings.filterwarnings("ignore", category=elasticsearch.exceptions.ElasticsearchWarning)
    docs_changed = 0
    if args.action == "move":
        if not re.match(r"<([-a-z0-9_]+\.?)+>", args.destination):
            sys.stderr.write("ERROR: Destination list (--destination) MUST be using the <foo.bar.baz> format!\n")
            exit(-1)

    async for doc in async_scan(client=es.es, q=args.search, index=es.db_mbox):
        source = doc["_source"]
        if args.action == "list":
            docs_changed += 1
            subject = source["subject"].replace("\n", "")
            print(f"""found: {doc['_id']} {source['list_raw']}: {subject}""")
        elif args.action == "move":
            if args.test:
                print(f"""[TEST] Would have moved {source["mid"]} from {source["list_raw"]} to {args.destination}""")
            else:
                sys.stdout.write(
                    f"""[MOVE] Moving {source["mid"]} from {source["list_raw"]} to {args.destination}..."""
                )
                sys.stdout.flush()
                await es.es.update(
                    index=es.db_mbox,
                    id=doc["_id"],
                    body={
                        "doc": {
                            "list": args.destination,
                            "list_raw": args.destination,
                        }
                    },
                )
                sys.stdout.write(" [DONE]\n")
                sys.stdout.flush()
            docs_changed += 1
        elif args.action == "private":
            if not source["private"]:
                if args.test:
                    print(f"""[TEST] Would have made {source["mid"]} from {source["list_raw"]} private""")
                else:
                    sys.stdout.write(f"""[HIDE] Turning {source["mid"]} from {source["list_raw"]} private...""")
                    sys.stdout.flush()
                    await es.es.update(
                        index=es.db_mbox,
                        id=doc["_id"],
                        body={
                            "doc": {
                                "private": True,
                            }
                        },
                    )
                    sys.stdout.write(" [DONE]\n")
                    sys.stdout.flush()
                docs_changed += 1
        elif args.action == "public":
            if source["private"]:
                if args.test:
                    print(f"""[TEST] Would have made {source["mid"]} from {source["list_raw"]} public""")
                else:
                    sys.stdout.write(f"""[SHOW] Turning {source["mid"]} from {source["list_raw"]} public...""")
                    sys.stdout.flush()
                    await es.es.update(
                        index=es.db_mbox,
                        id=doc["_id"],
                        body={
                            "doc": {
                                "private": False,
                            }
                        },
                    )
                    sys.stdout.write(" [DONE]\n")
                    sys.stdout.flush()
                docs_changed += 1
        elif args.action == "delete":
            if args.test:
                print(
                    f"""[TEST] Would have deleted {source["mid"]} (and source {source["dbid"]}) from {source["list_raw"]}"""
                )
            else:
                sys.stdout.write(
                    f"""[DELETE] Removing {source["mid"]} (and source {source["dbid"]}) from {source["list_raw"]}..."""
                )
                sys.stdout.flush()
                await es.es.delete(
                    index=es.db_mbox,
                    id=doc["_id"],
                )
                await es.es.delete(
                    index=es.db_source,
                    id=source["dbid"],
                )
                sys.stdout.write(" [DONE]\n")
                sys.stdout.flush()
            docs_changed += 1
    stop_time = time.time()
    time_taken = int(stop_time - start_time)
    print(f"Handled {docs_changed} document(s) in {time_taken} second(s).")
    await es.es.close()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
