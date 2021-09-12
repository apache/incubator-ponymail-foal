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

"""Auxiliary text modding library for Apache Pony Mail (Foal)"""

import re
import typing

def normalize_lid(lid: str, strict: bool = False) -> str:
    """ Ensures that a List ID is in standard form, i.e. <a.b.c.d> """
    # If of format "list name" <foo.bar.baz>
    # we crop away the description (#511)
    m = re.match(r'".*"\s+(.+)', lid)
    if m:
        lid = m.group(1)
    # Drop <> and anything before/after, if found
    m = re.search(r"<(.+)>", lid)
    if m:
        lid = m.group(1)
    # Belt-and-braces: remove possible extraneous chars, ensure @s are converted to dots
    lid = "<%s>" % lid.strip(" <>").replace("@", ".")
    # Replace invalid characters with underscores so as to not invalidate doc IDs.
    lid = re.sub(r"[^-+~_<>.a-zA-Z0-9@]", "_", lid)
    # Finally, ensure we have a loosely valid list ID value
    if strict and not re.match(r"^<.+\..+>$", lid):
        print("Invalid list-id %s" % lid)
        return None
    return lid
