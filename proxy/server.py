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
                    "enum": ["get", "post", "put", "delete"],
                },
                "url": {
                    "type": "string"
                },
                "timeout": "integer",
                "post_type": {
                    "enum": ["form", "json"]
                },
            },
            "headers": {
                "$ref": "#/definitions/argumentfield"
            },
            "data": {
                "$ref": "#/definitions/argumentfield",
            },
            "body": {
                "type": "string",
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


def proxyhdr(f):
    def to_response(*args, **kw):
        try:
            result = f(*args, **kw)
        except Exception as err:
            bottle.abort(500, str(err))

        headers = {
            "set-cookie", "content-type"}

        for k, v in result.headers.iteritems():
            if k in headers:
                bottle.response.add_header(k, v)

        bottle.response.status = result.status_code

        return result.content
    return to_response


@proxyhdr
def get_proxy(data):
    return requests.get(
        data.url,
        headers=data.headers,
        timeout=data.try_get(["meta", "timeout"], 10))


@proxyhdr
def post_proxy(data):
    form_data = None
    json_data = None
    post_type = data.try_get(["meta", "post_type"])

    if post_type == "form":
        form_data = data.try_get(["data"])
    elif post_type == "json":
        json_data = data.try_get(["data"])

    return requests.post(
        data.url,
        headers=data.headers,
        data=form_data,
        json=json_data)


def proxy_hdr(data):
    method = data.get("meta", "method")
    hdr_map = {
        "get": get_proxy,
        "post": post_proxy,
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
