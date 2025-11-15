# Ghiseul.ro monitor

An easy way to monitor if an institution is accessible on [ghiseul.ro](https://ghiseul.ro). The script uses
[Selenium](https://www.selenium.dev/) with ChromeDriver to login to Ghiseul and check if that particular user can make a
payment to the institution you want to monitor. The output of the check is exposed over HTTP
using Flask (port `8080` by default).

## Installation

### Docker

Just pull the docker image and pass the proper environment variables or CLI arguments. You can also build your own
image using the `Dockerfile`. Maybe in the future I'll create a basic Helm chart for Kubernetes.

```bash
docker pull ghcr.io/bzzzm/ghiseul-monitor
docker run -it -p 8080:8080 --env-file .env ghiseul-monitor
```

### Ol' way

1. Clone this repo
2. Create an virtualenv with `python3 -m virtualenv .venv`
3. Install requirements with `python3 -m pip install -r requirements.txt`
4. Run it with `python3 main.py --username=blabla --password=secret --institution=1234` or create an `.env` file

## FAQ

### How do I get the institution ID?

1. Login into your account and wait for the page to load.
2. Using DevTools in Chrome (or your favorite browser), inspect the "Suma de plata" button for the particular
institution. The ID of the element should be something like `showDebiteBtn_ID`. That number at the end is what you
are looking for.

### How do I add the output in Uptime Kuma?

Here is a configured check in [Uptime Kuma](https://uptimekuma.org/).

![Screenshot](https://i.imgur.com/aHfhStB.png)

### Can I fork/modify?

Be my guest. If you think this script is missing some functionality that others can use, please make a PR.

### Is this supported by ghiseul.ro?

No, I have no affiliation with ghiseul.ro. To be honest I haven't even read the
[Terms and Conditions](https://www.ghiseul.ro/ghiseul/public/informatii/termenisiconditii) to make sure that using this
script is allowed. Probably not, so use at your OWN risk.

### How do I... ?

First try to run the script with `--help`, maybe that will give you the info you need. If not, open an issue, but I
won't promise I will monitor these or answer in a reasonable time.

## TODO

- [ ] Add support for `X-Forwarded-For`
- [ ] Add interation number in the output
- [ ] Specify timezone in the `date` key of the output
