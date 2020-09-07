# Google OAuth plugin
import plugins.server
import plugins.session

import requests
from google.oauth2 import id_token
from google.auth.transport import requests


async def process(formdata, session, server: plugins.server.BaseServer):
    js = None
    request = requests.Request()

    id_info = await server.runners.run(id_token.verify_oauth2_token,
                                       formdata.get("id_token"),
                                       request,
                                       server.config.oauth.google_client_id
                                       )

    if id_info and "email" in id_info:
        js = {
            "email": id_info["email"],
            "name": id_info["email"],
            "oauth_domain": "www.googleapis.com",
        }
    return js
