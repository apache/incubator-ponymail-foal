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

"""Endpoint for sending emails to the list via the UI"""
import plugins.server
import plugins.session
import email.message
import email.utils
import email.header
import aiosmtplib
import fnmatch
import typing
import aiohttp.web
import uuid

COMPOSER_VERSION = "0.4"  # Bump when changing logic

async def process(
    server: plugins.server.BaseServer,
    session: plugins.session.SessionObject,
    indata: dict,
) -> typing.Union[dict, aiohttp.web.Response]:

    if not server.config.ui.mailhost:
        return {"error": "This server has not been set up for sending email yet."}

    # Figure out outgoing MTA
    mailhost = server.config.ui.mailhost
    mailport = 25
    if ":" in mailhost:
        mailhost, _mailport = mailhost.split(":", 1)
        mailport = int(_mailport)

    # Figure out if recipient list is on allowed list
    to = indata.get("to", "")
    mldomain = to.strip("<>").split("@")[-1]
    allowed_to_send = False
    for allowed_domain in server.config.ui.sender_domains.split(" "):
        if fnmatch.fnmatch(mldomain, allowed_domain):
            allowed_to_send = True
            break
    if not allowed_to_send:
        return {"error": "Recipient mailing list is not an allowed recipient for emails via the web."}

    # If logged in and everything, prep for dispatch
    if session.credentials and session.credentials.authoritative:
        subject = indata.get("subject")
        body = indata.get("body")
        irt = indata.get("in-reply-to")
        references = indata.get("references")

        if to and subject and body:
            msg = email.message.EmailMessage()
            if irt:
                msg["In-reply-to"] = irt
            if references:
                msg["References"] = references
            msg["From"] = email.utils.formataddr(
                (str(email.header.Header(session.credentials.name, "utf-8")), session.credentials.email)
            )
            msg["To"] = to
            msg["Subject"] = str(email.header.Header(subject, "utf-8"))
            msg["Date"] = email.utils.formatdate()
            msg["Message-ID"] = f"<pony-{str(uuid.uuid4())}-{to}>"
            msg["User-Agent"] = "Apache Pony Mail Foal Composer v/%s" % COMPOSER_VERSION
            msg.set_charset("utf-8")
            msg.set_content(body)
            await aiosmtplib.send(msg, hostname=mailhost, port=mailport)
            return {"okay": True, "message": "Message dispatched!"}
        else:
            return {"error": "You need to fill out both recipient, subject and text body."}
    else:
        return {"error": "You need to be logged in via an authoritative source to send emails."}


def register(server: plugins.server.BaseServer):
    return plugins.server.Endpoint(process)
