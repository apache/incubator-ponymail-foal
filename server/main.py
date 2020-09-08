#!/usr/bin/env python3
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

"""Apache Pony Mail, Codename Foal - A Python variant of Pony Mail"""
import argparse
import asyncio
import importlib
import json
import os
import sys
import traceback

import aiohttp.web
import yaml

import plugins.background
import plugins.configuration
import plugins.database
import plugins.formdata
import plugins.offloader
import plugins.server
import plugins.session

PONYMAIL_FOAL_VERSION = "0.1.0"


class Server(plugins.server.BaseServer):
    """Main server class, responsible for handling requests and scheduling offloader threads """

    def __init__(self, args: argparse.Namespace):
        print(
            "==== Apache Pony Mail (Foal v/%s) starting... ====" % PONYMAIL_FOAL_VERSION
        )
        # Load configuration
        yml = yaml.safe_load(open(args.config))
        self.config = plugins.configuration.Configuration(yml)
        self.data = plugins.configuration.InterData()
        self.handlers = dict()
        self.dbpool = asyncio.Queue()
        self.runners = plugins.offloader.ExecutorPool(threads=10)
        self.server = None

        # Make a pool of 15 database connections for async queries
        for _ in range(1, 15):
            self.dbpool.put_nowait(plugins.database.Database(self.config.database))

        # Load each URL endpoint
        for endpoint_file in os.listdir("endpoints"):
            if endpoint_file.endswith(".py"):
                endpoint = endpoint_file[:-3]
                m = importlib.import_module(f"endpoints.{endpoint}")
                if hasattr(m, "register"):
                    self.handlers[endpoint] = m.__getattribute__("register")(self)
                    print(f"Registered endpoint /api/{endpoint}")
                else:
                    print(
                        f"Could not find entry point 'register()' in {endpoint_file}, skipping!"
                    )

    async def handle_request(
        self, request: aiohttp.web.BaseRequest
    ) -> aiohttp.web.Response:
        """Generic handler for all incoming HTTP requests"""
        resp: aiohttp.web.Response

        # Define response headers first...
        headers = {
            "Server": "PyPony/%s" % PONYMAIL_FOAL_VERSION,
        }

        # Figure out who is going to handle this request, if any
        # We are backwards compatible with the old Lua interface URLs
        body_type = "form"
        handler = request.path.split("/")[-1]
        if handler.endswith(".lua"):
            body_type = "form"
            handler = handler[:-4]
        if handler.endswith(".json"):
            body_type = "json"
            handler = handler[:-5]

        # Parse form data if any
        try:
            indata = await plugins.formdata.parse_formdata(body_type, request)
        except ValueError as e:
            return aiohttp.web.Response(headers=headers, status=400, text=str(e))

        # Find a handler, or 404
        if handler in self.handlers:
            session = await plugins.session.get_session(self, request)
            try:
                # Wait for endpoint response. This is typically JSON in case of success,
                # but could be an exception (that needs a traceback) OR
                # it could be a custom response, which we just pass along to the client.
                output = await self.handlers[handler].exec(self, session, indata)
                if session.database:
                    self.dbpool.put_nowait(session.database)
                    self.dbpool.task_done()
                    session.database = None
                headers["content-type"] = "application/json"
                if output and not isinstance(output, aiohttp.web.Response):
                    jsout = await self.runners.run(json.dumps, output, indent=2)
                    headers["Content-Length"] = str(len(jsout))
                    return aiohttp.web.Response(headers=headers, status=200, text=jsout)
                elif isinstance(output, aiohttp.web.Response):
                    return output
                else:
                    return aiohttp.web.Response(
                        headers=headers, status=404, text="Content not found"
                    )
            except:
                if session.database:
                    self.dbpool.put_nowait(session.database)
                    self.dbpool.task_done()
                    session.database = None
                exc_type, exc_value, exc_traceback = sys.exc_info()
                err = "\n".join(
                    traceback.format_exception(exc_type, exc_value, exc_traceback)
                )
                return aiohttp.web.Response(
                    headers=headers, status=500, text="API error occurred: " + err
                )
        else:
            return aiohttp.web.Response(
                headers=headers, status=404, text="API Endpoint not found!"
            )

    async def server_loop(self, loop: asyncio.AbstractEventLoop):  # Note, loop never used.
        self.server = aiohttp.web.Server(self.handle_request)
        runner = aiohttp.web.ServerRunner(self.server)
        await runner.setup()
        site = aiohttp.web.TCPSite(
            runner, self.config.server.ip, self.config.server.port
        )
        await site.start()
        print(
            "==== Serving up Pony goodness at %s:%s ===="
            % (self.config.server.ip, self.config.server.port)
        )
        await plugins.background.run_tasks(self)

    def run(self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.server_loop(loop))
        except KeyboardInterrupt:
            pass
        loop.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        help="Configuration file to load (default: ponymail.yaml)",
        default="ponymail.yaml",
    )
    cliargs = parser.parse_args()
    pubsub_server = Server(cliargs)
    pubsub_server.run()
