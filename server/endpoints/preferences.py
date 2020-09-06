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

import plugins.server
import plugins.aaa

""" Generic preferences endpoint for Pony Mail codename Foal"""
""" This is incomplete, but will work for anonymous tests. """

async def process(
    server: plugins.server.BaseServer, session: dict, indata: dict
) -> dict:
    prefs = {"login": {}}
    lists = {}
    for ml, entry in server.data.lists.items():
        if "@" in ml:
            lname, ldomain = ml.split("@", 1)
            can_access = True
            if entry.get("private", False):
                can_access = plugins.aaa.can_access_list(session, ml)
            if can_access:
                if ldomain not in lists:
                    lists[ldomain] = {}
                lists[ldomain][lname] = entry["count"]
    prefs["lists"] = lists

    return prefs


def register(server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
