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
This file contains the various newer generation ID generators for Pony Mail's archivers.
For older ID generators, see generators_old.py
"""

import hashlib

if not __package__:
    import dkim_id
else:
    from . import dkim_id

# DKIM-ID generator: uses DKIM canonicalisation
# Recommended as default for clusters
def dkimid(_msg, _body, lid, _attachments, raw_msg):
    r"""
    DKIM-ID generator: truncated SHA-256 HMAC if DKIM input
    We use the headers recommended in RFC 4871, plus DKIM-Signature

    Parameters:
    _msg - the parsed message (not used)
    _body - the parsed text content (not used)
    lid - list id
    _attachments - list of attachments (not used)
    raw_msg - the original message bytes

    Returns: str "<dkimid>", a 32 lower char base32 encoded SHA-256 HMAC

    >>> dkimid(None, None, None, None, b"")
    '8fgp2do75oqo6qd08vs4p7dpp1gj4vjn'
    """
    if isinstance(lid, str):
        lid = lid.encode("utf-8", errors="replace")
    return dkim_id.dkim_id(raw_msg, lid)


# Full generator: uses the entire email (including server-dependent data)
# Used by default until August 2020.
# See 'dkim' for recommended generation.
def full(msg, _body, lid, _attachments, _raw_msg):
    """
    Full generator: uses the entire email
    (including server-dependent data)
    The id is almost certainly unique,
    but different copies of the message are likely to have different headers, thus ids
    WARNING: the archiver by default adds an archived-at header with the current time.
    This is included in the hash, so messages will get different Permalinks if reloaded from source

    Parameters:
    msg - the parsed message
    _body - the parsed text content (not used)
    lid - list id
    _attachments - list of attachments (not used)
    _raw_msg - the original message bytes (not used)

    Returns: "<hash>@<lid>" where hash is sha224 of message bytes
    """
    mid = "%s@%s" % (hashlib.sha224(msg.as_bytes()).hexdigest(), lid)
    return mid


__GENERATORS = {
    'dkim': dkimid,
    'full': full,
}


def generator(name):
    try:
        return __GENERATORS[name]
    except KeyError:
        print("WARN: generator %s not found, defaulting to 'dkim'" % name)
        return dkimid


def generate(name, msg, body, lid, attachments, raw_msg):
    return generator(name)(msg, body, lid, attachments, raw_msg)


def generator_names():
    return list(__GENERATORS)
