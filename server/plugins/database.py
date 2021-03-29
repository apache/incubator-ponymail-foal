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
This is the Database library stub for Pony Mail codename Foal
"""

import uuid
import typing
import elasticsearch

import plugins.configuration
import plugins.defuzzer


class DBNames:
    def __init__(self, dbprefix):
        self.mbox = f"{dbprefix}-mbox"
        self.source = f"{dbprefix}-source"
        self.attachment = f"{dbprefix}-attachment"
        self.account = f"{dbprefix}-account"
        self.session = f"{dbprefix}-session"
        self.notification = f"{dbprefix}-notification"
        self.auditlog = f"{dbprefix}-auditlog"


DBError = elasticsearch.ElasticsearchException


class Database:
    client: elasticsearch.AsyncElasticsearch
    config: plugins.configuration.DBConfig
    dbs: DBNames

    def __init__(self, config: plugins.configuration.DBConfig):
        self.config = config
        self.uuid = str(uuid.uuid4())
        self.dbs = DBNames(config.db_prefix)
        if self.config.dburl:
            self.client = elasticsearch.AsyncElasticsearch([self.config.dburl, ])
        else:
            self.client = elasticsearch.AsyncElasticsearch(
                [
                    {
                        "host": config.hostname,
                        "port": config.port,
                        "url_prefix": config.url_prefix or "",
                        "use_ssl": config.secure,
                    },
                ]
            )

    async def search(self, index="", **kwargs):
        if not index:
            index = self.dbs.mbox
        res = await self.client.search(index=index, **kwargs)
        return res

    async def get(self, index="", **kwargs):
        if not index:
            index = self.dbs.mbox
        res = await self.client.get(index=index, **kwargs)
        return res

    async def delete(self, index="", **kwargs):
        if not index:
            index = self.dbs.session
        res = await self.client.delete(index=index, **kwargs)
        return res

    async def index(self, index="", **kwargs):
        if not index:
            index = self.dbs.session
        res = await self.client.index(index=index, **kwargs)
        return res

    async def scan(self,
                   query=None,
                   scroll="5m",
                   preserve_order=False,
                   size=1000,
                   request_timeout=None,
                   clear_scroll=True,
                   scroll_kwargs=None,
                   **kwargs) -> typing.AsyncIterator[dict]:
        
        scroll_kwargs = scroll_kwargs or {}

        if not preserve_order:
            query = query.copy() if query else {}
            query["sort"] = "_doc"

        # Do the search
        resp = await self.search(
            body=query, scroll=scroll, size=size, request_timeout=request_timeout, **kwargs
        )
        scroll_id = resp.get("_scroll_id")

        # While we can scroll, fetch a page
        try:
            while scroll_id and resp["hits"]["hits"]:
                for hit in resp["hits"]["hits"]:
                    yield hit
                resp = await self.client.scroll(
                    body={"scroll_id": scroll_id, "scroll": scroll}, **scroll_kwargs
                )
                scroll_id = resp.get("_scroll_id")

        # Shut down and clear scroll once done
        finally:
            if scroll_id and clear_scroll:
                await self.client.clear_scroll(body={"scroll_id": [scroll_id]}, ignore=(404,))
