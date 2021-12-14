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

"""
    Github OAuth plugin.
    This follows the workflow described at: https://developer.github.com/apps/building-oauth-apps/authorizing-oauth-apps
    To make this work, please set up an application at https://github.com/settings/applications/
    copy the client ID and secret to your ponymail.yaml's oauth configuration, as such:
    oauth:
      github_client_id: abcdef123456
      github_client_secret: bcfdgefa572564576
"""

import aiohttp.client
import plugins.server
import typing


async def process(formdata: dict, _session, server: plugins.server.BaseServer) -> typing.Optional[dict]:
    formdata["client_id"] = server.config.oauth.github_client_id
    formdata["client_secret"] = server.config.oauth.github_client_secret
    headers = {"Accept": "application/json"}
    async with aiohttp.client.request(
        "POST", "https://github.com/login/oauth/access_token", headers=headers, data=formdata
    ) as rv:
        resp = await rv.json()
        if "access_token" in resp:
            async with aiohttp.client.request(
                "GET", "https://api.github.com/user", headers={"authorization": "token %s" % resp["access_token"]}
            ) as orv:
                js = await orv.json()
                js["oauth_domain"] = "github.com"
                # Full name and email address might not always be available to us. Fake it till you make it.
                js["name"] = js.get("name", js["login"])
                js["email"] = js.get("email", "%s@users.github.com" % js["login"])
                return js
    return None
