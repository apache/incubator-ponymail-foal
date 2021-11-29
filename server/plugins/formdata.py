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

import io
import json
import urllib.parse

import aiohttp.web
import multipart

PYPONY_MAX_PAYLOAD_KB = 256
PYPONY_MAX_PAYLOAD = PYPONY_MAX_PAYLOAD_KB * 1024
ERRONEOUS_PAYLOAD = "Erroneous payload received"


async def parse_formdata(body_type, request: aiohttp.web.BaseRequest) -> dict:
    # Start with query string data for seeding our data dictionary
    indata = {k: v for k, v in request.query.items()}

    # PUT/POST form data?
    if request.method in ["PUT", "POST"]:
        if request.can_read_body:
            try:
                if (
                    request.content_length
                    and request.content_length > PYPONY_MAX_PAYLOAD
                ):
                    raise ValueError("Form data payload too large, max %dkb allowed" % PYPONY_MAX_PAYLOAD_KB)
                body = await request.text()
                if body_type == "json":
                    try:
                        js = json.loads(body)
                        assert isinstance(
                            js, dict
                        )  # json data MUST be an dictionary object, {...}
                        indata.update(js)
                    except ValueError as e:
                        raise ValueError(ERRONEOUS_PAYLOAD) from e
                elif body_type == "form":
                    if (
                        request.headers.get("content-type", "").lower()
                        == "application/x-www-form-urlencoded"
                    ):
                        try:
                            for key, val in urllib.parse.parse_qsl(body):
                                indata[key] = val
                        except ValueError as e:
                            raise ValueError(ERRONEOUS_PAYLOAD) from e
                    # If multipart, turn our body into a BytesIO object and use multipart on it
                    elif (
                        "multipart/form-data"
                        in request.headers.get("content-type", "").lower()
                    ):
                        fh = request.headers.get("content-type", "" )
                        fb = fh.find("boundary=")
                        if fb > 0:
                            boundary = fh[fb + 9 :]
                            if boundary:
                                try:
                                    for part in multipart.MultipartParser(
                                        io.BytesIO(body.encode("utf-8")),
                                        boundary,
                                        len(body),
                                    ):
                                        indata[part.name] = part.value
                                except ValueError as e:
                                    raise ValueError(ERRONEOUS_PAYLOAD) from e
            finally:
                pass
    return indata
