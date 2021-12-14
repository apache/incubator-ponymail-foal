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
Google OAuth plugin:
Requires ponymail.yaml to have an oauth section like so:

oauth:
  google_client_id:    your-client-id-here

"""
import google.auth.transport.urllib3 # type: ignore
import google.oauth2.id_token # type: ignore
import plugins.server
import plugins.session
import typing
import urllib3


async def process(formdata: dict, _session, server: plugins.server.BaseServer) -> typing.Optional[dict]:
    js: typing.Optional[dict] = None
    request = google.auth.transport.urllib3.Request(urllib3.PoolManager())
    # This is a synchronous process, so we offload it to an async runner in order to let the main loop continue.
    id_info = await server.runners.run(
        google.oauth2.id_token.verify_oauth2_token,
        formdata.get("id_token"),
        request,
        server.config.oauth.google_client_id,
    )

    if id_info and "email" in id_info:
        js = {
            "email": id_info["email"],
            "name": id_info["email"],
            "oauth_domain": "www.googleapis.com",
        }
    return js
