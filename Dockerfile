FROM python:slim

RUN pip install py7zr
RUN pip install argparse

RUN mkdir /roms
WORKDIR /roms

COPY prune.py /

ENTRYPOINT [ "python", "/prune.py" ]
