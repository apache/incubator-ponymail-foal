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

import base64
import hashlib
import sys

import plugins.generators_old

try:
    import blake3
except ImportError:
    if sys.version_info >= (3, 10):
        if "blake3" not in hashlib.algorithms_available:
            raise RuntimeError("BLAKE3 is not supported")

        def blake3_context_160(lid: str, message: bytes) -> bytes:
            h = hashlib.blake3(message, derive_key_context=lid)
            return h.digest(length=160 // 8)

    else:
        raise RuntimeError("BLAKE3 is not supported")
else:

    def blake3_context_160(lid: str, message: bytes) -> bytes:
        if "`context`" in blake3.blake3.__doc__:
            # NOTE: Can be removed when blake3 0.1.9 or 0.2.0 is published
            h = blake3.blake3(message, context=lid)
        else:
            h = blake3.blake3(message, derive_key_context=lid)
        return h.digest(length=160 // 8)


def pibble32(data: bytes) -> str:
    r"""
    Base32 encodes bytes with alphabet 0-9 b-d f-h j-t v-z.

    >>> pibble32(b"\xca\xfe\xc0\xff\xee")
    'sczd1zzg'
    """
    table: bytes = bytes.maketrans(
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567",
        b"0123456789bcdfghjklmnopqrstvwxyz",
    )
    encoded: bytes = base64.b32encode(data)
    return str(encoded.translate(table), "ascii")


def blakey(_msg, _body, lid, _attachments, raw_msg):
    r"""
    BLAKE3 generator: uses lid and message source
    Has 160 bit security

    Parameters:
    _msg - the parsed message (not used)
    _body - the parsed text content (not used)
    lid - list id
    _attachments - list of attachments (not used)
    raw_msg - the original message bytes

    Returns: str "<blake3>", a 32 lower char custom base32 encoded digest

    >>> blakey(None, None, "", None, b"")
    'gj81364o27jfff9568s0v7pvfj6yy2oq'
    """
    # The digest is 160 bits (i.e. 20 bytes)
    digest: bytes = blake3_context_160(lid, raw_msg)
    # The pibble32 encoded digest is 256 bits (i.e. 32 bytes)
    # But still only has 160 bit security
    return pibble32(digest)


# Full generator: uses the entire email (including server-dependent data)
# Used by default until August 2020.
# See 'blakey' for recommended generation.
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
    'blakey': blakey,
    'dkim': plugins.generators_old.dkim,
    'full': full,
    'medium': plugins.generators_old.medium,
    'cluster': plugins.generators_old.cluster,
    'legacy': plugins.generators_old.legacy,
}


def generator(name):
    try:
        return __GENERATORS[name]
    except KeyError:
        print("WARN: generator %s not found, defaulting to 'legacy'" % name)
        return legacy


def generate(name, msg, body, lid, attachments, raw_msg):
    return generator(name)(msg, body, lid, attachments, raw_msg)


def generator_names():
    return list(__GENERATORS)
