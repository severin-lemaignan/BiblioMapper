Requirements
------------

- `pypdf2`
- `cerminer`
- `pdftotxt`
- `imagemagik` (`convert`)
- `flask`
- `anystyle` (for references parsing)
- Python bindings for `crossref`


Starting the app
----------------





Requires Flask (`sudo apt install python3-flask`).

To start the server:

```
export FLASK_APP=app.py
flask run
```

During dev, for hot-reload:

```
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```
