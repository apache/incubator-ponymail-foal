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
import typing

from . import generators_old

# For optional nonce
config: typing.Optional[dict] = None

# Headers from RFC 4871, the precursor to RFC 6376
rfc4871_subset = {
    b"from", b"sender", b"reply-to", b"subject", b"date",
    b"message-id", b"to", b"cc", b"mime-version", b"content-type",
    b"content-transfer-encoding", b"content-id",
    b"content-description", b"resent-date", b"resent-from",
    b"resent-sender", b"resent-to", b"resent-cc",
    b"resent-message-id", b"in-reply-to", b"references", b"list-id",
    b"list-help", b"list-unsubscribe", b"list-subscribe",
    b"list-post", b"list-owner", b"list-archive", b"dkim-signature"
}

# Authenticity headers from RFC 8617
rfc4871_and_rfc8617_subset = rfc4871_subset | {
    b"arc-authentication-results", b"arc-message-signature",
    b"arc-seal"
}


def rfc822_parse_dkim(suffix,
                      head_canon=False, body_canon=False,
                      head_subset=None, archive_list_id=None):
    headers = []
    keep = True
    list_ids = set()

    while suffix:
        # Edge case: headers don't end LF (add LF)
        line, suffix = (suffix.split(b"\n", 1) + [b""])[:2]
        if line in {b"\r", b""}:
            break
        end = b"\n" if line.endswith(b"\r") else b"\r\n"
        if line[0] in {0x09, 0x20}:
            # Edge case: starts with a continuation (treat like From)
            if headers and (keep is True):
                headers[-1][1] += line + end
        elif not line.startswith(b"From "):
            # Edge case: header start contains no colon (use whole line)
            # "A field-name MUST be contained on one line." (RFC 822 B.2)
            k, v = (line.split(b":", 1) + [b""])[:2]
            k_lower = k.lower()
            if k_lower == "list-id":
                list_ids.add(k_lower)
            if (head_subset is None) or (k_lower in head_subset):
                keep = True
                headers.append([k, v + end])
            else:
                keep = False
    # The remaining suffix is the body
    body = suffix.replace(b"\r\n", b"\n")
    body = body.replace(b"\n", b"\r\n")

    # Optional X-Archive-List-ID augmentation
    if (archive_list_id is not None) and (archive_list_id not in list_ids):
        xali_value = b" " + bytes(archive_list_id, "ascii")
        headers.append([b"X-Archive-List-ID", xali_value])
    # Optional nonce from local config
    if config is not None:
        if (config.get("archiver") and
                config['archiver'].get('nonce')):
            nonce = config['archiver'].get('nonce')
            headers.append([b"X-Archive-Nonce", nonce])
    # Optional head canonicalisation (DKIM relaxed)
    if head_canon is True:
        for i in range(len(headers)):
            k, v = headers[i]
            crlf = v.endswith(b"\r\n")
            if crlf is True:
                v = v[:-2]
            v = v.replace(b"\r\n", b"")
            v = v.replace(b"\t", b" ")
            v = v.strip(b" ")
            v = b" ".join(vv for vv in v.split(b" ") if vv)
            if crlf is True:
                v = v + b"\r\n"
            headers[i] = [k.lower(), v]
    # Optional body canonicalisation (DKIM simple)
    if body_canon is True:
        while body.endswith(b"\r\n\r\n"):
            body = body[:-2]
    return (headers, body)


def pibble(hashable, size=10):
    table = bytes.maketrans(
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567",
        b"0123456789bcdfghjklmnopqrstvwxyz",
    )
    digest = hashlib.sha3_256(hashable).digest()
    prefix = digest[:size]
    encoded = base64.b32encode(prefix)
    return str(encoded.translate(table), "ascii")


# DKIM generator: uses DKIM canonicalisation
# Used by default
def dkim(_msg, _body, lid, _attachments, raw_msg):
    """
    DKIM generator: uses DKIM relaxed/simple canonicalisation
    We use the headers recommended in RFC 4871, plus DKIM-Signature

    Parameters:
    _msg - the parsed message (not used)
    _body - the parsed text content (not used)
    lid - list id
    _attachments - list of attachments (not used)
    raw_msg - the original message bytes

    Returns: str "<pibble>", a sixteen char custom base32 encoded hash
    """
    headers, body = rfc822_parse_dkim(raw_msg,
                                      head_canon=True, body_canon=True,
                                      head_subset=rfc4871_subset, archive_list_id=lid)
    hashable = b"".join([h for header in headers for h in header])
    if body:
        hashable += b"\r\n" + body
    # The pibble is the 80-bit SHA3-256 prefix
    # It is base32 encoded using 0-9 a-z except [aeiu]
    return pibble(hashable)


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
    'dkim': dkim,
    'full': full,
    'medium': generators_old.medium,
    'cluster': generators_old.cluster,
    'legacy': generators_old.legacy,
}


def generator(name):
    try:
        return __GENERATORS[name]
    except KeyError:
        print("WARN: generator %s not found, defaulting to 'legacy'" % name)
        return plugins.generators_old.legacy


def generate(name, msg, body, lid, attachments, raw_msg):
    return generator(name)(msg, body, lid, attachments, raw_msg)


def generator_names():
    return list(__GENERATORS)
