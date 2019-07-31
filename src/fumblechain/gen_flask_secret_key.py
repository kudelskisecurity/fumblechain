#!/usr/bin/env python3

"""Generate a random Flask secret key.
This secret key is used by Flask to sign cookies, for example."""

import base64
import os


def main():
    skey = base64.b64encode(os.urandom(16)).decode("utf-8")

    outfile = "gen/fumblestore_secret_key.env"
    if not os.path.exists(outfile):
        with open(outfile, "w+") as fout:
            print(f"FUMBLESTORE_FLASK_SECRET_KEY={skey}", file=fout)


if __name__ == '__main__':
    main()
