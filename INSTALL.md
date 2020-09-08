# Installation instructions

<!-- toc -->

- [Basic requirements](#basic-requirements)
- [Installation steps:](#installation-steps)
- [Archiving new emails via Postfix or the likes](#archiving-new-emails-via-postfix-or-the-likes)
- [Setting up OAuth](#setting-up-oauth)
  * [Setting up Google OAuth](#setting-up-google-oauth)
  * [Setting up GitHub OAuth](#setting-up-github-oauth)

<!-- tocstop -->

## Basic requirements
- Linux or other UNIX-like operating system
- ElastichSearch 6.x or higher (7.x recommended) installed
- Python 3.7.3 or higher
- PipEnv program (typically `apt install pipenv` or `yum install pipenv` etc)
- A web server of your choice with proxy capabilities

## Installation steps:

- Clone the Foal git repository to your machine: `git clone https://github.com/apache/incubator-ponymail-foal.git foal`
- Install the Python requirements for the setup:
~~~shell script
cd foal/
pipenv install -r requirements.txt
~~~
- Run the setup process:
~~~shell script
cd tools/
python3 setup.py
cd ..
~~~
- Import any mailboxes you need to, using `tools/import-mbox.py`
- Install the server requirements:
~~~shell script
cd server/
pipenv install -r requirements.txt
~~~
- start the server:
~~~shell script
pipenv run python3 main.py
~~~


## Archiving new emails via Postfix or the likes
To set up archiving, the easiest path is to edit your `/etc/aliases` file on the machine
that receives email. If your receiving address for email is `inbox@yourmachine.tld`, your 
alias entry should look like this:
~~~text
inbox: "| /path/to/foal/tools/archiver.py"
~~~

Once you have added the entry, be sure to run the `newaliases` command to update the compiled alias list.
`archiver.py` will automatically sort out which list the email is for, if there is a List-ID header.
You can override or manually set a list using the `--lid` flag:
~~~text
inbox-somealias: "| /path/to/foal/tools/archiver.py --lid somealias@mydomain.tld"
~~~

## Setting up OAuth
By default, OAuth is enabled for the following providers:

- Google
- GitHub
- Generic (like oauth.apache.org)

None of these are marked as _authoritative_ by default. Authoritative OAuth domains 
allow users to compose emails via the UI and see private emails (unless you reshape the 
AAA plugin). Non-authoritative domains only allows the user to log in, nothing more.

To set an OAuth provider as authoritative, you need to add or uncomment the 
`authoritative_domains` section of the `oauth` configuration in `server/ponymail.yaml`:

~~~yaml
oauth:
  authoritative_domains:
    - googleapis.com
    - myoauthprovider.tld
~~~

Currently, you will also need to enable or tweak your `webui/js/config.js` file to match your 
choice of OAuth providers, though that is subject to change.

### Setting up Google OAuth
To begin using Google OAuth, you must procure an OAUth2 client id from the 
[Gooogle Developers Console](https://console.developers.google.com/apis/credentials/oauthclient/).
Callback URL must be oauth.html in your webui installation.

Once you have a `Client ID`, you should set it in `server/ponymail.yaml`  in the 
`google_client_id` directive. You will also need to currently set it in `webui/js/config.js`.

After this is done, OAuth should work with Google, and you may enable authoritativeness by adding 
`googleapis.com` to the `authoritative_domains` section in `server/ponymail.yaml`.

### Setting up GitHub OAuth
To begin using GitHub OAuth, create an OAuth app at the 
[GitHub Developer Console](https://github.com/settings/developers).
Callback URL must be oauth.html in your webui installation.

Once you have created your OAuth app, copy the client ID and client secret to your 
`server/ponymail.yaml` oauth section, as `github_client_id` and `github_client_secret` 
respectively.

When you've done that, you must currently also edit `webui/js/config.js` and set the 
`client_id` for GitHub to the correct value.
