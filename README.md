# stadsarkiv-client

## Install for development

    git clone https://github.com/aarhusstadsarkiv/stadsarkiv-client.git

    cd stadsarkiv-client

    virtualenv venv # Python >= 3.10.6 should work   

    source venv/bin/activate

Or (Windows)

    source venv/Scripts/activate

Install requirements:

    pip install -r requirements.txt

## Run for development

    python -m stadsarkiv_client server-dev

Or (shortcut): 

    ./bin/server-dev.sh

## Install as requirement

    virtualenv venv

    source venv/bin/activate

Update version and install latest version:

    pip uninstall -y stadsarkiv-client
    pip install git+https://github.com/aarhusstadsarkiv/stadsarkiv-client@main

You may also install a specific version:

    pip install git+https://github.com/aarhusstadsarkiv/stadsarkiv-client@version

## Run required module

For development:

    server-dev

Options 

    server-dev --help

Usage: server-dev [OPTIONS]

  Start the running Gunicorn dev-server.

Options:
  --port INTEGER     Server port.
  --workers INTEGER  Number of workers.
  --host TEXT        Server host.
  --help             Show this message and exit.

Start or restart (stop and start) for production:

    server-prod

Stop server:

    server-stop

## Modifying the required module

You may override the default module using the following files and dirs:

    .env
    settings.py
    language.py
    hooks.py
    templates/
    static/

All the above files and dirs are optional. You may see examples of all the above files in the 
[example-config directory](https://github.com/aarhusstadsarkiv/stadsarkiv-client/tree/main/example-config)
(These files are well documented)

These files and dirs should be placed in the directory where you run the module from - otherwise they will be ignored.

## Fix code

Run black, mypy and flake8:

    ./bin/fix.sh
