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

import http.server
import json

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print(self)
        self.send_response(405)
        self.end_headers()

    def do_POST(self):
        print(self.path)
        print(self.headers)
        print("++++++++")
        print(self.rfile.read1())
        print("--------")
        self.send_response(200)
        self.end_headers()
        ret = {
          "hits" : {
            "total" : 0,
            "hits" : [ ]
          },
          "aggregations" : {
              "listnames" : {
                  "buckets" : []
              }
          }
        }

        self.wfile.write(json.dumps(ret).encode('utf-8'))

# Bind to the local address only.
server_address = ('127.0.0.1', 9200)
httpd = http.server.HTTPServer(server_address, Handler)
httpd.serve_forever() 

