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
import elasticsearch.exceptions

import plugins.configuration


class Timeout (elasticsearch.exceptions.ConnectionTimeout):
    """Database timeout exception"""


class DBNames:
    def __init__(self, dbprefix):
        self.db_mbox = f"{dbprefix}-mbox"
        self.db_source = f"{dbprefix}-source"
        self.db_attachment = f"{dbprefix}-attachment"
        self.db_account = f"{dbprefix}-account"
        self.db_session = f"{dbprefix}-session"
        self.db_notification = f"{dbprefix}-notification"
        self.db_auditlog = f"{dbprefix}-auditlog"


DBError = elasticsearch.ElasticsearchException


class Database:
    client: elasticsearch.AsyncElasticsearch
    config: plugins.configuration.DBConfig
    dbs: DBNames
    uuid: str

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
            index = self.dbs.db_mbox
        try:
            res = await self.client.search(index=index, **kwargs)
            return res
        except elasticsearch.exceptions.ConnectionTimeout as e:
            raise Timeout(e)

    async def get(self, index="", **kwargs):
        if not index:
            index = self.dbs.db_mbox
        res = await self.client.get(index=index, **kwargs)
        return res

    async def delete(self, index="", **kwargs):
        if not index:
            index = self.dbs.db_session
        res = await self.client.delete(index=index, **kwargs)
        return res

    async def index(self, index="", **kwargs):
        if not index:
            index = self.dbs.db_session
        res = await self.client.index(index=index, **kwargs)
        return res

    async def create(self, index=None, **kwargs):
        """Create a new document (put if missing)"""
        res = await self.client.create(index=index, **kwargs)
        return res

    async def info(self, **kwargs):
        """Get ES info"""
        res = await self.client.info(**kwargs)
        return res

    async def update(self, index="", **kwargs):
        if not index:
            index = self.dbs.db_session
        res = await self.client.update(index=index, **kwargs)
        return res

    async def scan(self,
                   query: dict = None,
                   scroll: str = "5m",
                   preserve_order: bool = False,
                   size: int = 1000,
                   request_timeout: int = 60,
                   clear_scroll: bool = True,
                   scroll_kwargs: dict = None,
                   **kwargs) -> typing.AsyncIterator[typing.List[dict]]:
        
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
                yield resp["hits"]["hits"]
                resp = await self.client.scroll(
                    body={"scroll_id": scroll_id, "scroll": scroll}, **scroll_kwargs
                )
                scroll_id = resp.get("_scroll_id")

        # Shut down and clear scroll once done
        finally:
            if scroll_id and clear_scroll:
                await self.client.clear_scroll(body={"scroll_id": [scroll_id]}, ignore=(404,))
