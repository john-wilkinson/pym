
import requests

from os import path
from bs4 import BeautifulSoup

from . import exceptions


URL = "https://pypi.python.org/pypi"

def find_download_url(package_name, version=""):
    """

    :param pacakge_name:
    :param version:
    :return:
    """
    print(package_name)
    print(version)
    url = "{}/{}/{}".format(URL, package_name, version)
    print(url)
    page = requests.get(url)
    if page.status_code != 200:
        raise exceptions.PackageUrlException('Failed to fetch page {} (status code {})'.format(url, page.status_code))

    soup = BeautifulSoup(page.content, 'html.parser')
    for link in soup.select('body a'):
        if link.string and link.string.endswith('.whl'):
            return link['href']
    raise exceptions.PackageUrlException('Failed to find package for {}@{}'.format(package_name, version))


def download_file(url, dest):
    local_filename, _, _ = url.split('/')[-1].partition('#')
    dest = path.join(dest, local_filename)
    # NOTE the stream=True parameter
    r = requests.get(url, stream=True)
    with open(dest, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): 
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
                #f.flush() commented by recommendation from J.F.Sebastian
    return dest
