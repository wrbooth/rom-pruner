FROM python:slim

RUN pip install py7zr
RUN pip install argparse

COPY prune.py /

RUN mkdir /roms
WORKDIR /roms

ENTRYPOINT [ "python", "/prune.py" ]
