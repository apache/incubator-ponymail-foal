#!/usr/bin/env python3

import sys
import email
import gzip
from email.policy import default
from email.policy import compat32

class MyHeaderClass(email.headerregistry.UnstructuredHeader):
    @classmethod
    def parse(cls, value, kwds):
#         print("Input:" + value)
        super().parse(value.lstrip(), kwds)
#         print(kwds)

# print(default.header_factory)
policy = default.clone()
policy.header_factory.map_to_type('references', MyHeaderClass)
policy.header_factory.map_to_type('message-id', MyHeaderClass)

def process(f):
    msg = email.message_from_binary_file(f, policy=policy)
    # N.B. This may repeat keys
    for key,val in msg.items():
        print()
        print(key, val)

for file in sys.argv[1:]:
    print(file)
    if file.find(".gz") != -1:
        with gzip.open(file,'rb') as gp:
            process(gp)
    else:
        with open(file, 'rb') as fp:
            process(fp)
