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


DBError = elasticsearch.ElasticsearchException


class Database:
    client: elasticsearch.AsyncElasticsearch
    config: plugins.configuration.DBConfig
    dbs: DBNames

    def __init__(self, config: plugins.configuration.DBConfig):
        self.config = config
        self.uuid = str(uuid.uuid4())
        self.dbs = DBNames(config.db_prefix)
        self.client = elasticsearch.AsyncElasticsearch(
            [
                {
                    "host": config.hostname,
                    "port": config.port,
                    "url_prefix": config.url_prefix,
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
