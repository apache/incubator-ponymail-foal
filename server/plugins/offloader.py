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

"""Offloading library for pushing heavy tasks to sub threads"""

import asyncio
import concurrent.futures

DEBUG = False


class ExecutorPool:
    """A pool of runners for offloading blocking processes to threads, so that async processing can continue"""

    def __init__(self, threads=None):
        # If no thread count is specified, will default to: min(32, os.cpu_count() + 4)
        self.threads = concurrent.futures.ThreadPoolExecutor(max_workers=threads)

    async def run(self, func, *args, **kwargs):
        if DEBUG:
            print("[Runner] initiating runner")
        runner = self.threads.submit(func, *args, **kwargs)
        if DEBUG:
            print("[Runner] Waiting for task %r to finish" % func)
        while runner.running():
            await asyncio.sleep(0.01)
        try:
            rv = runner.result()
        except Exception as e:
            rv = e
        if DEBUG:
            print("[Runner] Done with task %r, put runner back in queue" % func)
        if isinstance(rv, BaseException):
            if DEBUG:
                print("[Runner] Task %r encountered an exception during run." % func)
            raise rv
        return rv
