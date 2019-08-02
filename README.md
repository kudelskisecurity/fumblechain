# FumbleChain: A Purposefully Vulnerable Blockchain

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-green.svg)](https://docs.python.org/3.7/whatsnew/) [![License: GPL v3](https://img.shields.io/badge/license-GPL%20v3-blue.svg)](http://www.gnu.org/licenses/gpl-3.0)

FumbleChain is a deliberately insecure blockchain designed to raise awareness about blockchain security.
The FumbleStore is a CTF in the form of a fake e-commerce web application that offers products you can buy using FumbleCoins, the ecosystem's cryptocurrency.
Purchasing new products requires players to exploit flaws and steal coins from crypto-wallets.

FumbleChain runs on any Unix-based operating system that has Docker installed.

# Why use FumbleChain?

FumbleChain comes with a simple Python3 codebase implementing a Proof-of-work blockchain similar to Bitcoin.
It is bundled with 20+ lessons/tutorials to learn about blockchain security, vulnerabilities and exploitation.
It is fully dockerized and easy to use. Test your skills by solving the challenges in the FumbleStore.
Leverage the embedded blockchain explorer and web or CLI wallet to learn about common blockchain pitfalls.

For more information, visit the FumbleChain microsite at http://fumblechain.io

## Live demo

No time to lose?

An instance of the FumbleStore is available at https://demo.fumblechain.io/ for demonstration purposes.

Note that for a seamless CTF experience, you may want to run the FumbleStore on your own machine.

# Requirements

To run the FumbleStore, you will need:

* Linux or macOS
* git
* docker
* docker-compose

## Installing docker

See https://docs.docker.com/install/linux/docker-ce/ubuntu

## Installing docker-compose

See https://docs.docker.com/compose/install/

# Usage

First, clone the `fumblechain` repository.

It is important to clone the repository with git because the following steps depend on the git history.

Downloading a zip archive of the master branch will not work.

Then checkout the `fumblestore` branch.

```
git clone https://github.com/kudelskisecurity/fumblechain.git
cd fumblechain
git checkout fumblestore
```

Finally start the CTF with:

```
cd src/fumblechain
./init_ctf.sh
```

Startup should take about 3 minutes.

When completed, you can access the CTF interface on http://localhost:20801/

## Deploy the FumbleStore publicly (e.g. on mydomain.com)

Follow the same instructions as above.

Except, configure the `.env` file in the `fumblestore` branch so that the variable `FC_HOST` contains the public domain name/ip address of the environment where you deploy the CTF (for example "mydomain.com").

Also make sure to set `IS_DOCKER_LOCAL` to `0` when deploying the CTF publicly so that it works for clients who connect from another machine.
Configure the application as desired by editing the `.env` file (e.g. enable CAPTCHA for registration).

When done, run `./init_ctf.sh` just as above.

## Debug mode

To run the FumbleStore in debug mode for development, follow these instructions:

Edit `.env` so that

```
DEBUG=1
```

Edit `docker-compose.yml` so that he local bind mount for the `fumblestore` service is active (uncomment the line below the comment that says "# for development")

Disable the captcha (see next section).

## CAPTCHA for user registration

When running the FumbleStore as a public instance, you may want to enable CAPTCHA for user registration to avoid spam.

To do so, edit `.env` so that:

```
RECAPTCHA_ENABLED=1
RECAPTCHA_SITE_KEY=your_site_key
RECAPTCHA_SECRET_KEY=your_secret_key
```

Obtain a site key and secret key for reCAPTCHA v2 here:

https://www.google.com/recaptcha/admin/create

Replace `your_site_key` and `your_secret_key` in the `.env` file as shown above with your own site key and secret key that you obtained from the link above.

# Contributing

Feel free to open a pull request or report bugs.

Ideas for new challenges or lessons are welcome!

The FumbleStore contains lessons about creating new challenges and new lessons.

# Disclaimer

When running this software on your own machine, you may expose yourself to attacks.
We cannot guarantee that the software is bug-free.
Upon starting the FumbleStore, various background services are started.
These services will listen for incoming connections on multiple TCP ports.
Proceed with caution and make sure your firewall rules are properly set.

# License and Copyright

Copyright(c) 2019 Nagravision SA.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License version 3 as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.
