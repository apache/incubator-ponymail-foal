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

# Generic OAuth plugin
import re
import typing
import aiohttp.client


async def process(formdata: dict, _session, _server) -> typing.Optional[dict]:
    # Extract domain, allowing for :port
    # Does not handle user/password prefix etc
    m = re.match(r"https?://([^/:]+)(?::\d+)?/", formdata["oauth_token"])
    if m:
        oauth_domain = m.group(1)
        headers = {"User-Agent": "Pony Mail OAuth Agent/0.1"}
        # This is a synchronous process, so we offload it to an async runner in order to let the main loop continue.
        async with aiohttp.client.request("POST", formdata["oauth_token"], headers=headers, data=formdata) as rv:
            js = await rv.json()
            js["oauth_domain"] = oauth_domain
        return js
    return None