# Installation instructions

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
