FROM php:8.5-apache

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev \
    && docker-php-ext-install pdo_pgsql \
    && a2enmod rewrite \
    && rm -rf /var/lib/apt/lists/*

COPY deploy/apache.conf /etc/apache2/sites-available/000-default.conf
RUN printf 'Listen 10000\n' > /etc/apache2/ports.conf \
    && install -d -o www-data -g www-data -m 0700 /var/www/logs

COPY app/ /var/www/app/
COPY web/ /var/www/web/
COPY deploy/index.php /var/www/web/index.php

EXPOSE 10000
