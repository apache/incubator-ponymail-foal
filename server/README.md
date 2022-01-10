# Pony Mail Foal - Backend UI Server

This is the (as of yet incomplete) backend server for the Foal UI.

## Progress

### What works
- The "phone book" (front page)
- Browsing threads on a list
- Viewing single threads, emails and sources
- Searching with keywords, quotes, +/- inclusion/exclusion
- Rudimentary AAA (logged in with an authoritative OAuth gives read access to everyting)
- Persistent user sessions across restarts of the server
- OAuth logins (Google, Github + Generic for now)
- Composing replies
- Mbox downloads

### What doesn't work
- Preferences
- Notifications/favorites


While rudimentary AAA works, the backend should not yet be used for private 
email archives unless restricted behind some form of external/parent 
authentication mechanism.


## How to run:
See the [Installation documentation](https://github.com/apache/incubator-ponymail-foal/blob/master/INSTALL.md) 
for instructions on how to install Foal.

Once followed, this should fire up a backend server on 127.0.0.1:8080. You can then proxy to 
that using a web server of your choice. The `/api/` URL of your online archive 
should be passed straight to the backend, while the rest should be served from 
the `webui/` directory in this repository.

An example Apache HTTPd configuration could be (for plain-text HTTP):

```
<VirtualHost *:80>
    ServerName archives.example.com        
    ServerAdmin webmaster@localhost
    DocumentRoot /var/www/foal/webui/
    # PathInfo is needed for threads
    AcceptPathInfo On
    # Also needed for threads to be able to handle message-ids with embedded /:
    AllowEncodedSlashes On # (or NoDecode)
    ProxyPass /api/ http://localhost:8080/api/
    <Directory /var/www/foal/webui/>
        Require all granted
        # MultiViews means you can shorten threads to https://localhost/thread/blablabla
        Options +MultiViews
    </Directory>
</VirtualHost>
``` 

