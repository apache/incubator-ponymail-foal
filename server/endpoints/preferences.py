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
import plugins.session
import aiohttp.web
import typing
import fnmatch

""" Generic preferences endpoint for Pony Mail codename Foal"""
""" This is incomplete, but will work for anonymous tests. """


async def process(
    server: plugins.server.BaseServer, session: plugins.session.SessionObject, indata: dict
) -> typing.Union[dict, aiohttp.web.Response]:

    versions: dict = {
        "foal": server.foal_version,
    }

    # Require login for this info
    if session.credentials and session.credentials.authoritative:
        versions["server"] = server.server_version
        if session.credentials.admin:
            versions["elasticsearch_engine"] = server.engine_version
            versions["elasticsearch_library"] = server.library_version

    prefs: dict = {"login": {}}
    prefs['versions'] = versions
    lists: dict = {}
    for ml, entry in server.data.lists.items():
        if "@" in ml:
            lname, ldomain = ml.split("@", 1)
            can_access = True
            if entry.get("private", True):
                can_access = plugins.aaa.can_access_list(session, ml)
            if server.config.ui.focus_domain != "*":
                if '*' in server.config.ui.focus_domain:
                    if not fnmatch.fnmatch(ldomain, server.config.ui.focus_domain):
                        continue
                elif ldomain != (server.config.ui.focus_domain or session.host):
                    continue
            if can_access:
                if ldomain not in lists:
                    lists[ldomain] = {}
                lists[ldomain][lname] = entry["count"]
    prefs["lists"] = lists
    if session and session.credentials:
        prefs["login"] = {
            "credentials": {
                "uid": session.credentials.uid,
                "email": session.credentials.email,
                "fullname": session.credentials.name,
            }
        }
        if session.credentials.admin is True:
            prefs["login"]["credentials"]["admin"] = True
            if server.config.ui.fully_delete:  # Needed by the UI
                prefs["login"]["credentials"]["fully_delete"] = True

    # Logging out??
    if indata.get("logout"):
        # Remove session from ElasticSearch
        await plugins.session.remove_session(session)

        # If stored in memory, remove from there.
        if session.cookie in server.data.sessions:
            del server.data.sessions[session.cookie]
        session.credentials = None
        return aiohttp.web.Response(
            headers={
                "set-cookie": "ponymail=deleted; path=/api; expires=Thu, 01 Jan 1970 00:00:00 GMT",
                "content-type": "application/json",
            },
            status=200,
            text='{"okay": true}',
        )

    return prefs


def register(server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
