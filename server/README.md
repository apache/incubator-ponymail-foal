# Pony Mail Foal - Backend UI Server

This is the (as of yet incomplete) backedn server for the Foal UI.
While it works on all-public archives with searching, threads, emails
and sources, the AAA (Access, Authentication and Authorization) plugin 
is not yet complete, in part due to waiting for OAuth to be completed.

This backend should not yet be used for private email archives unless 
restricted behind some form of external/parent authentication mechanism.


## How to run:
- Install the Pony Mail service through `tools/setup.py` first. 
  This will create a ponymail.yaml for the backend server as well
- install `pipenv`, for example via aptitude: `apt install pipenv`.
- Install the environment for the server: `pipenv install -r requirements.txt`
- Run the server: `pipenv run python3 main.py`

This should fire up a backend server on 127.0.0.1:8080. You can then proxy to 
that using a web server of your choice. The `/api/` URL of your online archive 
should be passed straight to the backend, while the rest should be served from 
the `webui/` directory in this repository.

An example Apache HTTPd configuration could be (for plain-text HTTP):

```
<VirtualHost *:80>
    ServerName archives.example.com        
    ServerAdmin webmaster@localhost
    DocumentRoot /var/www/foal/webui/
    ProxyPass /api/ http://localhost:8080/api/
    <Directory /var/www/foal/webui/>
        Require all granted
    </Directory>
</VirtualHost>
``` 

