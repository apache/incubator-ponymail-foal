#!/usr/bin/env python3

import sys
import email
import gzip
from email.policy import default

class MyHeaderClass(email.headerregistry.UnstructuredHeader):
    @classmethod
    def parse(cls, value, kwds):
        print("Input:" + value)
        super().parse(value.lstrip(), kwds)
        print(kwds)

# print(default.header_factory)
policy = default.clone()
policy.header_factory.map_to_type('references', MyHeaderClass)
policy.header_factory.map_to_type('message-id', MyHeaderClass)

def process(f):
    msg = email.message_from_binary_file(f, policy=policy)

    # print(msg.defects)
    # for item in msg.raw_items():
    #     print(item)
    # N.B. This may repeat keys
    for key,val in msg.items():
        print()
        print(key)
        print(val.__class__)
        print(val.defects)
        print(val)
        # for k,v in email.header.decode_header(val):
        #     if v is None or v.find("8bit") != -1:
        #         if isinstance(k, bytes):
        #             print([key, k,v])
        #             sys.exit(1)
        #     else:
        #         print([key,k,v])
        #         sys.exit(1)
        # print(val.defects)
        # print(val.__class__)
        # if isinstance(val, email.headerregistry.AddressHeader):
        #     for addr in val.addresses:
        #         print(addr)
        # else:

for file in sys.argv[1:]:
    print(file)
    if file.find(".gz") != -1:
        with gzip.open(file,'rb') as gp:
            process(gp)
    else:
        with open(file, 'rb') as fp:
            process(fp)
