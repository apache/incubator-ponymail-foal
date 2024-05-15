FROM ubuntu:24.04

ENV \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && \
    DEBIAN_FRONTEND='noninteractive' apt-get install -y \
    curl git vim apache2 apache2-dev python3-pip

RUN curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor -o /usr/share/keyrings/elastic.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/elastic.gpg] https://artifacts.elastic.co/packages/7.x/apt stable main" | tee -a /etc/apt/sources.list.d/elastic-7.x.list
RUN apt-get update && \
    DEBIAN_FRONTEND='noninteractive' apt-get install -y \
    elasticsearch

RUN \
    a2enmod cgi && \
    a2enmod headers && \
    a2enmod rewrite && \
    a2enmod authnz_ldap && \
    a2enmod speling && \
    a2enmod remoteip && \
    a2enmod expires && \
    a2enmod proxy_http && \
    echo "ServerName pmfoal.local" > /etc/apache2/conf-enabled/servername.conf

COPY server/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt  --break-system-packages
COPY tools/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt  --break-system-packages

COPY docker-config/pmfoal.conf /etc/apache2/sites-enabled/000-default.conf

# Allow access to ES from host node
RUN echo "network.host: 0.0.0.0\ndiscovery.type: single-node" >> /etc/elasticsearch/elasticsearch.yml

# Add new items at the end so previous layers can be re-used

WORKDIR /var/www/ponymail

CMD /etc/init.d/elasticsearch start; apache2ctl -DFOREGROUND
