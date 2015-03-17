#!/usr/bin/env python
# encoding: utf-8

from datetime import datetime
from operator import getitem
import logging

import bottle
import requests
from jsonschema.validators import Draft4Validator as Validator
from jsonschema.exceptions import ValidationError

app = bottle.default_app()
logger = logging.getLogger(__name__)


class RequstData(object):
    validator = Validator({
        "definitions": {
            "argumentfield": {
                "type": "object"
            }
        },
        "type": "object",
        "required": ["meta"],
        "properties": {
            "meta": {
                "$ref": "#/definitions/argumentfield",
                "method": {
                    "type": "string",
                    "oneOf": ["get", "post", "put", "delete"],
                },
                "url": {
                    "type": "string"
                },
                "timeout": "integer",
            },
            "headers": {
                "$ref": "#/definitions/argumentfield"
            },
            "data": {
                "oneOf": [
                    {"forms": {
                        "$ref": "#/definitions/argumentfield"
                    }},
                    {"json": {
                        "$ref": "#/definitions/argumentfield"
                    }},
                ]
            },
        }
    })

    def __init__(self, data):
        self.validator.validate(data)
        self.data = data

    def get(self, *keys):
        return reduce(getitem, keys, self.data)

    def try_get(self, keys, default=None):
        try:
            return self.get(*keys)
        except KeyError:
            return default

    @property
    def url(self):
        return self.get("meta", "url")

    @property
    def headers(self):
        return self.try_get(["headers"], {})

    @property
    def forms(self):
        return self.try_get(["data", "forms"], None)

    @property
    def json(self):
        return self.try_get(["data", "json"], None)


def proxyhdr(f):
    def to_response(*args, **kw):
        result = f(*args, **kw)

        return result.content
    return to_response


@proxyhdr
def get_proxy(data):
    return requests.get(data.url, headers=data.headers)


def proxy_hdr(data):
    method = data.get("meta", "method")
    hdr_map = {
        "get": get_proxy,
    }
    hdr = hdr_map[method]
    return hdr(data)


@app.post("/proxy")
def proxy():
    try:
        data = RequstData(bottle.request.json)
    except ValueError as err:
        bottle.abort(400, str(err))
    except ValidationError as err:
        bottle.abort(400, "/%s: %s" % ("/".join(err.path), err.message))

    return proxy_hdr(data)


@app.route("/")
def index():
    now = datetime.now()
    return now.isoformat()


if __name__ == "__main__":
    import sys
    _, host, port = sys.argv
    bottle.run(app, host=host, port=int(port))
