# Apify Python SDK base image.
# https://hub.docker.com/r/apify/actor-python
FROM apify/actor-python:3.14

COPY --chown=myuser:myuser requirements.txt ./

RUN echo "Python version:" \
 && python --version \
 && echo "Pip version:" \
 && pip --version \
 && echo "Installing dependencies:" \
 && pip install --no-cache-dir -r requirements.txt \
 && echo "All installed Python packages:" \
 && pip freeze

COPY --chown=myuser:myuser . ./

RUN python -m compileall -q fmcsa_actor/

CMD ["python", "-m", "fmcsa_actor"]
