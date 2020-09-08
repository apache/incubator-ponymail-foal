"""
Google OAuth plugin:
Requires ponymail.yaml to have an oauth section like so:

oauth:
  google_client_id:    your-client-id-here

"""
import google.auth.transport.requests
import google.oauth2.id_token
import plugins.server
import plugins.session


async def process(formdata, session, server: plugins.server.BaseServer):
    js = None
    request = google.auth.transport.requests.Request()
    id_info = await server.runners.run(
        google.oauth2.id_token.verify_oauth2_token,
        formdata.get("id_token"),
        request,
        server.config.oauth.google_client_id,
    )

    if id_info and "email" in id_info:
        js = {
            "email": id_info["email"],
            "name": id_info["email"],
            "oauth_domain": "www.googleapis.com",
        }
    return js
