# Generic OAuth plugin
import re
import requests


async def process(formdata, session, server):
    js = None
    m = re.match(r"https?://(.+)/", formdata["oauth_token"])
    if m:
        oauth_domain = m.group(1)
        headers = {"User-Agent": "Pony Mail OAuth Agent/0.1"}
        # This is a synchronous process, so we offload it to an async runner in order to let the main loop continue.
        rv = await server.runners.run(
            requests.post, formdata["oauth_token"], headers=headers, data=formdata
        )
        js = rv.json()
        js["oauth_domain"] = oauth_domain
        js["authoritative"] = True
    return js
