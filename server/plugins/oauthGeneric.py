# Generic OAuth plugin
import re
import requests


def process(formdata, session):
    js = None
    m = re.match(r"https?://(.+)/", formdata["oauth_token"])
    if m:
        oauth_domain = m.group(1)
        headers = {"User-Agent": "Pony Mail OAuth Agent/0.1"}
        rv = requests.post(formdata["oauth_token"], headers=headers, data=formdata)
        # try:
        js = rv.json()
        js["oauth_domain"] = oauth_domain
        js['authoritative'] = True

    return js
