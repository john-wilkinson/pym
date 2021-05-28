# Not Functional

As wheel packaging has changed since this was written, and the pypi package locations have also moved, this project is not currently functional.

# pym
A python package manager for creating and using local-scoped packages

Pym is very similar to Npm in behavior.

When you install packages, by default it puts them under a `pym_packages` directory in your project repository.

![](https://raw.githubusercontent.com/john-wilkinson/pym/master/docs/usage.gif)

## Setup

To setup pym, clone the repo and run the python setup tool in the cloned repo:

```
python setup.py install
```

## Create Project

To create a pym project, run in the project directory:

```
pym init
```

This creates a `pym.json` file acting as your project manifest in your current directory.

## Install Packages

To install packages (only git and wheels are supported right now):

```
pym install tornado
```

```
pym install https://github.com/tornadoweb/tornado.git
```

For pypi, a particular version can be specified by using `@<version>`

```
pym install tornado@4.5.2
```

For git, particular tag, checkout, or branch can be specified by putting a `#` with the modifier after the repo url.

```
pym install https://github.com/tornadoweb/tornado.git#v4.5.2
```

The `--save` flag can be added to save it to your project's `pym.json` manifest.

Running  `pym install` in a project location will install all of its dependencies.

The installation process will create a `pym.json` file in each dependency as it is installed, if one does not exist.

## Using the packages

In your code, run `import pym` at the top of your application. That will allow you to import all the packages you have installed locally.

Ex:

```
import pym
import tornado.ioloop
import tornado.web

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
```
