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
    Simple endpoint that does a local login

To enable:
- ensure server/ponymail.yaml contains the following in the oauth section:

oauth:
  ...
  authoritative_domains:
    - localhost
  admins:
    - admin@apache.org

- Add the --testendpoints qualifier to the server startup command
  Alternatively copy the files server/test/testauth.[py|.yaml] to the server/endpoints directory
  They can be renamed if necessary, so long as they have the same basename;
  adjust the URLs below to reflect the new name

- then add the following to config.js under pm_config.oauth:
        user: {
            name: "Test Auth User",
            oauth_portal: "http://localhost/api/testauth",
            oauth_url: "http://localhost/api/testauth"
        },
        admin: {
            name: "Test Auth Admin",
            oauth_portal: "http://localhost/api/testauth",
            oauth_url: "http://localhost/api/testauth"
        },
(This assumes that the test installation is at http://localhost/. Adjust as necessary.)

This will add two extra options to the login screen.
Clicking on either "Test sign in as ..." link will automatically login (without prompting)

The data returned by the login can be changed without restarting: just edit the testauth.yaml file.
"""

import aiohttp
import plugins.server
import typing
import uuid
import yaml

def debug(server, text):
    if server.api_logger:
        server.api_logger.debug(text)

async def process(server: plugins.server.BaseServer, session: dict, indata: dict) -> typing.Union[aiohttp.web.Response, dict]:
    debug(server, f'INDATA {indata}')
    redirect_uri = indata.get('redirect_uri')
    code = indata.get('code')
    if redirect_uri:
        token = str(uuid.uuid4())
        headers = {"Location": f"{redirect_uri}&code={token}"}
        return aiohttp.web.Response(headers=headers, status=302, text="Try here")
    elif code:
        # Try to read companion file
        datafile = __file__.replace('.py', '.yaml')
        debug(server, f'file: {datafile}')
        try:
            data =  yaml.safe_load(open(datafile))['oauth_data']
            debug(server, f'using data from {datafile}')
            # if the user is not provided, use the key
            user = indata.get('user', indata.get('key', 'user'))
            if user in data:
                data = data[user]
                data['state'] = indata.get('state')
                debug(server, f"testauth: {data}")
                return data
            else:
                debug(server, f"Could not find record for {user}")
        except:
           debug(server,  f'Could not find data file {datafile}')
    
    return {"okay": False, "message": "Invalid invocation!"}

def register(server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
