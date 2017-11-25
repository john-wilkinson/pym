
import requests

from os import path

from . import exceptions

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
