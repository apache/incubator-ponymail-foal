"""
    Github OAuth plugin.
    This follows the workflow described at: https://developer.github.com/apps/building-oauth-apps/authorizing-oauth-apps
    To make this work, please set up an application at https://github.com/settings/applications/
    copy the client ID and secret to your ponymail.yaml's oauth configuration, as such:
    oauth:
      github_client_id: abcdef123456
      github_client_secret: bcfdgefa572564576
"""

import re
import requests
import plugins.server
import typing


async def process(formdata, session, server: plugins.server.BaseServer) -> typing.Optional[dict]:
    formdata['client_id'] = server.config.oauth.github_client_id
    formdata['client_secret'] = server.config.oauth.github_client_secret

    rv = await server.runners.run(requests.post, 'https://github.com/login/oauth/access_token', data=formdata)
    m = re.search(r"(access_token=[a-f0-9]+)", rv.text)

    if m:
        rv = await server.runners.run(requests.get, "https://api.github.com/user?%s" % m.group(1))
        js = rv.json()
        js["oauth_domain"] = "github.com"
        return js
    return None
